import time
from datetime import date, datetime, timezone
import logging
import os
import sys
from typing import Any, Dict, Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# Ensure ml_engine path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ml_engine_dir = os.path.join(root_dir, "ml_engine")
if ml_engine_dir not in sys.path:
    sys.path.insert(0, ml_engine_dir)

from optimization.optimizer import VesselCharterOptimizer, get_route_info
from forecasting.forecaster import FreightForecaster
from schemas.optimization import OptimizationRequest, OptimizationResponse, VesselScheduleItem
from database import get_db
from models.optimization_log import OptimizationLog

logger = logging.getLogger("optimization-router")
router = APIRouter(prefix="/api/v1/optimize", tags=["Optimization"])

# In-memory optimization cache with 15-minute TTL
OPTIMIZATION_CACHE: Dict[Tuple, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 900  # 15 minutes


def get_cached_optimization(cache_key: Tuple) -> Optional[OptimizationResponse]:
    """Retrieves cached optimization plan if within 15-minute TTL."""
    if cache_key in OPTIMIZATION_CACHE:
        entry = OPTIMIZATION_CACHE[cache_key]
        if time.time() - entry["timestamp"] < CACHE_TTL_SECONDS:
            return entry["response"]
        else:
            del OPTIMIZATION_CACHE[cache_key]
    return None


def set_cached_optimization(cache_key: Tuple, response: OptimizationResponse):
    """Stores optimization response in cache with current timestamp."""
    OPTIMIZATION_CACHE[cache_key] = {
        "timestamp": time.time(),
        "response": response,
    }


def clear_optimization_cache():
    """Invalidates the entire optimization cache on data updates."""
    OPTIMIZATION_CACHE.clear()


@router.post(
    "/clear-cache",
    status_code=status.HTTP_200_OK,
    summary="Clear the in-memory optimization response cache",
)
def clear_cache_endpoint():
    """Manually flushes the optimization cache dict."""
    clear_optimization_cache()
    logger.info("Optimization cache manually cleared.")
    return {"status": "success", "message": "Optimization cache cleared successfully"}


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
    Returns cached solution if invoked with identical parameters within 15 minutes.
    """
    allow_lighterage = payload.allow_lighterage if payload.allow_lighterage is not None else True
    cache_key = (
        round(float(payload.required_cargo_mt), 2),
        str(payload.target_port).strip().lower(),
        str(payload.origin_port or "Australia").strip().lower(),
        int(payload.planning_horizon_days),
        round(float(payload.disruption_multiplier or 1.0), 4),
        str(payload.disruption_name or "").strip(),
        bool(allow_lighterage),
    )

    if not payload.force_refresh:
        cached_res = get_cached_optimization(cache_key)
        if cached_res is not None:
            logger.info(f"Returning cached MILP optimization response for key: {cache_key}")
            cached_copy = cached_res.model_copy()
            cached_copy.is_cached = True
            return cached_copy

    try:
        optimizer = VesselCharterOptimizer()
        result = optimizer.optimize_charter_plan(
            required_cargo_mt=payload.required_cargo_mt,
            target_port=payload.target_port,
            planning_horizon_days=payload.planning_horizon_days,
            origin_port=payload.origin_port or "Australia",
            disruption_multiplier=payload.disruption_multiplier or 1.0,
            allow_lighterage=allow_lighterage,
            db=db,
            force_refresh=bool(payload.force_refresh),
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

        # Strategic Procurement Engine: Spot vs. 6-Month COA Analysis
        coa_rate_usd_per_mt = None
        coa_total_cost_usd = None
        coa_savings_usd = None
        procurement_recommendation = None
        market_trend = None
        coa_discount_pct = None

        if result.get("status") == "Optimal" and result.get("total_estimated_cost_usd"):
            try:
                forecaster = FreightForecaster()
                primary_vessel = schedule_items[0].vessel_type if schedule_items else "Capesize"
                cargo_needed = float(result.get("required_cargo_mt") or payload.required_cargo_mt)
                spot_total_cost = float(result["total_estimated_cost_usd"])

                route_info = get_route_info(payload.origin_port)
                combined_multiplier = route_info["multiplier"] * (payload.disruption_multiplier or 1.0)

                coa_info = forecaster.get_medium_term_coa_rate(
                    vessel_type=primary_vessel,
                    required_cargo_mt=cargo_needed,
                    rate_multiplier=combined_multiplier,
                    db=db,
                )
                coa_rate_usd_per_mt = coa_info.get("rate")
                market_trend = coa_info.get("trend", "STABLE")
                coa_discount_pct = coa_info.get("discount_pct", 0.0)

                coa_total_cost_usd = round(cargo_needed * coa_rate_usd_per_mt, 2)
                if result.get("strategy_used") == "MID_SEA_LIGHTERAGE":
                    coa_total_cost_usd += float(result.get("lighterage_penalty_applied", 0.0))
                    coa_total_cost_usd = round(coa_total_cost_usd, 2)

                # Enhanced Recommendation Logic:
                # If COA is strictly cheaper -> LOCK_IN_COA
                # Contango Override: If market_trend == "CONTANGO" AND coa_total_cost_usd is within 5% of spot_total_cost,
                # force recommendation to "LOCK_IN_COA" to hedge against impending rate hikes.
                if coa_total_cost_usd < spot_total_cost:
                    procurement_recommendation = "LOCK_IN_COA"
                    coa_savings_usd = round(spot_total_cost - coa_total_cost_usd, 2)
                elif market_trend == "CONTANGO" and ((coa_total_cost_usd - spot_total_cost) / (spot_total_cost or 1.0)) <= 0.05:
                    procurement_recommendation = "LOCK_IN_COA"
                    coa_savings_usd = round(spot_total_cost * 0.08, 2)  # Projected 8% rate hike avoidance
                else:
                    procurement_recommendation = "STAY_SPOT"
                    coa_savings_usd = round(coa_total_cost_usd - spot_total_cost, 2)

                logger.info(
                    f"Strategic Procurement Analysis: Spot=${spot_total_cost:,.2f} vs COA=${coa_total_cost_usd:,.2f} "
                    f"(@${coa_rate_usd_per_mt}/MT, Disc={coa_discount_pct}%, Trend={market_trend}) -> "
                    f"Recommendation: {procurement_recommendation} (Savings=${coa_savings_usd:,.2f})"
                )
            except Exception as coa_err:
                logger.warning(f"Could not compute strategic COA rate ({coa_err}).")

        response = OptimizationResponse(
            status=result["status"],
            target_port=result.get("target_port"),
            origin_port=result.get("origin_port"),
            route=route_str,
            port_max_draft_m=result.get("port_max_draft_m"),
            port_max_loa_m=result.get("port_max_loa_m"),
            port_max_beam_m=result.get("port_max_beam_m"),
            port_handling_rate_tpd=result.get("port_handling_rate_tpd"),
            port_waiting_hours=result.get("port_waiting_hours"),
            port_turnaround_days=result.get("port_turnaround_days"),
            deadheading_cost_usd=result.get("deadheading_cost_usd"),
            idle_time_penalty_usd=result.get("idle_time_penalty_usd"),
            required_cargo_mt=result.get("required_cargo_mt"),
            total_cargo_allocated_mt=result.get("total_cargo_allocated_mt"),
            total_estimated_cost_usd=float(result["total_estimated_cost_usd"]),
            estimated_savings_usd=float(result["estimated_savings_usd"]),
            benchmark_naive_cost_usd=result.get("benchmark_naive_cost_usd"),
            vessel_schedule=schedule_items,
            strategy_used=result.get("strategy_used", "DIRECT_DISCHARGE"),
            lighterage_penalty_applied=float(result.get("lighterage_penalty_applied", 0.0)),
            lighterage_vessel_type=result.get("lighterage_vessel_type"),
            lighterage_vessel_count=result.get("lighterage_vessel_count"),
            lighterage_strictly_cheaper=result.get("lighterage_strictly_cheaper"),
            lighterage_cost_premium=result.get("lighterage_cost_premium"),
            coa_rate_usd_per_mt=coa_rate_usd_per_mt,
            coa_total_cost_usd=coa_total_cost_usd,
            coa_savings_usd=coa_savings_usd,
            procurement_recommendation=procurement_recommendation,
            market_trend=market_trend,
            coa_discount_pct=coa_discount_pct,
            message=result.get("message"),
        )

        # Log optimization audit to database if schedule was formed
        try:
            db.rollback()
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
            db.rollback()
            logger.warning(f"Could not persist optimization log to database ({log_err}).")

        # Cache response under key for 15 minutes
        set_cached_optimization(cache_key, response)
        return response

    except Exception as e:
        logger.error(f"Optimization execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"MILP optimization engine failed: {str(e)}",
        )
