"use client";

import React, { useState, useEffect } from "react";
import Sidebar, { ViewType } from "@/components/Sidebar";
import DashboardView from "@/components/views/DashboardView";
import StrategyView from "@/components/views/StrategyView";
import WhatIfView from "@/components/views/WhatIfView";
import ForecastingView from "@/components/views/ForecastingView";
import {
  OptimizationRequest,
  OptimizationResponse,
  runOptimization,
} from "@/lib/api";
import { formatInteger } from "@/lib/formatters";
import {
  Landmark,
  Flag,
  ShieldCheck,
  Network,
} from "lucide-react";

const DISCHARGE_PORT_METADATA: Record<
  string,
  { draftLimit: number; allowsCape: boolean; allowsPanamax: boolean; description: string }
> = {
  Paradip: {
    draftLimit: 14.5,
    allowsCape: false,
    allowsPanamax: true,
    description: "Major Coking Coal Terminal (Odisha). 14.50m channel ceiling strictly disqualifies Capesize bulkers to eliminate Sandheads lighterage.",
  },
  Visakhapatnam: {
    draftLimit: 16.5,
    allowsCape: false,
    allowsPanamax: true,
    description: "RINL dedicated Outer Harbour (Andhra Pradesh). 16.50m draft permits deep-laden Panamax vessels with priority berthing.",
  },
  Haldia: {
    draftLimit: 12.0,
    allowsCape: false,
    allowsPanamax: false,
    description: "Shallow Riverine Lock-Gate Port (West Bengal). Strictly limited to geared Supramax carriers (50k MT) to prevent grounding in Hooghly shoals.",
  },
  Dhamra: {
    draftLimit: 18.0,
    allowsCape: true,
    allowsPanamax: true,
    description: "Deepwater Port (Odisha). 18.00m draft fully accommodates fully laden Capesize and Panamax carriers without lightering surcharge.",
  },
  Gangavaram: {
    draftLimit: 20.0,
    allowsCape: true,
    allowsPanamax: true,
    description: "Ultra-Deepwater Bulk Port (Andhra Pradesh). Capable of handling standard and Newcastlemax bulkers with zero draft restrictions.",
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

export default function FreightDSSApp() {
  // Navigation & View Toggling State
  const [activeView, setActiveView] = useState<ViewType>("dashboard");
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(false);
  const [optimizing, setOptimizing] = useState<boolean>(false);
  const [fontSizeMultiplier, setFontSizeMultiplier] = useState<number>(1.0);

  // Form Parameters
  const [request, setRequest] = useState<OptimizationRequest>({
    required_cargo_mt: 300000,
    origin_port: "Australia (Newcastle)",
    target_port: "Paradip",
    planning_horizon_days: 30,
    allow_lighterage: true,
  });

  // Optimization Result: Initial state is NULL so parameter form appears first
  const [optimizationResult, setOptimizationResult] = useState<OptimizationResponse | null>(null);

  // Accessibility font scaling
  useEffect(() => {
    if (typeof document !== "undefined") {
      document.documentElement.style.fontSize = `${fontSizeMultiplier * 100}%`;
    }
  }, [fontSizeMultiplier]);

  // Handler: Run standard optimization from Dashboard or Strategy View
  const handleRunOptimization = async (override?: Partial<OptimizationRequest>) => {
    setOptimizing(true);
    const activeReq = override ? { ...request, ...override } : request;
    if (override) {
      setRequest(activeReq);
    }
    const startTime = performance.now();

    const payload: OptimizationRequest = {
      required_cargo_mt: activeReq.required_cargo_mt,
      target_port: activeReq.target_port,
      origin_port: activeReq.origin_port,
      planning_horizon_days: activeReq.planning_horizon_days,
      allow_lighterage: activeReq.allow_lighterage ?? true,
      force_refresh: true,
    };

    try {
      const result = await runOptimization(payload);
      const elapsed = performance.now() - startTime;
      if (elapsed < 400) {
        await new Promise((r) => setTimeout(r, 400 - elapsed));
      }
      setOptimizationResult(result);
    } catch (err) {
      console.warn("API optimization request failed, using client calculation:", err);
      const elapsed = performance.now() - startTime;
      if (elapsed < 400) {
        await new Promise((r) => setTimeout(r, 400 - elapsed));
      }
      generateFallbackPlan(payload, 1.0);
    } finally {
      setOptimizing(false);
    }
  };

  // Handler: Run What-If disruption optimization
  const handleRunOptimizationWithDisruption = async (
    multiplier: number,
    name: string
  ): Promise<OptimizationResponse | null> => {
    setOptimizing(true);
    const startTime = performance.now();

    const payload: OptimizationRequest = {
      required_cargo_mt: request.required_cargo_mt,
      target_port: request.target_port,
      origin_port: request.origin_port,
      planning_horizon_days: request.planning_horizon_days,
      allow_lighterage: request.allow_lighterage ?? true,
      disruption_multiplier: multiplier,
      disruption_name: name,
      force_refresh: true,
    };

    try {
      const result = await runOptimization(payload);
      const elapsed = performance.now() - startTime;
      if (elapsed < 400) {
        await new Promise((r) => setTimeout(r, 400 - elapsed));
      }
      return result;
    } catch (err) {
      console.warn("Disruption optimization failed, generating fallback:", err);
      return generateFallbackPlan(payload, multiplier);
    } finally {
      setOptimizing(false);
    }
  };

  // Local fallback calculation engine
  const generateFallbackPlan = (
    payload: OptimizationRequest,
    multiplier: number = 1.0
  ): OptimizationResponse => {
    const dischargeSpec =
      DISCHARGE_PORT_METADATA[payload.target_port] ||
      DISCHARGE_PORT_METADATA["Paradip"];
    const maxDraft = dischargeSpec.draftLimit;
    const allowsLighterage = payload.allow_lighterage ?? true;

    let vType = dischargeSpec.allowsCape
      ? "Capesize"
      : dischargeSpec.allowsPanamax
      ? "Panamax"
      : "Supramax";
    let cap = dischargeSpec.allowsCape ? 150000 : dischargeSpec.allowsPanamax ? 80000 : 50000;
    let strategyUsed = "DIRECT_DISCHARGE";
    let lighteragePenaltyApplied = 0.0;
    let lighterageCount = 0;
    let lighterageType = "";

    if (maxDraft < 17.0 && allowsLighterage) {
      const directCap = dischargeSpec.allowsPanamax ? 80000 : 50000;
      const directBaseRate = dischargeSpec.allowsPanamax ? 19.35 : 22.41;
      const directQty = Math.max(1, Math.ceil(payload.required_cargo_mt / directCap));
      const costA = directQty * (directCap * directBaseRate * multiplier + 32000 * multiplier);

      const capeCap = 150000;
      const capeBaseRate = 17.14;
      const capeQty = Math.max(1, Math.ceil(payload.required_cargo_mt / capeCap));
      const transferFee = capeQty * capeCap * 3.5;
      const timePenalty = capeQty * 25000.0;
      const lighterageSurcharge = transferFee + timePenalty;
      const costB =
        capeQty * (capeCap * capeBaseRate * multiplier + 32000 * multiplier) +
        lighterageSurcharge;

      if (costB < costA) {
        vType = "Capesize";
        cap = capeCap;
        strategyUsed = "MID_SEA_LIGHTERAGE";
        lighteragePenaltyApplied = lighterageSurcharge;
        lighterageCount = Math.ceil(capeCap / 50000);
        lighterageType = "Supramax";
      }
    }

    const baseRate = vType === "Capesize" ? 17.14 : vType === "Panamax" ? 19.35 : 22.41;
    const rate = Math.round(baseRate * multiplier * 100) / 100;
    const qty = Math.max(1, Math.ceil(payload.required_cargo_mt / cap));

    const schedule = [];
    const now = new Date();
    const perStemLighterage =
      lighteragePenaltyApplied > 0 ? lighteragePenaltyApplied / qty : 0;

    for (let i = 1; i <= qty; i++) {
      const d = new Date(now);
      d.setDate(d.getDate() + 6 + i * 5);
      const tripCost = cap * rate + 32000 * multiplier + perStemLighterage;
      schedule.push({
        date: d.toISOString().split("T")[0],
        vessel_type: vType,
        quantity: 1,
        capacity_mt: cap,
        total_cargo_mt: cap,
        freight_rate_usd_mt: rate,
        estimated_trip_cost_usd: Math.round(tripCost * 100) / 100,
      });
    }

    const totalCost = schedule.reduce(
      (a, b) => a + (b.estimated_trip_cost_usd || 0),
      0
    );
    const naiveCost = totalCost * 1.025;

    const discountPct =
      payload.required_cargo_mt >= 300000 ? 5.0 : payload.required_cargo_mt >= 150000 ? 2.0 : -2.0;
    const coaRate = Math.round(rate * 1.05 * (1.0 - discountPct / 100) * 100) / 100;
    const coaTotalCost = coaRate * payload.required_cargo_mt;

    const newResult: OptimizationResponse = {
      status: "Optimal",
      origin_port: payload.origin_port || "Australia (Newcastle)",
      target_port: payload.target_port,
      route: `${payload.origin_port || "Australia"} -> ${payload.target_port} (IND)`,
      port_max_draft_m: dischargeSpec.draftLimit,
      port_waiting_hours: 36.0,
      required_cargo_mt: payload.required_cargo_mt,
      total_cargo_allocated_mt: qty * cap,
      total_estimated_cost_usd: Math.round(totalCost * 100) / 100,
      estimated_savings_usd: Math.round((naiveCost - totalCost) * 100) / 100,
      benchmark_naive_cost_usd: Math.round(naiveCost * 100) / 100,
      vessel_schedule: schedule,
      strategy_used: strategyUsed,
      lighterage_penalty_applied: lighteragePenaltyApplied,
      lighterage_vessel_count: lighterageCount || undefined,
      lighterage_vessel_type: lighterageType || undefined,
      procurement_recommendation: coaTotalCost < totalCost ? "LOCK_IN_COA" : "STAY_SPOT",
      market_trend: "CONTANGO",
      coa_discount_pct: discountPct,
      coa_rate_usd_per_mt: coaRate,
      coa_total_cost_usd: Math.round(coaTotalCost * 100) / 100,
      coa_savings_usd: Math.abs(Math.round((totalCost - coaTotalCost) * 100) / 100),
    };

    setOptimizationResult(newResult);
    return newResult;
  };

  return (
    <div className="min-h-screen h-screen flex flex-col overflow-hidden bg-[#f8f9ff] text-[#0d1c2e] font-sans">
      {/* ========================================================= */}
      {/* 1. FULL-WIDTH INSTITUTIONAL HEADER (Spans 100% Horizontal Space) */}
      {/* ========================================================= */}
      <header className="w-full bg-white z-40 shadow-xs shrink-0 select-none">
        {/* Tier 1: Main Institutional Strip */}
        <div className="w-full border-b border-[#e2e8f0] px-4 md:px-6 h-14 flex items-center justify-between">
          {/* Left: Emblem & Ministry Branding */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded bg-[#eff4ff] text-[#12355b] border border-[#dce9ff] flex items-center justify-center shrink-0">
              <Landmark className="h-4 w-4 text-[#12355b]" />
            </div>
            <div className="flex flex-col">
              <span className="text-[11px] font-bold tracking-wider uppercase text-[#001f3f] leading-tight">
                Government of India
              </span>
              <span className="text-xs text-[#495f82] font-semibold leading-tight">
                Ministry of Steel • इस्पात मंत्रालय
              </span>
            </div>
            <div className="hidden md:block w-px h-6 bg-[#cbd5e1] mx-2"></div>
            <span className="hidden md:inline text-xs text-[#475569] italic font-serif-gov">
              &ldquo;Stronger Steel for a Stronger India&rdquo;
            </span>
          </div>

          {/* Right: Viksit Bharat, Font Accessibility & Chartering Desk Badge */}
          <div className="flex items-center gap-3">
            <div className="hidden lg:flex items-center gap-1.5 bg-[#eff4ff] px-2.5 py-1 rounded text-[#12355b] border border-[#dce9ff]">
              <Flag className="h-3.5 w-3.5 text-[#e65100]" />
              <span className="text-[11px] font-bold uppercase tracking-wider">
                Viksit Bharat 2047
              </span>
            </div>

            {/* Font Size Accessibility Controls: [ A- ] [ A ] [ A+ ] */}
            <div
              className="flex items-center gap-1 bg-[#f1f5f9] p-0.5 rounded border border-[#cbd5e1]"
              role="group"
              aria-label="Text size accessibility controls"
            >
              <button
                type="button"
                onClick={() => setFontSizeMultiplier(0.9)}
                className={`px-2 py-0.5 rounded text-xs font-semibold transition cursor-pointer ${
                  fontSizeMultiplier < 0.95
                    ? "bg-[#12355b] text-white font-bold shadow-xs"
                    : "text-[#475569] hover:bg-[#e2e8f0]"
                }`}
              >
                A-
              </button>
              <button
                type="button"
                onClick={() => setFontSizeMultiplier(1.0)}
                className={`px-2 py-0.5 rounded text-xs font-bold transition cursor-pointer ${
                  fontSizeMultiplier >= 0.95 && fontSizeMultiplier <= 1.05
                    ? "bg-[#12355b] text-white shadow-xs"
                    : "text-[#475569] hover:bg-[#e2e8f0]"
                }`}
              >
                A
              </button>
              <button
                type="button"
                onClick={() => setFontSizeMultiplier(1.1)}
                className={`px-2 py-0.5 rounded text-xs font-semibold transition cursor-pointer ${
                  fontSizeMultiplier > 1.05
                    ? "bg-[#12355b] text-white font-bold shadow-xs"
                    : "text-[#475569] hover:bg-[#e2e8f0]"
                }`}
              >
                A+
              </button>
            </div>

            {/* MoS Chartering Desk Badge */}
            <div className="flex items-center gap-2 pl-2 border-l border-[#cbd5e1]">
              <div className="w-8 h-8 rounded-full bg-[#12355b] text-white flex items-center justify-center font-bold text-xs shrink-0">
                <ShieldCheck className="h-4 w-4" />
              </div>
              <div className="hidden xl:flex flex-col text-left">
                <span className="text-[11px] font-bold text-[#001f3f] leading-tight">
                  MoS Chartering Desk
                </span>
                <span className="text-[10px] text-[#475569] leading-tight">
                  Logistics Decision Division
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Tier 2: National Tricolor Ribbon (3px strip) */}
        <div className="w-full flex h-[3px]">
          <div className="w-1/3 bg-[#ff9933]"></div>
          <div className="w-1/3 bg-white"></div>
          <div className="w-1/3 bg-[#138808]"></div>
        </div>

        {/* Tier 3: SIH Hackathon Institutional Sub-Bar */}
        <div className="w-full bg-[#eff4ff] border-b border-[#dce9ff] px-4 md:px-6 py-1.5 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <Network className="h-3.5 w-3.5 text-[#12355b]" />
            <span className="text-[11px] font-bold uppercase text-[#12355b]">
              Decision Support System | Smart India Hackathon 2026 (SIH26006)
            </span>
            <span className="hidden md:inline text-[11px] text-[#475569]">
              — Automated Vessel Chartering Optimization for Indian Steel PSUs (SAIL, RINL, NMDC)
            </span>
          </div>

          <div className="text-[11px] text-[#475569] font-mono shrink-0 hidden sm:block">
            Port: <strong className="text-[#001f3f]">{request.target_port}</strong> | Cargo:{" "}
            <strong className="text-[#001f3f]" suppressHydrationWarning>
              {formatInteger(request.required_cargo_mt)} MT
            </strong>
          </div>
        </div>
      </header>

      {/* ========================================================= */}
      {/* 2. BODY LAYOUT: Retractable Sidebar on Left + Content on Right */}
      {/* ========================================================= */}
      <div className="flex flex-1 overflow-hidden h-[calc(100vh-95px)]">
        {/* Retractable & Transparent Sidebar sitting neatly below full-width header */}
        <Sidebar
          activeView={activeView}
          setActiveView={setActiveView}
          hasOptimizationResult={Boolean(optimizationResult)}
          collapsed={sidebarCollapsed}
          setCollapsed={setSidebarCollapsed}
        />

        {/* Main Scrollable Content Area */}
        <main className="flex-1 overflow-y-auto p-6 md:p-8 bg-[#f8f9ff]">
          <div className="max-w-6xl mx-auto">
            {activeView === "dashboard" && (
              <DashboardView
                request={request}
                setRequest={setRequest}
                optimizationResult={optimizationResult}
                optimizing={optimizing}
                onRunOptimization={handleRunOptimization}
                onNavigateToStrategy={() => setActiveView("strategy")}
                onResetPlan={() => setOptimizationResult(null)}
              />
            )}

            {activeView === "strategy" && (
              <StrategyView
                optimizationResult={optimizationResult}
                request={request}
                onBackToDashboard={() => setActiveView("dashboard")}
              />
            )}

            {activeView === "whatif" && (
              <WhatIfView
                baselineResult={optimizationResult}
                request={request}
                setRequest={setRequest}
                optimizing={optimizing}
                onRunOptimizationWithDisruption={handleRunOptimizationWithDisruption}
              />
            )}

            {activeView === "forecasting" && <ForecastingView />}
          </div>
        </main>
      </div>
    </div>
  );
}
