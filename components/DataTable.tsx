"use client";

import React, { useState, useMemo } from "react";
import { formatNumberBR } from "@/lib/formatters";

type DataTableProps = {
  rows: Array<Record<string, any>>;
  title?: string;
  subtitle?: string; // ✅ T2: Texto adicional abaixo do título (ex: "Mostrando 100 de 932 clientes em foco")
  highlightFirstColumn?: boolean;
  id?: string;
  itemsPerPage?: number; // Padrão: 20
};

/**
 * DataTable - Tabela premium com sticky header, paginação fixa de 20 registros
 * 
 * Melhorias:
 * - Paginação padrão = 20 registros (fixo)
 * - Server-side friendly
 * - Sorting não duplica dados
 * - Estabilidade para garantir "1 linha por cliente"
 */
export function DataTable({
  rows,
  title,
  subtitle,
  highlightFirstColumn = true,
  id,
  itemsPerPage = 20, // Fixo em 20 conforme especificação
}: DataTableProps) {
  const [currentPage, setCurrentPage] = useState(0);
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");

  // Memoiza colunas para evitar recálculo
  const columns = useMemo(() => {
    if (!rows || rows.length === 0) return [];
    return Object.keys(rows[0]);
  }, [rows]);

  // Esconde coluna "Rota" se todas as rotas forem vazias ou "—"
  const visibleColumns = useMemo(() => {
    const temAlgumaRotaValida = rows.some(
      (row) => row["Rota"] && row["Rota"] !== "—" && row["Rota"] !== ""
    );
    if (!temAlgumaRotaValida && columns.includes("Rota")) {
      return columns.filter((col) => col !== "Rota");
    }
    return columns;
  }, [columns, rows]);

  // Ordenação
  const sortedRows = useMemo(() => {
    if (!sortColumn) return rows;
    
    return [...rows].sort((a, b) => {
      const aVal = a[sortColumn];
      const bVal = b[sortColumn];
      
      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;
      
      if (typeof aVal === "number" && typeof bVal === "number") {
        return sortDirection === "asc" ? aVal - bVal : bVal - aVal;
      }
      
      const aStr = String(aVal);
      const bStr = String(bVal);
      return sortDirection === "asc"
        ? aStr.localeCompare(bStr, "pt-BR")
        : bStr.localeCompare(aStr, "pt-BR");
    });
  }, [rows, sortColumn, sortDirection]);

  // Paginação
  const totalPages = Math.ceil(sortedRows.length / itemsPerPage);
  const paginatedRows = useMemo(() => {
    const start = currentPage * itemsPerPage;
    const end = start + itemsPerPage;
    return sortedRows.slice(start, end);
  }, [sortedRows, currentPage, itemsPerPage]);

  const handleSort = (column: string) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortColumn(column);
      setSortDirection("asc");
    }
    setCurrentPage(0); // Reset para primeira página ao ordenar
  };

  if (!rows || rows.length === 0) {
    return null;
  }

  return (
    <div
      id={id}
      className="bg-[#0F172A] border border-white/5 rounded-xl overflow-hidden shadow-lg"
    >
      {title && (
        <div className="px-6 py-4 border-b border-white/5">
          <h3 className="text-white font-semibold text-xl mb-0">{title}</h3>
          {subtitle && (
            <p className="text-sm text-white/60 mt-2">{subtitle}</p>
          )}
        </div>
      )}
      <div className="overflow-x-auto max-h-[70vh] overflow-y-auto">
        <table className="w-full border-collapse">
          <thead className="bg-white/5 sticky top-0 z-10">
            <tr>
              {visibleColumns.map((col) => (
                <th
                  key={col}
                  className={`text-left text-white/60 px-4 py-3 text-xs font-semibold uppercase tracking-wide cursor-pointer hover:bg-white/10 transition-colors ${
                    highlightFirstColumn && col === visibleColumns[0]
                      ? "bg-white/10"
                      : ""
                  }`}
                  onClick={() => handleSort(col)}
                >
                  <div className="flex items-center gap-2">
                    {col.replace(/_/g, " ")}
                    {sortColumn === col && (
                      <span className="text-white/40">
                        {sortDirection === "asc" ? "↑" : "↓"}
                      </span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginatedRows.map((row, i) => {
              // Gera key estável baseada no primeiro campo (geralmente ID)
              const firstKey = visibleColumns[0];
              const rowKey = row[firstKey] ? `${firstKey}-${row[firstKey]}` : `row-${currentPage}-${i}`;
              
              return (
              <tr
                key={rowKey}
                className={`border-b border-white/5 hover:bg-white/5 transition-colors ${
                  i % 2 === 0 ? "bg-white/2" : "bg-transparent"
                }`}
              >
                {visibleColumns.map((col, c) => {
                  const cellValue = row[col];
                  // ✅ Renderiza valores com múltiplas linhas (separados por \n)
                  const renderCellValue = () => {
                    if (cellValue === null || cellValue === undefined || cellValue === "") {
                      return "—";
                    }
                    if (typeof cellValue === "number") {
                      return formatNumberBR(cellValue);
                    }
                    const strValue = String(cellValue);
                    // Se contém \n, renderiza múltiplas linhas
                    if (strValue.includes("\n")) {
                      return (
                        <div className="flex flex-col gap-1">
                          {strValue.split("\n").map((line, idx) => (
                            <span key={idx} className={idx > 0 ? "text-white/60" : ""}>
                              {line.trim() || "—"}
                            </span>
                          ))}
                        </div>
                      );
                    }
                    return strValue;
                  };
                  
                  return (
                    <td
                      key={`cell-${i}-${c}-${col}`}
                      className={`px-4 py-3 text-white text-sm ${
                        highlightFirstColumn && c === 0
                          ? "font-semibold text-white"
                          : "text-white/80"
                      }`}
                    >
                      {renderCellValue()}
                    </td>
                  );
                })}
              </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      
      {/* Paginação */}
      {totalPages > 1 && (
        <div className="px-6 py-4 border-t border-white/5 flex items-center justify-between">
          <div className="text-sm text-white/60">
            Mostrando {currentPage * itemsPerPage + 1} a{" "}
            {Math.min((currentPage + 1) * itemsPerPage, sortedRows.length)} de{" "}
            {sortedRows.length} registros
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentPage((p) => Math.max(0, p - 1))}
              disabled={currentPage === 0}
              className="px-3 py-1 text-sm text-white/80 bg-white/5 rounded border border-white/10 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white/10 transition-colors"
            >
              Anterior
            </button>
            <span className="text-sm text-white/60">
              Página {currentPage + 1} de {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={currentPage >= totalPages - 1}
              className="px-3 py-1 text-sm text-white/80 bg-white/5 rounded border border-white/10 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white/10 transition-colors"
            >
              Próxima
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
