"use client";

import React from "react";
import { clsx } from "clsx";
import type { QueryResult } from "./types";

type RegionTableProps = {
  result?: QueryResult;
  showHeader?: boolean;
};

const TROPHY = "🥇";

export function RegionTable({ result, showHeader = true }: RegionTableProps) {
  if (!result || !result.table.length) return null;

  const numericColumnStart = Math.max(result.table[0].columns.length - 2, 1);

  return (
    <div className="space-y-3">
      {showHeader ? <p className="text-sm font-semibold text-slate-300">Ranking de vendedores</p> : null}
      <div className="overflow-hidden rounded-2xl border border-slate-700 bg-slate-900/60 shadow-inner shadow-blue-900/20">
        <div className="max-h-80 overflow-auto">
          <table className="min-w-full border-collapse text-sm text-slate-300">
            <thead className="sticky top-0 z-10 bg-slate-900/95 backdrop-blur">
              <tr className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                {result.table[0].columns.map((column, idx) => (
                  <th
                    key={column}
                    className={clsx("px-5 py-3 text-left text-slate-400/80", idx >= numericColumnStart && "text-right")}
                  >
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {result.table.map((row, rowIndex) => (
                <tr
                  key={`${rowIndex}-${row.rows[0]}`}
                  className="border-b border-slate-800/60 odd:bg-slate-900/40 even:bg-slate-900/20 transition hover:bg-slate-800/40"
                >
                  {row.rows.map((value, cellIndex) => (
                    <td
                      key={`${rowIndex}-${cellIndex}`}
                      className={clsx(
                        "px-5 py-3 text-sm font-medium text-slate-200/90",
                        cellIndex >= numericColumnStart ? "text-right text-slate-50" : "text-left"
                      )}
                    >
                      {cellIndex === 1 && rowIndex === 0 ? (
                        <span className="inline-flex items-center gap-2">
                          <span>{TROPHY}</span>
                          <span>{value}</span>
                        </span>
                      ) : (
                        value
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

