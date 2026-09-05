"use client";

import React from "react";
import { OptimizationRequest } from "@/lib/api";
import { formatInteger } from "@/lib/formatters";
import { DotBorderWrapper } from "@/components/ui/dot-border-wrapper";
import { Slider } from "@/components/ui/slider";
import {
  Sliders,
  Anchor,
  Calendar,
  Layers,
  Play,
  RefreshCw,
  AlertCircle,
  Zap,
  Globe,
  Navigation,
  Compass,
} from "lucide-react";

interface OptimizationPanelProps {
  request: OptimizationRequest;
  onChange: (updated: Partial<OptimizationRequest>) => void;
  onOptimize: () => void;
  loading: boolean;
  disruptionMultiplier?: number;
  activeDisruptionName?: string | null;
}

const ORIGIN_PORTS = [
  {
    value: "Australia",
    name: "Australia (Newcastle)",
    country: "AUS",
    multiplier: "1.00x Base Corridor",
    desc: "Primary Pacific Coking Coal Export Terminal (~5,200 nm)",
  },
  {
    value: "Indonesia",
    name: "Indonesia (Samarinda)",
    country: "IDN",
    multiplier: "0.85x Short-Haul",
    desc: "Low-Distance Thermal & Semi-Soft Coal Corridor (~2,600 nm)",
  },
  {
    value: "South Africa",
    name: "South Africa (Richards Bay)",
    country: "ZAF",
    multiplier: "1.15x Medium-Haul",
    desc: "Indian Ocean Coal Hub to East Coast India (~4,800 nm)",
  },
  {
    value: "Brazil",
    name: "Brazil (Tubarao)",
    country: "BRA",
    multiplier: "1.35x Long-Haul",
    desc: "Atlantic High-Grade Direct Shipping Ore Deepwater Terminal (~8,900 nm)",
  },
];

const DISCHARGE_PORTS = [
  { name: "Paradip", draft: "14.5m", type: "Major Ore & Coking Coal Terminal (Odisha)" },
  { name: "Visakhapatnam", draft: "16.5m", type: "RINL Dedicated Outer Harbour (Andhra Pradesh)" },
  { name: "Haldia", draft: "12.0m", type: "Shallow Riverine Channel (SAIL Durgapur feeder)" },
  { name: "Dhamra", draft: "18.0m", type: "Deepwater Capesize Berth (Odisha)" },
  { name: "Gangavaram", draft: "20.0m", type: "Ultra-Deepwater Bulk Port (Andhra Pradesh)" },
];

export default function OptimizationPanel({
  request,
  onChange,
  onOptimize,
  loading,
  disruptionMultiplier = 1.0,
  activeDisruptionName = null,
}: OptimizationPanelProps) {
  const selectedOrigin =
    ORIGIN_PORTS.find(
      (p) =>
        p.value.toLowerCase() === (request.origin_port || "Australia").toLowerCase() ||
        (request.origin_port || "").includes(p.value)
    ) || ORIGIN_PORTS[0];

  const selectedDischargePort =
    DISCHARGE_PORTS.find((p) => p.name === request.target_port) || DISCHARGE_PORTS[0];

  const spikePct = Math.round(((disruptionMultiplier || 1.0) - 1.0) * 100);

  return (
    <div className="rounded-xl border border-[#1c263c] bg-[#0e1422] p-5 shadow-sm flex flex-col justify-between h-full">
      <div>
        {/* Header */}
        <div className="flex items-center justify-between pb-3.5 border-b border-[#1c263c] mb-4">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-md bg-[#141c2e] text-blue-400 border border-[#1c263c]">
              <Sliders className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-xs font-bold text-slate-100 uppercase tracking-wider">
                Procurement Parameters
              </h3>
            </div>
          </div>
        </div>

        {/* Active Disruption Shock Pill */}
        {activeDisruptionName && disruptionMultiplier > 1.0 && (
          <div className="mb-4 rounded-lg bg-amber-500/10 border border-amber-500/30 px-3 py-2 flex items-center justify-between text-xs text-amber-300">
            <div className="flex items-center gap-1.5 font-medium">
              <Zap className="h-3.5 w-3.5 text-amber-400 shrink-0" />
              <span className="truncate">Active Stress Shock: +{spikePct}%</span>
            </div>
            <span className="text-[10px] font-mono bg-amber-500/20 px-2 py-0.5 rounded text-amber-200 font-bold shrink-0">
              {disruptionMultiplier.toFixed(2)}x Multiplier
            </span>
          </div>
        )}

        {/* Input Form Fields */}
        <div className="space-y-4">
          {/* 1. Required Cargo Volume */}
          <div>
            <label className="flex items-center justify-between text-xs font-medium text-slate-300 mb-1.5">
              <span className="flex items-center gap-1.5">
                <Layers className="h-3.5 w-3.5 text-slate-400" />
                Required Cargo Volume
              </span>
              <span className="text-xs text-blue-400 font-mono font-semibold">
                {formatInteger(request.required_cargo_mt)} MT
              </span>
            </label>
            <div className="relative">
              <input
                type="number"
                min={20000}
                max={1000000}
                step={10000}
                value={request.required_cargo_mt}
                onChange={(e) =>
                  onChange({ required_cargo_mt: Number(e.target.value) || 0 })
                }
                disabled={loading}
                className="w-full rounded-lg bg-[#080c14] border border-[#1c263c] px-3.5 py-2 text-sm text-slate-100 font-mono focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none transition"
              />
              <span className="absolute right-3 top-2 text-xs text-slate-500 font-medium">
                MT
              </span>
            </div>

            {/* Standard PSU Tonnage Presets */}
            <div className="flex items-center gap-1.5 mt-2">
              {[80000, 150000, 300000, 500000].map((preset) => (
                <button
                  key={preset}
                  type="button"
                  onClick={() => onChange({ required_cargo_mt: preset })}
                  className={`text-[10px] font-mono px-2 py-1 rounded border transition ${
                    request.required_cargo_mt === preset
                      ? "bg-blue-600/20 text-blue-300 border-blue-500/50 font-bold"
                      : "bg-[#080c14] text-slate-400 border-[#1c263c] hover:bg-[#141c2e] hover:text-slate-200"
                  }`}
                >
                  {formatInteger(preset / 1000)}k MT
                </button>
              ))}
            </div>
          </div>

          {/* 2. Departure Port / Origin */}
          <div>
            <label className="flex items-center justify-between text-xs font-medium text-slate-300 mb-1.5">
              <span className="flex items-center gap-1.5">
                <Compass className="h-3.5 w-3.5 text-slate-400" />
                Raw Material Loading Origin
              </span>
              <span className="text-[11px] text-slate-400 font-mono">
                {selectedOrigin.multiplier}
              </span>
            </label>
            <select
              value={request.origin_port || "Australia"}
              onChange={(e) => onChange({ origin_port: e.target.value })}
              disabled={loading}
              className="w-full rounded-lg bg-[#080c14] border border-[#1c263c] px-3 py-2 text-xs text-slate-100 focus:border-blue-500 focus:outline-none transition font-mono cursor-pointer"
            >
              {ORIGIN_PORTS.map((port) => (
                <option key={port.value} value={port.value} className="bg-[#0e1422] text-slate-100">
                  {port.name} &bull; {port.multiplier}
                </option>
              ))}
            </select>
            <p className="text-[11px] text-slate-400 mt-1 leading-snug">
              {selectedOrigin.desc}
            </p>
          </div>

          {/* 3. Target Indian Discharge Port */}
          <div>
            <label className="flex items-center justify-between text-xs font-medium text-slate-300 mb-1.5">
              <span className="flex items-center gap-1.5">
                <Anchor className="h-3.5 w-3.5 text-slate-400" />
                Target Indian Discharge Port
              </span>
              <span className="text-[11px] text-amber-400 font-mono font-semibold">
                Draft Limit: {selectedDischargePort.draft}
              </span>
            </label>
            <select
              value={request.target_port}
              onChange={(e) => onChange({ target_port: e.target.value })}
              disabled={loading}
              className="w-full rounded-lg bg-[#080c14] border border-[#1c263c] px-3 py-2 text-xs text-slate-100 focus:border-blue-500 focus:outline-none transition font-mono cursor-pointer"
            >
              {DISCHARGE_PORTS.map((port) => (
                <option key={port.name} value={port.name} className="bg-[#0e1422] text-slate-100">
                  {port.name} (Max Draft: {port.draft})
                </option>
              ))}
            </select>
          </div>

          {/* 4. Laycan Planning Horizon Window */}
          <div>
            <div className="flex items-center justify-between text-xs font-medium text-slate-300 mb-1">
              <span className="flex items-center gap-1.5">
                <Calendar className="h-3.5 w-3.5 text-slate-400" />
                Charter Laycan Planning Window
              </span>
              <span className="text-xs text-blue-400 font-mono font-semibold">
                {request.planning_horizon_days} Days Forward
              </span>
            </div>
            <Slider
              value={request.planning_horizon_days}
              onChange={(val) => {
                const days = typeof val === "number" ? val : val[0];
                onChange({ planning_horizon_days: days });
              }}
              min={7}
              max={60}
              step={1}
              disabled={loading}
              showValue={true}
              valuePosition="right"
              formatValue={(v) => `${v}d`}
            />
          </div>
        </div>
      </div>

      {/* Action Button with Dot Border HUD Effect */}
      <div className="pt-3 mt-3 border-t border-[#1c263c]">
        <DotBorderWrapper
          theme={disruptionMultiplier > 1.0 ? "amber" : "blue"}
          className="w-full"
        >
          <button
            type="button"
            onClick={onOptimize}
            disabled={loading}
            className={`w-full rounded-lg px-4 py-2.5 text-xs font-semibold tracking-wider uppercase shadow transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 ${
              disruptionMultiplier > 1.0
                ? "bg-amber-600 hover:bg-amber-500 text-white"
                : "bg-blue-600 hover:bg-blue-500 text-white"
            }`}
          >
            {loading ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin text-white" />
                <span>Solving Constrained MILP Matrix...</span>
              </>
            ) : (
              <>
                <Play className="h-3.5 w-3.5 fill-white" />
                <span>
                  {disruptionMultiplier > 1.0
                    ? `Execute Optimizer (+${spikePct}% Shock Active)`
                    : "Execute MILP Optimizer"}
                </span>
              </>
            )}
          </button>
        </DotBorderWrapper>
      </div>
    </div>
  );
}
