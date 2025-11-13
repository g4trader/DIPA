"use client";

import React, { useMemo } from "react";
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

const legendFormatter = (value: string) => `→ ${value}`;

type DipaChartProps = {
  chart?: ChartConfig;
  emptyMessage?: string;
  refreshKey?: number;
};

export function DipaChart({ chart, emptyMessage = "Sem dados suficientes para exibir o gráfico.", refreshKey = 0 }: DipaChartProps) {
  const chartData = chart?.data ?? [];
  const containerKey = useMemo(() => {
    if (!chartData.length) return "empty";
    return chartData
      .map((entry) =>
        Object.keys(entry)
          .sort()
          .map((key) => `${key}:${entry[key as keyof typeof entry]}`)
          .join("|")
      )
      .join(";");
  }, [chartData]);

  if (!chartData.length) {
    return (
      <div className="flex h-40 items-center justify-center rounded-xl border border-slate-800 bg-slate-900/40 text-xs text-slate-500">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-slate-700 bg-slate-900/60 p-4 shadow-inner shadow-blue-900/20">
      <div className="h-56 w-full overflow-hidden rounded-xl border border-slate-800/60 bg-slate-950/50">
        <ResponsiveContainer key={`${refreshKey}-${containerKey}`} width="99%" height="100%">
          {chart?.type === "area" ? <AreaVisualization chart={chart} /> : <BarVisualization chart={chart!} />}
        </ResponsiveContainer>
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
      <Legend formatter={legendFormatter} wrapperStyle={{ paddingTop: 8 }} />
      {chart.series.map((serie) => (
        <Area
          key={serie.key}
          type="monotone"
          dataKey={serie.key}
          stroke={serie.color ?? "#3B82F6"}
          strokeWidth={2.5}
          fill={serie.color ?? "#3B82F6"}
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
      <Legend formatter={legendFormatter} wrapperStyle={{ paddingTop: 8 }} />
      {chart.series.map((serie) => (
        <Bar key={serie.key} dataKey={serie.key} fill={serie.color ?? "#3B82F6"} radius={[12, 12, 0, 0]} />
      ))}
    </BarChart>
  );
}

