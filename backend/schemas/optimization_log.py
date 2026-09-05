from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field


class OptimizationLogBase(BaseModel):
    route: str = Field(..., min_length=1, max_length=100)
    vessel_type: str = Field(..., min_length=1, max_length=50)
    recommended_charter_date: date
    estimated_total_cost: float = Field(..., ge=0)
    estimated_savings: float = Field(default=0.0)
    status: str = Field(default="COMPLETED")


class OptimizationLogCreate(OptimizationLogBase):
    pass


class OptimizationLogResponse(OptimizationLogBase):
    id: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
