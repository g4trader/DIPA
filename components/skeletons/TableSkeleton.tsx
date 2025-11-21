"use client";

import React from "react";

/**
 * TableSkeleton - Skeleton específico para tabelas
 */
export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="bg-[#0F172A] border border-white/5 rounded-xl overflow-hidden">
      <div className="px-6 py-4 border-b border-white/5">
        <div className="h-6 w-48 bg-white/10 rounded animate-pulse"></div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-white/5">
            <tr>
              {[...Array(4)].map((_, i) => (
                <th key={i} className="px-4 py-3">
                  <div className="h-4 w-24 bg-white/10 rounded animate-pulse"></div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[...Array(rows)].map((_, i) => (
              <tr key={i} className="border-b border-white/5">
                {[...Array(4)].map((_, j) => (
                  <td key={j} className="px-4 py-3">
                    <div className="h-4 w-full bg-white/10 rounded animate-pulse"></div>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

