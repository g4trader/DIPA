"use client";

import React from "react";
import { clsx } from "clsx";

type BadgeStatusProps = {
  status: "success" | "alert" | "warning" | "info";
  children: React.ReactNode;
  className?: string;
};

/**
 * BadgeStatus - Componente de badge de status padronizado DIPAM
 */
export function BadgeStatus({
  status,
  children,
  className = "",
}: BadgeStatusProps) {
  const statusClasses = {
    success: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    alert: "bg-red-500/10 text-red-400 border-red-500/20",
    warning: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
    info: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  };

  return (
    <span
      className={clsx(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border",
        statusClasses[status],
        className
      )}
    >
      {children}
    </span>
  );
}

