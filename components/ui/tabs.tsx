
"use client";
import * as React from "react";
export function Tabs({ defaultValue, children }: { defaultValue: string; children: React.ReactNode }) {
  return <div data-default={defaultValue}>{children}</div>;
}
export function TabsList({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={className + " bg-slate-100 rounded-lg p-1"}>{children}</div>;
}
export function TabsTrigger({ value, children, ...props }: any) {
  return <button data-value={value} className="px-3 py-1 text-sm rounded-lg hover:bg-white">{children}</button>;
}
export function TabsContent({ value, children, className }: any) {
  return <div data-value={value} className={className}>{children}</div>;
}
