"use client";

import React from "react";
import { clsx } from "clsx";

type CardProps = {
  children: React.ReactNode;
  className?: string;
  padding?: "sm" | "md" | "lg";
};

/**
 * Card - Componente de card padronizado DIPAM
 */
export function Card({
  children,
  className = "",
  padding = "md",
}: CardProps) {
  const paddingClasses = {
    sm: "p-4",
    md: "p-6",
    lg: "p-8",
  };

  return (
    <div
      className={clsx(
        "bg-[#0F172A] border border-white/5 rounded-xl shadow-lg",
        paddingClasses[padding],
        className
      )}
    >
      {children}
    </div>
  );
}

