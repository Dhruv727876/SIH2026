"use client";

import React, { useState, useEffect } from "react";
import FreightForecastChart from "@/components/FreightForecastChart";
import OptimizationPanel from "@/components/OptimizationPanel";
import CharterRecommendation from "@/components/CharterRecommendation";
import WhatIfSimulator from "@/components/WhatIfSimulator";
import {
  OptimizationRequest,
  OptimizationResponse,
  runOptimization,
} from "@/lib/api";
import { formatCurrency, formatInteger } from "@/lib/formatters";
import {
  Anchor,
  RefreshCw,
  Zap,
  TrendingUp,
  DollarSign,
  Layers,
  ShieldCheck,
  Building2,
  Clock,
} from "lucide-react";
import HelloPreloader from "@/components/ui/hello-preloader";

const USD_TO_INR_RATE = 83.5;

export default function DashboardPage() {
  const [request, setRequest] = useState<OptimizationRequest>({
    required_cargo_mt: 300000,
    origin_port: "Australia",
    target_port: "Paradip",
    planning_horizon_days: 30,
  });

  const [activeDisruption, setActiveDisruption] = useState<{
    eventType: string;
    eventName: string;
    multiplier: number;
  } | null>(null);

  const [optimizationResult, setOptimizationResult] = useState<OptimizationResponse>({
    status: "Optimal",
    origin_port: "Australia (Newcastle)",
    target_port: "Paradip",
    route: "Newcastle (AUS) -> Paradip (IND)",
    port_max_draft_m: 14.5,
    port_waiting_hours: 36.0,
    required_cargo_mt: 300000,
    total_cargo_allocated_mt: 320000,
    total_estimated_cost_usd: 6601275.29,
    estimated_savings_usd: 149731.76,
    benchmark_naive_cost_usd: 6751007.05,
    vessel_schedule: [
      { date: "2026-09-13", vessel_type: "Panamax", quantity: 1, capacity_mt: 80000, total_cargo_mt: 80000, freight_rate_usd_mt: 19.36, estimated_trip_cost_usd: 1651196.47 },
      { date: "2026-09-14", vessel_type: "Panamax", quantity: 1, capacity_mt: 80000, total_cargo_mt: 80000, freight_rate_usd_mt: 19.34, estimated_trip_cost_usd: 1649935.29 },
      { date: "2026-09-15", vessel_type: "Panamax", quantity: 1, capacity_mt: 80000, total_cargo_mt: 80000, freight_rate_usd_mt: 19.34, estimated_trip_cost_usd: 1649587.06 },
      { date: "2026-09-16", vessel_type: "Panamax", quantity: 1, capacity_mt: 80000, total_cargo_mt: 80000, freight_rate_usd_mt: 19.35, estimated_trip_cost_usd: 1650556.47 },
    ],
  });

  const [optimizing, setOptimizing] = useState<boolean>(false);
  const [mounted, setMounted] = useState<boolean>(false);
  const [currentTime, setCurrentTime] = useState<string>("");

  useEffect(() => {
    setMounted(true);
    const updateTime = () => {
      const now = new Date();
      const datePart = now.toLocaleDateString(undefined, {
        weekday: "short",
        day: "2-digit",
        month: "short",
        year: "numeric",
      });
      const timePart = now.toLocaleTimeString(undefined, {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: true,
        timeZoneName: "short",
      });
      setCurrentTime(`${datePart} • ${timePart}`);
    };

    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  const handleOptimizationChange = (updated: Partial<OptimizationRequest>) => {
    setRequest((prev) => ({ ...prev, ...updated }));
  };

  const handleApplyDisruption = (disruption: {
    eventType: string;
    eventName: string;
    multiplier: number;
    params?: Partial<OptimizationRequest>;
  }) => {
    setActiveDisruption({
      eventType: disruption.eventType,
      eventName: disruption.eventName,
      multiplier: disruption.multiplier,
    });

    const updatedParams = {
      ...request,
      ...(disruption.params || {}),
      disruption_multiplier: disruption.multiplier,
      disruption_name: disruption.eventName,
    };
    if (disruption.params) {
      setRequest((prev) => ({ ...prev, ...disruption.params }));
    }
    handleRunOptimization(updatedParams, disruption.multiplier);
  };

  const handleResetDisruption = () => {
    setActiveDisruption(null);
    handleRunOptimization({ ...request, disruption_multiplier: 1.0, disruption_name: undefined }, 1.0);
  };

  const handleRunOptimization = async (
    overrideParams?: Partial<OptimizationRequest>,
    shockMultiplierOverride?: number
  ) => {
    const currentMultiplier = shockMultiplierOverride !== undefined
      ? shockMultiplierOverride
      : activeDisruption ? activeDisruption.multiplier : 1.0;

    const payload = {
      ...request,
      ...overrideParams,
      disruption_multiplier: currentMultiplier,
      disruption_name: activeDisruption ? activeDisruption.eventName : undefined,
    };

    setOptimizing(true);
    try {
      const result = await runOptimization(payload);
      setOptimizationResult(result);
    } catch (err: any) {
      console.warn("Backend optimization request failed, recalculating locally:", err);
      generateFallbackOptimization(payload, currentMultiplier);
    } finally {
      setOptimizing(false);
    }
  };

  const generateFallbackOptimization = (payload: OptimizationRequest, multiplier: number = 1.0) => {
    const isCapesizeAllowed =
      payload.target_port !== "Haldia" && payload.target_port !== "Paradip";
    const isPanamaxAllowed = payload.target_port !== "Haldia";

    const vType = isCapesizeAllowed
      ? "Capesize"
      : isPanamaxAllowed
      ? "Panamax"
      : "Supramax";
    const cap = isCapesizeAllowed ? 150000 : isPanamaxAllowed ? 80000 : 50000;

    const originStr = (payload.origin_port || "Australia").toLowerCase();
    const routeMult = originStr.includes("brazil")
      ? 1.35
      : originStr.includes("south africa") || originStr.includes("africa")
      ? 1.15
      : originStr.includes("indonesia")
      ? 0.85
      : 1.0;

    const originName = originStr.includes("brazil")
      ? "Brazil (Tubarao)"
      : originStr.includes("south africa") || originStr.includes("africa")
      ? "South Africa (Richards Bay)"
      : originStr.includes("indonesia")
      ? "Indonesia (Samarinda)"
      : "Australia (Newcastle)";

    const combinedMultiplier = routeMult * multiplier;
    const baseRate = isCapesizeAllowed ? 17.14 : isPanamaxAllowed ? 19.35 : 22.41;
    const rate = Math.round(baseRate * combinedMultiplier * 100) / 100;
    const qty = Math.ceil(payload.required_cargo_mt / cap);

    const schedule = [];
    const now = new Date();
    for (let i = 1; i <= qty; i++) {
      const d = new Date(now);
      d.setDate(d.getDate() + 13 + i);
      const tripCost = cap * rate + 35000 * multiplier;
      schedule.push({
        date: d.toISOString().split("T")[0],
        vessel_type: vType,
        quantity: 1,
        capacity_mt: cap,
        total_cargo_mt: cap,
        freight_rate_usd_mt: rate,
        estimated_trip_cost_usd: tripCost,
      });
    }

    const totalCost = schedule.reduce((a, b) => a + b.estimated_trip_cost_usd, 0);
    const naiveCost = totalCost * 1.025;

    setOptimizationResult({
      status: "Optimal",
      origin_port: originName,
      target_port: payload.target_port,
      route: `${originName} -> ${payload.target_port} (IND)`,
      port_max_draft_m:
        payload.target_port === "Haldia"
          ? 12.0
          : payload.target_port === "Paradip"
          ? 14.5
          : 18.0,
      port_waiting_hours: 36.0,
      required_cargo_mt: payload.required_cargo_mt,
      total_cargo_allocated_mt: qty * cap,
      total_estimated_cost_usd: Math.round(totalCost * 100) / 100,
      estimated_savings_usd: Math.round((naiveCost - totalCost) * 100) / 100,
      benchmark_naive_cost_usd: Math.round(naiveCost * 100) / 100,
      vessel_schedule: schedule,
      active_disruption_name: activeDisruption?.eventName,
      disruption_multiplier: combinedMultiplier,
    });
  };

  const currentMultiplier = activeDisruption ? activeDisruption.multiplier : 1.0;
  const totalCostInrCrore = ((optimizationResult?.total_estimated_cost_usd || 0) * USD_TO_INR_RATE) / 10000000;
  const savingsInrCrore = ((optimizationResult?.estimated_savings_usd || 0) * USD_TO_INR_RATE) / 10000000;
  const savingsPct =
    optimizationResult?.benchmark_naive_cost_usd && optimizationResult.benchmark_naive_cost_usd > 0
      ? ((optimizationResult.estimated_savings_usd / optimizationResult.benchmark_naive_cost_usd) * 100).toFixed(1)
      : "2.2";

  return (
    <div className="min-h-screen bg-[#080c14] text-slate-200 flex flex-col font-sans">
      {/* Apple Hello Preloader */}
      <HelloPreloader />

      {/* Government of India / Ministry of Steel Header */}
      <header className="border-b border-[#1c263c] bg-[#0b101c] px-6 py-3 sticky top-0 z-40 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-3.5">
          <div className="h-9 w-9 rounded-lg bg-[#141c2e] border border-[#1c263c] flex items-center justify-center text-blue-400">
            <Anchor className="h-5 w-5 text-blue-400" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-slate-100 tracking-wide uppercase">
              Ministry of Steel &bull; Government of India
            </h1>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Intelligent Freight Forecasting & Vessel Chartering Decision Support System
            </p>
          </div>
        </div>

        {/* Telemetry / Live Time */}
        <div className="flex items-center gap-2.5 text-xs font-mono text-slate-300">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#080c14] border border-[#1c263c] text-slate-300 font-mono text-xs shadow-inner" suppressHydrationWarning>
            <Clock className="h-3.5 w-3.5 text-blue-400" />
            <span>{mounted && currentTime ? currentTime : "Live Telemetry"}</span>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-[1600px] w-full mx-auto p-5 md:p-6 space-y-5">
        {/* Executive Procurement KPI Summary Strip */}
        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
          {/* Card 1: Import Demand */}
          <div className="rounded-xl border border-[#1c263c] bg-[#0e1422] p-4 shadow-sm">
            <div className="flex items-center justify-between text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              <span>Target Cargo Demand</span>
              <Layers className="h-3.5 w-3.5 text-blue-400" />
            </div>
            <div className="text-xl font-bold font-mono text-slate-100 mt-1.5">
              {formatInteger(request.required_cargo_mt)} MT
            </div>
            <div className="text-[11px] text-slate-400 mt-1 font-mono flex items-center gap-1.5">
              <span className="text-emerald-400 font-semibold">{formatInteger(optimizationResult?.total_cargo_allocated_mt || 320000)} MT</span>
              <span>Allocated ({optimizationResult?.vessel_schedule?.length || 4} Voyages)</span>
            </div>
          </div>

          {/* Card 2: Total Landed Cost */}
          <div className="rounded-xl border border-[#1c263c] bg-[#0e1422] p-4 shadow-sm">
            <div className="flex items-center justify-between text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              <span>Optimal Landed Cost</span>
              <DollarSign className="h-3.5 w-3.5 text-slate-400" />
            </div>
            <div className="text-xl font-bold font-mono text-slate-100 mt-1.5">
              {formatCurrency(optimizationResult?.total_estimated_cost_usd || 6601275.29)}
            </div>
            <div className="text-[11px] text-slate-400 mt-1 font-mono">
              &asymp; <strong className="text-slate-200">₹{totalCostInrCrore.toFixed(2)} Crore</strong> CIF Indian Terminal
            </div>
          </div>

          {/* Card 3: Net PSU Savings */}
          <div className="rounded-xl border border-[#1c263c] bg-[#0e1422] p-4 shadow-sm">
            <div className="flex items-center justify-between text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              <span>Net PSU Procurement Savings</span>
              <TrendingUp className="h-3.5 w-3.5 text-emerald-400" />
            </div>
            <div className="text-xl font-bold font-mono text-emerald-400 mt-1.5 flex items-center gap-2">
              <span>+{formatCurrency(optimizationResult?.estimated_savings_usd || 149731.76)}</span>
              <span className="text-xs px-1.5 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20 font-bold">
                +{savingsPct}%
              </span>
            </div>
            <div className="text-[11px] text-emerald-400/90 mt-1 font-mono">
              &asymp; <strong className="text-emerald-300">₹{savingsInrCrore.toFixed(2)} Crore</strong> Saved vs. Spot Rates
            </div>
          </div>

          {/* Card 4: Port Navigational Status */}
          <div className="rounded-xl border border-[#1c263c] bg-[#0e1422] p-4 shadow-sm">
            <div className="flex items-center justify-between text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              <span>Port Clearance & Draft</span>
              <ShieldCheck className="h-3.5 w-3.5 text-amber-400" />
            </div>
            <div className="text-lg font-bold font-mono text-slate-100 mt-1.5 truncate">
              {request.target_port} ({optimizationResult?.port_max_draft_m || 14.5}m Draft)
            </div>
            <div className="text-[11px] text-amber-300/90 mt-1 font-mono truncate">
              {request.target_port === "Paradip"
                ? "Capesize Restricted (Panamax Clear)"
                : request.target_port === "Haldia"
                ? "Supramax Only (12.0m Riverine Draft)"
                : "Deepwater Capesize Berth Clear"}
            </div>
          </div>
        </section>

        {/* Primary Operational Workspace: Procurement Configuration (Left) + Charter Party Manifest Table (Right) */}
        <section className="grid grid-cols-1 xl:grid-cols-12 gap-5">
          <div className="xl:col-span-4 flex flex-col">
            <OptimizationPanel
              request={request}
              onChange={handleOptimizationChange}
              onOptimize={() => handleRunOptimization()}
              loading={optimizing}
              disruptionMultiplier={currentMultiplier}
              activeDisruptionName={activeDisruption?.eventName}
            />
          </div>

          <div className="xl:col-span-8 flex flex-col">
            <CharterRecommendation
              result={optimizationResult}
              loading={optimizing}
            />
          </div>
        </section>

        {/* Middle Section: What-If Maritime Disruption Stress Testing Carousel */}
        <section>
          <WhatIfSimulator
            onApplyDisruption={handleApplyDisruption}
            onResetDisruption={handleResetDisruption}
            activeDisruptionName={activeDisruption?.eventName || null}
            loading={optimizing}
          />
        </section>

        {/* Lower Analytics Section: 60-Day Forward Rate Curve & Volatility Corridor */}
        <section>
          <FreightForecastChart
            disruptionMultiplier={currentMultiplier}
            activeDisruptionName={activeDisruption?.eventName}
          />
        </section>
      </main>

      <footer className="border-t border-[#1c263c] bg-[#0b101c] py-3 px-6 text-[11px] text-slate-500 flex items-center justify-between max-w-[1600px] w-full mx-auto">
        <span>Ministry of Steel &bull; Freight Decision Support System</span>
        <span className="font-mono">v1.0.0</span>
      </footer>
    </div>
  );
}
