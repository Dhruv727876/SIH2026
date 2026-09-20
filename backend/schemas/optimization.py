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
    force_refresh: Optional[bool] = Field(
        default=False,
        description="If True, forces re-execution of the MILP solver and bypasses cached plans",
    )
    allow_lighterage: Optional[bool] = Field(
        default=True,
        description="Whether to allow mid-sea lighterage for large vessels (e.g. Capesize at Sandheads) for shallow ports",
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
    port_max_loa_m: Optional[float] = None
    port_max_beam_m: Optional[float] = None
    port_handling_rate_tpd: Optional[float] = None
    port_waiting_hours: Optional[float] = None
    port_turnaround_days: Optional[float] = None
    deadheading_cost_usd: Optional[float] = None
    idle_time_penalty_usd: Optional[float] = None
    required_cargo_mt: Optional[float] = None
    total_cargo_allocated_mt: Optional[float] = None
    total_estimated_cost_usd: float = Field(..., description="Optimized landed logistics cost in USD")
    estimated_savings_usd: float = Field(..., description="Estimated cost savings compared to naive spot booking")
    benchmark_naive_cost_usd: Optional[float] = None
    vessel_schedule: List[VesselScheduleItem] = Field(
        default_factory=list,
        description="Recommended vessel chartering schedule",
    )
    strategy_used: Optional[str] = Field(
        default="DIRECT_DISCHARGE",
        description="Logistics strategy selected ('DIRECT_DISCHARGE' or 'MID_SEA_LIGHTERAGE')",
    )
    lighterage_penalty_applied: Optional[float] = Field(
        default=0.0,
        description="Total lighterage penalty cost applied in USD (transshipment fee + demurrage wait)",
    )
    lighterage_vessel_type: Optional[str] = Field(
        default=None,
        description="The type of vessel used for the secondary transfer (e.g., Supramax)",
    )
    lighterage_vessel_count: Optional[int] = Field(
        default=None,
        description="Number of secondary vessels required to move the cargo from anchorage to port",
    )
    lighterage_strictly_cheaper: Optional[bool] = Field(
        default=None,
        description="True if Scenario B lighterage was strictly cheaper than Scenario A direct discharge",
    )
    lighterage_cost_premium: Optional[float] = Field(
        default=None,
        description="Cost premium fraction of lighterage over direct discharge (e.g. 0.05 for +5%)",
    )
    coa_rate_usd_per_mt: Optional[float] = Field(
        default=None,
        description="Forecasted 6-month forward COA rate per MT",
    )
    coa_total_cost_usd: Optional[float] = Field(
        default=None,
        description="Total cost if fulfilled via 6-month COA",
    )
    coa_savings_usd: Optional[float] = Field(
        default=None,
        description="Financial savings of choosing the recommended strategy",
    )
    procurement_recommendation: Optional[str] = Field(
        default=None,
        description="'LOCK_IN_COA' or 'STAY_SPOT'",
    )
    market_trend: Optional[str] = Field(
        default=None,
        description="'CONTANGO', 'BACKWARDATION', or 'STABLE'",
    )
    coa_discount_pct: Optional[float] = Field(
        default=None,
        description="Percentage discount or premium applied to COA rate",
    )
    message: Optional[str] = None
    is_cached: Optional[bool] = Field(default=False, description="True if response was retrieved from deterministic cache")

