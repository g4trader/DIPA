"use client";

import React from "react";

/**
 * BigNumberSkeleton - Skeleton para Big Number
 */
export function BigNumberSkeleton() {
  return (
    <div className="bg-[#0F172A] border border-white/10 rounded-xl p-6 animate-pulse">
      <div className="h-4 w-32 bg-white/10 rounded mb-4"></div>
      <div className="h-12 w-48 bg-white/10 rounded"></div>
    </div>
  );
}

