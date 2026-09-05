from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class PortDataBase(BaseModel):
    port_name: str = Field(..., min_length=1, max_length=100, description="Port identifier name")
    max_draft_meters: float = Field(..., gt=0, description="Maximum permissible draft in meters")
    current_waiting_time_hours: float = Field(default=0.0, ge=0, description="Congestion waiting time in hours")


class PortDataCreate(PortDataBase):
    """Schema for adding or updating port telemetry."""
    pass


class PortDataResponse(PortDataBase):
    """Schema returned for port telemetry queries."""
    id: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
