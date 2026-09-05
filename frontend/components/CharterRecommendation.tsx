"use client";

import React, { useState } from "react";
import { OptimizationResponse } from "@/lib/api";
import { formatCurrency, formatInteger } from "@/lib/formatters";
import { DotBorderWrapper } from "@/components/ui/dot-border-wrapper";
import { TextShimmer } from "@/components/ui/shimmer-text";
import {
  CheckCircle2,
  AlertTriangle,
  Ship,
  Calendar,
  Layers,
  FileSpreadsheet,
  ShieldCheck,
  Fuel,
  Clock,
  ExternalLink,
  ChevronRight,
  HelpCircle,
} from "lucide-react";

interface CharterRecommendationProps {
  result: OptimizationResponse | null;
  loading: boolean;
}

const USD_TO_INR_RATE = 83.5;

export default function CharterRecommendation({
  result,
  loading,
}: CharterRecommendationProps) {
  const [copied, setCopied] = useState<boolean>(false);

  if (loading) {
    return (
      <div className="rounded-xl border border-[#1c263c] bg-[#0e1422] p-8 flex flex-col items-center justify-center min-h-[360px] text-center shadow-sm">
        <TextShimmer className="font-light text-2xl sm:text-3xl tracking-tight">
          Agent is thinking ...
        </TextShimmer>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="rounded-xl border border-dashed border-[#1c263c] bg-[#0e1422]/60 p-8 flex flex-col items-center justify-center min-h-[360px] text-center">
        <div className="p-3 rounded-full bg-[#080c14] text-slate-500 mb-3 border border-[#1c263c]">
          <Ship className="h-6 w-6" />
        </div>
        <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
          Awaiting Parameter Execution
        </h4>
        <p className="text-xs text-slate-500 max-w-xs mt-1">
          Configure departure origin, target PSU discharge terminal, and required tonnage, then execute the MILP solver.
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

  const totalVessels = result.vessel_schedule.reduce((acc, s) => acc + s.quantity, 0);
  const totalCostInrCrore = (result.total_estimated_cost_usd * USD_TO_INR_RATE) / 10000000;
  const savingsInrCrore = (result.estimated_savings_usd * USD_TO_INR_RATE) / 10000000;
  const savingsPct =
    result.benchmark_naive_cost_usd && result.benchmark_naive_cost_usd > 0
      ? ((result.estimated_savings_usd / result.benchmark_naive_cost_usd) * 100).toFixed(1)
      : "2.2";

  // CSV Export handler
  const handleExportCSV = () => {
    if (!result.vessel_schedule || result.vessel_schedule.length === 0) return;

    const headers = [
      "Voyage #",
      "Laycan Date",
      "Vessel Class",
      "Cargo Parcel (MT)",
      "Freight Rate ($/MT)",
      "Trip Cost (USD)",
      "Trip Cost (INR Lakhs)",
      "Origin Port",
      "Discharge Port",
      "Status",
    ];

    const rows = result.vessel_schedule.map((s, idx) => {
      const tripCost = s.estimated_trip_cost_usd || (s.capacity_mt || 80000) * (s.freight_rate_usd_mt || 20);
      const inrLakhs = (tripCost * USD_TO_INR_RATE) / 100000;
      return [
        idx + 1,
        s.date,
        s.vessel_type,
        s.capacity_mt || s.total_cargo_mt,
        s.freight_rate_usd_mt?.toFixed(2),
        tripCost.toFixed(2),
        inrLakhs.toFixed(2),
        result.origin_port || "Australia",
        result.target_port || "Paradip",
        "DISPATCHED",
      ].join(",");
    });

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `charter_party_manifest_${result.target_port}_${new Date().toISOString().split("T")[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="rounded-xl border border-[#1c263c] bg-[#0e1422] p-5 space-y-5 shadow-sm">
      {/* Top Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#1c263c]">
        <div className="flex items-center gap-2.5">
          <div
            className={`p-1.5 rounded-lg border ${
              isOptimal
                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                : "bg-rose-500/10 text-rose-400 border-rose-500/20"
            }`}
          >
            {isOptimal ? <CheckCircle2 className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-bold text-slate-100 uppercase tracking-wider">
                Vessel Dispatch & Charter Manifest
              </h3>
              <span
                className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                  isOptimal
                    ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20 font-semibold"
                    : "bg-rose-500/10 text-rose-400 border-rose-500/20"
                }`}
              >
                {result.status}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5 font-mono">
              {result.route || `${result.origin_port} -> ${result.target_port}`}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <DotBorderWrapper theme="emerald" wrapperClassName="p-0">
            <button
              type="button"
              onClick={handleExportCSV}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#141c2e] hover:bg-[#1a253d] text-slate-200 text-xs font-medium border border-[#1c263c] transition shadow-sm"
            >
              <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-400" />
              <span>Export Manifest (CSV)</span>
            </button>
          </DotBorderWrapper>
        </div>
      </div>

      {/* Active Corridor & Compliance Strip */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 px-3.5 py-2.5 rounded-lg bg-[#141c2e] border border-[#1c263c] text-xs">
        <div className="flex items-center gap-2">
          <Ship className="h-4 w-4 text-blue-400 shrink-0" />
          <span className="text-slate-400 font-medium">Corridor:</span>
          <span className="font-mono text-slate-100 font-semibold">
            {result.route || `${result.origin_port} -> ${result.target_port}`}
          </span>
        </div>

        <div className="flex items-center gap-3 text-[11px]">
          <span className="text-slate-400 font-mono">
            Tonnage Allocated: <strong className="text-emerald-400">{formatInteger(result.total_cargo_allocated_mt || 0)} MT</strong> / {formatInteger(result.required_cargo_mt || 0)} MT
          </span>
          <span className="text-slate-400 font-mono">
            Voyages: <strong className="text-slate-200">{totalVessels} Ships</strong>
          </span>
        </div>
      </div>

      {/* Draft Restriction Warning Box if Capesize/Panamax Restricted */}
      {draftExclusions.length > 0 && (
        <div className="rounded-lg bg-amber-500/10 border border-amber-500/25 px-3.5 py-2.5 flex items-start gap-2.5 text-xs text-amber-300">
          <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold text-[11px] uppercase tracking-wider text-amber-200">
              Port Navigational Channel Constraints Enforced
            </div>
            <ul className="mt-0.5 space-y-0.5 list-disc list-inside text-[11px] text-amber-300/90 font-mono">
              {draftExclusions.map((ex, idx) => (
                <li key={idx}>{ex}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Tabular Manifest Schedule */}
      <div className="rounded-lg border border-[#1c263c] overflow-hidden bg-[#080c14]">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#141c2e] text-slate-400 text-[10px] uppercase font-semibold tracking-wider border-b border-[#1c263c]">
              <tr>
                <th className="py-2.5 px-3.5">Laycan Date</th>
                <th className="py-2.5 px-3">Vessel Class</th>
                <th className="py-2.5 px-3">Parcels</th>
                <th className="py-2.5 px-3">Parcel Size (MT)</th>
                <th className="py-2.5 px-3 text-right">Freight Rate ($/MT)</th>
                <th className="py-2.5 px-3 text-right">Trip Cost (USD)</th>
                <th className="py-2.5 px-3 text-right">Trip Cost (INR)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#162032] font-mono text-slate-200">
              {result.vessel_schedule.map((row, idx) => {
                const tripCost =
                  row.estimated_trip_cost_usd ||
                  (row.capacity_mt || 80000) * (row.freight_rate_usd_mt || 20);
                const tripCostInrLakhs = (tripCost * USD_TO_INR_RATE) / 100000;

                return (
                  <tr key={idx} className="hover:bg-[#0e1422] transition">
                    <td className="py-2.5 px-3.5 font-medium text-slate-300 flex items-center gap-1.5">
                      <Calendar className="h-3.5 w-3.5 text-slate-500" />
                      <span>{row.date}</span>
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="px-2 py-0.5 rounded bg-[#141c2e] border border-[#1c263c] text-blue-300 text-[11px] font-semibold">
                        {row.vessel_type}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-slate-400">{row.quantity}x</td>
                    <td className="py-2.5 px-3 text-slate-100 font-semibold">
                      {formatInteger(row.capacity_mt || row.total_cargo_mt || 0)} MT
                    </td>
                    <td className="py-2.5 px-3 text-right text-slate-200 font-semibold">
                      ${row.freight_rate_usd_mt?.toFixed(2)}/MT
                    </td>
                    <td className="py-2.5 px-3 text-right font-bold text-slate-100">
                      {formatCurrency(tripCost)}
                    </td>
                    <td className="py-2.5 px-3 text-right text-slate-400 text-[11px]">
                      ₹{tripCostInrLakhs.toFixed(1)} L
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
