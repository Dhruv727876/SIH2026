"use client";

import React from "react";
import FreightForecastChart from "@/components/FreightForecastChart";

export default function ForecastingView() {
  return (
    <div className="space-y-4">
      {/* Title & Header in Natural Government Style */}
      <div>
        <h1 className="font-serif-gov text-3xl font-bold text-[#001f3f] tracking-tight">
          Forward Freight Rate Forecasting
        </h1>
        <p className="text-xs text-[#475569] mt-0.5">
          Multi-horizon predictive rate curves powered by hybrid LightGBM (15-day tactical) and Prophet (180-day macroeconomic) models
        </p>
      </div>

      {/* Authentic Freight Forecast Chart */}
      <FreightForecastChart />
    </div>
  );
}
