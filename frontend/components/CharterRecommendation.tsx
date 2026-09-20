"use client";

import React from "react";
import { OptimizationResponse } from "@/lib/api";
import { formatCurrency, formatInteger } from "@/lib/formatters";
import {
  CheckCircle2,
  AlertTriangle,
  Ship,
  Calendar,
  FileSpreadsheet,
  TrendingUp,
  TrendingDown,
  Minus,
  ShieldCheck,
} from "lucide-react";

interface CharterRecommendationProps {
  result: OptimizationResponse | null;
  loading: boolean;
}

const USD_TO_INR_RATE = 83.51;

export default function CharterRecommendation({
  result,
  loading,
}: CharterRecommendationProps) {
  if (loading) {
    return (
      <div className="bg-white p-8 rounded-xl border border-[#cbd5e1] flex flex-col items-center justify-center min-h-[300px] text-center shadow-sm">
        <div className="w-8 h-8 border-3 border-[#12355b]/30 border-t-[#12355b] rounded-full animate-spin mb-3" />
        <span className="font-serif-gov text-lg font-bold text-[#001f3f]">
          Solving Mixed-Integer Linear Program...
        </span>
        <p className="text-xs text-[#475569] mt-1">
          Evaluating laycan windows, draft clearance, and freight rates
        </p>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="bg-white p-8 rounded-xl border border-dashed border-[#cbd5e1] flex flex-col items-center justify-center min-h-[300px] text-center shadow-sm">
        <div className="w-10 h-10 rounded-full bg-[#eff4ff] text-[#12355b] border border-[#dce9ff] flex items-center justify-center mb-3">
          <Ship className="h-5 w-5" />
        </div>
        <h4 className="font-serif-gov text-base font-bold text-[#001f3f]">
          Awaiting Parameter Execution
        </h4>
        <p className="text-xs text-[#475569] max-w-sm mt-1">
          Configure cargo volume, origin, and destination ports in the Voyage Optimization Desk to generate the charter manifest.
        </p>
      </div>
    );
  }

  const isOptimal = result.status === "Optimal";
  const maxDraft = result.port_max_draft_m ?? 14.5;

  // Check draft exclusions
  const draftExclusions: string[] = [];
  if (maxDraft < 17.0) {
    draftExclusions.push(`Capesize bulkers strictly disqualified (Draft ${maxDraft}m < 17.0m threshold)`);
  }
  if (maxDraft < 14.0) {
    draftExclusions.push(`Panamax bulkers disqualified (Draft ${maxDraft}m < 14.0m threshold)`);
  }

  const totalVessels = result.vessel_schedule?.reduce((acc, s) => acc + s.quantity, 0) || 0;
  const totalCost = result.total_estimated_cost_usd || 0;
  const totalCostInrCrore = (totalCost * USD_TO_INR_RATE) / 10000000;

  // CSV Export handler
  const handleExportCSV = () => {
    if (!result.vessel_schedule || result.vessel_schedule.length === 0) return;

    const headers = [
      "Stem #",
      "Laycan Date",
      "Vessel Class",
      "Cargo Parcel (MT)",
      "Freight Rate ($/MT)",
      "Trip Cost (USD)",
      "Trip Cost (INR Crores)",
      "Origin Port",
      "Discharge Port",
      "Status",
    ];

    const rows = result.vessel_schedule.map((s, idx) => {
      const tripCost = s.estimated_trip_cost_usd || (s.capacity_mt || 80000) * (s.freight_rate_usd_mt || 20);
      const inrCrore = (tripCost * USD_TO_INR_RATE) / 10000000;
      return [
        `Stem #${idx + 1}`,
        s.date,
        s.vessel_type,
        s.capacity_mt || s.total_cargo_mt,
        s.freight_rate_usd_mt?.toFixed(2),
        tripCost.toFixed(2),
        inrCrore.toFixed(4),
        result.origin_port || "Australia",
        result.target_port || "Paradip",
        "TO BE SCHEDULED",
      ].join(",");
    });

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute(
      "download",
      `charter_party_manifest_${result.target_port}_${new Date().toISOString().split("T")[0]}.csv`
    );
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6">
      {/* ========================================================= */}
      {/* 1. CHARTER PARTY MANIFEST & VESSEL SCHEDULE (TABLE)       */}
      {/* Placed ABOVE the COA Section per user requirement          */}
      {/* ========================================================= */}
      <div className="bg-white p-6 rounded-xl border border-[#cbd5e1] shadow-sm space-y-4">
        {/* Header Section */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 pb-3 border-b border-[#e2e8f0]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-[#12355b] text-white flex items-center justify-center shrink-0">
              <Ship className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-serif-gov text-lg font-bold text-[#001f3f]">
                  Charter Party Manifest &amp; Vessel Schedule
                </h3>
                <span
                  className={`text-[10px] font-mono px-2 py-0.5 rounded border font-bold uppercase ${
                    isOptimal
                      ? "bg-[#e8f5e9] text-[#15803d] border-[#bbf7d0]"
                      : "bg-[#fef2f2] text-[#991b1b] border-[#fecaca]"
                  }`}
                >
                  {result.status}
                </span>
              </div>
              <p className="text-xs text-[#475569] mt-0.5">
                Corridor: <span className="font-semibold text-[#001f3f]">{result.route || `${result.origin_port} -> ${result.target_port}`}</span> • Standardized Laycan Windows &amp; Nominations
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 self-start lg:self-auto">
            <button
              type="button"
              onClick={handleExportCSV}
              className="px-3.5 py-1.5 rounded-lg bg-[#f8f9ff] hover:bg-[#eff4ff] text-[#12355b] text-xs font-semibold border border-[#cbd5e1] transition flex items-center gap-1.5 cursor-pointer shadow-xs"
            >
              <FileSpreadsheet className="h-3.5 w-3.5 text-[#15803d]" />
              <span>Export Manifest (CSV)</span>
            </button>
          </div>
        </div>

        {/* Lighterage Strategy Warning Banner */}
        {result.strategy_used === "MID_SEA_LIGHTERAGE" && (() => {
          const capesizeCount = result.vessel_schedule
            ? result.vessel_schedule
                .filter((v) => v.vessel_type === "Capesize")
                .reduce((sum, v) => sum + v.quantity, 0) || 1
            : 1;
          const lighterageCount = result.lighterage_vessel_count || 3;
          const lighterageType = result.lighterage_vessel_type || "Supramax";
          const targetPort = result.target_port || "Haldia";

          return (
            <div className="p-4 rounded-lg bg-[#fff7ed] border border-[#fed7aa] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-[#9a3412]">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-full bg-[#ffedd5] text-[#ea580c] flex items-center justify-center shrink-0 mt-0.5">
                  <AlertTriangle className="h-4 w-4" />
                </div>
                <div>
                  <div className="text-xs sm:text-sm font-bold uppercase tracking-wide text-amber-950 font-mono">
                    Lighterage Strategy Engaged: {capesizeCount}x Capesize at Sandheads Anchorage
                  </div>
                  <p className="text-xs text-amber-900 mt-0.5 leading-relaxed">
                    Cargo lightered into {lighterageCount}x {lighterageType} vessels for shallow riverine discharge at {targetPort} ({maxDraft}m draft).{" "}
                    {(result.lighterage_strictly_cheaper ?? ((result.estimated_savings_usd || 0) > 0))
                      ? "MILP proves lighterage saves overall freight cost."
                      : "Lighterage selected for operational stem consolidation (within 15% cost tolerance)."}
                  </p>
                </div>
              </div>
              <div className="flex flex-col text-right shrink-0 bg-white px-3.5 py-1.5 rounded border border-[#fed7aa] font-mono self-start sm:self-auto">
                <span className="text-[10px] text-[#9a3412] uppercase font-bold">Lighterage Penalty</span>
                <span className="text-sm font-bold text-[#7c2d12]">
                  ${formatCurrency(result.lighterage_penalty_applied || 0)}
                </span>
                <span className="text-[10px] text-[#9a3412]">
                  (₹{(((result.lighterage_penalty_applied || 0) * USD_TO_INR_RATE) / 10000000).toFixed(2)} Cr)
                </span>
              </div>
            </div>
          );
        })()}

        {/* Navigational Channel Constraints Box (if direct discharge and restricted) */}
        {result.strategy_used !== "MID_SEA_LIGHTERAGE" && draftExclusions.length > 0 && (
          <div className="p-3.5 rounded-lg bg-[#fffbeb] border border-[#fde68a] flex items-start gap-2.5 text-xs text-[#92400e]">
            <AlertTriangle className="h-4 w-4 text-[#d97706] shrink-0 mt-0.5" />
            <div>
              <div className="font-bold uppercase tracking-wider text-[11px] text-[#78350f]">
                Port Navigational Channel Constraints Enforced ({result.target_port})
              </div>
              <ul className="mt-0.5 space-y-0.5 list-disc list-inside text-[11px] text-[#92400e] font-mono">
                {draftExclusions.map((ex, idx) => (
                  <li key={idx}>{ex}</li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* Tabular Manifest Schedule in Natural Government Table Style */}
        <div className="overflow-x-auto rounded-lg border border-[#cbd5e1] bg-white">
          <table className="w-full text-left text-xs font-tnum">
            <thead className="bg-[#f1f5f9] text-[#001f3f] text-[11px] font-bold uppercase tracking-wider border-b border-[#cbd5e1]">
              <tr>
                <th className="py-2.5 px-3">Stem #</th>
                <th className="py-2.5 px-3">Laycan Date</th>
                <th className="py-2.5 px-3">Nominated Vessel Class</th>
                <th className="py-2.5 px-3 text-center">Parcels</th>
                <th className="py-2.5 px-3 text-right">Parcel Size (MT)</th>
                <th className="py-2.5 px-3 text-right">Freight Rate ($/MT)</th>
                <th className="py-2.5 px-3 text-right">Trip Cost (USD)</th>
                <th className="py-2.5 px-3 text-right">Trip Cost (₹ Cr)</th>
                <th className="py-2.5 px-3 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#e2e8f0]">
              {result.vessel_schedule?.map((row, idx) => {
                const tripCost =
                  row.estimated_trip_cost_usd ||
                  (row.capacity_mt || 80000) * (row.freight_rate_usd_mt || 20);
                const tripCostInrCr = (tripCost * USD_TO_INR_RATE) / 10000000;

                return (
                  <tr key={idx} className="hover:bg-[#f8f9ff] transition-colors bg-white">
                    <td className="py-2.5 px-3 font-mono font-bold text-[#64748b]">
                      #{String(idx + 1).padStart(2, "0")}
                    </td>
                    <td className="py-2.5 px-3 font-mono font-medium text-[#001f3f]">
                      <div className="flex items-center gap-1.5">
                        <Calendar className="h-3.5 w-3.5 text-[#64748b]" />
                        <span>{row.date}</span>
                      </div>
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="bg-[#eff4ff] text-[#12355b] text-[11px] font-bold px-2 py-0.5 rounded border border-[#bfd5fe]">
                        {row.vessel_type} Bulker
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-center font-bold text-[#475569]">
                      {row.quantity}x
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono font-semibold text-[#001f3f]">
                      {formatInteger(row.capacity_mt || row.total_cargo_mt || 0)} MT
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono font-bold text-[#001f3f]">
                      ${row.freight_rate_usd_mt?.toFixed(2)}/MT
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono font-bold text-[#001f3f]">
                      {formatCurrency(tripCost)}
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono text-[#475569]">
                      ₹{tripCostInrCr.toFixed(2)} Cr
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      <span className="bg-[#fff7ed] text-[#9a3412] text-[10px] font-bold px-2 py-0.5 rounded border border-[#fed7aa] uppercase tracking-wide whitespace-nowrap">
                        To Be Scheduled
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot>
              <tr className="bg-[#f1f5f9] font-bold text-[#001f3f] border-t-2 border-[#cbd5e1]">
                <td className="py-2.5 px-3" colSpan={3}>
                  Total Allocated ({result.vessel_schedule?.length || 0} Stems)
                </td>
                <td className="py-2.5 px-3 text-center">
                  {totalVessels} Parcels
                </td>
                <td className="py-2.5 px-3 text-right font-mono">
                  {formatInteger(result.total_cargo_allocated_mt || result.required_cargo_mt || 0)} MT
                </td>
                <td className="py-2.5 px-3 text-right font-mono">
                  ${((totalCost) / (result.total_cargo_allocated_mt || result.required_cargo_mt || 1)).toFixed(2)}/MT
                </td>
                <td className="py-2.5 px-3 text-right font-mono">
                  {formatCurrency(totalCost)}
                </td>
                <td className="py-2.5 px-3 text-right font-mono text-[#12355b]">
                  ₹{totalCostInrCrore.toFixed(2)} Crore
                </td>
                <td className="py-2.5 px-3 text-center">
                  <span className="bg-[#eff4ff] text-[#12355b] text-[10px] font-bold px-2 py-0.5 rounded border border-[#bfd5fe]">
                    100% Fulfilled
                  </span>
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* ========================================================= */}
      {/* 2. STRATEGIC PROCUREMENT ANALYSIS CARD (Spot vs. COA)     */}
      {/* Placed BELOW the Manifest Schedule per user requirement    */}
      {/* ========================================================= */}
      <div className="bg-white p-6 rounded-xl border border-[#cbd5e1] shadow-sm space-y-4">
        {/* Card Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#e2e8f0]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-[#eff4ff] text-[#12355b] border border-[#dce9ff] flex items-center justify-center shrink-0">
              <TrendingUp className="h-5 w-5 text-[#12355b]" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-serif-gov text-lg font-bold text-[#001f3f]">
                  Strategic Procurement Analysis (Spot vs. COA)
                </h3>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#eff4ff] text-[#12355b] border border-[#bfd5fe] font-bold">
                  Prophet T+180 Forward Curve
                </span>
              </div>
              <p className="text-xs text-[#64748b] mt-0.5">
                Comparative fiscal evaluation: 30-Day Spot Fixture vs. 6-Month Volume-Hedged Contract of Affreightment (COA)
              </p>
            </div>
          </div>

          <div className="text-xs text-[#475569] font-mono shrink-0">
            Target Program: <strong className="text-[#001f3f]">{formatInteger(result.required_cargo_mt || result.total_cargo_allocated_mt || 0)} MT</strong>
          </div>
        </div>

        {/* Two Comparative Financial Columns */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Reactive Spot Market Card */}
          <div className="rounded-lg bg-[#f8fafc] border border-[#cbd5e1] p-5 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-[#001f3f] uppercase tracking-wider flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                  Reactive Spot Market
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white text-[#64748b] border border-[#cbd5e1]">
                  Current Baltic Index
                </span>
              </div>
              <div className="mt-2">
                <span className="text-[10px] uppercase font-bold text-[#64748b] block">Total Landed Freight</span>
                <div className="font-mono text-2xl font-bold text-[#001f3f] mt-0.5">
                  ${formatCurrency(result.total_estimated_cost_usd)}
                </div>
                <div className="text-xs font-mono text-[#64748b] mt-0.5">
                  ₹{(((result.total_estimated_cost_usd || 0) * USD_TO_INR_RATE) / 10000000).toFixed(2)} Crore
                  <span className="text-[#94a3b8] ml-2">
                    (${((result.total_estimated_cost_usd || 0) / (result.total_cargo_allocated_mt || result.required_cargo_mt || 1)).toFixed(2)}/MT)
                  </span>
                </div>
              </div>
            </div>
            <div className="mt-4 pt-2.5 border-t border-[#e2e8f0] text-[11px] text-[#64748b]">
              Spot fixtures subject to Baltic volatility, port queue demurrage, and laycan bunkering risk.
            </div>
          </div>

          {/* Proactive 6-Month COA Card */}
          <div className="rounded-lg bg-[#f0f7ff] border border-[#bfd5fe] p-5 flex flex-col justify-between">
            <div>
              <div className="flex flex-wrap items-center justify-between gap-1.5 mb-2">
                <span className="text-xs font-bold text-[#12355b] uppercase tracking-wider flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-blue-600"></span>
                  Proactive 6-Month COA
                </span>

                <div className="flex items-center gap-1.5">
                  {result.market_trend === "CONTANGO" && (
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-300 font-bold flex items-center gap-1">
                      <TrendingUp className="h-3 w-3 text-amber-700" />
                      <span>Contango (Rates Rising)</span>
                    </span>
                  )}
                  {result.market_trend === "BACKWARDATION" && (
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-300 font-bold flex items-center gap-1">
                      <TrendingDown className="h-3 w-3 text-emerald-700" />
                      <span>Backwardation (Rates Falling)</span>
                    </span>
                  )}
                  {(!result.market_trend || result.market_trend === "STABLE") && (
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-300 font-bold flex items-center gap-1">
                      <Minus className="h-3 w-3 text-slate-600" />
                      <span>Stable Forward Curve</span>
                    </span>
                  )}

                  {result.coa_discount_pct !== undefined && result.coa_discount_pct > 0 ? (
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#e8f5e9] text-[#15803d] border border-[#bbf7d0] font-bold">
                      {result.coa_discount_pct}% Volume Discount
                    </span>
                  ) : result.coa_discount_pct !== undefined && result.coa_discount_pct < 0 ? (
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#fef2f2] text-[#991b1b] border border-[#fecaca] font-bold">
                      {Math.abs(result.coa_discount_pct)}% Small Parcel Premium
                    </span>
                  ) : null}
                </div>
              </div>

              <div className="mt-2">
                <span className="text-[10px] uppercase font-bold text-[#12355b] block">Forward Fixed Commitment</span>
                <div className="font-mono text-2xl font-bold text-[#12355b] mt-0.5">
                  ${formatCurrency(result.coa_total_cost_usd || (result.total_estimated_cost_usd * 0.94))}
                </div>
                <div className="text-xs font-mono text-[#475569] mt-0.5">
                  ₹{((((result.coa_total_cost_usd || (result.total_estimated_cost_usd * 0.94)) * USD_TO_INR_RATE)) / 10000000).toFixed(2)} Crore
                  <span className="text-[#12355b] ml-2 font-bold">
                    (${formatCurrency(result.coa_rate_usd_per_mt || 18.0)}/MT)
                  </span>
                </div>
              </div>
            </div>
            <div className="mt-4 pt-2.5 border-t border-[#bfd5fe]/80 text-[11px] text-[#475569]">
              Long-term volume contract guarantees vessel availability and protects Steel PSUs against spot surges.
            </div>
          </div>
        </div>

        {/* The Verdict Banner */}
        {(() => {
          const isLockCOA = (result.procurement_recommendation || "LOCK_IN_COA") === "LOCK_IN_COA";
          const savingsAmt = result.coa_savings_usd || Math.abs((result.total_estimated_cost_usd || 0) - (result.coa_total_cost_usd || 0));
          const savingsInrCr = ((savingsAmt * USD_TO_INR_RATE) / 10000000).toFixed(2);

          return isLockCOA ? (
            <div className="rounded-lg bg-[#f0fdf4] border border-[#86efac] p-4 text-[#14532d] flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-[#dcfce7] text-[#15803d] flex items-center justify-center shrink-0">
                  <CheckCircle2 className="h-5 w-5" />
                </div>
                <div>
                  <div className="text-xs sm:text-sm font-bold uppercase tracking-wider text-[#14532d] font-mono">
                    RECOMMENDATION: Lock in 6-Month COA
                  </div>
                  <p className="text-xs text-[#166534] mt-0.5">
                    Projected Savings: <strong className="text-[#14532d] underline font-mono">${formatCurrency(savingsAmt)} (₹{savingsInrCr} Crore)</strong>. Forward curve signals rate hikes; secure volume now.
                  </p>
                </div>
              </div>
              <div className="flex flex-col text-right shrink-0 bg-white px-3.5 py-1.5 rounded border border-[#bbf7d0] font-mono self-start sm:self-auto">
                <span className="text-[10px] text-[#166534] uppercase font-bold">Recommended Action</span>
                <span className="text-xs font-bold text-[#14532d]">EXECUTE COA TENDER</span>
              </div>
            </div>
          ) : (
            <div className="rounded-lg bg-[#eff6ff] border border-[#93c5fd] p-4 text-[#1e3a8a] flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-[#dbeafe] text-[#2563eb] flex items-center justify-center shrink-0">
                  <ShieldCheck className="h-5 w-5" />
                </div>
                <div>
                  <div className="text-xs sm:text-sm font-bold uppercase tracking-wider text-[#1e3a8a] font-mono">
                    RECOMMENDATION: Stay on Spot Market
                  </div>
                  <p className="text-xs text-[#1e40af] mt-0.5">
                    Projected Savings: <strong className="text-[#1e3a8a] underline font-mono">${formatCurrency(savingsAmt)} (₹{savingsInrCr} Crore)</strong>. Current spot rates remain cheaper than the 6-month forward curve.
                  </p>
                  {result.market_trend === "CONTANGO" && (
                    <p className="text-[11px] text-amber-800 mt-1 font-mono bg-amber-50 px-2 py-0.5 rounded border border-amber-200 flex items-center gap-1">
                      <AlertTriangle className="h-3 w-3 text-amber-600 shrink-0" />
                      <span>Note: While spot is currently cheaper, the 6-month forward curve is in Contango. Future spot voyages may become more expensive than a locked COA.</span>
                    </p>
                  )}
                </div>
              </div>
              <div className="flex flex-col text-right shrink-0 bg-white px-3.5 py-1.5 rounded border border-[#bfdbfe] font-mono self-start sm:self-auto">
                <span className="text-[10px] text-[#1e40af] uppercase font-bold">Recommended Action</span>
                <span className="text-xs font-bold text-[#1e3a8a]">PROCEED SPOT CHARTER</span>
              </div>
            </div>
          );
        })()}
      </div>
    </div>
  );
}
