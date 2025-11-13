
"use client";

import * as React from "react";
import { clsx } from "clsx";

export function Select({ children }: { children: React.ReactNode }) {
  return <div className="relative">{children}</div>;
}

export function SelectTrigger({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <div
      className={clsx(
        "flex h-10 items-center justify-between rounded-xl border border-slate-700 bg-slate-900 px-4 text-sm text-slate-100 focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-500/40",
        className
      )}
    >
      {children}
    </div>
  );
}

export function SelectContent({ children }: { children: React.ReactNode }) {
  return <div className="hidden">{children}</div>;
}

export function SelectItem({ value, children }: { value: string; children: React.ReactNode }) {
  return (
    <div data-value={value} className="hidden">
      {children}
    </div>
  );
}

export function SelectValue({ placeholder }: { placeholder: string }) {
  return <span className="text-slate-400">{placeholder}</span>;
}
