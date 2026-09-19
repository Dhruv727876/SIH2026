"use client";

import React from "react";
import {
  LayoutDashboard,
  Route,
  AlertTriangle,
  TrendingUp,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

export type ViewType = "dashboard" | "strategy" | "whatif" | "forecasting";

interface SidebarProps {
  activeView: ViewType;
  setActiveView: (view: ViewType) => void;
  hasOptimizationResult: boolean;
  collapsed: boolean;
  setCollapsed: (collapsed: boolean) => void;
}

export default function Sidebar({
  activeView,
  setActiveView,
  hasOptimizationResult,
  collapsed,
  setCollapsed,
}: SidebarProps) {
  const navItems = [
    {
      id: "dashboard" as ViewType,
      label: "Dashboard",
      icon: LayoutDashboard,
      disabled: false,
    },
    {
      id: "strategy" as ViewType,
      label: "Voyage Strategy",
      icon: Route,
      disabled: !hasOptimizationResult,
      badge: hasOptimizationResult ? "Ready" : undefined,
    },
    {
      id: "whatif" as ViewType,
      label: "What-If Simulator",
      icon: AlertTriangle,
      disabled: false,
    },
    {
      id: "forecasting" as ViewType,
      label: "Forward Forecasting",
      icon: TrendingUp,
      disabled: false,
    },
  ];

  return (
    <aside
      className={`h-full select-none transition-all duration-300 ease-in-out flex flex-col justify-between shrink-0 z-30 ${
        collapsed ? "w-14" : "w-60"
      } bg-[#f8fafc]/90 backdrop-blur-md border-r border-[#cbd5e1] text-[#0f2444] shadow-xs`}
    >
      {/* Top Header Section */}
      <div>
        <div
          className={`h-14 flex items-center ${
            collapsed ? "justify-center px-2" : "justify-between px-4"
          } border-b border-[#e2e8f0]`}
        >
          {!collapsed && (
            <div className="flex flex-col truncate">
              <h2 className="text-sm font-bold text-[#001f3f] tracking-tight truncate">
                Decision Support System
              </h2>
              <span className="text-[10px] text-[#64748b] truncate leading-tight">
                Ministry of Steel (SIH26006)
              </span>
            </div>
          )}

          <button
            type="button"
            onClick={() => setCollapsed(!collapsed)}
            className="p-1 rounded text-[#64748b] hover:text-[#001f3f] hover:bg-[#e2e8f0] transition cursor-pointer"
            title={collapsed ? "Expand Sidebar" : "Collapse Sidebar"}
            aria-label="Toggle Sidebar"
          >
            {collapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronLeft className="h-4 w-4" />
            )}
          </button>
        </div>

        {/* Navigation List - Exact Matching Style */}
        <nav className="py-2 space-y-0.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeView === item.id;
            const isDisabled = item.disabled;

            return (
              <button
                key={item.id}
                type="button"
                disabled={isDisabled}
                onClick={() => {
                  if (!isDisabled) setActiveView(item.id);
                }}
                title={collapsed ? item.label : undefined}
                className={`w-full flex items-center ${
                  collapsed ? "justify-center px-0 py-3" : "justify-between px-4 py-2.5"
                } text-xs transition-colors text-left relative ${
                  isActive
                    ? "bg-[#e8f0fe] text-[#0b57d0] font-semibold border-l-4 border-[#0b57d0]"
                    : isDisabled
                    ? "text-[#94a3b8] opacity-50 cursor-not-allowed border-l-4 border-transparent"
                    : "text-[#334155] hover:bg-[#f1f5f9] hover:text-[#001f3f] border-l-4 border-transparent cursor-pointer"
                }`}
              >
                <div className="flex items-center gap-3 truncate">
                  <Icon
                    className={`h-4 w-4 shrink-0 ${
                      isActive ? "text-[#0b57d0]" : isDisabled ? "text-[#94a3b8]" : "text-[#5f6368]"
                    }`}
                  />
                  {!collapsed && (
                    <span className="truncate text-[13px]">{item.label}</span>
                  )}
                </div>

                {!collapsed && item.badge && (
                  <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-emerald-100 text-emerald-800 border border-emerald-300 font-bold">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Bottom Subtle Status */}
      <div className="p-3 border-t border-[#e2e8f0]">
        {!collapsed && (
          <div className="text-[11px] text-[#64748b] leading-tight mb-2">
            <span className="font-semibold text-[#001f3f] block">SAIL • RINL Desk</span>
            <span className="text-[10px]">RoFR Indian Flag Priority</span>
          </div>
        )}

        {/* National Tricolor Indicator */}
        <div className="w-full flex h-[3px] rounded-full overflow-hidden opacity-90">
          <div className="w-1/3 bg-[#ff9933]"></div>
          <div className="w-1/3 bg-white"></div>
          <div className="w-1/3 bg-[#138808]"></div>
        </div>
      </div>
    </aside>
  );
}
