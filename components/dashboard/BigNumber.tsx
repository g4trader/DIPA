"use client";

import React from "react";
import { formatNumberBR } from "@/lib/formatters";

type BigNumberProps = {
  value: string | number;
  label: string;
  subtle?: string;
  className?: string;
  id?: string;
};

/**
 * BigNumber - Componente otimizado para exibir números grandes
 * 
 * Server Component quando possível, responsivo, com acessibilidade
 */
export function BigNumber({
  value,
  label,
  subtle,
  className = "",
  id,
}: BigNumberProps) {
  const formattedValue =
    typeof value === "number"
      ? formatNumberBR(value)
      : typeof value === "string"
      ? formatNumberBR(value)
      : formatNumberBR(0);

  return (
    <div
      id={id}
      className={`bg-[#0F172A] border border-white/10 rounded-xl p-6 shadow-lg ${className}`}
      role="status"
      aria-label={`${label}: ${formattedValue}${subtle ? `, ${subtle}` : ""}`}
    >
      <div className="flex flex-col gap-2">
        <p className="text-sm text-white/60 uppercase tracking-wide font-medium">
          {label}
        </p>
        <div className="flex items-baseline gap-2">
          <p className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight text-white">
            {formattedValue}
          </p>
          {subtle && (
            <span className="text-sm text-white/50 ml-2">{subtle}</span>
          )}
        </div>
      </div>
    </div>
  );
}

