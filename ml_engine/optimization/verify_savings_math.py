"""
Standalone Verification Script: Audit and Remediation for Optimizer Savings Math.
Mathematically verifies:
1. Apples-to-apples penalty structure in naive benchmark vs optimizer.
2. Direct Discharge selected when cheaper than Lighterage at shallow ports.
3. Estimated savings strictly greater than zero (Savings > 0).
4. No double-counting of lighterage surcharge.
"""

import os
import sys

# Set up module path
current_dir = os.path.dirname(os.path.abspath(__file__))
ml_engine_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(ml_engine_dir)
if ml_engine_dir not in sys.path:
    sys.path.insert(0, ml_engine_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from optimization.optimizer import VesselCharterOptimizer, VESSEL_SPECS, DEMURRAGE_DAILY_RATE_USD


def run_verification():
    print("=" * 80)
    print("RUNNING FINANCIAL QUANT & LEAD QA VERIFICATION ON VESSEL CHARTER OPTIMIZER")
    print("=" * 80)

    optimizer = VesselCharterOptimizer()

    # Scenario 1: Port with shallow draft (Haldia - 12.0m draft limit)
    # Capesize (17.0m draft) cannot enter directly and requires mid-sea lighterage at Sandheads.
    # Panamax (14.0m draft) is also restricted by draft/LOA.
    # Supramax (11.0m draft) CAN berth directly.
    # Cargo volume: 70,000 MT.
    # Lighterage with Capesize incurs $3.50/MT + $25,000 transfer demurrage penalty ($550k surcharge),
    # plus minimum 150k MT Capesize charter hire, making Direct Discharge with Supramax significantly cheaper!
    
    cargo_mt = 70000
    target_port = "Haldia"
    origin = "Australia"

    print(f"\n[Test 1] Testing Shallow Port Allocation: {origin} -> {target_port} ({cargo_mt:,.0f} MT)")
    result = optimizer.optimize_charter_plan(
        required_cargo_mt=cargo_mt,
        target_port=target_port,
        planning_horizon_days=30,
        origin_port=origin,
        allow_lighterage=True,
    )

    strategy = result["strategy_used"]
    naive_cost = result["benchmark_naive_cost_usd"]
    opt_cost = result["total_estimated_cost_usd"]
    savings = result["estimated_savings_usd"]
    lighterage_penalty = result["lighterage_penalty_applied"]

    print(f"-> Strategy Selected: {strategy}")
    print(f"-> Lighterage Penalty Applied to Plan: ${lighterage_penalty:,.2f}")
    print(f"-> Naive Benchmark Cost: ${naive_cost:,.2f}")
    print(f"-> Optimized Plan Cost:  ${opt_cost:,.2f}")
    print(f"-> Estimated Savings:    ${savings:,.2f}")

    # Assertions
    assert strategy == "DIRECT_DISCHARGE", f"Expected DIRECT_DISCHARGE but got {strategy}"
    assert lighterage_penalty == 0.0, f"Expected 0.0 lighterage penalty for Direct Discharge but got {lighterage_penalty}"
    assert opt_cost > 0.0, f"Optimized cost must be positive, got {opt_cost}"
    assert naive_cost > opt_cost, f"Naive cost (${naive_cost:,.2f}) must exceed optimized cost (${opt_cost:,.2f})"
    assert savings > 0.0, f"CRITICAL FAILURE: Estimated savings (${savings:,.2f}) must be > 0.0!"
    assert abs(savings - (naive_cost - opt_cost)) < 0.05, "Savings must equal naive_cost - total_estimated_cost_usd"

    print(">>> Test 1 PASSED: Direct Discharge successfully selected and Savings > $0.00!")

    # Scenario 2: Paradip with 80,000 MT cargo
    # Paradip draft: 14.5m -> Capesize (17.0m) infeasible directly, Panamax (14.0m) feasible directly.
    # 1 Panamax parcel (80,000 MT) discharges directly vs Capesize + lighterage.
    print(f"\n[Test 2] Testing Paradip Single-Parcel Allocation (80,000 MT)")
    result_paradip = optimizer.optimize_charter_plan(
        required_cargo_mt=80000,
        target_port="Paradip",
        planning_horizon_days=30,
        origin_port=origin,
        allow_lighterage=True,
    )

    strategy_p = result_paradip["strategy_used"]
    naive_p = result_paradip["benchmark_naive_cost_usd"]
    opt_p = result_paradip["total_estimated_cost_usd"]
    savings_p = result_paradip["estimated_savings_usd"]

    print(f"-> Strategy Selected: {strategy_p}")
    print(f"-> Naive Benchmark Cost: ${naive_p:,.2f}")
    print(f"-> Optimized Plan Cost:  ${opt_p:,.2f}")
    print(f"-> Estimated Savings:    ${savings_p:,.2f}")

    assert strategy_p == "DIRECT_DISCHARGE", f"Expected DIRECT_DISCHARGE for 80k MT at Paradip, got {strategy_p}"
    assert savings_p > 0.0, f"CRITICAL FAILURE: Paradip savings (${savings_p:,.2f}) must be > 0.0!"

    print(">>> Test 2 PASSED: Direct Discharge beats Lighterage for 80k MT parcel and Savings > $0.00!")

    # Scenario 3: Verify Unit Math in _compute_naive_benchmark directly
    print("\n[Test 3] Mathematical Unit Verification of _compute_naive_benchmark Breakdown")
    forecasts = optimizer.fetch_freight_rate_forecasts(horizon_days=30)
    naive_cape_shallow = optimizer._compute_naive_benchmark(
        required_cargo_mt=150000,
        feasible_vessels=["Capesize"],
        forecasts=forecasts,
        waiting_hours=36.0,
        handling_rate_tpd=45000.0,
        distance_nm=5200.0,
        rate_multiplier=1.0,
        is_shallow_port=True,
    )

    naive_cape_deep = optimizer._compute_naive_benchmark(
        required_cargo_mt=150000,
        feasible_vessels=["Capesize"],
        forecasts=forecasts,
        waiting_hours=36.0,
        handling_rate_tpd=45000.0,
        distance_nm=5200.0,
        rate_multiplier=1.0,
        is_shallow_port=False,
    )

    expected_lighterage_diff = (1 * 150000 * 3.50) + (1 * DEMURRAGE_DAILY_RATE_USD)  # $525,000 + $25,000 = $550,000
    actual_diff = round(naive_cape_shallow - naive_cape_deep, 2)
    print(f"-> Shallow Port Benchmark (with Lighterage): ${naive_cape_shallow:,.2f}")
    print(f"-> Deep Port Benchmark (no Lighterage):      ${naive_cape_deep:,.2f}")
    print(f"-> Lighterage Delta:                         ${actual_diff:,.2f} (Expected: ${expected_lighterage_diff:,.2f})")

    assert abs(actual_diff - expected_lighterage_diff) < 1.0, (
        f"Lighterage penalty difference mismatch: actual {actual_diff} vs expected {expected_lighterage_diff}"
    )

    print(">>> Test 3 PASSED: Naive benchmark correctly applies Lighterage Surcharge ($3.50/MT + $25k/vessel) exactly once.")

    print("\n" + "=" * 80)
    print("ALL QUANT AND QA MATHEMATICAL ASSERTIONS COMPLETED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    run_verification()
