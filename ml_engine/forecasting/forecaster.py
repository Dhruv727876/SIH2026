import copy
import logging
import math
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
import random
import numpy as np
import pandas as pd
import requests

# Enforce global determinism
np.random.seed(42)
random.seed(42)

# In-memory forecast cache to avoid re-fitting Prophet Stan chains on every optimization solve:
# Key: (index_name, disruption_event) -> (timestamp, List[Dict[str, Any]])
_FORECAST_CACHE: Dict[Tuple[str, Optional[str]], Tuple[float, List[Dict[str, Any]]]] = {}
_FORECAST_CACHE_TTL = 900  # 15 minutes


def clear_forecast_cache():
    """Invalidates the forecaster in-memory cache."""
    global _FORECAST_CACHE
    _FORECAST_CACHE.clear()
    logger.info("Forecaster in-memory cache cleared successfully.")


# Add parent directory to path so we can import from data_pipeline
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from data_pipeline.fetch_market_data import generate_synthetic_series, load_kaggle_bdi_data
from data_pipeline.fetch_disruptions import get_disruption_shock_multiplier

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("freight-forecaster")

# Render uses the PORT env var (usually 10000). Fallback to 8000 for local dev.
PORT = os.getenv("PORT", "8000")
API_BASE_URL = os.getenv("API_BASE_URL", f"http://127.0.0.1:{PORT}").rstrip("/")


class FreightForecaster:
    """
    Hybrid Freight & Fuel Rate Forecasting Engine.
    Combines LightGBM for short-term volatility (1-15 days) and Prophet/Holt for long-term (16-60 days),
    incorporating real 25-year historical Kaggle BDI data when available.
    """

    def __init__(self, backend_api_url: Optional[str] = None):
        self.backend_api_url = (backend_api_url or API_BASE_URL).rstrip("/")

    def fetch_historical_data(self, index_name: str, limit: int = 180, db: Optional[Any] = None) -> pd.DataFrame:
        """
        Fetches historical records from DB, Kaggle dataset, backend API, or synthetic fallback.
        """
        # If explicitly asking for Kaggle BDI, load from CSV
        if index_name == "BDI_KAGGLE":
            df_kaggle = load_kaggle_bdi_data()
            if not df_kaggle.empty:
                return df_kaggle

        records: List[Dict[str, Any]] = []

        # 1. First priority: Direct DB Session if running within backend process
        if db is not None:
            try:
                from models.market_data import MarketData
                from sqlalchemy import select
                stmt = (
                    select(MarketData)
                    .where(MarketData.index_name == index_name)
                    .order_by(MarketData.timestamp.desc())
                    .limit(limit)
                )
                db_rows = db.scalars(stmt).all()
                if db_rows and len(db_rows) >= 15:
                    records = [
                        {
                            "timestamp": r.timestamp.isoformat() if hasattr(r.timestamp, "isoformat") else str(r.timestamp),
                            "value": float(r.value),
                            "index_name": r.index_name,
                            "currency": r.currency,
                        }
                        for r in db_rows
                    ]
                    logger.info(f"Retrieved {len(records)} records for {index_name} directly from database.")
            except Exception as e:
                logger.warning(f"Direct DB query for market data failed ({e}).")

        # 2. Only attempt HTTP call if no direct DB provided and not localhost self-call
        if not records and db is None:
            try:
                url = f"{self.backend_api_url}/api/v1/market-data"
                params = {"index_name": index_name, "limit": limit}
                resp = requests.get(url, params=params, timeout=1.5)
                if resp.status_code == 200:
                    records = resp.json()
                    logger.info(f"Retrieved {len(records)} records for {index_name} from backend API.")
            except Exception as e:
                logger.debug(f"Could not connect to backend API ({e}). Using synthetic series fallback.")

        # 3. If backend returned no records, check if Kaggle data exists for generic BDI or generate synthetic
        if len(records) < 15:
            if index_name in ("BDI", "BDI_KAGGLE"):
                df_k = load_kaggle_bdi_data()
                if not df_k.empty:
                    return df_k

            logger.info(f"Generating synthetic historical series for {index_name}...")
            records = generate_synthetic_series(index_name=index_name, days=limit)

        df = pd.DataFrame(records)
        if "timestamp" not in df or "value" not in df:
            raise ValueError(f"Invalid market data format for index {index_name}")

        df["timestamp"] = pd.to_datetime(df["timestamp"])
        if df["timestamp"].dt.tz is not None:
            df["timestamp"] = df["timestamp"].dt.tz_localize(None)
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna(subset=["value"]).sort_values("timestamp").reset_index(drop=True)

        # Resample / forward fill daily gaps
        try:
            df = df.set_index("timestamp").asfreq("D").ffill().bfill().reset_index()
        except Exception:
            df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

        return df

    def _create_lag_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generates lag, rolling window, and temporal features for tree-based modeling.
        """
        df_feat = df.copy()
        for lag in [1, 2, 3, 7, 14, 21, 30]:
            df_feat[f"lag_{lag}"] = df_feat["value"].shift(lag)

        for window in [7, 14, 30]:
            df_feat[f"rolling_mean_{window}"] = df_feat["value"].shift(1).rolling(window=window).mean()
            df_feat[f"rolling_std_{window}"] = df_feat["value"].shift(1).rolling(window=window).std().fillna(0.0)

        df_feat["dayofweek"] = df_feat["timestamp"].dt.dayofweek
        df_feat["month"] = df_feat["timestamp"].dt.month
        return df_feat

    def train_and_predict_short_term(
        self,
        df: pd.DataFrame,
        horizon: int = 15,
    ) -> List[Dict[str, Any]]:
        """
        Trains a gradient-boosted model (LightGBM / Sklearn) or robust autoregressive model
        for short-term (1-15 days) forecasting.
        """
        df_feat = self._create_lag_features(df)
        feature_cols = [c for c in df_feat.columns if c not in ["timestamp", "index_name", "currency", "value", "id"]]

        train_df = df_feat.dropna().reset_index(drop=True)
        if len(train_df) < 10:
            logger.warning("Insufficient training samples. Using autoregressive trend projection.")
            return self._autoregressive_short_term(df, horizon)

        X_train = train_df[feature_cols]
        y_train = train_df["value"]

        model = None
        # Tier 1: Try LightGBM
        try:
            import lightgbm as lgb
            model = lgb.LGBMRegressor(
                n_estimators=100,
                learning_rate=0.05,
                max_depth=4,
                num_leaves=15,
                random_state=42,
                deterministic=True,
                force_row_wise=True,
                n_jobs=1,
                verbosity=-1,
            )
            model.fit(X_train, y_train)
            logger.info("Trained LightGBM regressor for short-term horizon.")
        except Exception as e:
            logger.info(f"LightGBM not available ({e}). Attempting Scikit-Learn...")

        # Tier 2: Try Scikit-Learn
        if model is None:
            try:
                from sklearn.ensemble import GradientBoostingRegressor
                model = GradientBoostingRegressor(n_estimators=80, learning_rate=0.05, max_depth=3, random_state=42)
                model.fit(X_train, y_train)
                logger.info("Trained Scikit-Learn GradientBoostingRegressor for short-term horizon.")
            except Exception as e:
                logger.info(f"Scikit-Learn not available ({e}). Falling back to NumPy Autoregressive Ridge model.")

        # Tier 3: NumPy / OLS Autoregressive Ridge model fallback
        if model is None:
            return self._autoregressive_short_term(df, horizon)

        # Estimate in-sample residual variance for confidence intervals
        in_sample_preds = model.predict(X_train)
        residuals = y_train.values - in_sample_preds
        rmse = float(np.sqrt(np.mean(residuals**2)))
        std_err = max(rmse, float(y_train.std() * 0.05))

        # Iterative recursive forecasting for next `horizon` days
        current_history = df.copy()
        predictions = []
        last_date = df["timestamp"].max()

        for step in range(1, horizon + 1):
            next_date = last_date + timedelta(days=step)
            temp_df = pd.concat([
                current_history,
                pd.DataFrame([{"timestamp": next_date, "value": np.nan}])
            ], ignore_index=True)

            temp_feat = self._create_lag_features(temp_df)
            x_next = temp_feat.iloc[[-1]][feature_cols]

            pred_val = float(model.predict(x_next)[0])
            pred_val = max(1.0, pred_val)

            interval_expansion = 1.0 + (step / horizon) * 0.5
            lower_bound = max(0.5, pred_val - (1.28 * std_err * interval_expansion))
            upper_bound = pred_val + (1.28 * std_err * interval_expansion)

            predictions.append({
                "timestamp": next_date.strftime("%Y-%m-%d"),
                "predicted_value": round(float(pred_val), 2),
                "lower_bound": round(float(lower_bound), 2),
                "upper_bound": round(float(upper_bound), 2),
            })

            current_history = pd.concat([
                current_history,
                pd.DataFrame([{"timestamp": next_date, "value": pred_val}])
            ], ignore_index=True)

        return predictions

    def _autoregressive_short_term(self, df: pd.DataFrame, horizon: int = 15) -> List[Dict[str, Any]]:
        """
        Pure NumPy Autoregressive model with exponential smoothing trend and momentum.
        """
        series = df["value"].values
        last_val = float(series[-1])
        last_date = df["timestamp"].max()

        mom_7 = (series[-1] - series[-7]) / 7.0 if len(series) >= 7 else 0.0
        mom_14 = (series[-1] - series[-14]) / 14.0 if len(series) >= 14 else 0.0
        drift = 0.6 * mom_7 + 0.4 * mom_14

        volatility = float(np.std(series[-30:])) if len(series) >= 30 else float(np.std(series))

        results = []
        current_val = last_val
        for i in range(1, horizon + 1):
            next_date = last_date + timedelta(days=i)
            damping = math.exp(-i / 8.0)
            current_val = max(1.0, current_val + drift * damping)

            spread = volatility * (0.8 + (i / horizon) * 0.6)
            lower = max(0.5, current_val - 1.28 * spread)
            upper = current_val + 1.28 * spread

            results.append({
                "timestamp": next_date.strftime("%Y-%m-%d"),
                "predicted_value": round(float(current_val), 2),
                "lower_bound": round(float(lower), 2),
                "upper_bound": round(float(upper), 2),
            })
        return results

    def train_and_predict_long_term(
        self,
        df: pd.DataFrame,
        horizon: int = 60,
        index_name: str = "BDI",
    ) -> List[Dict[str, Any]]:
        """
        Trains Facebook Prophet (or Statsmodels / Multi-factor fallback) for long-term (16-60 days).
        Tailors the training dataset and seasonality priors specifically to each vessel segment:
        - BDI / BDI_KAGGLE: 25-year macroeconomic historical Baltic Dry Index
        - BHSI: Real 25-year Kaggle Handysize bulk carrier series
        - BCI, BPI, BSI: Trained on each index's actual historical observations and vessel-class dynamics.
        """
        training_df = df.copy()
        is_monthly_data = False

        if index_name in ("BDI", "BDI_KAGGLE"):
            kaggle_df = load_kaggle_bdi_data()
            if not kaggle_df.empty and len(kaggle_df) >= 24:
                logger.info("Enriching long-term Prophet model with 25-year Kaggle historical BDI data.")
                current_base = float(df["value"].iloc[-1]) if not df.empty else 2000.0
                kaggle_mean = float(kaggle_df["value"].mean())
                scaling_factor = (current_base / kaggle_mean) if kaggle_mean > 0 else 1.0

                scaled_kaggle = kaggle_df.copy()
                scaled_kaggle["value"] = scaled_kaggle["value"] * scaling_factor
                training_df = scaled_kaggle
                is_monthly_data = True
        else:
            # BCI, BPI, BSI, BHSI: Train Prophet directly on each index's specific series
            logger.info(f"Training Prophet on {len(df)} historical observations specifically for {index_name}.")
            training_df = df.copy()
            is_monthly_data = False

        # Tier 1: Prophet
        try:
            from prophet import Prophet
            prophet_df = training_df[["timestamp", "value"]].rename(columns={"timestamp": "ds", "value": "y"})
            prophet_df["ds"] = pd.to_datetime(prophet_df["ds"])
            if prophet_df["ds"].dt.tz is not None:
                prophet_df["ds"] = prophet_df["ds"].dt.tz_localize(None)

            np.random.seed(42)
            random.seed(42)
            prophet_kwargs = {
                "daily_seasonality": False,
                "weekly_seasonality": not is_monthly_data,
                "yearly_seasonality": is_monthly_data,
                "interval_width": 0.80,
                "mcmc_samples": 0,
            }
            try:
                # Explicitly pass fixed seed for L-BFGS optimizer determinism if version supports it
                m = Prophet(seed=42, **prophet_kwargs)
            except (TypeError, ValueError):
                m = Prophet(**prophet_kwargs)
            m.fit(prophet_df)

            # Generate future horizon (daily frequency starting from recent date)
            future_days = []
            start_date = df["timestamp"].max() if not df.empty else datetime.now()
            if hasattr(start_date, "tzinfo") and start_date.tzinfo is not None:
                start_date = start_date.replace(tzinfo=None)
            for i in range(1, horizon + 1):
                future_days.append(start_date + timedelta(days=i))

            future = pd.DataFrame({"ds": future_days})
            future["ds"] = pd.to_datetime(future["ds"])
            if future["ds"].dt.tz is not None:
                future["ds"] = future["ds"].dt.tz_localize(None)
            forecast = m.predict(future)

            predictions = []
            for _, row in forecast.iterrows():
                pred_val = max(1.0, float(row["yhat"]))
                lower = max(0.5, float(row["yhat_lower"]))
                upper = float(row["yhat_upper"])

                predictions.append({
                    "timestamp": pd.to_datetime(row["ds"]).strftime("%Y-%m-%d"),
                    "predicted_value": round(pred_val, 2),
                    "lower_bound": round(lower, 2),
                    "upper_bound": round(upper, 2),
                })
            logger.info(f"Generated Prophet long-term forecast ({horizon} days) using {'Kaggle 25-Year Trend' if is_monthly_data else 'Recent Series'}.")
            return predictions
        except Exception as e:
            logger.info(f"Prophet not available ({e}). Attempting Statsmodels Holt...")

        # Tier 2: Statsmodels
        try:
            from statsmodels.tsa.api import Holt
            series = df.set_index("timestamp")["value"]
            model = Holt(series, initialization_method="estimated").fit(smoothing_level=0.3, smoothing_trend=0.1)
            forecast_values = model.forecast(horizon)

            residuals_std = float(series.std() * 0.12)
            last_date = df["timestamp"].max()

            results = []
            for i, val in enumerate(forecast_values, start=1):
                target_date = last_date + timedelta(days=i)
                pred = max(1.0, float(val))
                spread = residuals_std * (1.0 + (i / horizon) * 1.5)
                results.append({
                    "timestamp": target_date.strftime("%Y-%m-%d"),
                    "predicted_value": round(pred, 2),
                    "lower_bound": round(max(0.5, pred - 1.28 * spread), 2),
                    "upper_bound": round(pred + 1.28 * spread, 2),
                })
            logger.info(f"Generated Statsmodels Holt forecast for {horizon} days.")
            return results
        except Exception as e:
            logger.info(f"Statsmodels not available ({e}). Using robust multi-factor trend model.")

        # Tier 3: Multi-factor seasonal trend fallback
        series = df["value"].values
        last_val = float(series[-1])
        mean_val = float(np.mean(series))
        std_val = float(np.std(series))
        last_date = df["timestamp"].max()

        results = []
        for i in range(1, horizon + 1):
            target_date = last_date + timedelta(days=i)
            weight_mean = min(0.6, i / horizon)
            pred = max(1.0, (1 - weight_mean) * last_val + weight_mean * mean_val)

            # Seasonal oscillation
            wave = 0.03 * mean_val * math.sin(2 * math.pi * i / 30.0)
            pred = max(1.0, pred + wave)

            spread = std_val * (0.8 + (i / horizon) * 1.2)
            results.append({
                "timestamp": target_date.strftime("%Y-%m-%d"),
                "predicted_value": round(float(pred), 2),
                "lower_bound": round(max(0.5, pred - 1.28 * spread), 2),
                "upper_bound": round(pred + 1.28 * spread, 2),
            })
        return results

    def get_full_forecast(
        self,
        index_name: str,
        disruption_event: Optional[str] = None,
        force_refresh: bool = False,
        db: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        Combines short-term (1-15 days) and long-term (16-60 days)
        into a unified, continuous 60-day prediction trajectory.
        Optionally applies a historical disruption shock multiplier.
        """
        cache_key = (
            str(index_name).strip().upper(),
            str(disruption_event).strip().upper() if disruption_event else None,
        )
        if not force_refresh and cache_key in _FORECAST_CACHE:
            cached_ts, cached_predictions = _FORECAST_CACHE[cache_key]
            if time.time() - cached_ts < _FORECAST_CACHE_TTL:
                logger.info(f"Returning cached forecast trajectory for {index_name} (age: {int(time.time() - cached_ts)}s)")
                return copy.deepcopy(cached_predictions)
            else:
                del _FORECAST_CACHE[cache_key]

        logger.info(f"Initiating hybrid freight forecast for index: {index_name} (Disruption: {disruption_event})...")
        np.random.seed(42)
        random.seed(42)
        df = self.fetch_historical_data(index_name, db=db)

        # 1. Generate 15-day short-term forecast
        short_term_preds = self.train_and_predict_short_term(df, horizon=15)

        # 2. Generate 60-day long-term forecast
        long_term_preds = self.train_and_predict_long_term(df, horizon=60, index_name=index_name)

        # 3. Hybrid blending:
        combined: List[Dict[str, Any]] = []
        combined.extend(short_term_preds)

        if len(short_term_preds) >= 15 and len(long_term_preds) >= 16:
            day15_short = short_term_preds[14]["predicted_value"]
            day15_long = long_term_preds[14]["predicted_value"]
            offset = day15_short - day15_long

            for step_idx in range(15, len(long_term_preds)):
                lt_item = long_term_preds[step_idx]
                decay = math.exp(-(step_idx - 14) / 12.0)
                adjusted_val = max(1.0, float(lt_item["predicted_value"] + offset * decay))
                adjusted_lower = max(0.5, float(lt_item["lower_bound"] + offset * decay))
                adjusted_upper = max(adjusted_val, float(lt_item["upper_bound"] + offset * decay))

                combined.append({
                    "timestamp": lt_item["timestamp"],
                    "predicted_value": round(adjusted_val, 2),
                    "lower_bound": round(adjusted_lower, 2),
                    "upper_bound": round(adjusted_upper, 2),
                })
        else:
            combined.extend(long_term_preds[15:])

        # 4. Apply disruption shock multiplier if specified
        if disruption_event:
            multiplier = get_disruption_shock_multiplier(disruption_event)
            if multiplier != 1.0:
                logger.info(f"Applying disruption shock multiplier {multiplier} for event: {disruption_event}")
                for item in combined:
                    item["predicted_value"] = round(item["predicted_value"] * multiplier, 2)
                    item["lower_bound"] = round(item["lower_bound"] * multiplier, 2)
                    item["upper_bound"] = round(item["upper_bound"] * multiplier, 2)

        logger.info(f"Successfully generated {len(combined)}-day unified forecast for {index_name}.")
        _FORECAST_CACHE[cache_key] = (time.time(), copy.deepcopy(combined))
        return combined

    def get_medium_term_coa_rate(
        self,
        vessel_type: str = "Capesize",
        required_cargo_mt: float = 150000.0,
        horizon_days: int = 180,
        rate_multiplier: float = 1.0,
        db: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Calculates the forecasted 6-Month forward Contract of Affreightment (COA) rate ($/MT)
        using the Prophet long-term model trajectory for 180 days (T+1 to T+180 / 6 Months).
        Detects forward market trend ('CONTANGO', 'BACKWARDATION', or 'STABLE') by comparing
        Short-Term (Days 1-30) vs Long-Term (Days 150-180), applies route and disruption rate multipliers,
        and applies real-world Volume-Tiered pricing:
          - >= 300,000 MT: 5% volume discount (0.95x)
          - >= 150,000 MT: 2% volume discount (0.98x)
          - < 150,000 MT:  2% small parcel risk premium (1.02x)
        Returns: {"rate": float, "trend": str, "discount_pct": float}
        """
        normalized_type = str(vessel_type or "Capesize").strip().capitalize()
        mapping = {
            "Capesize": {"index": "BCI", "scale": 1.0 / 140.0, "fallback": 18.0},
            "Panamax": {"index": "BPI", "scale": 1.0 / 85.0, "fallback": 20.5},
            "Supramax": {"index": "BSI", "scale": 1.0 / 58.0, "fallback": 23.5},
            "Handysize": {"index": "BHSI", "scale": 1.0 / 32.0, "fallback": 24.5},
        }
        spec = mapping.get(normalized_type, mapping["Capesize"])
        index_name = spec["index"]
        scale = spec["scale"]

        try:
            df = self.fetch_historical_data(index_name, db=db)
            forecast_180 = self.train_and_predict_long_term(df, horizon=horizon_days, index_name=index_name)
            if not forecast_180:
                fallback_rate = round(float(spec["fallback"] * rate_multiplier), 2)
                return {"rate": fallback_rate, "trend": "STABLE", "discount_pct": 0.0}

            # 1. Short-Term Average (Days 1 to 30)
            short_term_slice = forecast_180[:30] if len(forecast_180) >= 30 else forecast_180
            short_term_avg = sum(float(item["predicted_value"]) for item in short_term_slice) / len(short_term_slice)

            # 2. Long-Term Average (Days 150 to 180)
            long_term_slice = forecast_180[149:180] if len(forecast_180) >= 180 else forecast_180[-30:]
            long_term_avg = sum(float(item["predicted_value"]) for item in long_term_slice) / len(long_term_slice)

            # 3. Market Trend Determination (Contango / Backwardation / Stable)
            if long_term_avg > 1.05 * short_term_avg:
                market_trend = "CONTANGO"
            elif long_term_avg < 0.95 * short_term_avg:
                market_trend = "BACKWARDATION"
            else:
                market_trend = "STABLE"

            # 4. Baseline 180-Day Forward Rate (scaled by route distance and crisis multipliers)
            avg_index_points = sum(float(item["predicted_value"]) for item in forecast_180) / len(forecast_180)
            base_rate_usd_mt = avg_index_points * scale * rate_multiplier

            # 5. Volume-Tiered COA Pricing
            cargo_qty = float(required_cargo_mt or 150000.0)
            if cargo_qty >= 300000.0:
                discount_applied = 5.0
                volume_multiplier = 0.95
            elif cargo_qty >= 150000.0:
                discount_applied = 2.0
                volume_multiplier = 0.98
            else:
                discount_applied = -2.0
                volume_multiplier = 1.02

            final_rate = round(float(base_rate_usd_mt * volume_multiplier), 2)

            logger.info(
                f"Computed 6-Month COA for {normalized_type} ({index_name}): "
                f"ShortTerm={short_term_avg:.1f}, LongTerm={long_term_avg:.1f} -> Trend={market_trend} | "
                f"Base Rate=${base_rate_usd_mt:.2f}/MT (Mult={rate_multiplier:.2f}x), Cargo={cargo_qty:,.0f} MT, Disc={discount_applied:+.1f}% -> Final Rate=${final_rate}/MT"
            )

            return {
                "rate": final_rate,
                "trend": market_trend,
                "discount_pct": discount_applied,
            }
        except Exception as e:
            logger.warning(f"Error calculating 6-month COA rate for {vessel_type} ({e}). Using fallback rate.")
            fallback_rate = round(float(spec["fallback"] * rate_multiplier), 2)
            return {"rate": fallback_rate, "trend": "STABLE", "discount_pct": 0.0}


if __name__ == "__main__":
    forecaster = FreightForecaster()
    forecast = forecaster.get_full_forecast("BCI", disruption_event="SUEZ")
    print(f"Generated {len(forecast)} forecast days with SUEZ disruption:")
    for f in forecast[:3]:
        print(f)
