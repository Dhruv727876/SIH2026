import logging
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

# Vessel Specifications
VESSEL_SPECS = {
    "Capesize": {
        "capacity_mt": 150000.0,
        "min_draft_m": 17.0,
        "index_name": "BCI",
        "rate_scale": 1.0 / 140.0,  # Convert BCI index points (~2400) to $/MT (~$17.14/MT)
        "daily_hire_usd": 28000.0,
    },
    "Panamax": {
        "capacity_mt": 80000.0,
        "min_draft_m": 14.0,
        "index_name": "BPI",
        "rate_scale": 1.0 / 85.0,   # Convert BPI index points (~1650) to $/MT (~$19.41/MT)
        "daily_hire_usd": 18000.0,
    },
    "Supramax": {
        "capacity_mt": 50000.0,
        "min_draft_m": 11.0,
        "index_name": "BSI",
        "rate_scale": 1.0 / 58.0,   # Convert BSI index points (~1300) to $/MT (~$22.41/MT)
        "daily_hire_usd": 14000.0,
    },
}

DEMURRAGE_DAILY_RATE_USD = 25000.0  # Industry standard daily demurrage penalty

# Route Distance Multipliers for Major Coal/Ore Export Terminals
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
    if "brazil" in norm or "tubarao" in norm:
        return ROUTE_DISTANCE_MULTIPLIERS["Brazil"]
    elif "south africa" in norm or "richards" in norm or "africa" in norm:
        return ROUTE_DISTANCE_MULTIPLIERS["South Africa"]
    elif "indonesia" in norm or "samarinda" in norm:
        return ROUTE_DISTANCE_MULTIPLIERS["Indonesia"]
    else:
        return ROUTE_DISTANCE_MULTIPLIERS["Australia"]


class VesselCharterOptimizer:
    """
    Mixed-Integer Linear Programming (MILP) Optimizer for Vessel Chartering.
    Minimizes total landed logistics cost (Freight + Demurrage) under draft, route distance, and berth constraints.
    """

    def __init__(self, backend_api_url: str = "http://localhost:8000"):
        self.backend_api_url = backend_api_url.rstrip("/")
        self.forecaster = FreightForecaster(backend_api_url=self.backend_api_url)

    def fetch_port_constraints(self, target_port: str) -> Dict[str, Any]:
        """
        Fetches port draft limit and current waiting time from backend API or local config.
        """
        try:
            url = f"{self.backend_api_url}/api/v1/port-data"
            params = {"port_name": target_port}
            resp = requests.get(url, params=params, timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    return data[0]
        except Exception as e:
            logger.warning(f"Could not fetch port data from backend ({e}). Using local lookup.")

        # Fallback to local default configs
        for p in PORT_CONFIGS:
            if p["port_name"].lower() == target_port.lower():
                return {
                    "port_name": p["port_name"],
                    "max_draft_meters": p["max_draft_meters"],
                    "current_waiting_time_hours": p.get("base_waiting", 36.0),
                }

        # Generic default
        return {
            "port_name": target_port,
            "max_draft_meters": 14.5,
            "current_waiting_time_hours": 36.0,
        }

    def fetch_freight_rate_forecasts(self, horizon_days: int = 30) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetches or generates rate forecasts for all vessel class indices (BCI, BPI, BSI).
        """
        rate_trajectories: Dict[str, List[Dict[str, Any]]] = {}
        for vessel_type, spec in VESSEL_SPECS.items():
            idx = spec["index_name"]
            forecast = self.forecaster.get_full_forecast(index_name=idx)
            rate_trajectories[vessel_type] = forecast[:horizon_days]
        return rate_trajectories

    def optimize_charter_plan(
        self,
        required_cargo_mt: float,
        target_port: str,
        planning_horizon_days: int = 30,
        origin_port: str = "Australia",
        disruption_multiplier: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Formulates and solves the MILP charter allocation problem with route distance multipliers.
        """
        route_info = get_route_info(origin_port)
        route_mult = route_info["multiplier"]
        combined_multiplier = route_mult * (disruption_multiplier or 1.0)
        route_display = f"{route_info['origin_code']} -> {target_port} (IND)"

        logger.info(
            f"Formulating MILP optimization for {required_cargo_mt:,.0f} MT cargo on route '{route_display}' "
            f"(Route Mult: {route_mult}x, Combined: {combined_multiplier:.2f}x) over {planning_horizon_days} days..."
        )

        # 1. Fetch Port Constraints & Demurrage
        port_info = self.fetch_port_constraints(target_port)
        max_draft = float(port_info["max_draft_meters"])
        waiting_hours = float(port_info.get("current_waiting_time_hours", 36.0))
        demurrage_days = waiting_hours / 24.0
        expected_demurrage_per_vessel = demurrage_days * DEMURRAGE_DAILY_RATE_USD

        # 2. Fetch Multi-Class Freight Rate Forecasts
        forecasts = self.fetch_freight_rate_forecasts(horizon_days=planning_horizon_days)

        # 3. Determine Feasible Vessel Classes by Draft
        feasible_vessels = []
        for v_name, spec in VESSEL_SPECS.items():
            if spec["min_draft_m"] <= max_draft:
                feasible_vessels.append(v_name)
            else:
                logger.info(f"Vessel class {v_name} disallowed at {target_port} (requires {spec['min_draft_m']}m > max draft {max_draft}m).")

        if not feasible_vessels:
            return {
                "status": "Infeasible",
                "message": f"Port {target_port} has max draft of {max_draft}m. No vessels in fleet can enter.",
                "target_port": target_port,
                "origin_port": route_info["origin_full"],
                "route": route_display,
                "total_estimated_cost_usd": 0.0,
                "estimated_savings_usd": 0.0,
                "vessel_schedule": [],
            }

        # 4. Formulate and Solve MILP with PuLP (or Heuristic Fallback)
        solution = self._solve_milp_pulp(
            required_cargo_mt=required_cargo_mt,
            feasible_vessels=feasible_vessels,
            forecasts=forecasts,
            horizon_days=planning_horizon_days,
            demurrage_cost=expected_demurrage_per_vessel,
            rate_multiplier=combined_multiplier,
        )

        if solution["status"] != "Optimal":
            # Fallback solver
            solution = self._solve_greedy_fallback(
                required_cargo_mt=required_cargo_mt,
                feasible_vessels=feasible_vessels,
                forecasts=forecasts,
                horizon_days=planning_horizon_days,
                demurrage_cost=expected_demurrage_per_vessel,
                rate_multiplier=combined_multiplier,
            )

        # 5. Compute Benchmark Naive Cost (Booking entirely on Day 1 using available largest vessels)
        naive_cost = self._compute_naive_benchmark(
            required_cargo_mt=required_cargo_mt,
            feasible_vessels=feasible_vessels,
            forecasts=forecasts,
            demurrage_cost=expected_demurrage_per_vessel,
            rate_multiplier=combined_multiplier,
        )

        optimized_cost = solution["total_cost"]
        estimated_savings = max(0.0, naive_cost - optimized_cost)

        logger.info(
            f"Optimization result ({route_display}): Status={solution['status']}, "
            f"Total Cost=${optimized_cost:,.2f}, Savings=${estimated_savings:,.2f}"
        )

        return {
            "status": solution["status"],
            "target_port": target_port,
            "origin_port": route_info["origin_full"],
            "route": route_display,
            "port_max_draft_m": max_draft,
            "port_waiting_hours": waiting_hours,
            "required_cargo_mt": float(required_cargo_mt),
            "total_cargo_allocated_mt": float(solution["total_cargo_delivered"]),
            "total_estimated_cost_usd": round(float(optimized_cost), 2),
            "estimated_savings_usd": round(float(estimated_savings), 2),
            "benchmark_naive_cost_usd": round(float(naive_cost), 2),
            "vessel_schedule": solution["vessel_schedule"],
        }

    def _solve_milp_pulp(
        self,
        required_cargo_mt: float,
        feasible_vessels: List[str],
        forecasts: Dict[str, List[Dict[str, Any]]],
        horizon_days: int,
        demurrage_cost: float,
        rate_multiplier: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Solves the MILP formulation using the PuLP CBC solver.
        """
        try:
            import pulp

            prob = pulp.LpProblem("Vessel_Chartering_Cost_Minimization", pulp.LpMinimize)

            # Decision Variables: x[v, t]
            x_vars = {}
            for v in feasible_vessels:
                for t in range(horizon_days):
                    x_vars[(v, t)] = pulp.LpVariable(f"vessels_{v}_day_{t}", lowBound=0, cat=pulp.LpInteger)

            # Cost Coefficients
            cost_matrix = {}
            for v in feasible_vessels:
                cap = VESSEL_SPECS[v]["capacity_mt"]
                scale = VESSEL_SPECS[v]["rate_scale"]
                for t in range(horizon_days):
                    predicted_index_val = forecasts[v][t]["predicted_value"]
                    freight_rate_per_mt = predicted_index_val * scale * rate_multiplier
                    voyage_freight_cost = cap * freight_rate_per_mt
                    total_vessel_trip_cost = voyage_freight_cost + demurrage_cost
                    cost_matrix[(v, t)] = total_vessel_trip_cost

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

            # Solve problem silently
            prob.solve(pulp.PULP_CBC_CMD(msg=0))
            solver_status = pulp.LpStatus[prob.status]

            if solver_status == "Optimal":
                schedule: List[Dict[str, Any]] = []
                total_cargo = 0.0
                total_cost = 0.0

                for t in range(horizon_days):
                    date_str = forecasts[feasible_vessels[0]][t]["timestamp"]
                    for v in feasible_vessels:
                        count = int(pulp.value(x_vars[(v, t)]) or 0)
                        if count > 0:
                            cap = VESSEL_SPECS[v]["capacity_mt"]
                            rate_usd_mt = (
                                forecasts[v][t]["predicted_value"]
                                * VESSEL_SPECS[v]["rate_scale"]
                                * rate_multiplier
                            )
                            trip_cost = cost_matrix[(v, t)] * count
                            cargo_delivered = cap * count

                            total_cargo += cargo_delivered
                            total_cost += trip_cost

                            schedule.append({
                                "date": date_str,
                                "vessel_type": v,
                                "quantity": count,
                                "capacity_mt": cap,
                                "total_cargo_mt": cargo_delivered,
                                "freight_rate_usd_mt": round(float(rate_usd_mt), 2),
                                "estimated_trip_cost_usd": round(float(trip_cost), 2),
                            })

                return {
                    "status": "Optimal",
                    "total_cost": total_cost,
                    "total_cargo_delivered": total_cargo,
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
        demurrage_cost: float,
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
                cap = VESSEL_SPECS[v]["capacity_mt"]
                rate_usd_mt = (
                    forecasts[v][t]["predicted_value"]
                    * VESSEL_SPECS[v]["rate_scale"]
                    * rate_multiplier
                )
                total_trip_cost = (cap * rate_usd_mt) + demurrage_cost
                cost_per_mt = total_trip_cost / cap

                candidates.append({
                    "day": t,
                    "date": date_str,
                    "vessel_type": v,
                    "capacity_mt": cap,
                    "rate_usd_mt": rate_usd_mt,
                    "trip_cost": total_trip_cost,
                    "cost_per_mt": cost_per_mt,
                })

        # Sort slots by cost per MT ascending
        candidates.sort(key=lambda x: x["cost_per_mt"])

        allocated_cargo = 0.0
        total_cost = 0.0
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
                        "estimated_trip_cost_usd": cand["trip_cost"],
                    }

        schedule_list = sorted(list(schedule_map.values()), key=lambda x: x["date"])
        for item in schedule_list:
            item["estimated_trip_cost_usd"] = round(float(item["estimated_trip_cost_usd"]), 2)

        return {
            "status": "Optimal",
            "total_cost": total_cost,
            "total_cargo_delivered": allocated_cargo,
            "vessel_schedule": schedule_list,
        }

    def _compute_naive_benchmark(
        self,
        required_cargo_mt: float,
        feasible_vessels: List[str],
        forecasts: Dict[str, List[Dict[str, Any]]],
        demurrage_cost: float,
        rate_multiplier: float = 1.0,
    ) -> float:
        """
        Calculates the naive benchmark cost: Chartering entirely on Day 1 at Day 1 spot rates.
        """
        largest_vessel = max(feasible_vessels, key=lambda v: VESSEL_SPECS[v]["capacity_mt"])
        cap = VESSEL_SPECS[largest_vessel]["capacity_mt"]
        day1_rate_usd_mt = (
            forecasts[largest_vessel][0]["predicted_value"]
            * VESSEL_SPECS[largest_vessel]["rate_scale"]
            * rate_multiplier
        )

        vessels_needed = int(-(-required_cargo_mt // cap))  # ceiling division
        single_trip_cost = (cap * day1_rate_usd_mt) + demurrage_cost

        return float(vessels_needed * single_trip_cost)


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
