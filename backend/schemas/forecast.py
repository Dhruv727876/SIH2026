from datetime import datetime
from typing import List
from pydantic import BaseModel, Field


class ForecastRequest(BaseModel):
    index_name: str = Field(default="BCI", description="Index to forecast (e.g. BCI, BPI, BSI, BRENT_CRUDE, BUNKER_SIN)")


class ForecastItem(BaseModel):
    timestamp: str = Field(..., description="Forecast date in YYYY-MM-DD format")
    predicted_value: float = Field(..., description="Point forecast rate or price")
    lower_bound: float = Field(..., description="Lower 80% confidence interval bound")
    upper_bound: float = Field(..., description="Upper 80% confidence interval bound")


class ForecastResponse(BaseModel):
    index_name: str
    forecast_horizon_days: int
    generated_at: datetime
    forecast: List[ForecastItem]
