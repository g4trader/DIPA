"use client";

import React from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip as RTooltip,
  XAxis,
  YAxis
} from "recharts";
import { ds } from "@/styles/ui";
import type { ChartConfig } from "./types";

type DipaChartProps = {
  chart?: ChartConfig;
  title: string;
};

export function DipaChart({ chart, title }: DipaChartProps) {
  if (!chart) return null;

  return (
    <div className="space-y-3">
      <p className="text-sm font-semibold text-slate-300">{title}</p>
      <div className="rounded-2xl border border-slate-700 bg-slate-900/60 p-6 shadow-inner shadow-blue-900/20 transition duration-200 ease-out hover:shadow-[0_0_12px_rgba(59,130,246,0.35)]">
        <div className="h-64 w-full overflow-hidden rounded-xl border border-slate-800/60 bg-slate-950/50">
          <ResponsiveContainer width="100%" height="100%">
            {chart.type === "area" ? <AreaVisualization chart={chart} /> : <BarVisualization chart={chart} />}
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

function AreaVisualization({ chart }: { chart: ChartConfig }) {
  return (
    <AreaChart data={chart.data} margin={{ top: 16, right: 24, left: 12, bottom: 8 }}>
      <CartesianGrid strokeDasharray="3 3" stroke={ds.chart.grid} />
      <XAxis dataKey={chart.xKey} tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: ds.chart.axis }} />
      <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: ds.chart.axis }} />
      <RTooltip contentStyle={{ background: ds.chart.tooltip, border: `1px solid ${ds.chart.tooltipBorder}`, borderRadius: 12 }} />
      <Legend />
      {chart.series.map((serie) => (
        <Area
          key={serie.key}
          type="monotone"
          dataKey={serie.key}
          stroke={serie.color}
          strokeWidth={3}
          fill={serie.color}
          fillOpacity={0.16}
          dot={{ r: 3 }}
          activeDot={{ r: 5 }}
        />
      ))}
    </AreaChart>
  );
}

function BarVisualization({ chart }: { chart: ChartConfig }) {
  return (
    <BarChart data={chart.data} margin={{ top: 16, right: 24, left: 12, bottom: 8 }}>
      <CartesianGrid strokeDasharray="3 3" stroke={ds.chart.grid} />
      <XAxis dataKey={chart.xKey} tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: ds.chart.axis }} />
      <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: ds.chart.axis }} />
      <RTooltip contentStyle={{ background: ds.chart.tooltip, border: `1px solid ${ds.chart.tooltipBorder}`, borderRadius: 12 }} />
      <Legend />
      {chart.series.map((serie) => (
        <Bar key={serie.key} dataKey={serie.key} fill={serie.color} radius={[14, 14, 0, 0]} />
      ))}
    </BarChart>
  );
}

