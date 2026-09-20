"use client";

import React, { useState } from "react";
import { OptimizationRequest, OptimizationResponse } from "@/lib/api";
import { formatCurrency, formatInteger } from "@/lib/formatters";
import {
  AlertTriangle,
  Flame,
  CloudRain,
  Anchor,
  Wind,
  ShieldAlert,
  ArrowUpRight,
  Calendar,
  Zap,
} from "lucide-react";

interface WhatIfViewProps {
  baselineResult: OptimizationResponse | null;
  request: OptimizationRequest;
  setRequest: React.Dispatch<React.SetStateAction<OptimizationRequest>>;
  optimizing: boolean;
  onRunOptimizationWithDisruption: (
    multiplier: number,
    name: string
  ) => Promise<OptimizationResponse | null>;
}

const USD_TO_INR_RATE = 83.51;

interface ScenarioOption {
  label: string;
  name: string;
  multiplier: number;
  description: string;
  historicalReference: string;
}

const DISRUPTION_SCENARIOS: ScenarioOption[] = [
  {
    label: "None (Baseline)",
    name: "Baseline Market Conditions",
    multiplier: 1.0,
    description: "Standard Baltic dry index curves with normal seasonal variability and berth queues.",
    historicalReference: "Regular trading conditions across Cape & Panamax routes.",
  },
  {
    label: "Red Sea Crisis (1.85x)",
    name: "Red Sea Crisis & Cape Route Diversion",
    multiplier: 1.85,
    description: "Houthi maritime missile corridor forces bulkers to bypass Bab-el-Mandeb via Cape of Good Hope (+14 voyage days).",
    historicalReference: "Q1 2024 Red Sea Houthi vessel targeting crisis.",
  },
  {
    label: "Monsoon Port Congestion (1.35x)",
    name: "Monsoon Port Congestion & Draft Reduction",
    multiplier: 1.35,
    description: "Southwest monsoon swell causes 4.5-day anchorage queues and 0.8m draft reduction at Paradip and Haldia.",
    historicalReference: "Annual Indian East Coast monsoon seasonal disruptions (June-August).",
  },
  {
    label: "Suez Canal Blockage (2.1x)",
    name: "Suez Canal Blockage & Chokepoint Gridlock",
    multiplier: 2.1,
    description: "Complete canal fairway grounding causing global dry bulker tonnage supply freeze and spot charter spike.",
    historicalReference: "Ever Given Suez Canal grounding (March 2021).",
  },
  {
    label: "Bay of Bengal Cyclone (1.5x)",
    name: "Bay of Bengal Severe Cyclonic Storm",
    multiplier: 1.5,
    description: "Very severe cyclonic storm halts cargo handling, causes port shutdowns, and spikes short-term coastal demurrage.",
    historicalReference: "Cyclone Fani (2019) & Cyclone Yaas (2021) terminal closures.",
  },
];

export default function WhatIfView({
  baselineResult,
  request,
  setRequest,
  optimizing,
  onRunOptimizationWithDisruption,
}: WhatIfViewProps) {
  const [selectedScenarioLabel, setSelectedScenarioLabel] = useState<string>(
    "Red Sea Crisis (1.85x)"
  );
  const [whatIfResult, setWhatIfResult] = useState<OptimizationResponse | null>(null);

  const activeScenario =
    DISRUPTION_SCENARIOS.find((s) => s.label === selectedScenarioLabel) ||
    DISRUPTION_SCENARIOS[1];

  const handleGenerateStressTest = async (e: React.FormEvent) => {
    e.preventDefault();
    const result = await onRunOptimizationWithDisruption(
      activeScenario.multiplier,
      activeScenario.name
    );
    if (result) {
      setWhatIfResult(result);
    }
  };

  const baselineCost = baselineResult?.total_estimated_cost_usd || 6601275;
  const stressedCost = whatIfResult?.total_estimated_cost_usd;
  const costDeltaUsd = stressedCost ? stressedCost - baselineCost : 0;
  const costDeltaSign = costDeltaUsd >= 0 ? "+" : "-";
  const costDeltaAbsUsd = Math.abs(costDeltaUsd);
  const costDeltaPct = stressedCost
    ? Math.abs((costDeltaUsd / baselineCost) * 100).toFixed(1)
    : "0.0";
  const costDeltaPctSign = costDeltaUsd >= 0 ? "+" : "-";
  const costDeltaInrCr = (Math.abs(costDeltaUsd) * USD_TO_INR_RATE / 10000000).toFixed(2);
  const costDeltaInrSign = costDeltaUsd >= 0 ? "increases" : "decreases";

  return (
    <div className="space-y-4">
      {/* Title & Header */}
      <div>
        <h1 className="font-serif-gov text-3xl font-bold text-[#001f3f] tracking-tight">
          What-If Maritime Disruption Simulator
        </h1>
        <p className="text-xs text-[#475569] mt-0.5">
          Simulate geopolitical shocks, canal closures, and weather delays on freight procurement costs
        </p>
      </div>

      {/* Main Parameters Card */}
      <div className="bg-white p-6 rounded border border-[#cbd5e1] shadow-sm space-y-4">
        <form onSubmit={handleGenerateStressTest} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="flex flex-col gap-1">
              <label className="text-xs font-bold text-[#001f3f]">
                Cargo Volume (MT)
              </label>
              <div className="flex items-center rounded border border-[#cbd5e1] bg-white overflow-hidden">
                <input
                  className="w-full h-9 px-3 text-sm font-mono text-[#0d1c2e] bg-transparent focus:outline-none"
                  type="number"
                  min="10000"
                  max="2000000"
                  step="5000"
                  placeholder="e.g. 300000"
                  value={request.required_cargo_mt === 0 || Number.isNaN(request.required_cargo_mt) ? "" : request.required_cargo_mt}
                  onChange={(e) => {
                    const raw = e.target.value;
                    setRequest((prev) => ({
                      ...prev,
                      required_cargo_mt: raw === "" ? (0 as unknown as number) : Number(raw),
                    }));
                  }}
                  onBlur={() => {
                    if (!request.required_cargo_mt || request.required_cargo_mt < 10000) {
                      setRequest((prev) => ({ ...prev, required_cargo_mt: 35000 }));
                    }
                  }}
                />
                <span className="h-9 px-3 bg-[#f1f5f9] text-[#475569] text-xs font-bold flex items-center justify-center border-l border-[#cbd5e1]">
                  MT
                </span>
              </div>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs font-bold text-[#001f3f]">
                Origin Port
              </label>
              <select
                className="w-full h-9 px-3 text-xs text-[#0d1c2e] bg-white rounded border border-[#cbd5e1] focus:outline-none cursor-pointer"
                value={request.origin_port}
                onChange={(e) =>
                  setRequest((prev) => ({ ...prev, origin_port: e.target.value }))
                }
              >
                <option value="Australia (Hay Point / Dalrymple)">Australia (Hay Point / Dalrymple)</option>
                <option value="Australia (Newcastle)">Australia (Newcastle)</option>
                <option value="Indonesia (Samarinda / Taboneo)">Indonesia (Samarinda / Taboneo)</option>
                <option value="Mozambique (Maputo / Beira)">Mozambique (Maputo / Beira)</option>
                <option value="Russia (Taman / Vostochny)">Russia (Taman / Vostochny)</option>
                <option value="USA (Hampton Roads / Baltimore)">USA (Hampton Roads / Baltimore)</option>
                <option value="South Africa (Richards Bay)">South Africa (Richards Bay)</option>
                <option value="Brazil (Tubarao)">Brazil (Tubarao)</option>
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs font-bold text-[#001f3f]">
                Destination Port
              </label>
              <select
                className="w-full h-9 px-3 text-xs text-[#0d1c2e] bg-white rounded border border-[#cbd5e1] focus:outline-none cursor-pointer"
                value={request.target_port}
                onChange={(e) =>
                  setRequest((prev) => ({ ...prev, target_port: e.target.value }))
                }
              >
                <option value="Paradip">Paradip (14.5m Draft / 260m LOA)</option>
                <option value="Visakhapatnam">Visakhapatnam (16.5m Draft / 300m LOA)</option>
                <option value="Gangavaram">Gangavaram (20.0m Draft / 320m LOA)</option>
                <option value="Gopalpur">Gopalpur (14.0m Draft / 230m LOA)</option>
                <option value="Dhamra">Dhamra (18.0m Draft / 315m LOA)</option>
                <option value="Sagar- Sandheads">Sagar- Sandheads (18.5m STS Transshipment)</option>
                <option value="Haldia">Haldia (12.0m Draft / 190m LOA)</option>
              </select>
            </div>
          </div>

          {/* Prominent Disruption Scenario Dropdown */}
          <div className="p-4 rounded bg-[#fff7ed] border border-[#ffedd5] space-y-2.5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
              <label className="text-xs font-bold text-[#9a3412] uppercase tracking-wider flex items-center gap-1.5">
                <AlertTriangle className="h-4 w-4 text-[#ea580c]" />
                <span>Disruption Scenario (Freight Shock Multiplier)</span>
              </label>
              <span className="text-xs font-mono font-bold text-[#9a3412] bg-white px-2 py-0.5 rounded border border-[#fed7aa]">
                {activeScenario.multiplier}x Impact
              </span>
            </div>

            <select
              value={selectedScenarioLabel}
              onChange={(e) => setSelectedScenarioLabel(e.target.value)}
              className="w-full h-10 px-3 text-sm font-semibold text-[#0d1c2e] bg-white rounded border border-[#fdba74] focus:outline-none focus:ring-1 focus:ring-[#ea580c] cursor-pointer"
            >
              {DISRUPTION_SCENARIOS.map((sc) => (
                <option key={sc.label} value={sc.label}>
                  {sc.label} — {sc.name}
                </option>
              ))}
            </select>

            <div className="p-3 bg-white rounded border border-[#fed7aa] text-xs text-[#431407]">
              <div className="font-bold text-[#7c2d12]">{activeScenario.name}</div>
              <p className="text-[#7c2d12]/80 mt-0.5 leading-relaxed text-[11px]">
                {activeScenario.description}
              </p>
              <div className="text-[10px] text-[#9a3412] mt-1 font-semibold italic">
                Benchmark Reference: {activeScenario.historicalReference}
              </div>
            </div>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={optimizing}
            className="w-full bg-[#12355b] hover:bg-[#001f3f] text-white py-3 px-6 rounded shadow-sm flex items-center justify-center gap-2 font-bold text-sm transition disabled:opacity-75 cursor-pointer"
          >
            {optimizing ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Simulating Maritime Shock &amp; Solving MILP...</span>
              </>
            ) : (
              <>
                <Zap className="h-4 w-4" />
                <span>Run Disruption Stress Test</span>
              </>
            )}
          </button>
        </form>
      </div>

      {/* Results Display */}
      {whatIfResult && (
        <div className="space-y-4">
          {/* Stress Test Delta Callout */}
          <div className="p-4 rounded-xl bg-[#fef2f2] border border-[#fca5a5] text-[#991b1b] flex flex-col md:flex-row md:items-center justify-between gap-3 shadow-xs">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-[#fee2e2] text-[#dc2626] flex items-center justify-center shrink-0">
                <AlertTriangle className="h-5 w-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#fee2e2] text-[#991b1b] border border-[#fca5a5] font-bold uppercase">
                    Stress Test Delta
                  </span>
                  <span className="text-xs font-mono font-bold text-[#b91c1c]">
                    {activeScenario.multiplier}x Shock Applied
                  </span>
                </div>
                <div className="text-2xl font-mono font-bold text-[#7f1d1d] mt-1">
                  {costDeltaSign}${formatCurrency(costDeltaAbsUsd)}{" "}
                  <span className="text-base text-[#991b1b] font-semibold">
                    ({costDeltaPctSign}{costDeltaPct}% Cost {costDeltaUsd >= 0 ? "Surge" : "Reduction"})
                  </span>
                </div>
                <p className="text-xs text-[#991b1b] mt-0.5">
                  PSU Budget Impact: Landed freight cost {costDeltaInrSign} by ₹{costDeltaInrCr} Crores.
                </p>
              </div>
            </div>

            <div className="flex flex-col text-right shrink-0 bg-white px-3.5 py-2 rounded border border-[#fca5a5] font-mono self-start md:self-auto">
              <span className="text-[10px] text-[#991b1b] uppercase font-semibold">
                Contingency Recommendation
              </span>
              <span className="text-xs font-bold text-[#7f1d1d]">
                {activeScenario.multiplier > 1.3
                  ? "TRIGGER 6-MONTH COA HEDGE"
                  : "ABSORB VIA SPOT BUFFER"}
              </span>
            </div>
          </div>

          {/* Stressed Stems Table */}
          {whatIfResult.vessel_schedule && (
            <div className="bg-white p-5 rounded border border-[#cbd5e1] shadow-sm space-y-3">
              <h3 className="font-serif-gov text-base font-bold text-[#001f3f]">
                Stressed Laycan Schedule &amp; Freight Rates
              </h3>
              <div className="overflow-x-auto rounded border border-[#cbd5e1]">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-[#f1f5f9] text-[#001f3f] text-[10px] uppercase border-b border-[#cbd5e1] font-bold">
                    <tr>
                      <th className="py-2.5 px-3">Laycan Window</th>
                      <th className="py-2.5 px-3">Vessel Class</th>
                      <th className="py-2.5 px-3">Parcel Size</th>
                      <th className="py-2.5 px-3 text-right">Stressed Freight Rate</th>
                      <th className="py-2.5 px-3 text-right">Trip Cost (USD)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#e2e8f0] text-[#0d1c2e]">
                    {whatIfResult.vessel_schedule.map((stem, idx) => {
                      // estimated_trip_cost_usd is the TOTAL cost for all vessels in this stem batch
                      // Divide by quantity to show per-vessel cost
                      const qty = stem.quantity || 1;
                      const totalBatchCost = stem.estimated_trip_cost_usd || 0;
                      const perVesselCost = totalBatchCost > 0
                        ? totalBatchCost / qty
                        : (stem.capacity_mt || 80000) * (stem.freight_rate_usd_mt || 20);
                      return (
                        <tr key={idx} className="hover:bg-[#f8f9ff]">
                          <td className="py-2 px-3 flex items-center gap-1.5 text-[#475569]">
                            <Calendar className="h-3 w-3 text-slate-400" />
                            <span>{stem.date}</span>
                          </td>
                          <td className="py-2 px-3 font-semibold text-[#12355b]">
                            {stem.vessel_type}
                          </td>
                          <td className="py-2 px-3">
                            {formatInteger(stem.capacity_mt || stem.total_cargo_mt || 0)} MT
                          </td>
                          <td className="py-2 px-3 text-right text-[#b91c1c] font-bold">
                            ${stem.freight_rate_usd_mt?.toFixed(2)}/MT
                          </td>
                          <td className="py-2 px-3 text-right font-bold text-[#001f3f]">
                            ${formatCurrency(perVesselCost)}
                            {qty > 1 && (
                              <span className="block text-[10px] text-[#64748b] font-normal">
                                ×{qty} = ${formatCurrency(totalBatchCost)} total
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
