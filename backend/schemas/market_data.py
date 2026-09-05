from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class MarketDataBase(BaseModel):
    timestamp: datetime = Field(..., description="Timestamp of the market data record")
    index_name: str = Field(..., min_length=1, max_length=50, description="Name of the index (e.g. BCI, BPI, BUNKER_SIN)")
    value: float = Field(..., description="Numerical value of the index/rate")
    currency: str = Field(default="USD", max_length=10, description="Currency denomination")


class MarketDataCreate(MarketDataBase):
    """Schema for ingesting a new market data point via POST."""
    pass


class MarketDataResponse(MarketDataBase):
    """Schema returned for market data queries."""
    id: int

    model_config = ConfigDict(from_attributes=True)
