import time
from datetime import datetime, timezone
import os
import sys
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# Ensure ml_engine is accessible in path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ml_engine_dir = os.path.join(root_dir, "ml_engine")
if ml_engine_dir not in sys.path:
    sys.path.insert(0, ml_engine_dir)

from forecasting.forecaster import FreightForecaster
from schemas.forecast import ForecastRequest, ForecastResponse, ForecastItem
from database import get_db

router = APIRouter(prefix="/api/v1/forecasts", tags=["Forecasting"])

# In-memory forecast cache with 15-minute TTL: {cache_key: {"timestamp": float, "response": ForecastResponse}}
FORECAST_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 900  # 15 minutes


def get_cached_forecast(key: str) -> Optional[ForecastResponse]:
    """Retrieves cached forecast if present and under 15-minute TTL."""
    if key in FORECAST_CACHE:
        entry = FORECAST_CACHE[key]
        if time.time() - entry["timestamp"] < CACHE_TTL_SECONDS:
            return entry["response"]
        else:
            del FORECAST_CACHE[key]
    return None


def set_cached_forecast(key: str, response: ForecastResponse):
    """Stores forecast response with current epoch timestamp."""
    FORECAST_CACHE[key] = {
        "timestamp": time.time(),
        "response": response,
    }


def clear_forecast_cache():
    """Invalidates the entire forecast cache on new market data ingestion."""
    FORECAST_CACHE.clear()


@router.post(
    "/generate",
    response_model=ForecastResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger and generate a 60-day hybrid freight/fuel rate forecast",
)
def generate_forecast(
    payload: ForecastRequest,
    db: Session = Depends(get_db),
):
    """
    Triggers the hybrid ML forecasting engine (LightGBM + Prophet/Statsmodels)
    for the specified index and returns the 60-day predictive trajectory.
    Returns cached response if requested with identical parameters within 15 minutes.
    """
    index_name = payload.index_name.upper().strip()
    cache_key = f"FORECAST_{index_name}"

    cached = get_cached_forecast(cache_key)
    if cached is not None:
        return cached

    try:
        forecaster = FreightForecaster()
        forecast_data = forecaster.get_full_forecast(index_name, db=db)

        forecast_items = [
            ForecastItem(
                timestamp=item["timestamp"],
                predicted_value=float(item["predicted_value"]),
                lower_bound=float(item["lower_bound"]),
                upper_bound=float(item["upper_bound"]),
            )
            for item in forecast_data
        ]

        response = ForecastResponse(
            index_name=index_name,
            forecast_horizon_days=len(forecast_items),
            generated_at=datetime.now(timezone.utc),
            forecast=forecast_items,
        )

        set_cached_forecast(cache_key, response)
        return response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Forecasting engine failed for {index_name}: {str(e)}",
        )


@router.get(
    "/{index_name}",
    response_model=ForecastResponse,
    summary="Retrieve current forecast for an index (cached or freshly generated)",
)
def get_forecast(
    index_name: str,
    db: Session = Depends(get_db),
):
    """
    Retrieves the 60-day forecast for the given index (e.g. BCI, BPI, BSI, BRENT_CRUDE, BUNKER_SIN).
    Returns cached prediction if available within 15 minutes, otherwise triggers fresh model generation.
    """
    idx = index_name.upper().strip()
    cache_key = f"FORECAST_{idx}"

    cached = get_cached_forecast(cache_key)
    if cached is not None:
        return cached

    # Generate on-demand if cache miss
    try:
        forecaster = FreightForecaster()
        forecast_data = forecaster.get_full_forecast(idx, db=db)

        forecast_items = [
            ForecastItem(
                timestamp=item["timestamp"],
                predicted_value=float(item["predicted_value"]),
                lower_bound=float(item["lower_bound"]),
                upper_bound=float(item["upper_bound"]),
            )
            for item in forecast_data
        ]

        response = ForecastResponse(
            index_name=idx,
            forecast_horizon_days=len(forecast_items),
            generated_at=datetime.now(timezone.utc),
            forecast=forecast_items,
        )

        set_cached_forecast(cache_key, response)
        return response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not retrieve forecast for {idx}: {str(e)}",
        )
