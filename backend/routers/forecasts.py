from datetime import datetime, timezone
import os
import sys
from typing import Dict, List
from fastapi import APIRouter, HTTPException, status

# Ensure ml_engine is accessible in path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ml_engine_dir = os.path.join(root_dir, "ml_engine")
if ml_engine_dir not in sys.path:
    sys.path.insert(0, ml_engine_dir)

from forecasting.forecaster import FreightForecaster
from schemas.forecast import ForecastRequest, ForecastResponse, ForecastItem

router = APIRouter(prefix="/api/v1/forecasts", tags=["Forecasting"])

# In-memory forecast cache to prevent redundant ML re-training: {index_name: ForecastResponse}
FORECAST_CACHE: Dict[str, Dict] = {}


@router.post(
    "/generate",
    response_model=ForecastResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger and generate a 60-day hybrid freight/fuel rate forecast",
)
def generate_forecast(payload: ForecastRequest):
    """
    Triggers the hybrid ML forecasting engine (LightGBM + Prophet/Statsmodels)
    for the specified index and returns the 60-day predictive trajectory.
    """
    index_name = payload.index_name.upper().strip()
    try:
        forecaster = FreightForecaster()
        forecast_data = forecaster.get_full_forecast(index_name)

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

        # Store in cache
        FORECAST_CACHE[index_name] = response.model_dump()
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
def get_forecast(index_name: str):
    """
    Retrieves the 60-day forecast for the given index (e.g. BCI, BPI, BSI, BRENT_CRUDE, BUNKER_SIN).
    Returns cached prediction if available, otherwise triggers fresh model generation.
    """
    idx = index_name.upper().strip()

    if idx in FORECAST_CACHE:
        return FORECAST_CACHE[idx]

    # Generate on-demand if cache miss
    try:
        forecaster = FreightForecaster()
        forecast_data = forecaster.get_full_forecast(idx)

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

        FORECAST_CACHE[idx] = response.model_dump()
        return response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not retrieve forecast for {idx}: {str(e)}",
        )
