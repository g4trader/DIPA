import React from "react";

type DataTableProps = {
  rows: Array<Record<string, any>>;
  title?: string;
  highlightFirstColumn?: boolean;
};

/**
 * DataTable - Tabela premium com sticky header e linhas zebradas
 * 
 * Exibe dados tabulares com visual enterprise e boa legibilidade
 */
export function DataTable({
  rows,
  title,
  highlightFirstColumn = true,
}: DataTableProps) {
  if (!rows || rows.length === 0) {
    return null;
  }

  let columns = Object.keys(rows[0]);
  
  // Esconde coluna "Rota" se todas as rotas forem vazias ou "—"
  const temAlgumaRotaValida = rows.some(
    (row) => row["Rota"] && row["Rota"] !== "—" && row["Rota"] !== ""
  );
  
  if (!temAlgumaRotaValida && columns.includes("Rota")) {
    columns = columns.filter((col) => col !== "Rota");
  }

  return (
    <div className="bg-[#0F172A] border border-white/5 rounded-xl overflow-hidden shadow-lg">
      {title && (
        <div className="px-6 py-4 border-b border-white/5">
          <h3 className="text-white font-semibold text-xl mb-0">{title}</h3>
        </div>
      )}
      <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
        <table className="w-full border-collapse">
          <thead className="bg-white/5 sticky top-0 z-10">
            <tr>
              {columns.map((col) => (
                <th
                  key={col}
                  className={`text-left text-white/60 px-4 py-3 text-xs font-semibold uppercase tracking-wide ${
                    highlightFirstColumn && col === columns[0]
                      ? "bg-white/10"
                      : ""
                  }`}
                >
                  {col.replace(/_/g, " ")}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr
                key={i}
                className={`border-b border-white/5 hover:bg-white/5 transition-colors ${
                  i % 2 === 0 ? "bg-white/2" : "bg-transparent"
                }`}
              >
                {columns.map((col, c) => (
                  <td
                    key={c}
                    className={`px-4 py-3 text-white text-sm ${
                      highlightFirstColumn && c === 0
                        ? "font-semibold text-white"
                        : "text-white/80"
                    }`}
                  >
                    {typeof row[col] === "number"
                      ? row[col].toLocaleString("pt-BR")
                      : row[col] || "—"}
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

