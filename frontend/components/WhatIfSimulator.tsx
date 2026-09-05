"use client";

import React, { useState, useEffect } from "react";
import {
  Cpu,
  RotateCcw,
  ChevronLeft,
  ChevronRight,
  ShieldAlert,
  CloudRain,
  Biohazard,
  Anchor,
  Zap,
} from "lucide-react";
import {
  fetchDisruptions,
  getDisruptionMultiplier,
  DisruptionEvent,
  OptimizationRequest,
} from "@/lib/api";
import FocusSliceCarousel, {
  FocusSliceItem,
} from "@/components/ui/focus-slice-carousel";

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
    event_name: "Iran-US Conflict & Strait of Hormuz Risk",
    category: "Geopolitical & Conflict",
    affected_region: "Persian Gulf / Strait of Hormuz",
    bdi_impact_pct: 28.0,
    freight_shock_multiplier: 1.28,
    description:
      "Drone/missile escalation and tanker interception threats in the Strait of Hormuz triggering war-risk insurance spikes (+400%), marine fuel surges, and vessel detours.",
  },
  {
    event_id: 2,
    date: "2022-02-24",
    event_type: "RUSSIA_UKRAINE_WAR",
    event_name: "Russia-Ukraine War & Black Sea Blockade",
    category: "Geopolitical & Conflict",
    affected_region: "Black Sea / Europe",
    bdi_impact_pct: 24.0,
    freight_shock_multiplier: 1.24,
    description:
      "War risk zones in the Black Sea and sanctions on Russian coal force Indian steel mills to source metallurgical coal from distant Australian and North American ports (+30% ton-miles).",
  },
  {
    event_id: 3,
    date: "2023-12-18",
    event_type: "RED_SEA_HOUTHI",
    event_name: "Red Sea & Bab el-Mandeb Houthi Strikes",
    category: "Geopolitical & Conflict",
    affected_region: "Red Sea / Cape of Good Hope",
    bdi_impact_pct: 22.0,
    freight_shock_multiplier: 1.22,
    description:
      "Vessel attacks forcing bulkers around the Cape of Good Hope, adding 10-15 voyage days, increasing bunker consumption, and tightening fleet availability.",
  },
  {
    event_id: 4,
    date: "2020-03-11",
    event_type: "COVID_PANDEMIC",
    event_name: "COVID-19 Port Quarantine & Crew Crisis",
    category: "Pandemic & Health",
    affected_region: "Global Major Hubs (China/India)",
    bdi_impact_pct: 35.0,
    freight_shock_multiplier: 1.35,
    description:
      "14-day mandatory vessel quarantine protocols, severe dock labor shortages, and post-lockdown commodity demand surges creating historic freight peaks.",
  },
  {
    event_id: 5,
    date: "2021-03-23",
    event_type: "SUEZ_BLOCKAGE",
    event_name: "Ever Given Suez Canal 6-Day Blockage",
    category: "Maritime Chokepoint",
    affected_region: "Suez Canal / Mediterranean",
    bdi_impact_pct: 20.0,
    freight_shock_multiplier: 1.20,
    description:
      "Canal obstruction stranding 360+ bulkers and container vessels, causing acute cascading port queue delays and regional bulk charter rate spikes.",
  },
  {
    event_id: 6,
    date: "2023-12-04",
    event_type: "CYCLONE_MICHAUNG",
    event_name: "Cyclone Michaung & Bay of Bengal Swells",
    category: "Climate & Natural",
    affected_region: "Indian East Coast (Paradip/Vizag)",
    bdi_impact_pct: 16.0,
    freight_shock_multiplier: 1.16,
    description:
      "Torrential cyclonic storms and heavy swell surges halting berth discharge operations, spiking vessel anchorage waiting queues to 96+ hours and escalating demurrage penalties.",
  },
  {
    event_id: 7,
    date: "2023-11-01",
    event_type: "PANAMA_DROUGHT",
    event_name: "Panama Canal Transit Drought Limits",
    category: "Climate & Natural",
    affected_region: "Panama / Transpacific",
    bdi_impact_pct: 15.0,
    freight_shock_multiplier: 1.15,
    description:
      "Severe Gatun Lake drought reducing daily vessel transit reservations from 36 to 22 ships, forcing dry bulk carriers onto long-haul diversion routes around South America.",
  },
  {
    event_id: 8,
    date: "2024-08-15",
    event_type: "HALDIA_SILTATION",
    event_name: "Haldia Riverine Draft Siltation Crisis",
    category: "Port Constraint",
    affected_region: "Hooghly River / Haldia Port",
    bdi_impact_pct: 25.0,
    freight_shock_multiplier: 1.25,
    description:
      "Monsoon siltation dropping allowable river draft below 11.5m, disqualifying standard Panamax ships and demanding costly transshipment/lighterage.",
  },
];

const CATEGORIES = [
  { id: "ALL", label: "All Scenarios" },
  { id: "Geopolitical & Conflict", label: "⚔️ Geopolitical" },
  { id: "Climate & Natural", label: "🌪️ Natural Disasters" },
  { id: "Pandemic & Health", label: "🦠 Pandemics" },
  { id: "Port Constraint", label: "⚓ Ports & Chokepoints" },
];

function getDisruptionImage(eventType?: string): string {
  switch (eventType) {
    case "IRAN_US_STRAIT_HORMUZ":
      return "https://images.unsplash.com/photo-1559136555-9303baea8ebd?w=1200&auto=format&fit=crop&q=80";
    case "RUSSIA_UKRAINE_WAR":
      return "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=1200&auto=format&fit=crop&q=80";
    case "RED_SEA_HOUTHI":
      return "https://images.unsplash.com/photo-1494412574643-ff11b0a5c1c3?w=1200&auto=format&fit=crop&q=80";
    case "COVID_PANDEMIC":
      return "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?w=1200&auto=format&fit=crop&q=80";
    case "SUEZ_BLOCKAGE":
      return "https://images.unsplash.com/photo-1518241353330-0f7941c2d9b5?w=1200&auto=format&fit=crop&q=80";
    case "CYCLONE_MICHAUNG":
      return "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1200&auto=format&fit=crop&q=80";
    case "PANAMA_DROUGHT":
      return "https://images.unsplash.com/photo-1578575437130-527eed3abbec?w=1200&auto=format&fit=crop&q=80";
    case "HALDIA_SILTATION":
      return "https://images.unsplash.com/photo-1574680096145-d05b474e2155?w=1200&auto=format&fit=crop&q=80";
    default:
      return "https://images.unsplash.com/photo-1518241353330-0f7941c2d9b5?w=1200&auto=format&fit=crop&q=80";
  }
}

function getDisruptionTint(category?: string): string {
  switch (category) {
    case "Geopolitical & Conflict":
      return "#381824";
    case "Climate & Natural":
      return "#1e2e1e";
    case "Pandemic & Health":
      return "#281b36";
    case "Port Constraint":
    case "Maritime Chokepoint":
      return "#152533";
    default:
      return "#121b2b";
  }
}

export default function WhatIfSimulator({
  onApplyDisruption,
  onResetDisruption,
  activeDisruptionName,
  loading,
}: WhatIfSimulatorProps) {
  const [disruptions, setDisruptions] =
    useState<DisruptionEvent[]>(FALLBACK_DISRUPTIONS);
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");
  const [activeIndex, setActiveIndex] = useState<number>(0);

  useEffect(() => {
    const loadEvents = async () => {
      try {
        const data = await fetchDisruptions();
        if (data && data.length > 0) {
          setDisruptions(data);
        }
      } catch (err) {
        console.warn(
          "Could not fetch disruptions from API. Using local historical records."
        );
      }
    };
    loadEvents();
  }, []);

  const handleCardClick = async (event: DisruptionEvent) => {
    if (activeDisruptionName === event.event_name) {
      onResetDisruption();
      return;
    }

    try {
      const multRes = await getDisruptionMultiplier(
        event.event_type || event.event_name
      );
      const multiplier =
        multRes.freight_shock_multiplier ||
        event.freight_shock_multiplier ||
        1.2;

      onApplyDisruption({
        eventType: event.event_type,
        eventName: event.event_name,
        multiplier: multiplier,
      });
    } catch (err) {
      const multiplier = event.freight_shock_multiplier || 1.2;
      onApplyDisruption({
        eventType: event.event_type,
        eventName: event.event_name,
        multiplier: multiplier,
      });
    }
  };

  const filteredDisruptions = disruptions.filter((d) => {
    if (selectedCategory === "ALL") return true;
    if (selectedCategory === "Port Constraint") {
      return (
        d.category === "Port Constraint" || d.category === "Maritime Chokepoint"
      );
    }
    return d.category === selectedCategory;
  });

  // Limit display to maximum 6 scenarios per view for optimal slice width
  const visibleDisruptions =
    selectedCategory === "ALL"
      ? filteredDisruptions.slice(0, 6)
      : filteredDisruptions;

  const sliceItems: FocusSliceItem[] = visibleDisruptions.map((ev) => {
    const isActive = activeDisruptionName === ev.event_name;

    return {
      id: ev.event_id || ev.event_type,
      image: getDisruptionImage(ev.event_type),
      tint: getDisruptionTint(ev.category),
      kicker: `${ev.category.toUpperCase()} • ${ev.affected_region.toUpperCase()}`,
      title: ev.event_name,
      subtitle: ev.description,
      action: isActive
        ? "Active Shock (Click to Reset ↺)"
        : "Simulate Shock →",
      isActive: isActive,
      onAction: () => handleCardClick(ev),
    };
  });

  const handlePrev = () => {
    setActiveIndex((prev) =>
      prev <= 0 ? visibleDisruptions.length - 1 : prev - 1
    );
  };

  const handleNext = () => {
    setActiveIndex((prev) =>
      prev >= visibleDisruptions.length - 1 ? 0 : prev + 1
    );
  };

  return (
    <div className="rounded-xl border border-[#1c263c] bg-[#0b101c] p-4 shadow-lg space-y-3">
      {/* Top Controls Bar: Title + Category Tabs + Reset Button + Prev/Next Controls */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 pb-3 border-b border-[#1c263c]">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-[#141c2e] border border-[#1c263c] text-blue-400">
            <Cpu className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-bold text-slate-100 uppercase tracking-wider">
                What-If Maritime Disruption Simulator
              </h3>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#141c2e] text-amber-400 border border-[#1c263c]">
                {visibleDisruptions.length} Scenarios
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              Interactive focus slice carousel &bull; Click any slice to expand stress scenario
            </p>
          </div>
        </div>

        {/* Category Filter Tabs & Navigation */}
        <div className="flex items-center gap-2 overflow-x-auto no-scrollbar py-0.5">
          <div className="flex items-center gap-1 bg-[#080c14] p-1 rounded-lg border border-[#1c263c]">
            {CATEGORIES.map((cat) => {
              const isSelected = selectedCategory === cat.id;
              return (
                <button
                  key={cat.id}
                  type="button"
                  onClick={() => {
                    setSelectedCategory(cat.id);
                    setActiveIndex(0);
                  }}
                  className={`text-[11px] px-2.5 py-1 rounded-md transition font-medium whitespace-nowrap ${
                    isSelected
                      ? "bg-blue-600/30 text-blue-300 border border-blue-500/40 font-semibold shadow-sm"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {cat.label}
                </button>
              );
            })}
          </div>

          {activeDisruptionName && (
            <button
              type="button"
              onClick={() => onResetDisruption()}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 text-xs font-semibold border border-amber-500/40 transition shrink-0 shadow-sm"
              title="Reset to 1.0x Normal Scenario"
            >
              <RotateCcw className="h-3.5 w-3.5 text-amber-400" />
              <span>Reset</span>
            </button>
          )}

          {/* Carousel Prev/Next Buttons */}
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={handlePrev}
              className="p-1.5 rounded-lg bg-[#080c14] border border-[#1c263c] hover:border-slate-500 text-slate-300 hover:text-white transition shadow-sm"
              aria-label="Previous scenario"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              onClick={handleNext}
              className="p-1.5 rounded-lg bg-[#080c14] border border-[#1c263c] hover:border-slate-500 text-slate-300 hover:text-white transition shadow-sm"
              aria-label="Next scenario"
            >
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* FocusSliceCarousel Container */}
      <div className="w-full h-[430px]">
        <FocusSliceCarousel
          items={sliceItems}
          selectedIndex={activeIndex}
          onSelectIndex={setActiveIndex}
          canvas="#080c14"
          ink="#f8fafc"
          muted="#94a3b8"
          link="#3b82f6"
          padding={8}
          gap={10}
          radius={16}
          focusRatio={3.8}
          panelHeight={46}
          panelColor="#0a0f1c"
          panelOpacity={95}
          panelBlur={16}
        />
      </div>
    </div>
  );
}
