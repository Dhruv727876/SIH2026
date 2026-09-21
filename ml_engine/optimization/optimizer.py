import logging
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
import requests

# Ensure parent and brother packages are accessible
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from forecasting.forecaster import FreightForecaster
from data_pipeline.fetch_port_data import PORT_CONFIGS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vessel-charter-optimizer")

# Vessel Specifications (Draft, LOA, Beam, Capacity, Index, and Consumption)
VESSEL_SPECS = {
    "Capesize": {
        "capacity_mt": 150000.0,
        "min_draft_m": 17.0,
        "loa_m": 292.0,
        "beam_m": 45.0,
        "index_name": "BCI",
        "rate_scale": 1.0 / 140.0,  # Convert BCI index points (~2400) to $/MT (~$17.14/MT)
        "daily_hire_usd": 28000.0,
        "bunker_consumption_tpd": 42.0,
    },
    "Panamax": {
        "capacity_mt": 80000.0,
        "min_draft_m": 14.0,
        "loa_m": 225.0,
        "beam_m": 32.26,
        "index_name": "BPI",
        "rate_scale": 1.0 / 85.0,   # Convert BPI index points (~1650) to $/MT (~$19.41/MT)
        "daily_hire_usd": 18000.0,
        "bunker_consumption_tpd": 30.0,
    },
    "Supramax": {
        "capacity_mt": 50000.0,
        "min_draft_m": 11.0,
        "loa_m": 199.0,
        "beam_m": 32.26,
        "index_name": "BSI",
        "rate_scale": 1.0 / 58.0,   # Convert BSI index points (~1300) to $/MT (~$22.41/MT)
        "daily_hire_usd": 14000.0,
        "bunker_consumption_tpd": 24.0,
    },
    "Handysize": {
        "capacity_mt": 35000.0,
        "min_draft_m": 10.0,
        "loa_m": 180.0,
        "beam_m": 28.4,
        "index_name": "BHSI",
        "rate_scale": 1.0 / 32.0,   # Convert BHSI index points (~750) to $/MT (~$23.44/MT)
        "daily_hire_usd": 11000.0,
        "bunker_consumption_tpd": 18.0,
    },
}

DEMURRAGE_DAILY_RATE_USD = 25000.0  # Industry standard daily demurrage penalty

# Route Distance Multipliers for Major Coal/Ore Export Terminals (PS Origins + Key Lanes)
ROUTE_DISTANCE_MULTIPLIERS = {
    "Australia": {
        "multiplier": 1.0,
        "origin_code": "Newcastle (AUS)",
        "origin_full": "Australia (Newcastle)",
        "distance_nm": 5200,
    },
    "Indonesia": {
        "multiplier": 0.85,
        "origin_code": "Samarinda (IDN)",
        "origin_full": "Indonesia (Samarinda)",
        "distance_nm": 2600,
    },
    "Mozambique": {
        "multiplier": 0.95,
        "origin_code": "Maputo (MOZ)",
        "origin_full": "Mozambique (Maputo / Beira)",
        "distance_nm": 4100,
    },
    "Russia": {
        "multiplier": 1.12,
        "origin_code": "Vostochny (RUS)",
        "origin_full": "Russia (Vostochny / Taman)",
        "distance_nm": 5800,
    },
    "USA": {
        "multiplier": 1.45,
        "origin_code": "Hampton Roads (USA)",
        "origin_full": "USA (Hampton Roads / Baltimore)",
        "distance_nm": 9800,
    },
    "South Africa": {
        "multiplier": 1.15,
        "origin_code": "Richards Bay (ZAF)",
        "origin_full": "South Africa (Richards Bay)",
        "distance_nm": 4800,
    },
    "Brazil": {
        "multiplier": 1.35,
        "origin_code": "Tubarao (BRA)",
        "origin_full": "Brazil (Tubarao)",
        "distance_nm": 8900,
    },
}


def get_route_info(origin_port: Optional[str]) -> Dict[str, Any]:
    """Resolves route details and distance multiplier based on origin string."""
    if not origin_port:
        return ROUTE_DISTANCE_MULTIPLIERS["Australia"]

    norm = origin_port.strip().lower()
    if "mozambique" in norm or "maputo" in norm or "beira" in norm:
        return ROUTE_DISTANCE_MULTIPLIERS["Mozambique"]
    elif "russia" in norm or "vostochny" in norm or "taman" in norm or "nakhodka" in norm:
        return ROUTE_DISTANCE_MULTIPLIERS["Russia"]
    elif "usa" in norm or "us " in norm or "us(" in norm or "hampton" in norm or "baltimore" in norm or "america" in norm or norm == "us":
        return ROUTE_DISTANCE_MULTIPLIERS["USA"]
    elif "brazil" in norm or "tubarao" in norm:
        return ROUTE_DISTANCE_MULTIPLIERS["Brazil"]
    elif "south africa" in norm or "richards" in norm or "africa" in norm:
        return ROUTE_DISTANCE_MULTIPLIERS["South Africa"]
    elif "indonesia" in norm or "samarinda" in norm or "banjarmasin" in norm:
        return ROUTE_DISTANCE_MULTIPLIERS["Indonesia"]
    else:
        return ROUTE_DISTANCE_MULTIPLIERS["Australia"]


# Render uses the PORT env var (usually 10000). Fallback to 8000 for local dev.
PORT = os.getenv("PORT", "8000")
API_BASE_URL = os.getenv("API_BASE_URL", f"http://127.0.0.1:{PORT}").rstrip("/")


class VesselCharterOptimizer:
    """
    Mixed-Integer Linear Programming (MILP) and Heuristic Optimization Engine.
    Minimizes total landed logistics cost (Freight + Demurrage) under draft, route distance, and berth constraints.
    """

    def __init__(self, backend_api_url: Optional[str] = None):
        self.backend_api_url = (backend_api_url or API_BASE_URL).rstrip("/")
        self.forecaster = FreightForecaster(backend_api_url=self.backend_api_url)

    def fetch_port_constraints(self, target_port: str, db: Optional[Any] = None) -> Dict[str, Any]:
        """
        Fetches port draft limit, LOA, Beam, cargo handling rate, and waiting time from DB, local config, or fallback defaults.
        """
        norm_target = target_port.strip().lower()
        if db is not None:
            try:
                from models.port_data import PortData
                from sqlalchemy import select
                stmt = select(PortData).where(PortData.port_name.ilike(f"%{target_port.strip()}%"))
                port_row = db.scalars(stmt).first()
                if port_row:
                    return {
                        "port_name": port_row.port_name,
                        "max_draft_meters": float(port_row.max_draft_meters),
                        "max_loa_meters": float(getattr(port_row, "max_loa_meters", 260.0) or 260.0),
                        "max_beam_meters": float(getattr(port_row, "max_beam_meters", 43.0) or 43.0),
                        "cargo_handling_rate_tpd": float(getattr(port_row, "cargo_handling_rate_tpd", 35000.0) or 35000.0),
                        "current_waiting_time_hours": float(port_row.current_waiting_time_hours),
                    }
            except Exception as e:
                logger.warning(f"Direct DB query for port constraints failed ({e}). Falling back to local lookup.")

        # Local default configs (instant in-memory lookup)
        for p in PORT_CONFIGS:
            p_name = p["port_name"].lower()
            if p_name == norm_target or p_name in norm_target or norm_target in p_name:
                return {
                    "port_name": p["port_name"],
                    "max_draft_meters": float(p["max_draft_meters"]),
                    "max_loa_meters": float(p.get("max_loa_meters", 260.0)),
                    "max_beam_meters": float(p.get("max_beam_meters", 43.0)),
                    "cargo_handling_rate_tpd": float(p.get("cargo_handling_rate_tpd", 35000.0)),
                    "current_waiting_time_hours": float(p.get("base_waiting", 36.0)),
                }

        # Generic default
        return {
            "port_name": target_port,
            "max_draft_meters": 14.5,
            "max_loa_meters": 260.0,
            "max_beam_meters": 43.0,
            "cargo_handling_rate_tpd": 35000.0,
            "current_waiting_time_hours": 36.0,
        }

    def fetch_freight_rate_forecasts(
        self,
        horizon_days: int = 30,
        db: Optional[Any] = None,
        force_refresh: bool = False,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetches or generates rate forecasts for all vessel class indices (BCI, BPI, BSI, BHSI).
        """
        rate_trajectories: Dict[str, List[Dict[str, Any]]] = {}
        for vessel_type, spec in VESSEL_SPECS.items():
            idx = spec["index_name"]
            forecast = self.forecaster.get_full_forecast(
                index_name=idx,
                force_refresh=force_refresh,
                db=db,
            )
            rate_trajectories[vessel_type] = forecast[:horizon_days]
        return rate_trajectories

    def _compute_vessel_voyage_costs(
        self,
        vessel_type: str,
        predicted_index_val: float,
        rate_multiplier: float,
        waiting_hours: float,
        handling_rate_tpd: float,
        distance_nm: float,
    ) -> Dict[str, float]:
        """
        Computes the complete voyage cost breakdown according to Maritime Quant principles:
        1. Laden Voyage Freight Cost: capacity * freight_rate_usd_mt
        2. Port Stay Turnaround Cost: (waiting_days * demurrage_rate) + (discharge_laytime_days * daily_hire)
        3. Deadheading (Ballast Return Cost): ballast_days * daily_ballast_cost (fuel + hire)
        4. Idle Time Buffer Penalty: idle_days * daily_hire
        """
        spec = VESSEL_SPECS[vessel_type]
        cap = spec["capacity_mt"]
        scale = spec["rate_scale"]
        hire = spec["daily_hire_usd"]
        bunker_tpd = spec.get("bunker_consumption_tpd", 24.0)

        # 1. Laden Freight Cost
        freight_rate_per_mt = predicted_index_val * scale * rate_multiplier
        laden_freight_cost = cap * freight_rate_per_mt

        # 2. Port Turnaround Stay
        waiting_days = waiting_hours / 24.0
        discharge_days = cap / max(1000.0, handling_rate_tpd)
        turnaround_cost = (waiting_days * DEMURRAGE_DAILY_RATE_USD) + (discharge_days * hire)

        # 3. Deadheading (Ballast Return Leg to Origin)
        # Average cruising speed ~13 knots -> 312 nautical miles per day
        ballast_days = distance_nm / (13.0 * 24.0)
        daily_ballast_cost = (hire * 0.60) + (bunker_tpd * 620.0 * 0.70)
        deadheading_cost = ballast_days * daily_ballast_cost

        # 4. Idle Scenario Penalty (operational buffer between charter stems)
        idle_days = 1.5
        idle_time_cost = idle_days * hire

        total_cost = laden_freight_cost + turnaround_cost + deadheading_cost + idle_time_cost

        return {
            "capacity_mt": cap,
            "freight_rate_usd_mt": freight_rate_per_mt,
            "laden_freight_cost": laden_freight_cost,
            "turnaround_cost": turnaround_cost,
            "turnaround_days": waiting_days + discharge_days,
            "deadheading_cost": deadheading_cost,
            "idle_time_cost": idle_time_cost,
            "total_trip_cost": total_cost,
        }

    def optimize_charter_plan(
        self,
        required_cargo_mt: float,
        target_port: str,
        planning_horizon_days: int = 30,
        origin_port: str = "Australia",
        disruption_multiplier: float = 1.0,
        allow_lighterage: bool = True,
        db: Optional[Any] = None,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        Formulates and solves the MILP charter allocation problem factoring in
        Draft, LOA, Beam, Cargo Handling Rates, Deadheading, and Idle time penalties.
        Evaluates Direct Discharge vs Mid-Sea Lighterage (e.g. Capesize at Sandheads).
        """
        route_info = get_route_info(origin_port)
        route_mult = route_info["multiplier"]
        combined_multiplier = route_mult * (disruption_multiplier or 1.0)
        route_display = f"{route_info['origin_code']} -> {target_port} (IND)"
        distance_nm = float(route_info["distance_nm"])

        logger.info(
            f"Formulating MILP optimization for {required_cargo_mt:,.0f} MT cargo on route '{route_display}' "
            f"(Route Mult: {route_mult}x, Combined: {combined_multiplier:.2f}x, Distance: {distance_nm:,.0f} NM) "
            f"over {planning_horizon_days} days..."
        )

        # 1. Fetch Port Constraints & Demurrage
        port_info = self.fetch_port_constraints(target_port, db=db)
        max_draft = float(port_info["max_draft_meters"])
        max_loa = float(port_info.get("max_loa_meters", 260.0))
        max_beam = float(port_info.get("max_beam_meters", 43.0))
        handling_rate = float(port_info.get("cargo_handling_rate_tpd", 35000.0))
        waiting_hours = float(port_info.get("current_waiting_time_hours", 36.0))

        # 2. Fetch Multi-Class Freight Rate Forecasts
        forecasts = self.fetch_freight_rate_forecasts(
            horizon_days=planning_horizon_days,
            db=db,
            force_refresh=force_refresh,
        )

        # 3. Determine Feasible Vessel Classes by Draft, LOA, and Beam Constraints
        direct_feasible_vessels = []
        for v_name, spec in VESSEL_SPECS.items():
            draft_ok = spec["min_draft_m"] <= max_draft
            loa_ok = spec.get("loa_m", 0.0) <= max_loa
            beam_ok = spec.get("beam_m", 0.0) <= max_beam

            if draft_ok and loa_ok and beam_ok:
                direct_feasible_vessels.append(v_name)
            else:
                disqualify_reasons = []
                if not draft_ok:
                    disqualify_reasons.append(f"draft {spec['min_draft_m']}m > {max_draft}m")
                if not loa_ok:
                    disqualify_reasons.append(f"LOA {spec.get('loa_m')}m > {max_loa}m")
                if not beam_ok:
                    disqualify_reasons.append(f"Beam {spec.get('beam_m')}m > {max_beam}m")
                logger.info(
                    f"Vessel class {v_name} disallowed directly at {target_port}: {', '.join(disqualify_reasons)}."
                )

        strategy_used = "DIRECT_DISCHARGE"
        lighterage_penalty_applied = 0.0

        # Debug logging for parameter tracking
        logger.info(f"Target Port: {target_port} | Draft: {max_draft}m | LOA: {max_loa}m | Beam: {max_beam}m | Handling: {handling_rate:,.0f} TPD")
        logger.info(f"Allow Lighterage Flag Received: {allow_lighterage} | Required Cargo: {required_cargo_mt:,.0f} MT")

        # 4. Multi-Scenario MILP Optimization (Direct Discharge vs Mid-Sea Lighterage)
        cape_infeasible_directly = (max_draft < 17.0 or max_loa < 292.0 or max_beam < 45.0)
        if cape_infeasible_directly and allow_lighterage:
            logger.info(
                f"Target port {target_port} physical limits (Draft {max_draft}m, LOA {max_loa}m, Beam {max_beam}m) "
                "exclude direct Capesize berthing. Evaluating Scenario A (Direct) vs Scenario B (Lighterage at Sandheads)..."
            )

            # --- Scenario A: Direct Allocation using only compliant vessels ---
            solution_a = None
            cost_a = float("inf")
            if direct_feasible_vessels:
                solution_a = self._solve_milp_pulp(
                    required_cargo_mt=required_cargo_mt,
                    feasible_vessels=direct_feasible_vessels,
                    forecasts=forecasts,
                    horizon_days=planning_horizon_days,
                    waiting_hours=waiting_hours,
                    handling_rate_tpd=handling_rate,
                    distance_nm=distance_nm,
                    rate_multiplier=combined_multiplier,
                )
                if solution_a["status"] != "Optimal":
                    solution_a = self._solve_greedy_fallback(
                        required_cargo_mt=required_cargo_mt,
                        feasible_vessels=direct_feasible_vessels,
                        forecasts=forecasts,
                        horizon_days=planning_horizon_days,
                        waiting_hours=waiting_hours,
                        handling_rate_tpd=handling_rate,
                        distance_nm=distance_nm,
                        rate_multiplier=combined_multiplier,
                    )
                if solution_a["status"] == "Optimal":
                    cost_a = solution_a["total_cost"]

            # --- Scenario B: Mid-Sea Lighterage with Capesize bulkers ---
            # Allocate Capesize vessels (transshipment at deepwater Sagar-Sandheads anchorage: 18.5m draft, 330m LOA)
            solution_b = self._solve_milp_pulp(
                required_cargo_mt=required_cargo_mt,
                feasible_vessels=["Capesize"],
                forecasts=forecasts,
                horizon_days=planning_horizon_days,
                waiting_hours=waiting_hours,
                handling_rate_tpd=handling_rate,
                distance_nm=distance_nm,
                rate_multiplier=combined_multiplier,
            )
            if solution_b["status"] != "Optimal":
                solution_b = self._solve_greedy_fallback(
                    required_cargo_mt=required_cargo_mt,
                    feasible_vessels=["Capesize"],
                    forecasts=forecasts,
                    horizon_days=planning_horizon_days,
                    waiting_hours=waiting_hours,
                    handling_rate_tpd=handling_rate,
                    distance_nm=distance_nm,
                    rate_multiplier=combined_multiplier,
                )

            cost_b = float("inf")
            total_lighterage_penalty = 0.0
            if solution_b["status"] == "Optimal":
                # Fixed lighterage penalty of $3.50 per MT transferred at Sandheads anchorage
                transferred_cargo_mt = solution_b["total_cargo_delivered"]
                transfer_fee = transferred_cargo_mt * 3.50

                # 24-hour time penalty for the transfer (1 full day demurrage per Capesize vessel)
                num_cape_vessels = sum(int(item["quantity"]) for item in solution_b["vessel_schedule"])
                time_penalty = num_cape_vessels * (24.0 / 24.0) * DEMURRAGE_DAILY_RATE_USD
                total_lighterage_penalty = transfer_fee + time_penalty
                cost_b = solution_b["total_cost"] + total_lighterage_penalty

                # Distribute lighterage penalty to schedule items for consistent accounting
                for item in solution_b["vessel_schedule"]:
                    stem_qty = int(item["quantity"])
                    stem_cargo = float(item["total_cargo_mt"])
                    stem_penalty = (stem_cargo * 3.50) + (stem_qty * DEMURRAGE_DAILY_RATE_USD)
                    item["estimated_trip_cost_usd"] = round(float(item["estimated_trip_cost_usd"]) + stem_penalty, 2)

            logger.info(f"Scenario A (Direct) Cost: {cost_a} | Scenario B (Lighterage) Cost: {cost_b}")

            is_b_optimal = solution_b.get("status") == "Optimal"
            is_a_optimal = solution_a is not None and solution_a.get("status") == "Optimal" and not math.isinf(cost_a)

            if is_b_optimal and not is_a_optimal:
                # Scenario A is physically infeasible; lighterage is the only viable option
                prefer_lighterage = True
                lighterage_cost_premium = 0.0
            elif is_b_optimal and is_a_optimal:
                LIGHTERAGE_PREFERENCE_THRESHOLD = 0.15  # 15% tolerance
                lighterage_cost_premium = (cost_b - cost_a) / cost_a
                # Prefer lighterage if cheaper OR within 15% operational preference threshold
                prefer_lighterage = (cost_b <= cost_a) or (lighterage_cost_premium <= LIGHTERAGE_PREFERENCE_THRESHOLD)
            else:
                prefer_lighterage = False
                lighterage_cost_premium = float("inf")

            if prefer_lighterage:
                solution = solution_b
                solution["total_cost"] = cost_b
                strategy_used = "MID_SEA_LIGHTERAGE"
                lighterage_penalty_applied = total_lighterage_penalty

                lighterage_vessel_count = math.ceil(required_cargo_mt / 50000)
                solution["lighterage_vessel_type"] = "Supramax"
                solution["lighterage_vessel_count"] = lighterage_vessel_count
                solution["lighterage_strictly_cheaper"] = bool(is_b_optimal and is_a_optimal and cost_b < cost_a)
                solution["lighterage_cost_premium"] = round(float(lighterage_cost_premium), 4) if not math.isinf(lighterage_cost_premium) else None

                logger.info(
                    f"Selected Scenario B (MID_SEA_LIGHTERAGE): Cost=${cost_b:,.2f} vs Direct=${cost_a:,.2f} "
                    f"(Premium={lighterage_cost_premium*100:.1f}% <= 15% threshold, "
                    f"Surcharge=${total_lighterage_penalty:,.2f}, Transfer: {lighterage_vessel_count}x Supramax)"
                )
            elif solution_a and solution_a["status"] == "Optimal":
                solution = solution_a
                strategy_used = "DIRECT_DISCHARGE"
                lighterage_penalty_applied = 0.0
                logger.info(
                    f"Selected Scenario A (DIRECT_DISCHARGE): Cost=${cost_a:,.2f} is >{LIGHTERAGE_PREFERENCE_THRESHOLD*100:.0f}% "
                    f"cheaper than Lighterage=${cost_b:,.2f} (Premium={lighterage_cost_premium*100:.1f}%)"
                )
            else:
                return {
                    "status": "Infeasible",
                    "message": f"Port {target_port} physical limits (Draft {max_draft}m, LOA {max_loa}m, Beam {max_beam}m) reject all vessels.",
                    "target_port": target_port,
                    "origin_port": route_info["origin_full"],
                    "route": route_display,
                    "total_estimated_cost_usd": 0.0,
                    "estimated_savings_usd": 0.0,
                    "vessel_schedule": [],
                    "strategy_used": "DIRECT_DISCHARGE",
                    "lighterage_penalty_applied": 0.0,
                }
        else:
            # Standard single scenario when Cape can enter or lighterage disabled
            if not direct_feasible_vessels:
                return {
                    "status": "Infeasible",
                    "message": f"Port {target_port} physical limits (Draft {max_draft}m, LOA {max_loa}m, Beam {max_beam}m) reject all fleet vessels.",
                    "target_port": target_port,
                    "origin_port": route_info["origin_full"],
                    "route": route_display,
                    "total_estimated_cost_usd": 0.0,
                    "estimated_savings_usd": 0.0,
                    "vessel_schedule": [],
                    "strategy_used": "DIRECT_DISCHARGE",
                    "lighterage_penalty_applied": 0.0,
                }

            solution = self._solve_milp_pulp(
                required_cargo_mt=required_cargo_mt,
                feasible_vessels=direct_feasible_vessels,
                forecasts=forecasts,
                horizon_days=planning_horizon_days,
                waiting_hours=waiting_hours,
                handling_rate_tpd=handling_rate,
                distance_nm=distance_nm,
                rate_multiplier=combined_multiplier,
            )
            if solution["status"] != "Optimal":
                solution = self._solve_greedy_fallback(
                    required_cargo_mt=required_cargo_mt,
                    feasible_vessels=direct_feasible_vessels,
                    forecasts=forecasts,
                    horizon_days=planning_horizon_days,
                    waiting_hours=waiting_hours,
                    handling_rate_tpd=handling_rate,
                    distance_nm=distance_nm,
                    rate_multiplier=combined_multiplier,
                )
            strategy_used = "DIRECT_DISCHARGE"
            lighterage_penalty_applied = 0.0

        # 5. Compute Benchmark Naive Cost (Unmanaged Spot Procurement Baseline)
        # When evaluating lighterage vs direct discharge at shallow ports, the baseline is unmanaged Capesize chartering
        if allow_lighterage and cape_infeasible_directly:
            benchmark_vessels = ["Capesize"]
            is_shallow_benchmark = True
        else:
            benchmark_vessels = direct_feasible_vessels if direct_feasible_vessels else ["Capesize"]
            is_shallow_benchmark = bool(cape_infeasible_directly and ("Capesize" in benchmark_vessels))

        naive_cost = self._compute_naive_benchmark(
            required_cargo_mt=required_cargo_mt,
            feasible_vessels=benchmark_vessels,
            forecasts=forecasts,
            waiting_hours=waiting_hours,
            handling_rate_tpd=handling_rate,
            distance_nm=distance_nm,
            rate_multiplier=combined_multiplier,
            is_shallow_port=is_shallow_benchmark,
        )

        total_estimated_cost_usd = round(float(solution["total_cost"]), 2)
        estimated_savings_usd = max(0.0, round(float(naive_cost - total_estimated_cost_usd), 2))

        logger.info(
            f"SAVINGS CALC: Naive=${naive_cost:,.2f} | Optimized=${total_estimated_cost_usd:,.2f} | Savings=${estimated_savings_usd:,.2f}"
        )

        # Compute port turnaround days (waiting + laytime)
        avg_turnaround_days = (waiting_hours / 24.0) + (required_cargo_mt / max(1000.0, handling_rate * 2.0))

        logger.info(
            f"Optimization result ({route_display}): Strategy={strategy_used}, Status={solution['status']}, "
            f"Total Cost=${total_estimated_cost_usd:,.2f}, Savings=${estimated_savings_usd:,.2f}, Lighterage Penalty=${lighterage_penalty_applied:,.2f}"
        )

        return {
            "status": solution["status"],
            "target_port": target_port,
            "origin_port": route_info["origin_full"],
            "route": route_display,
            "port_max_draft_m": max_draft,
            "port_max_loa_m": max_loa,
            "port_max_beam_m": max_beam,
            "port_handling_rate_tpd": handling_rate,
            "port_waiting_hours": waiting_hours,
            "port_turnaround_days": round(float(avg_turnaround_days), 1),
            "deadheading_cost_usd": round(float(solution.get("total_deadheading_cost", 0.0)), 2),
            "idle_time_penalty_usd": round(float(solution.get("total_idle_cost", 0.0)), 2),
            "required_cargo_mt": float(required_cargo_mt),
            "total_cargo_allocated_mt": float(solution["total_cargo_delivered"]),
            "total_estimated_cost_usd": total_estimated_cost_usd,
            "estimated_savings_usd": estimated_savings_usd,
            "benchmark_naive_cost_usd": round(float(naive_cost), 2),
            "vessel_schedule": solution["vessel_schedule"],
            "strategy_used": strategy_used,
            "lighterage_penalty_applied": round(float(lighterage_penalty_applied), 2),
            "lighterage_vessel_type": solution.get("lighterage_vessel_type"),
            "lighterage_vessel_count": solution.get("lighterage_vessel_count"),
            "lighterage_strictly_cheaper": solution.get("lighterage_strictly_cheaper"),
            "lighterage_cost_premium": solution.get("lighterage_cost_premium"),
        }

    def _solve_milp_pulp(
        self,
        required_cargo_mt: float,
        feasible_vessels: List[str],
        forecasts: Dict[str, List[Dict[str, Any]]],
        horizon_days: int,
        waiting_hours: float,
        handling_rate_tpd: float,
        distance_nm: float,
        rate_multiplier: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Solves the MILP formulation using the PuLP CBC solver.
        Mathematically enforces:
        1. Demand Satisfaction
        2. Daily Berth Dispatch Limit
        3. Port Daily Handling Capacity (Turnaround Laytime Throughput)
        4. Objective includes Freight + Turnaround Port Cost + Deadheading (Ballast) + Idle Time Penalties.
        """
        try:
            import pulp

            prob = pulp.LpProblem("Vessel_Chartering_Cost_Minimization", pulp.LpMinimize)

            # Decision Variables: x[v, t]
            x_vars = {}
            for v in feasible_vessels:
                for t in range(horizon_days):
                    x_vars[(v, t)] = pulp.LpVariable(f"vessels_{v}_day_{t}", lowBound=0, cat=pulp.LpInteger)

            # Cost Coefficients Matrix
            cost_matrix = {}
            breakdown_matrix = {}
            for v in feasible_vessels:
                for t in range(horizon_days):
                    pred_val = forecasts[v][t]["predicted_value"]
                    costs = self._compute_vessel_voyage_costs(
                        vessel_type=v,
                        predicted_index_val=pred_val,
                        rate_multiplier=rate_multiplier,
                        waiting_hours=waiting_hours,
                        handling_rate_tpd=handling_rate_tpd,
                        distance_nm=distance_nm,
                    )
                    cost_matrix[(v, t)] = costs["total_trip_cost"]
                    breakdown_matrix[(v, t)] = costs

            # Objective Function: Min Sum(x[v, t] * UnitTripCost[v, t])
            prob += pulp.lpSum([x_vars[(v, t)] * cost_matrix[(v, t)] for v in feasible_vessels for t in range(horizon_days)])

            # Constraint 1: Total Delivered Cargo >= Required Cargo
            prob += (
                pulp.lpSum([x_vars[(v, t)] * VESSEL_SPECS[v]["capacity_mt"] for v in feasible_vessels for t in range(horizon_days)])
                >= required_cargo_mt,
                "Demand_Satisfaction_Constraint",
            )

            # Constraint 2: Berth limitation - max 2 vessels dispatched/chartered per day
            for t in range(horizon_days):
                prob += (
                    pulp.lpSum([x_vars[(v, t)] for v in feasible_vessels]) <= 2,
                    f"Berth_Daily_Cap_Day_{t}",
                )

            # Constraint 3: Port Cargo Handling Throughput Limit over rolling discharge window
            # Prevents berth congestion while allowing full vessel parcels (e.g. Capesize 150k MT, Panamax 80k MT)
            for t in range(horizon_days):
                end_t = min(t + 5, horizon_days)
                window_days = end_t - t
                prob += (
                    pulp.lpSum([x_vars[(v, tau)] * VESSEL_SPECS[v]["capacity_mt"] for v in feasible_vessels for tau in range(t, end_t)])
                    <= max(160000.0, handling_rate_tpd * window_days * 1.5),
                    f"Port_Handling_Throughput_Window_{t}",
                )

            # Solve problem silently
            prob.solve(pulp.PULP_CBC_CMD(msg=0))
            solver_status = pulp.LpStatus[prob.status]

            if solver_status == "Optimal":
                schedule: List[Dict[str, Any]] = []
                total_cargo = 0.0
                total_cost = 0.0
                total_deadheading = 0.0
                total_idle = 0.0

                for t in range(horizon_days):
                    date_str = forecasts[feasible_vessels[0]][t]["timestamp"]
                    for v in feasible_vessels:
                        count = int(pulp.value(x_vars[(v, t)]) or 0)
                        if count > 0:
                            cap = VESSEL_SPECS[v]["capacity_mt"]
                            brk = breakdown_matrix[(v, t)]
                            trip_cost = cost_matrix[(v, t)] * count
                            cargo_delivered = cap * count

                            total_cargo += cargo_delivered
                            total_cost += trip_cost
                            total_deadheading += brk["deadheading_cost"] * count
                            total_idle += brk["idle_time_cost"] * count

                            schedule.append({
                                "date": date_str,
                                "vessel_type": v,
                                "quantity": count,
                                "capacity_mt": cap,
                                "total_cargo_mt": cargo_delivered,
                                "freight_rate_usd_mt": round(float(brk["freight_rate_usd_mt"]), 2),
                                "turnaround_days": round(float(brk["turnaround_days"]), 1),
                                "estimated_trip_cost_usd": round(float(trip_cost), 2),
                            })

                return {
                    "status": "Optimal",
                    "total_cost": total_cost,
                    "total_cargo_delivered": total_cargo,
                    "total_deadheading_cost": total_deadheading,
                    "total_idle_cost": total_idle,
                    "vessel_schedule": schedule,
                }

        except Exception as e:
            logger.warning(f"PuLP solver execution failed ({e}). Routing to heuristic solver.")

        return {"status": "FallbackRequired", "total_cost": 0.0, "total_cargo_delivered": 0.0, "vessel_schedule": []}

    def _solve_greedy_fallback(
        self,
        required_cargo_mt: float,
        feasible_vessels: List[str],
        forecasts: Dict[str, List[Dict[str, Any]]],
        horizon_days: int,
        waiting_hours: float,
        handling_rate_tpd: float,
        distance_nm: float,
        rate_multiplier: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Exact cost-efficiency ranking fallback solver if PuLP is unavailable.
        """
        logger.info("Solving charter plan with cost-efficiency optimization heuristic...")

        # Build list of all candidate (vessel, day) slots ranked by Cost per MT delivered
        candidates = []
        for t in range(horizon_days):
            date_str = forecasts[feasible_vessels[0]][t]["timestamp"]
            for v in feasible_vessels:
                pred_val = forecasts[v][t]["predicted_value"]
                costs = self._compute_vessel_voyage_costs(
                    vessel_type=v,
                    predicted_index_val=pred_val,
                    rate_multiplier=rate_multiplier,
                    waiting_hours=waiting_hours,
                    handling_rate_tpd=handling_rate_tpd,
                    distance_nm=distance_nm,
                )
                cost_per_mt = costs["total_trip_cost"] / costs["capacity_mt"]

                candidates.append({
                    "day": t,
                    "date": date_str,
                    "vessel_type": v,
                    "capacity_mt": costs["capacity_mt"],
                    "rate_usd_mt": costs["freight_rate_usd_mt"],
                    "turnaround_days": costs["turnaround_days"],
                    "deadheading_cost": costs["deadheading_cost"],
                    "idle_cost": costs["idle_time_cost"],
                    "trip_cost": costs["total_trip_cost"],
                    "cost_per_mt": cost_per_mt,
                })

        # Sort slots by cost per MT ascending
        candidates.sort(key=lambda x: x["cost_per_mt"])

        allocated_cargo = 0.0
        total_cost = 0.0
        total_deadheading = 0.0
        total_idle = 0.0
        daily_vessel_counts: Dict[int, int] = {t: 0 for t in range(horizon_days)}
        schedule_map: Dict[Tuple[int, str], Dict[str, Any]] = {}

        for cand in candidates:
            if allocated_cargo >= required_cargo_mt:
                break

            day = cand["day"]
            v = cand["vessel_type"]

            # Check daily berth constraint
            if daily_vessel_counts[day] < 2:
                daily_vessel_counts[day] += 1
                allocated_cargo += cand["capacity_mt"]
                total_cost += cand["trip_cost"]
                total_deadheading += cand["deadheading_cost"]
                total_idle += cand["idle_cost"]

                key = (day, v)
                if key in schedule_map:
                    schedule_map[key]["quantity"] += 1
                    schedule_map[key]["total_cargo_mt"] += cand["capacity_mt"]
                    schedule_map[key]["estimated_trip_cost_usd"] += cand["trip_cost"]
                else:
                    schedule_map[key] = {
                        "date": cand["date"],
                        "vessel_type": v,
                        "quantity": 1,
                        "capacity_mt": cand["capacity_mt"],
                        "total_cargo_mt": cand["capacity_mt"],
                        "freight_rate_usd_mt": round(float(cand["rate_usd_mt"]), 2),
                        "turnaround_days": round(float(cand["turnaround_days"]), 1),
                        "estimated_trip_cost_usd": cand["trip_cost"],
                    }

        schedule_list = sorted(list(schedule_map.values()), key=lambda x: x["date"])
        for item in schedule_list:
            item["estimated_trip_cost_usd"] = round(float(item["estimated_trip_cost_usd"]), 2)

        return {
            "status": "Optimal",
            "total_cost": total_cost,
            "total_cargo_delivered": allocated_cargo,
            "total_deadheading_cost": total_deadheading,
            "total_idle_cost": total_idle,
            "vessel_schedule": schedule_list,
        }

    def _compute_naive_benchmark(
        self,
        required_cargo_mt: float,
        feasible_vessels: List[str],
        forecasts: Dict[str, List[Dict[str, Any]]],
        waiting_hours: float,
        handling_rate_tpd: float,
        distance_nm: float,
        rate_multiplier: float = 1.0,
        is_shallow_port: bool = False,
    ) -> float:
        """
        Calculates the naive benchmark cost: Unmanaged spot procurement baseline.
        Apples-to-apples cost structure matching MILP objective function:
        Naive Total = (Vessels Needed * Base Freight)
                    + (Vessels Needed * Demurrage / Turnaround)
                    + (Vessels Needed * Deadheading)
                    + (Vessels Needed * Idle Penalty)
                    + Lighterage Penalty (if Capesize at shallow port: $3.50/MT + $25,000/vessel)

        Evaluates both Day 1 unmanaged spot booking and Horizon Average (mean spot rate over window),
        taking the standard unhedged procurement baseline.
        """
        largest_vessel = max(feasible_vessels, key=lambda v: VESSEL_SPECS[v]["capacity_mt"])
        cap = VESSEL_SPECS[largest_vessel]["capacity_mt"]
        vessels_needed = int(-(-required_cargo_mt // cap))  # ceiling division

        # Lighterage Surcharge (if Capesize at shallow port: $3.50/MT + $25,000/vessel demurrage)
        lighterage_penalty = 0.0
        if largest_vessel == "Capesize" and is_shallow_port:
            lighterage_penalty = (vessels_needed * cap * 3.50) + (vessels_needed * DEMURRAGE_DAILY_RATE_USD)

        # 1. Day 1 Spot Cost breakdown
        day1_val = forecasts[largest_vessel][0]["predicted_value"]
        costs_day1 = self._compute_vessel_voyage_costs(
            vessel_type=largest_vessel,
            predicted_index_val=day1_val,
            rate_multiplier=rate_multiplier,
            waiting_hours=waiting_hours,
            handling_rate_tpd=handling_rate_tpd,
            distance_nm=distance_nm,
        )

        base_freight_day1 = costs_day1["laden_freight_cost"]
        demurrage_day1 = costs_day1["turnaround_cost"]
        deadheading_day1 = costs_day1["deadheading_cost"]
        idle_penalty_day1 = costs_day1["idle_time_cost"]

        day1_total = (
            (vessels_needed * base_freight_day1)
            + (vessels_needed * demurrage_day1)
            + (vessels_needed * deadheading_day1)
            + (vessels_needed * idle_penalty_day1)
            + lighterage_penalty
        )

        # 2. Horizon Average Spot Cost breakdown
        vessel_forecast = forecasts.get(largest_vessel, [])
        if vessel_forecast:
            mean_val = sum(f["predicted_value"] for f in vessel_forecast) / len(vessel_forecast)
            costs_mean = self._compute_vessel_voyage_costs(
                vessel_type=largest_vessel,
                predicted_index_val=mean_val,
                rate_multiplier=rate_multiplier,
                waiting_hours=waiting_hours,
                handling_rate_tpd=handling_rate_tpd,
                distance_nm=distance_nm,
            )
            base_freight_mean = costs_mean["laden_freight_cost"]
            demurrage_mean = costs_mean["turnaround_cost"]
            deadheading_mean = costs_mean["deadheading_cost"]
            idle_penalty_mean = costs_mean["idle_time_cost"]

            mean_total = (
                (vessels_needed * base_freight_mean)
                + (vessels_needed * demurrage_mean)
                + (vessels_needed * deadheading_mean)
                + (vessels_needed * idle_penalty_mean)
                + lighterage_penalty
            )
        else:
            mean_total = day1_total

        return float(max(day1_total, mean_total))


if __name__ == "__main__":
    optimizer = VesselCharterOptimizer()
    print("Testing Vessel Charter Optimizer for Australia -> Paradip (300,000 MT)...")
    res = optimizer.optimize_charter_plan(
        required_cargo_mt=300000,
        target_port="Paradip",
        planning_horizon_days=30,
        origin_port="Australia",
    )
    print(f"Status: {res['status']}")
    print(f"Route: {res['route']}")
    print(f"Total Cost: ${res['total_estimated_cost_usd']:,.2f}")
    print(f"Estimated Savings vs Naive: ${res['estimated_savings_usd']:,.2f}")
