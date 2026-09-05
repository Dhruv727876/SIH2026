import logging
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
import requests

# Add parent directory to path so we can import from data_pipeline
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from data_pipeline.fetch_market_data import generate_synthetic_series, load_kaggle_bdi_data
from data_pipeline.fetch_disruptions import get_disruption_shock_multiplier

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("freight-forecaster")

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")


class FreightForecaster:
    """
    Hybrid Freight & Fuel Rate Forecasting Engine.
    Combines LightGBM for short-term volatility (1-15 days) and Prophet/Holt for long-term (16-60 days),
    incorporating real 25-year historical Kaggle BDI data when available.
    """

    def __init__(self, backend_api_url: Optional[str] = None):
        self.backend_api_url = (backend_api_url or API_BASE_URL).rstrip("/")

    def fetch_historical_data(self, index_name: str, limit: int = 180) -> pd.DataFrame:
        """
        Fetches historical records from FastAPI backend, Kaggle dataset, or synthetic fallback.
        """
        # If explicitly asking for Kaggle BDI, load from CSV
        if index_name == "BDI_KAGGLE":
            df_kaggle = load_kaggle_bdi_data()
            if not df_kaggle.empty:
                return df_kaggle

        records: List[Dict[str, Any]] = []
        try:
            url = f"{self.backend_api_url}/api/v1/market-data"
            params = {"index_name": index_name, "limit": limit}
            resp = requests.get(url, params=params, timeout=4)
            if resp.status_code == 200:
                records = resp.json()
                logger.info(f"Retrieved {len(records)} records for {index_name} from backend API.")
        except Exception as e:
            logger.warning(f"Could not connect to backend API ({e}). Using synthetic series fallback.")

        # If backend returned no records, check if Kaggle data exists for generic BDI or generate synthetic
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
    ) -> List[Dict[str, Any]]:
        """
        Trains Facebook Prophet (or Statsmodels / Multi-factor fallback) for long-term (16-60 days).
        If real Kaggle 25-year historical data is available, leverages it for macroeconomic seasonal cycles.
        """
        # Check if Kaggle 25-year BDI dataset is available to enrich long-term training
        training_df = df.copy()
        is_monthly_data = False

        kaggle_df = load_kaggle_bdi_data()
        if not kaggle_df.empty and len(kaggle_df) >= 24:
            logger.info("Enriching long-term Prophet model with 25-year Kaggle historical BDI data.")
            # Scale Kaggle BDI trend to current index level baseline
            current_base = float(df["value"].iloc[-1]) if not df.empty else 2000.0
            kaggle_mean = float(kaggle_df["value"].mean())
            scaling_factor = (current_base / kaggle_mean) if kaggle_mean > 0 else 1.0

            scaled_kaggle = kaggle_df.copy()
            scaled_kaggle["value"] = scaled_kaggle["value"] * scaling_factor
            training_df = scaled_kaggle
            is_monthly_data = True

        # Tier 1: Prophet
        try:
            from prophet import Prophet
            prophet_df = training_df[["timestamp", "value"]].rename(columns={"timestamp": "ds", "value": "y"})
            prophet_df["ds"] = pd.to_datetime(prophet_df["ds"])
            if prophet_df["ds"].dt.tz is not None:
                prophet_df["ds"] = prophet_df["ds"].dt.tz_localize(None)

            m = Prophet(
                daily_seasonality=False,
                weekly_seasonality=not is_monthly_data,
                yearly_seasonality=True,
                interval_width=0.80,
            )
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
    ) -> List[Dict[str, Any]]:
        """
        Combines short-term (1-15 days) and long-term (16-60 days)
        into a unified, continuous 60-day prediction trajectory.
        Optionally applies a historical disruption shock multiplier.
        """
        logger.info(f"Initiating hybrid freight forecast for index: {index_name} (Disruption: {disruption_event})...")
        df = self.fetch_historical_data(index_name)

        # 1. Generate 15-day short-term forecast
        short_term_preds = self.train_and_predict_short_term(df, horizon=15)

        # 2. Generate 60-day long-term forecast
        long_term_preds = self.train_and_predict_long_term(df, horizon=60)

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
        return combined


if __name__ == "__main__":
    forecaster = FreightForecaster()
    forecast = forecaster.get_full_forecast("BCI", disruption_event="SUEZ")
    print(f"Generated {len(forecast)} forecast days with SUEZ disruption:")
    for f in forecast[:3]:
        print(f)
