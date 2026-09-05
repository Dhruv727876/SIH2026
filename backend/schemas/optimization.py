from typing import List, Optional
from pydantic import BaseModel, Field


class OptimizationRequest(BaseModel):
    required_cargo_mt: float = Field(
        ...,
        gt=0,
        description="Total quantity of raw materials required in Metric Tons (MT), e.g. 300,000 MT",
    )
    target_port: str = Field(
        ...,
        min_length=1,
        description="Destination discharge port (e.g. Paradip, Visakhapatnam, Haldia, Dhamra, Gangavaram)",
    )
    origin_port: Optional[str] = Field(
        default="Australia",
        description="Departure / Loading port or country (e.g. Australia, Brazil, South Africa, Indonesia)",
    )
    planning_horizon_days: int = Field(
        default=30,
        ge=7,
        le=60,
        description="Optimization planning window in days",
    )
    disruption_multiplier: Optional[float] = Field(
        default=1.0,
        description="Optional crisis shock multiplier applied to freight rates",
    )
    disruption_name: Optional[str] = Field(
        default=None,
        description="Optional name of active disruption event",
    )


class VesselScheduleItem(BaseModel):
    date: str = Field(..., description="Chartering dispatch date (YYYY-MM-DD)")
    vessel_type: str = Field(..., description="Vessel class (Capesize, Panamax, Supramax)")
    quantity: int = Field(..., description="Number of vessels scheduled on this date")
    capacity_mt: Optional[float] = None
    total_cargo_mt: Optional[float] = None
    freight_rate_usd_mt: Optional[float] = None
    estimated_trip_cost_usd: Optional[float] = None


class OptimizationResponse(BaseModel):
    status: str = Field(..., description="Solver status ('Optimal', 'Infeasible')")
    target_port: Optional[str] = None
    origin_port: Optional[str] = None
    route: Optional[str] = None
    port_max_draft_m: Optional[float] = None
    port_waiting_hours: Optional[float] = None
    required_cargo_mt: Optional[float] = None
    total_cargo_allocated_mt: Optional[float] = None
    total_estimated_cost_usd: float = Field(..., description="Optimized landed logistics cost in USD")
    estimated_savings_usd: float = Field(..., description="Estimated cost savings compared to naive spot booking")
    benchmark_naive_cost_usd: Optional[float] = None
    vessel_schedule: List[VesselScheduleItem] = Field(
        default_factory=list,
        description="Recommended vessel chartering schedule",
    )
    message: Optional[str] = None
