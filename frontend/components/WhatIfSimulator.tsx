"use client";

import React, { useState, useEffect } from "react";
import {
  ShieldAlert,
  RotateCcw,
  Zap,
  ChevronRight,
  TrendingUp,
  AlertTriangle,
  Flame,
  Waves,
  Anchor,
  Wind,
} from "lucide-react";
import {
  fetchDisruptions,
  DisruptionEvent,
  OptimizationRequest,
} from "@/lib/api";

interface WhatIfSimulatorProps {
  onApplyDisruption: (disruption: {
    eventType: string;
    eventName: string;
    multiplier: number;
    params?: Partial<OptimizationRequest>;
  }) => void;
  onResetDisruption: () => void;
  activeDisruptionName: string | null;
  loading: boolean;
}

const FALLBACK_DISRUPTIONS: DisruptionEvent[] = [
  {
    event_id: 1,
    date: "2024-04-14",
    event_type: "IRAN_US_STRAIT_HORMUZ",
    event_name: "Strait of Hormuz Conflict Risk",
    category: "Geopolitical",
    affected_region: "Persian Gulf / Strait of Hormuz",
    bdi_impact_pct: 28.0,
    freight_shock_multiplier: 1.28,
    description:
      "Escalation in the Strait of Hormuz triggering war-risk insurance spikes (+400%), marine fuel surges, and severe bulk carrier detours.",
  },
  {
    event_id: 2,
    date: "2023-12-18",
    event_type: "RED_SEA_HOUTHI",
    event_name: "Red Sea & Bab el-Mandeb Strikes",
    category: "Geopolitical",
    affected_region: "Red Sea / Cape of Good Hope",
    bdi_impact_pct: 22.0,
    freight_shock_multiplier: 1.22,
    description:
      "Vessel diversions around the Cape of Good Hope adding 12-15 voyage days, inflating bunker consumption and tightening Panamax availability.",
  },
  {
    event_id: 3,
    date: "2023-05-14",
    event_type: "CYCLONE_MOCHA_BAY_BENGAL",
    event_name: "Bay of Bengal Super Cyclone Alert",
    category: "Weather Shock",
    affected_region: "East Coast India (Paradip/Vizag)",
    bdi_impact_pct: 18.0,
    freight_shock_multiplier: 1.18,
    description:
      "Port shutdown at Paradip and Dhamra due to gale-force winds (>65 knots), increasing anchorage waiting queues from 1.8 to 6.5 days.",
  },
  {
    event_id: 4,
    date: "2023-09-08",
    event_type: "AUSTRALIA_LNG_STRIKE",
    event_name: "Australian Port & Berth Strike Action",
    category: "Labor Unrest",
    affected_region: "Newcastle / Gladstone (AUS)",
    bdi_impact_pct: 15.0,
    freight_shock_multiplier: 1.15,
    description:
      "Terminal tugboat and stevedore stoppages in Newcastle delaying coal parcel loading and triggering demurrage clauses ($25,000/day).",
  },
];

export default function WhatIfSimulator({
  onApplyDisruption,
  onResetDisruption,
  activeDisruptionName,
  loading,
}: WhatIfSimulatorProps) {
  const [disruptions, setDisruptions] = useState<DisruptionEvent[]>(FALLBACK_DISRUPTIONS);
  const [customMultiplier, setCustomMultiplier] = useState<number>(1.0);
  const [selectedDisruption, setSelectedDisruption] = useState<DisruptionEvent | null>(null);

  useEffect(() => {
    fetchDisruptions()
      .then((data) => {
        if (data && data.length > 0) setDisruptions(data);
      })
      .catch((err) => {
        console.warn("Using fallback disruption models:", err);
      });
  }, []);

  const handleSelectEvent = (event: DisruptionEvent) => {
    setSelectedDisruption(event);
    setCustomMultiplier(event.freight_shock_multiplier);
    onApplyDisruption({
      eventType: event.event_type,
      eventName: event.event_name,
      multiplier: event.freight_shock_multiplier,
    });
  };

  const handleCustomSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    setCustomMultiplier(val);
    onApplyDisruption({
      eventType: "CUSTOM_SHOCK",
      eventName: `Custom Freight Shock (${((val - 1.0) * 100).toFixed(0)}% Surcharge)`,
      multiplier: val,
    });
  };

  const handleReset = () => {
    setSelectedDisruption(null);
    setCustomMultiplier(1.0);
    onResetDisruption();
  };

  return (
    <div className="w-full bg-white p-6 rounded border border-[#cbd5e1] shadow-sm mb-6 scroll-mt-28" id="what-if-section">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 mb-5 border-b border-[#e2e8f0]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded bg-[#12355b] text-white flex items-center justify-center shrink-0">
            <span className="material-symbols-outlined text-[22px]">crisis_alert</span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-serif-gov text-lg font-bold text-[#001f3f]">
                What-If Maritime Disruption & Stress-Testing Simulator
              </h3>
              <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-[#fff9c4] text-[#b45309] border border-[#fef08a]">
                Operational Stress Engine
              </span>
            </div>
            <p className="text-xs text-[#475569] mt-0.5">
              Simulate geopolitical route closures, weather delays, and fuel price shocks to evaluate supply chain resilience
            </p>
          </div>
        </div>

        {activeDisruptionName && (
          <button
            onClick={handleReset}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#f1f5f9] hover:bg-[#e2e8f0] text-[#12355b] text-xs font-semibold border border-[#cbd5e1] transition-colors"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            <span>Reset to Baseline (1.0x)</span>
          </button>
        )}
      </div>

      {/* Disruption Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 mb-5">
        {disruptions.slice(0, 4).map((d) => {
          const isActive = activeDisruptionName === d.event_name;
          const spikePct = Math.round((d.freight_shock_multiplier - 1.0) * 100);

          return (
            <div
              key={d.event_id}
              onClick={() => handleSelectEvent(d)}
              className={`p-4 rounded border transition-all cursor-pointer flex flex-col justify-between ${
                isActive
                  ? "bg-[#eff4ff] border-[#12355b] ring-2 ring-[#12355b]/20 shadow-sm"
                  : "bg-[#f8f9ff] border-[#e2e8f0] hover:border-[#94a3b8] hover:bg-white"
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-white text-[#475569] border border-[#cbd5e1]">
                    {d.category || "Disruption"}
                  </span>
                  <span className="font-mono text-xs font-bold text-[#b45309] bg-[#fff9c4] px-2 py-0.5 rounded">
                    +{spikePct}% Freight
                  </span>
                </div>
                <h4 className="text-xs font-bold text-[#001f3f] leading-snug mb-1">
                  {d.event_name}
                </h4>
                <p className="text-[11px] text-[#475569] line-clamp-2 leading-relaxed">
                  {d.description}
                </p>
              </div>

              <div className="mt-3 pt-2.5 border-t border-[#e2e8f0] flex items-center justify-between">
                <span className="text-[11px] text-[#64748b]">Multiplier:</span>
                <span className="font-mono text-xs font-bold text-[#12355b]">
                  {d.freight_shock_multiplier.toFixed(2)}x
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Interactive Manual Shock Slider */}
      <div className="bg-[#f8f9ff] p-4 rounded border border-[#e2e8f0] flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center justify-between text-xs font-semibold text-[#001f3f] mb-1.5">
            <span className="flex items-center gap-1.5">
              <Zap className="h-4 w-4 text-[#e65100]" />
              Manual Freight Rate Inflation Multiplier:
            </span>
            <span className="font-mono text-sm font-bold text-[#12355b]">
              {customMultiplier.toFixed(2)}x (+{((customMultiplier - 1.0) * 100).toFixed(0)}% Surcharge)
            </span>
          </div>
          <input
            type="range"
            min="1.0"
            max="1.7"
            step="0.02"
            value={customMultiplier}
            onChange={handleCustomSliderChange}
            disabled={loading}
            className="w-full h-2 bg-[#cbd5e1] rounded-lg appearance-none cursor-pointer accent-[#12355b]"
          />
          <div className="flex justify-between text-[10px] text-[#64748b] font-mono mt-1">
            <span>1.0x (Calm Market)</span>
            <span>1.25x (Regional Crisis)</span>
            <span>1.5x (Major Canal Closure)</span>
            <span>1.7x (War Surcharge)</span>
          </div>
        </div>

        <div className="shrink-0 flex items-center gap-2 bg-white px-3 py-2 rounded border border-[#cbd5e1] text-xs font-mono text-[#001f3f]">
          <span className="w-2 h-2 rounded-full bg-[#15803d]"></span>
          <span>Active Stress: <strong>{((customMultiplier - 1.0) * 100).toFixed(0)}% Delta</strong></span>
        </div>
      </div>
    </div>
  );
}
