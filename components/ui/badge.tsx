import * as React from "react";

export function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-full bg-slate-700 px-3 py-1 text-xs font-medium text-slate-200 shadow-sm shadow-slate-900/40">
      {children}
    </span>
  );
}
