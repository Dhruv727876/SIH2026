"use client";

import React, { useState } from "react";
import { OptimizationRequest, OptimizationResponse } from "@/lib/api";
import { formatCurrency, formatInteger } from "@/lib/formatters";
import {
  Ship,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  DollarSign,
  TrendingUp,
  Layers,
  Zap,
} from "lucide-react";

interface DashboardViewProps {
  request: OptimizationRequest;
  setRequest: React.Dispatch<React.SetStateAction<OptimizationRequest>>;
  optimizationResult: OptimizationResponse | null;
  optimizing: boolean;
  onRunOptimization: () => void;
  onNavigateToStrategy: () => void;
  onResetPlan: () => void;
}

const USD_TO_INR_RATE = 83.51;

const DISCHARGE_PORT_METADATA: Record<
  string,
  { draftLimit: number; allowsCape: boolean; allowsPanamax: boolean; description: string }
> = {
  Paradip: {
    draftLimit: 14.5,
    allowsCape: false,
    allowsPanamax: true,
    description: "Major Coking Coal Terminal (Odisha). 14.50m channel ceiling strictly disqualifies direct Capesize bulkers.",
  },
  Visakhapatnam: {
    draftLimit: 16.5,
    allowsCape: false,
    allowsPanamax: true,
    description: "RINL dedicated Outer Harbour (Andhra Pradesh). 16.50m draft permits deep-laden Panamax vessels.",
  },
  Haldia: {
    draftLimit: 12.0,
    allowsCape: false,
    allowsPanamax: false,
    description: "Shallow Riverine Lock-Gate Port (West Bengal). Strictly limited to geared Supramax carriers (50k MT).",
  },
  Dhamra: {
    draftLimit: 18.0,
    allowsCape: true,
    allowsPanamax: true,
    description: "Deepwater Port (Odisha). 18.00m draft fully accommodates Capesize and Panamax carriers.",
  },
  Gangavaram: {
    draftLimit: 20.0,
    allowsCape: true,
    allowsPanamax: true,
    description: "Ultra-Deepwater Bulk Port (Andhra Pradesh). Capable of handling Newcastlemax bulkers with zero draft restrictions.",
  },
  Mormugao: {
    draftLimit: 14.1,
    allowsCape: false,
    allowsPanamax: true,
    description: "Mooring Berth (Goa). Accommodates Panamax bulkers.",
  },
  Jaigad: {
    draftLimit: 18.5,
    allowsCape: true,
    allowsPanamax: true,
    description: "Deepwater Berth (Maharashtra). Accommodates Capesize bulkers.",
  },
};

export default function DashboardView({
  request,
  setRequest,
  optimizationResult,
  optimizing,
  onRunOptimization,
  onNavigateToStrategy,
  onResetPlan,
}: DashboardViewProps) {
  const [constraintsExpanded, setConstraintsExpanded] = useState<boolean>(false);

  const currentDischargeMeta =
    DISCHARGE_PORT_METADATA[request.target_port] || DISCHARGE_PORT_METADATA["Paradip"];

  const hasResult = Boolean(optimizationResult);

  return (
    <div className="space-y-6">
      {/* ========================================================= */}
      {/* 1. TOP SECTION: VOYAGE OPTIMIZATION DESK (Always Visible) */}
      {/* ========================================================= */}
      <div className="space-y-4">
        {/* Title & Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-serif-gov text-3xl font-bold text-[#001f3f] tracking-tight">
              Voyage Optimization Desk
            </h1>
            <p className="text-xs text-[#475569] mt-0.5">
              Configure demand, draft limits, and laycan horizons to generate least-cost charter plan
            </p>
          </div>

          {hasResult && (
            <button
              type="button"
              onClick={onResetPlan}
              className="px-3.5 py-1.5 rounded bg-[#f1f5f9] hover:bg-[#e2e8f0] text-[#475569] text-xs font-semibold border border-[#cbd5e1] transition cursor-pointer"
            >
              Clear Results
            </button>
          )}
        </div>

        {/* The Main Voyage Parameter Form Card */}
        <div className="bg-white p-6 rounded border border-[#cbd5e1] shadow-sm">
          <form
            className="flex flex-col gap-4"
            onSubmit={(e) => {
              e.preventDefault();
              onRunOptimization();
            }}
          >
            {/* Row 1: Cargo Volume */}
            <div className="flex flex-col gap-1">
              <label className="text-xs font-bold text-[#001f3f] flex items-center justify-between">
                <span>Required Cargo Volume (Tonnage)</span>
                <span className="text-[11px] text-[#64748b] font-normal">
                  Standard SAIL / RINL Parcels
                </span>
              </label>
              <div className="flex items-center rounded border border-[#cbd5e1] bg-white focus-within:border-[#12355b] focus-within:ring-1 focus-within:ring-[#12355b] overflow-hidden">
                <input
                  className="w-full h-9 px-3 text-sm font-mono text-[#0d1c2e] bg-transparent focus:outline-none"
                  type="number"
                  min="50000"
                  max="2000000"
                  step="10000"
                  value={request.required_cargo_mt}
                  onChange={(e) =>
                    setRequest((prev) => ({
                      ...prev,
                      required_cargo_mt: parseFloat(e.target.value) || 300000,
                    }))
                  }
                />
                <span className="h-9 px-4 bg-[#f1f5f9] text-[#475569] text-xs font-bold flex items-center justify-center border-l border-[#cbd5e1]">
                  MT
                </span>
              </div>
            </div>

            {/* Row 2: Origin & Destination Ports */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="flex flex-col gap-1">
                <label className="text-xs font-bold text-[#001f3f]">
                  Origin Port / Loading Terminal
                </label>
                <select
                  className="w-full h-9 px-3 text-xs text-[#0d1c2e] bg-white rounded border border-[#cbd5e1] focus:outline-none focus:border-[#12355b] cursor-pointer"
                  value={request.origin_port}
                  onChange={(e) =>
                    setRequest((prev) => ({ ...prev, origin_port: e.target.value }))
                  }
                >
                  <option value="Australia (Newcastle)">
                    Australia (Newcastle) — Primary Coking Coal
                  </option>
                  <option value="Australia (Hay Point / Dalrymple)">
                    Australia (Hay Point / Dalrymple)
                  </option>
                  <option value="Australia (Gladstone)">
                    Australia (Gladstone)
                  </option>
                  <option value="Indonesia (Samarinda)">
                    Indonesia (Samarinda) — Low-Haul
                  </option>
                  <option value="South Africa (Richards Bay)">
                    South Africa (Richards Bay) — Medium-Haul
                  </option>
                  <option value="USA (Hampton Roads)">
                    USA (Hampton Roads) — High Grade Met Coal
                  </option>
                  <option value="Brazil (Tubarao)">
                    Brazil (Tubarao) — Deepwater Bulk Hub
                  </option>
                </select>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-xs font-bold text-[#001f3f] flex items-center justify-between">
                  <span>Destination Port (India)</span>
                  <span className="text-[10px] text-[#e65100] font-semibold bg-[#fff3e0] px-2 py-0.5 rounded border border-[#ffe0b2]">
                    {currentDischargeMeta.draftLimit}m Draft Limit
                  </span>
                </label>
                <select
                  className="w-full h-9 px-3 text-xs text-[#0d1c2e] bg-white rounded border border-[#cbd5e1] focus:outline-none focus:border-[#12355b] cursor-pointer"
                  value={request.target_port}
                  onChange={(e) =>
                    setRequest((prev) => ({ ...prev, target_port: e.target.value }))
                  }
                >
                  <option value="Paradip">Paradip (PPT - Berth CBX/CQ, 14.5m Draft)</option>
                  <option value="Visakhapatnam">Visakhapatnam (VPT - Outer Harbour, 16.5m Draft)</option>
                  <option value="Haldia">Haldia (HDC - Lock Gate Constrained, 12.0m Draft)</option>
                  <option value="Dhamra">Dhamra (DPCL - Capesize Ready, 18.0m Draft)</option>
                  <option value="Gangavaram">Gangavaram (GPL - Newcastlemax Ready, 20.0m Draft)</option>
                  <option value="Mormugao">Mormugao (MPT - Mooring Berth, 14.1m Draft)</option>
                  <option value="Jaigad">Jaigad (JSP - Deepwater Berth, 18.5m Draft)</option>
                </select>
              </div>
            </div>

            {/* Row 3: Planning Horizon Window */}
            <div className="flex flex-col gap-1">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-[#001f3f]">
                  Planning Horizon Window
                </label>
                <span className="text-[10px] text-[#64748b]">
                  Laycan Allocation Window (7 to 60 Days)
                </span>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex-1 flex items-center rounded border border-[#cbd5e1] bg-white focus-within:border-[#12355b] focus-within:ring-1 focus-within:ring-[#12355b] overflow-hidden">
                  <input
                    className="w-full h-9 px-3 text-sm font-mono text-[#0d1c2e] bg-transparent focus:outline-none"
                    type="number"
                    min="7"
                    max="60"
                    value={request.planning_horizon_days}
                    onChange={(e) =>
                      setRequest((prev) => ({
                        ...prev,
                        planning_horizon_days: parseInt(e.target.value) || 30,
                      }))
                    }
                  />
                  <span className="h-9 px-4 bg-[#f1f5f9] text-[#475569] text-xs font-bold flex items-center justify-center border-l border-[#cbd5e1]">
                    Days
                  </span>
                </div>
                <div className="hidden sm:flex items-center gap-1.5">
                  {[15, 30, 45, 60].map((days) => (
                    <button
                      key={days}
                      type="button"
                      onClick={() =>
                        setRequest((prev) => ({ ...prev, planning_horizon_days: days }))
                      }
                      className={`h-9 px-3.5 rounded border text-xs font-semibold transition cursor-pointer ${
                        request.planning_horizon_days === days
                          ? "bg-[#12355b] text-white border-[#12355b]"
                          : "bg-[#f8f9ff] text-[#475569] border-[#cbd5e1] hover:bg-[#e2e8f0]"
                      }`}
                    >
                      {days}D
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Row 4: Mid-Sea Lighterage Option Toggle */}
            <div className="flex items-center justify-between p-3.5 rounded bg-[#f8f9ff] border border-[#cbd5e1]">
              <div className="flex flex-col">
                <span className="text-xs font-bold text-[#001f3f] flex items-center gap-1.5">
                  <span>Allow Mid-Sea Lighterage</span>
                  <span className="text-[10px] font-semibold text-amber-800 bg-amber-100 px-2 py-0.5 rounded border border-amber-200">
                    Sandheads STS
                  </span>
                </span>
                <span className="text-[11px] text-[#64748b] mt-0.5">
                  Evaluate Capesize lighterage at Sandheads vs direct discharge for shallow ports (&lt;17m)
                </span>
              </div>

              <div className="flex items-center gap-3 shrink-0">
                <span
                  className={`text-xs font-bold font-mono px-2 py-0.5 rounded border transition-colors ${
                    (request.allow_lighterage ?? true)
                      ? "bg-[#e8f5e9] text-[#15803d] border-[#bbf7d0]"
                      : "bg-[#f1f5f9] text-[#64748b] border-[#cbd5e1]"
                  }`}
                >
                  {(request.allow_lighterage ?? true) ? "ON" : "OFF"}
                </span>
                <button
                  type="button"
                  role="switch"
                  aria-checked={request.allow_lighterage ?? true}
                  onClick={() =>
                    setRequest((prev) => ({
                      ...prev,
                      allow_lighterage: !(prev.allow_lighterage ?? true),
                    }))
                  }
                  className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-[#12355b] focus:ring-offset-2 ${
                    (request.allow_lighterage ?? true) ? "bg-[#12355b]" : "bg-slate-300"
                  }`}
                >
                  <span
                    className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-md ring-0 transition duration-200 ease-in-out ${
                      (request.allow_lighterage ?? true) ? "translate-x-5" : "translate-x-0"
                    }`}
                  />
                </button>
              </div>
            </div>

            {/* Physical Port Constraints & Charter Policies Accordion */}
            <div className="border border-[#cbd5e1] rounded overflow-hidden">
              <button
                type="button"
                onClick={() => setConstraintsExpanded(!constraintsExpanded)}
                className="w-full px-4 py-2.5 bg-[#f1f5f9] hover:bg-[#e2e8f0] flex items-center justify-between text-left text-[#001f3f] transition cursor-pointer"
              >
                <span className="text-xs font-bold">
                  Physical Port Constraints &amp; Charter Policies ({request.target_port})
                </span>
                <span className="text-xs text-[#64748b] font-medium">
                  {constraintsExpanded ? "Collapse ▲" : "Expand ▼"}
                </span>
              </button>

              {constraintsExpanded && (
                <div className="p-3.5 grid grid-cols-1 sm:grid-cols-3 gap-3 border-t border-[#e2e8f0] bg-white">
                  <div className="p-2.5 bg-[#eff4ff] rounded border border-[#bfd5fe]">
                    <div className="text-[10px] uppercase font-bold text-[#12355b]">
                      Max Nav Draft Limit
                    </div>
                    <div className="text-sm font-bold text-[#001f3f] mt-0.5">
                      {currentDischargeMeta.draftLimit.toFixed(2)} Metres
                    </div>
                    <div className="text-[10px] text-[#2563eb] mt-0.5">
                      Dynamic: Enforced for {request.target_port}
                    </div>
                  </div>

                  <div className="p-2.5 bg-[#f8f9ff] rounded border border-[#e2e8f0]">
                    <div className="text-[10px] uppercase font-bold text-[#64748b]">
                      Demurrage Tolerance
                    </div>
                    <div className="text-sm font-bold text-[#001f3f] mt-0.5">
                      $18,500 / day
                    </div>
                    <div className="text-[10px] text-[#64748b] mt-0.5">
                      Baltic C5 Cap Benchmark
                    </div>
                  </div>

                  <div className="p-2.5 bg-[#f8f9ff] rounded border border-[#e2e8f0]">
                    <div className="text-[10px] uppercase font-bold text-[#64748b]">
                      Vessel Age Ceiling
                    </div>
                    <div className="text-sm font-bold text-[#001f3f] mt-0.5">
                      &le; 15 Years
                    </div>
                    <div className="text-[10px] text-[#64748b] mt-0.5">
                      DG Shipping Statutory Rule
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Primary Action Button */}
            <div className="pt-1">
              <button
                type="submit"
                disabled={optimizing}
                className="w-full bg-[#12355b] hover:bg-[#001f3f] text-white py-3 px-6 rounded shadow-sm flex items-center justify-center gap-2 transition font-bold text-sm disabled:opacity-75 cursor-pointer"
              >
                {optimizing ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Solving Mixed-Integer Linear Program (PuLP)...</span>
                  </>
                ) : (
                  <>
                    <Zap className="h-4 w-4" />
                    <span>Generate Least-Cost Voyage Plan</span>
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* ========================================================= */}
      {/* 2. BOTTOM SECTION: POST-EXECUTION DETAILS (Shown Below Form) */}
      {/* ========================================================= */}
      {hasResult && optimizationResult && (() => {
        const totalCost = optimizationResult.total_estimated_cost_usd;
        const totalCostInrCrore = (totalCost * USD_TO_INR_RATE) / 10000000;
        const savingsUsd = optimizationResult.estimated_savings_usd || 0;
        const savingsInrCrore = (savingsUsd * USD_TO_INR_RATE) / 10000000;
        const primaryVessel =
          optimizationResult.vessel_schedule?.[0]?.vessel_type || "Panamax";
        const totalStems =
          optimizationResult.vessel_schedule?.reduce((acc, v) => acc + v.quantity, 0) ||
          optimizationResult.vessel_schedule?.length ||
          0;
        const allocatedMt =
          optimizationResult.total_cargo_allocated_mt || request.required_cargo_mt;

        return (
          <div className="space-y-4 pt-2 border-t border-[#cbd5e1]/60">
            {/* Post-Calculation Header & Quick Action */}
            <div className="bg-white p-5 rounded border border-[#cbd5e1] shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="flex items-center gap-3.5">
                <div className="w-11 h-11 rounded bg-[#e8f5e9] text-[#15803d] border border-[#bbf7d0] flex items-center justify-center shrink-0">
                  <CheckCircle2 className="h-6 w-6" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="font-serif-gov text-xl font-bold text-[#001f3f] tracking-tight">
                      Voyage Optimization Results
                    </h2>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#e8f5e9] text-[#15803d] border border-[#bbf7d0] font-bold uppercase">
                      {optimizationResult.status || "Optimal Plan"}
                    </span>
                  </div>
                  <p className="text-xs text-[#475569] mt-0.5">
                    Corridor: <span className="font-semibold text-[#001f3f]">{optimizationResult.route || `${request.origin_port} -> ${request.target_port}`}</span> • All navigational draft constraints satisfied.
                  </p>
                </div>
              </div>

              <button
                type="button"
                onClick={onNavigateToStrategy}
                className="px-5 py-2.5 rounded bg-[#12355b] hover:bg-[#001f3f] text-white text-xs font-bold transition shadow-sm flex items-center gap-2 self-start md:self-auto shrink-0 cursor-pointer"
              >
                <span>View Full Strategy &amp; Schedule</span>
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>

            {/* 4-Stat Metric Summary Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 items-stretch">
              <div className="bg-white p-5 rounded-xl border border-[#cbd5e1] shadow-xs flex flex-col justify-between h-full">
                <div className="flex items-center justify-between text-[#64748b] text-xs">
                  <span className="uppercase tracking-wider font-bold text-[10px] text-[#64748b]">Total Landed Freight</span>
                  <div className="w-7 h-7 rounded-md bg-[#eff4ff] text-[#12355b] flex items-center justify-center shrink-0">
                    <DollarSign className="h-4 w-4" />
                  </div>
                </div>
                <div className="my-3">
                  <div className="text-xl font-bold font-mono text-[#001f3f] tracking-tight truncate">
                    ${formatCurrency(totalCost)}
                  </div>
                  <div className="text-xs font-mono text-[#64748b] mt-1 truncate">
                    ₹{totalCostInrCrore.toFixed(2)} Crore
                  </div>
                </div>
                <div className="pt-2.5 border-t border-[#e2e8f0] text-[11px] text-[#64748b] mt-auto">
                  CIF Indian Berth Delivery
                </div>
              </div>

              <div className="bg-white p-5 rounded-xl border border-[#cbd5e1] shadow-xs flex flex-col justify-between h-full">
                <div className="flex items-center justify-between text-[#64748b] text-xs">
                  <span className="uppercase tracking-wider font-bold text-[10px] text-[#64748b]">Primary Vessel Class</span>
                  <div className="w-7 h-7 rounded-md bg-[#eff4ff] text-[#12355b] flex items-center justify-center shrink-0">
                    <Ship className="h-4 w-4" />
                  </div>
                </div>
                <div className="my-3">
                  <div className="text-xl font-bold text-[#001f3f] tracking-tight truncate">
                    {primaryVessel} Bulker
                  </div>
                  <div className="text-xs text-[#64748b] mt-1 font-mono truncate">
                    {totalStems} Total Scheduled Stems
                  </div>
                </div>
                <div className="pt-2.5 border-t border-[#e2e8f0] text-[11px] text-[#64748b] font-mono mt-auto">
                  {formatInteger(allocatedMt)} MT Cargo Allocated
                </div>
              </div>

              <div className="bg-white p-5 rounded-xl border border-[#cbd5e1] shadow-xs flex flex-col justify-between h-full">
                <div className="flex items-center justify-between text-[#64748b] text-xs">
                  <span className="uppercase tracking-wider font-bold text-[10px] text-[#64748b]">Voyage Strategy</span>
                  <div className="w-7 h-7 rounded-md bg-amber-50 text-amber-700 flex items-center justify-center shrink-0">
                    <Layers className="h-4 w-4" />
                  </div>
                </div>
                <div className="my-3">
                  <div className="text-xl font-bold text-[#001f3f] tracking-tight truncate">
                    {optimizationResult.strategy_used === "MID_SEA_LIGHTERAGE"
                      ? "Mid-Sea Lighterage"
                      : "Direct Discharge"}
                  </div>
                  <div className="text-xs text-[#64748b] mt-1 truncate">
                    {optimizationResult.strategy_used === "MID_SEA_LIGHTERAGE"
                      ? "Sandheads STS Transshipment"
                      : "Draft Compliant Direct Berth"}
                  </div>
                </div>
                <div className="pt-2.5 border-t border-[#e2e8f0] text-[11px] text-[#64748b] mt-auto">
                  Draft Limit: {currentDischargeMeta.draftLimit}m Enforced
                </div>
              </div>

              <div className="bg-white p-5 rounded-xl border border-[#cbd5e1] shadow-xs flex flex-col justify-between h-full">
                <div className="flex items-center justify-between text-[#64748b] text-xs">
                  <span className="uppercase tracking-wider font-bold text-[10px] text-[#64748b]">Estimated Savings</span>
                  <div className="w-7 h-7 rounded-md bg-[#e8f5e9] text-[#15803d] flex items-center justify-center shrink-0">
                    <TrendingUp className="h-4 w-4" />
                  </div>
                </div>
                <div className="my-3">
                  <div className="text-xl font-bold text-[#15803d] tracking-tight truncate">
                    ₹{savingsInrCrore.toFixed(2)} Cr
                  </div>
                  <div className="text-xs text-[#64748b] mt-1 font-mono truncate">
                    ${formatCurrency(savingsUsd)} vs Naive Spot
                  </div>
                </div>
                <div className="pt-2.5 border-t border-[#e2e8f0] text-[11px] text-[#15803d] font-semibold mt-auto">
                  Forward Curve Arbitrage
                </div>
              </div>
            </div>

            {/* Lighterage Notice Banner if active */}
            {optimizationResult.strategy_used === "MID_SEA_LIGHTERAGE" && (
              <div className="p-4 rounded bg-[#fff7ed] border border-[#ffedd5] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-[#c2410c]">
                <div className="flex items-center gap-3">
                  <span className="text-2xl shrink-0">⚠️</span>
                  <div>
                    <div className="text-xs font-bold uppercase tracking-wider text-amber-950 font-mono">
                      Mid-Sea Lighterage Strategy Active (Sandheads Anchorage)
                    </div>
                    <p className="text-xs text-amber-800 mt-0.5">
                      Destination draft constraint ({currentDischargeMeta.draftLimit}m) active. Cargo transported via Capesize and transshipped to {optimizationResult.lighterage_vessel_count || 3}x {optimizationResult.lighterage_vessel_type || "Supramax"} vessels for riverine berthing.
                    </p>
                  </div>
                </div>
                <span className="px-3 py-1 bg-white rounded border border-amber-300 text-xs font-mono font-bold text-amber-900 self-start sm:self-auto shrink-0">
                  Lighterage Penalty: ${formatCurrency(optimizationResult.lighterage_penalty_applied || 0)}
                </span>
              </div>
            )}
          </div>
        );
      })()}
    </div>
  );
}
