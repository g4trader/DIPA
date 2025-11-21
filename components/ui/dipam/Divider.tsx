"use client";

import React from "react";
import { clsx } from "clsx";

type DividerProps = {
  className?: string;
  orientation?: "horizontal" | "vertical";
};

/**
 * Divider - Componente de divisor leve padronizado DIPAM
 */
export function Divider({
  className = "",
  orientation = "horizontal",
}: DividerProps) {
  if (orientation === "vertical") {
    return (
      <div
        className={clsx("w-px bg-white/5", className)}
        role="separator"
        aria-orientation="vertical"
      />
    );
  }

  return (
    <div
      className={clsx("h-px bg-white/5", className)}
      role="separator"
      aria-orientation="horizontal"
    />
  );
}

