"use client";

import React from "react";

/**
 * DashboardSkeleton - Skeleton para o dashboard completo
 * 
 * Shimmer effect, animação leve, sem flicker, placeholders responsivos
 */
export function DashboardSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      {/* Big Number Skeleton */}
      <div className="bg-[#0F172A] border border-white/10 rounded-xl p-6">
        <div className="h-4 w-32 bg-white/10 rounded mb-4"></div>
        <div className="h-12 w-48 bg-white/10 rounded"></div>
      </div>

      {/* Resumo Executivo Skeleton */}
      <div className="bg-[#0F172A] border border-white/5 rounded-xl p-5">
        <div className="h-6 w-40 bg-white/10 rounded mb-4"></div>
        <div className="space-y-2">
          <div className="h-4 w-full bg-white/10 rounded"></div>
          <div className="h-4 w-full bg-white/10 rounded"></div>
          <div className="h-4 w-3/4 bg-white/10 rounded"></div>
        </div>
      </div>

      {/* Tabela Skeleton */}
      <div className="bg-[#0F172A] border border-white/5 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-white/5">
          <div className="h-6 w-48 bg-white/10 rounded"></div>
        </div>
        <div className="p-6 space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="flex gap-4">
              <div className="h-4 flex-1 bg-white/10 rounded"></div>
              <div className="h-4 w-24 bg-white/10 rounded"></div>
              <div className="h-4 w-32 bg-white/10 rounded"></div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

