"use client";

import React from "react";
import { clsx } from "clsx";

type SubheadingProps = {
  children: React.ReactNode;
  className?: string;
};

/**
 * Subheading - Componente de subtítulo padronizado DIPAM
 */
export function Subheading({
  children,
  className = "",
}: SubheadingProps) {
  return (
    <p className={clsx("text-sm text-white/60 uppercase tracking-wide font-medium", className)}>
      {children}
    </p>
  );
}

