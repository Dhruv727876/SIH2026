"use client";

import React from "react";
import { cn } from "@/lib/utils";

export interface DotBorderWrapperProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  theme?: "blue" | "amber" | "emerald" | "default";
  active?: boolean;
  className?: string;
  wrapperClassName?: string;
}

export function DotBorderWrapper({
  children,
  theme = "blue",
  active = false,
  className,
  wrapperClassName,
  ...props
}: DotBorderWrapperProps) {
  // Theme color variables matching the high-tech institutional command center
  const themeStyles = {
    blue: {
      "--dot-color": "#38bdf8",
      "--line-color": "#38bdf8aa",
      "--grid-color": "#38bdf825",
    },
    amber: {
      "--dot-color": "#f59e0b",
      "--line-color": "#f59e0baa",
      "--grid-color": "#f59e0b25",
    },
    emerald: {
      "--dot-color": "#34d399",
      "--line-color": "#34d399aa",
      "--grid-color": "#34d39925",
    },
    default: {
      "--dot-color": "#ffffff",
      "--line-color": "#ffffff88",
      "--grid-color": "#ffffff20",
    },
  }[theme];

  return (
    <div
      className={cn(
        "dot-border-container relative inline-flex w-full group/neu p-[5px] transition-all",
        active && "is-active",
        wrapperClassName
      )}
      style={themeStyles as React.CSSProperties}
      {...props}
    >
      {/* Repeating Diagonal Tech Grid Overlay on Hover */}
      <div className="pointer-events-none absolute inset-0 rounded-lg opacity-0 transition-opacity duration-300 group-hover/neu:opacity-100 [background-image:repeating-linear-gradient(45deg,var(--grid-color)_0_1px,transparent_2px_6px)]" />

      {/* Outer Laser Corner Dots */}
      <span className="dot-corner pointer-events-none absolute -top-1 -left-1 h-1.5 w-1.5 rounded-[1px] bg-[var(--dot-color)] opacity-0 shadow-[0_0_8px_var(--dot-color)] transition-all duration-300 ease-out group-hover/neu:opacity-100 group-hover/neu:-top-1 group-hover/neu:-left-1" />
      <span className="dot-corner pointer-events-none absolute -top-1 -right-1 h-1.5 w-1.5 rounded-[1px] bg-[var(--dot-color)] opacity-0 shadow-[0_0_8px_var(--dot-color)] transition-all duration-300 ease-out group-hover/neu:opacity-100 group-hover/neu:-top-1 group-hover/neu:-right-1" />
      <span className="dot-corner pointer-events-none absolute -bottom-1 -right-1 h-1.5 w-1.5 rounded-[1px] bg-[var(--dot-color)] opacity-0 shadow-[0_0_8px_var(--dot-color)] transition-all duration-300 ease-out group-hover/neu:opacity-100 group-hover/neu:-bottom-1 group-hover/neu:-right-1" />
      <span className="dot-corner pointer-events-none absolute -bottom-1 -left-1 h-1.5 w-1.5 rounded-[1px] bg-[var(--dot-color)] opacity-0 shadow-[0_0_8px_var(--dot-color)] transition-all duration-300 ease-out group-hover/neu:opacity-100 group-hover/neu:-bottom-1 group-hover/neu:-left-1" />

      {/* Animated Crosshair Dash Lines */}
      <span className="pointer-events-none absolute top-0 left-0 h-[1px] w-full origin-left scale-x-0 transition-transform duration-300 ease-out group-hover/neu:scale-x-100 [background-image:repeating-linear-gradient(90deg,transparent_0_2px,var(--line-color)_2px_6px)]" />
      <span className="pointer-events-none absolute top-0 right-0 h-full w-[1px] origin-top scale-y-0 transition-transform duration-300 ease-out group-hover/neu:scale-y-100 [background-image:repeating-linear-gradient(0deg,transparent_0_2px,var(--line-color)_2px_6px)]" />
      <span className="pointer-events-none absolute bottom-0 right-0 h-[1px] w-full origin-right scale-x-0 transition-transform duration-300 ease-out group-hover/neu:scale-x-100 [background-image:repeating-linear-gradient(90deg,transparent_0_2px,var(--line-color)_2px_6px)]" />
      <span className="pointer-events-none absolute bottom-0 left-0 h-full w-[1px] origin-bottom scale-y-0 transition-transform duration-300 ease-out group-hover/neu:scale-y-100 [background-image:repeating-linear-gradient(0deg,transparent_0_2px,var(--line-color)_2px_6px)]" />

      {/* Button Content */}
      <div className={cn("relative z-10 w-full", className)}>
        {children}
      </div>
    </div>
  );
}

export default DotBorderWrapper;
