
"use client";
import * as React from "react";
export function Select({ value, onValueChange, children }: any){ return <div>{children}</div>; }
export function SelectTrigger({ className, children }: any){ return <div className={className+" h-10 rounded-xl border border-slate-300 bg-white px-3 text-sm flex items-center"}>{children}</div>; }
export function SelectContent({ children }: any){ return <div className="hidden">{children}</div>; }
export function SelectItem({ value, children }: any){ return <div data-value={value} className="hidden">{children}</div>; }
export function SelectValue({ placeholder }: any){ return <span className="text-slate-600">{placeholder}</span>; }
