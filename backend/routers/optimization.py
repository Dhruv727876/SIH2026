from datetime import date, datetime, timezone
import logging
import os
import sys
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# Ensure ml_engine path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ml_engine_dir = os.path.join(root_dir, "ml_engine")
if ml_engine_dir not in sys.path:
    sys.path.insert(0, ml_engine_dir)

from optimization.optimizer import VesselCharterOptimizer
from schemas.optimization import OptimizationRequest, OptimizationResponse, VesselScheduleItem
from database import get_db
from models.optimization_log import OptimizationLog

logger = logging.getLogger("optimization-router")
router = APIRouter(prefix="/api/v1/optimize", tags=["Optimization"])


@router.post(
    "",
    response_model=OptimizationResponse,
    status_code=status.HTTP_200_OK,
    summary="Optimize vessel chartering schedule using MILP with Route Multipliers",
)
def run_vessel_charter_optimization(
    payload: OptimizationRequest,
    db: Session = Depends(get_db),
):
    """
    Computes an optimal vessel chartering plan that minimizes total freight and demurrage costs
    while satisfying physical draft, route distance multiplier, and berth constraints.
    """
    try:
        optimizer = VesselCharterOptimizer()
        result = optimizer.optimize_charter_plan(
            required_cargo_mt=payload.required_cargo_mt,
            target_port=payload.target_port,
            planning_horizon_days=payload.planning_horizon_days,
            origin_port=payload.origin_port or "Australia",
            disruption_multiplier=payload.disruption_multiplier or 1.0,
        )

        schedule_items = [
            VesselScheduleItem(
                date=s["date"],
                vessel_type=s["vessel_type"],
                quantity=int(s["quantity"]),
                capacity_mt=float(s.get("capacity_mt", 0.0)),
                total_cargo_mt=float(s.get("total_cargo_mt", 0.0)),
                freight_rate_usd_mt=float(s.get("freight_rate_usd_mt", 0.0)),
                estimated_trip_cost_usd=float(s.get("estimated_trip_cost_usd", 0.0)),
            )
            for s in result.get("vessel_schedule", [])
        ]

        route_str = result.get("route", f"{payload.origin_port or 'Australia'} -> {payload.target_port}")

        response = OptimizationResponse(
            status=result["status"],
            target_port=result.get("target_port"),
            origin_port=result.get("origin_port"),
            route=route_str,
            port_max_draft_m=result.get("port_max_draft_m"),
            port_waiting_hours=result.get("port_waiting_hours"),
            required_cargo_mt=result.get("required_cargo_mt"),
            total_cargo_allocated_mt=result.get("total_cargo_allocated_mt"),
            total_estimated_cost_usd=float(result["total_estimated_cost_usd"]),
            estimated_savings_usd=float(result["estimated_savings_usd"]),
            benchmark_naive_cost_usd=result.get("benchmark_naive_cost_usd"),
            vessel_schedule=schedule_items,
            message=result.get("message"),
        )

        # Log optimization audit to database if schedule was formed
        try:
            primary_vessel = schedule_items[0].vessel_type if schedule_items else "Mixed"
            first_date = datetime.strptime(schedule_items[0].date, "%Y-%m-%d").date() if schedule_items else date.today()

            log_entry = OptimizationLog(
                timestamp=datetime.now(timezone.utc),
                route=route_str,
                vessel_type=primary_vessel,
                recommended_charter_date=first_date,
                estimated_total_cost=float(result["total_estimated_cost_usd"]),
                estimated_savings=float(result["estimated_savings_usd"]),
                status=result["status"],
            )
            db.add(log_entry)
            db.commit()
        except Exception as log_err:
            logger.warning(f"Could not persist optimization log to database ({log_err}).")

        return response

    except Exception as e:
        logger.error(f"Optimization execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"MILP optimization engine failed: {str(e)}",
        )
