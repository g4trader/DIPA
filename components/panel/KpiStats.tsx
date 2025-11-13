"use client";

import React from "react";

type KpiStatsProps = {
  items: { label: string; value: string; helper?: string }[];
};

export function KpiStats({ items }: KpiStatsProps) {
  if (!items.length) return null;

  return (
    <div className="grid gap-4 sm:grid-cols-3">
      {items.map((item) => (
        <KpiCard key={item.label} label={item.label} value={item.value} helper={item.helper} />
      ))}
    </div>
  );
}

function KpiCard({ label, value, helper }: { label: string; value: string; helper?: string }) {
  return (
    <div className="relative overflow-hidden rounded-2xl border border-blue-500/30 bg-slate-900/80 p-6 shadow-inner shadow-blue-900/30 transition duration-200 ease-out hover:-translate-y-0.5 hover:shadow-[0_0_14px_rgba(59,130,246,0.45)]">
      <span className="pointer-events-none absolute inset-x-4 top-0 h-px bg-gradient-to-r from-transparent via-blue-500/60 to-transparent" />
      <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">{label}</p>
      <p className="mt-3 text-4xl font-semibold tracking-tight text-slate-50 md:text-5xl">{value}</p>
      {helper ? <p className="mt-2 text-xs text-slate-400/80">{helper}</p> : null}
    </div>
  );
}

