import logging
import os
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("market-data-fetcher")

# Index specifications and baseline characteristics
INDEX_SPECS = {
    "BCI": {"base": 2400.0, "volatility": 0.035, "currency": "USD", "unit": "Points"},
    "BPI": {"base": 1650.0, "volatility": 0.025, "currency": "USD", "unit": "Points"},
    "BSI": {"base": 1300.0, "volatility": 0.020, "currency": "USD", "unit": "Points"},
    "BRENT_CRUDE": {"base": 82.5, "volatility": 0.018, "currency": "USD", "unit": "$/bbl"},
    "BUNKER_SIN": {"base": 620.0, "volatility": 0.015, "currency": "USD", "unit": "$/MT"},
    "USD_INR": {"base": 83.4, "volatility": 0.003, "currency": "INR", "unit": "INR/USD"},
    "BDI_KAGGLE": {"base": 2100.0, "volatility": 0.030, "currency": "USD", "unit": "Points"},
}


def load_kaggle_bdi_data(
    csv_path: str = "ml_engine/data_pipeline/raw_data/shipping_rates.csv",
) -> pd.DataFrame:
    """
    Loads 25-year historical Baltic Dry Index (BDI) data from the Kaggle dataset
    'Global Supply Chain & Trade Disruptions 25 years' (shipping_rates.csv).
    
    Extracts 'date' and 'baltic_dry_index', formats into standard time-series schema:
    ['timestamp', 'index_name', 'value', 'currency'].
    """
    # Resolve relative paths robustly
    if not os.path.exists(csv_path):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        alt_path = os.path.join(base_dir, "raw_data", "shipping_rates.csv")
        if os.path.exists(alt_path):
            csv_path = alt_path

    if not os.path.exists(csv_path):
        logger.warning(f"Kaggle shipping rates CSV not found at {csv_path}. Returning empty DataFrame.")
        return pd.DataFrame(columns=["timestamp", "index_name", "value", "currency"])

    try:
        df = pd.read_csv(csv_path)
        logger.info(f"Loaded Kaggle dataset from {csv_path} with {len(df)} rows and columns: {list(df.columns)}")

        # Find date column
        date_col = None
        for col in ["date", "Date", "timestamp", "Timestamp", "DATE", "Month"]:
            if col in df.columns:
                date_col = col
                break

        # Find BDI column
        bdi_col = None
        for col in ["baltic_dry_index", "bdi", "BDI", "Baltic_Dry_Index", "baltic_dry", "index_value", "rate"]:
            if col in df.columns:
                bdi_col = col
                break

        if date_col is None or bdi_col is None:
            # Fallback to first 2 columns if specific names aren't matched
            date_col = df.columns[0]
            bdi_col = df.columns[1]
            logger.info(f"Mapping columns by position: Date='{date_col}', Value='{bdi_col}'")

        # Parse and clean
        df_clean = df[[date_col, bdi_col]].copy()
        df_clean.columns = ["timestamp", "value"]

        # Date parsing
        df_clean["timestamp"] = pd.to_datetime(df_clean["timestamp"], errors="coerce")
        df_clean["value"] = pd.to_numeric(df_clean["value"], errors="coerce")
        df_clean = df_clean.dropna(subset=["timestamp", "value"])

        # Add standard columns
        df_clean["index_name"] = "BDI_KAGGLE"
        df_clean["currency"] = "USD"

        # Sort and deduplicate
        df_clean = df_clean.sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)
        logger.info(f"Successfully processed {len(df_clean)} Kaggle BDI monthly records ({df_clean['timestamp'].min().strftime('%Y-%m')} to {df_clean['timestamp'].max().strftime('%Y-%m')}).")
        return df_clean

    except Exception as e:
        logger.error(f"Error loading Kaggle BDI data from {csv_path}: {e}")
        return pd.DataFrame(columns=["timestamp", "index_name", "value", "currency"])


def generate_synthetic_series(
    index_name: str,
    days: int = 180,
    end_date: datetime | None = None,
) -> List[Dict[str, Any]]:
    """
    Generates a realistic mean-reverting random walk time-series for shipping & macro indices.
    """
    if end_date is None:
        end_date = datetime.now(timezone.utc)

    spec = INDEX_SPECS.get(index_name, {"base": 100.0, "volatility": 0.02, "currency": "USD"})
    current_val = spec["base"]
    volatility = spec["volatility"]
    currency = spec["currency"]

    records = []
    for i in range(days, 0, -1):
        record_date = end_date - timedelta(days=i)
        if record_date.weekday() in (5, 6):
            continue

        mean_reversion_pull = 0.05 * (spec["base"] - current_val) / spec["base"]
        shock = random.gauss(0, volatility)
        current_val = max(1.0, current_val * (1.0 + mean_reversion_pull + shock))

        records.append({
            "timestamp": record_date.replace(hour=0, minute=0, second=0, microsecond=0).isoformat(),
            "index_name": index_name,
            "value": round(float(current_val), 2),
            "currency": currency,
        })

    return records


def generate_all_synthetic_market_data(days: int = 180) -> List[Dict[str, Any]]:
    """
    Generates synthetic market data for all configured indices as a fallback.
    """
    logger.info("Generating realistic synthetic market telemetry across all indices...")
    all_records: List[Dict[str, Any]] = []
    for index_name in ["BCI", "BPI", "BSI", "BRENT_CRUDE", "BUNKER_SIN", "USD_INR"]:
        series = generate_synthetic_series(index_name, days=days)
        all_records.extend(series)
    return all_records


def fetch_real_market_data(days: int = 180) -> List[Dict[str, Any]]:
    """
    Fetches real-world historical market telemetry using Yahoo Finance (yfinance)
    and Kaggle historical shipping datasets, with graceful fallbacks.
    """
    records: List[Dict[str, Any]] = []
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days + 10)

    # 1. Ingest Kaggle 25-Year BDI Data if available
    kaggle_df = load_kaggle_bdi_data()
    if not kaggle_df.empty:
        for _, row in kaggle_df.iterrows():
            ts = row["timestamp"]
            ts_dt = ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts
            if getattr(ts_dt, "tzinfo", None) is None:
                ts_dt = ts_dt.replace(tzinfo=timezone.utc)
            records.append({
                "timestamp": ts_dt.isoformat(),
                "index_name": "BDI_KAGGLE",
                "value": round(float(row["value"]), 2),
                "currency": "USD",
            })
        logger.info(f"Appended {len(kaggle_df)} Kaggle BDI historical points to ingestion queue.")

    # 2. Ingest Yahoo Finance benchmarks
    yf_symbols = {
        "BRENT_CRUDE": {"symbol": "BZ=F", "currency": "USD"},
        "USD_INR": {"symbol": "USDINR=X", "currency": "INR"},
    }

    try:
        import yfinance as yf
        logger.info(f"Attempting market data extraction via yfinance for past {days} days...")

        for index_name, meta in yf_symbols.items():
            symbol = meta["symbol"]
            currency = meta["currency"]
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"))

                if hist.empty or "Close" not in hist:
                    logger.warning(f"No history returned for {symbol}. Falling back to synthetic simulation.")
                    records.extend(generate_synthetic_series(index_name, days=days, end_date=end_date))
                    continue

                for ts, row in hist.iterrows():
                    close_val = row["Close"]
                    if pd_isna(close_val):
                        continue
                    ts_dt = ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts
                    if getattr(ts_dt, "tzinfo", None) is None:
                        ts_dt = ts_dt.replace(tzinfo=timezone.utc)

                    records.append({
                        "timestamp": ts_dt.isoformat(),
                        "index_name": index_name,
                        "value": round(float(close_val), 2),
                        "currency": currency,
                    })
                logger.info(f"Successfully retrieved {len(hist)} real records for {index_name} ({symbol}).")
            except Exception as e:
                logger.warning(f"Error fetching {symbol} via yfinance: {e}. Using synthetic fallback.")
                records.extend(generate_synthetic_series(index_name, days=days, end_date=end_date))

    except ImportError:
        logger.warning("yfinance package not installed in environment. Using synthetic simulation.")
        records.extend(generate_all_synthetic_market_data(days=days))
    except Exception as e:
        logger.error(f"Unexpected error in yfinance fetcher: {e}. Falling back to synthetic simulation.")
        records.extend(generate_all_synthetic_market_data(days=days))

    # 3. For Baltic freight indices (BCI, BPI, BSI) and Singapore Bunker (BUNKER_SIN),
    # generate domain-accurate synthetic series
    proprietary_indices = ["BCI", "BPI", "BSI", "BUNKER_SIN"]
    for idx in proprietary_indices:
        records.extend(generate_synthetic_series(idx, days=days, end_date=end_date))

    return records


def pd_isna(val: Any) -> bool:
    """Helper to check for null or NaN values."""
    try:
        import math
        return val is None or (isinstance(val, float) and math.isnan(val))
    except Exception:
        return val is None


if __name__ == "__main__":
    k_df = load_kaggle_bdi_data()
    print("Kaggle BDI Sample:")
    print(k_df.head())
    data = fetch_real_market_data(days=10)
    print(f"Total fetched records: {len(data)}")
