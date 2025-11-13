"use client";

import React from "react";
import { clsx } from "clsx";

type KpiStatsProps = {
  items: { label: string; value: string; helper?: string }[];
  className?: string;
};

export function KpiStats({ items, className }: KpiStatsProps) {
  if (!items.length) return null;

  return (
    <div className={clsx("grid gap-4 sm:grid-cols-3", className)}>
      {items.map((item) => (
        <PreviewKpiCard key={item.label} label={item.label} value={item.value} helper={item.helper} />
      ))}
    </div>
  );
}

export function PreviewKpiCard({ label, value, helper }: { label: string; value: string; helper?: string }) {
  return (
    <div className="flex flex-col justify-between rounded-xl border border-slate-700 bg-slate-900/60 px-4 py-3">
      <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400 overflow-hidden text-ellipsis">
        {label}
      </p>
      <p className="mt-2 text-2xl font-semibold text-slate-50 whitespace-nowrap">{value}</p>
      {helper ? <p className="mt-1 text-xs text-slate-500">{helper}</p> : null}
    </div>
  );
}

