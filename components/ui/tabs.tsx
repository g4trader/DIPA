
"use client";
import * as React from "react";
import { clsx } from "clsx";

export function Tabs({ defaultValue, children }: { defaultValue: string; children: React.ReactNode }) {
  return <div data-default={defaultValue}>{children}</div>;
}

export function TabsList({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={clsx("flex gap-2 rounded-xl border border-slate-700 bg-slate-800/70 p-1", className)}>{children}</div>
  );
}

export function TabsTrigger({ value, children, className, ...props }: any) {
  return (
    <button
      data-value={value}
      className={clsx(
        "rounded-lg px-3 py-1 text-sm text-slate-300 transition hover:bg-slate-700 data-[state=active]:bg-blue-600 data-[state=active]:text-white",
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}

export function TabsContent({ value, children, className }: any) {
  return (
    <div data-value={value} className={className}>
      {children}
    </div>
  );
}
