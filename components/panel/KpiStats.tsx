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
        <KpiCard key={item.label} label={item.label} value={item.value} helper={item.helper} />)
      )}
    </div>
  );
}

function KpiCard({ label, value, helper }: { label: string; value: string; helper?: string }) {
  return (
    <div className="rounded-2xl border border-slate-700/80 bg-slate-900/70 px-4 py-5 shadow-inner shadow-blue-900/30">
      <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-400">{label}</p>
      <p className="mt-3 text-2xl font-semibold text-slate-50">{value}</p>
      {helper ? <p className="mt-1 text-xs text-slate-500">{helper}</p> : null}
    </div>
  );
}

