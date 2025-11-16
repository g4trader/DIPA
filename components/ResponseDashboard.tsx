import React from "react";
import { TrendingUp, TrendingDown, Minus, Target, Users, AlertCircle, Lightbulb } from "lucide-react";
import { CopilotStructuredResponse } from "@/types/agent";
import { clsx } from "clsx";

type Props = {
  data: CopilotStructuredResponse;
};

/**
 * Componente de Dashboard Estruturado para respostas do DIPAM COPILOT™
 * Renderiza cards visuais modernos baseados em dados estruturados
 */
export const ResponseDashboard: React.FC<Props> = ({ data }) => {
  return (
    <div className="space-y-6">
      {/* Card 1: Resumo Executivo */}
      {data.resumoExecutivo && (
        <div className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900/95 to-slate-950/95 p-6 shadow-xl">
          <div className="flex items-start gap-4">
            <div className="rounded-xl bg-blue-500/10 p-3 border border-blue-500/20">
              <Target className="w-6 h-6 text-blue-400" />
            </div>
            <div className="flex-1 space-y-3">
              <h3 className="text-lg font-semibold text-slate-100">Resumo Executivo</h3>
              <div className="text-sm leading-relaxed text-slate-300 whitespace-pre-line">
                {data.resumoExecutivo.split("\n\n").map((para, idx) => (
                  <p key={idx} className="mb-3 last:mb-0">
                    {para.trim()}
                  </p>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Card 2: KPIs do Mês */}
      {data.kpis && data.kpis.length > 0 && (
        <div className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900/95 to-slate-950/95 p-6 shadow-xl">
          <div className="flex items-center gap-3 mb-4">
            <div className="rounded-xl bg-emerald-500/10 p-2 border border-emerald-500/20">
              <TrendingUp className="w-5 h-5 text-emerald-400" />
            </div>
            <h3 className="text-lg font-semibold text-slate-100">KPIs do Mês</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {data.kpis.map((kpi, idx) => (
              <div
                key={idx}
                className="rounded-xl border border-slate-800 bg-slate-900/80 p-5 hover:bg-slate-900 transition-colors"
              >
                <div className="flex items-start justify-between mb-2">
                  <p className="text-xs font-medium text-slate-400 uppercase tracking-wide">
                    {kpi.icon && <span className="mr-2">{kpi.icon}</span>}
                    {kpi.label}
                  </p>
                  {kpi.variation && (
                    <span
                      className={clsx(
                        "text-xs font-semibold px-2 py-1 rounded-full",
                        kpi.variation.startsWith("+") || parseFloat(kpi.variation) > 0
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                          : kpi.variation.startsWith("-") || parseFloat(kpi.variation) < 0
                          ? "bg-red-500/10 text-red-400 border border-red-500/20"
                          : "bg-slate-700/50 text-slate-400 border border-slate-700"
                      )}
                    >
                      {kpi.variation}
                    </span>
                  )}
                </div>
                <p
                  className={clsx(
                    "text-2xl font-bold",
                    kpi.color === "positive"
                      ? "text-emerald-400"
                      : kpi.color === "negative"
                      ? "text-red-400"
                      : "text-slate-100"
                  )}
                >
                  {typeof kpi.value === "number"
                    ? kpi.value.toLocaleString("pt-BR", {
                        style: kpi.value > 1000 ? "currency" : "decimal",
                        currency: "BRL",
                        minimumFractionDigits: kpi.value > 1000 ? 0 : 1,
                        maximumFractionDigits: kpi.value > 1000 ? 0 : 1,
                      })
                    : kpi.value}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Card 3: Ranking de Vendedores */}
      {data.rankingVendedores && data.rankingVendedores.length > 0 && (
        <div className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900/95 to-slate-950/95 p-6 shadow-xl">
          <div className="flex items-center gap-3 mb-4">
            <div className="rounded-xl bg-amber-500/10 p-2 border border-amber-500/20">
              <Users className="w-5 h-5 text-amber-400" />
            </div>
            <h3 className="text-lg font-semibold text-slate-100">Ranking de Vendedores</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="text-left py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">
                    #
                  </th>
                  <th className="text-left py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">
                    Vendedor
                  </th>
                  {data.rankingVendedores[0]?.supervisor && (
                    <th className="text-left py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">
                      Supervisor
                    </th>
                  )}
                  <th className="text-right py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">
                    Meta
                  </th>
                  <th className="text-right py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">
                    Realizado
                  </th>
                  <th className="text-right py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">
                    Atingimento
                  </th>
                  <th className="text-right py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">
                    Gap
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.rankingVendedores.map((v, idx) => (
                  <tr
                    key={idx}
                    className="border-b border-slate-800/50 hover:bg-slate-900/50 transition-colors"
                  >
                    <td className="py-3 px-4 text-slate-400 font-medium">{v.rank || idx + 1}</td>
                    <td className="py-3 px-4 text-slate-100 font-medium">{v.vendedor}</td>
                    {data.rankingVendedores[0]?.supervisor && (
                      <td className="py-3 px-4 text-slate-400 text-xs">{v.supervisor || "—"}</td>
                    )}
                    <td className="py-3 px-4 text-slate-300 text-right">
                      {v.meta.toLocaleString("pt-BR", {
                        style: "currency",
                        currency: "BRL",
                      })}
                    </td>
                    <td className="py-3 px-4 text-slate-200 text-right font-medium">
                      {v.realizado.toLocaleString("pt-BR", {
                        style: "currency",
                        currency: "BRL",
                      })}
                    </td>
                    <td
                      className={clsx(
                        "py-3 px-4 text-right font-semibold",
                        v.atingimento >= 100
                          ? "text-emerald-400"
                          : v.atingimento >= 80
                          ? "text-yellow-400"
                          : "text-red-400"
                      )}
                    >
                      {v.atingimento.toFixed(1)}%
                    </td>
                    <td
                      className={clsx(
                        "py-3 px-4 text-right font-semibold",
                        v.gap >= 0 ? "text-emerald-400" : "text-red-400"
                      )}
                    >
                      {v.gap >= 0 ? "+" : ""}
                      {v.gap.toLocaleString("pt-BR", {
                        style: "currency",
                        currency: "BRL",
                      })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Card 4: Clientes Críticos */}
      {data.clientesCriticos && data.clientesCriticos.length > 0 && (
        <div className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900/95 to-slate-950/95 p-6 shadow-xl">
          <div className="flex items-center gap-3 mb-4">
            <div className="rounded-xl bg-orange-500/10 p-2 border border-orange-500/20">
              <AlertCircle className="w-5 h-5 text-orange-400" />
            </div>
            <h3 className="text-lg font-semibold text-slate-100">Clientes Críticos</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="text-left py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">
                    Cliente
                  </th>
                  {data.clientesCriticos[0]?.vendedor && (
                    <th className="text-left py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">
                      Vendedor
                    </th>
                  )}
                  <th className="text-right py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">
                    Faturamento
                  </th>
                  <th className="text-right py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">
                    Pedidos
                  </th>
                  {data.clientesCriticos[0]?.variacao !== undefined && (
                    <th className="text-right py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">
                      Variação
                    </th>
                  )}
                  {data.clientesCriticos[0]?.insight && (
                    <th className="text-left py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">
                      Insight
                    </th>
                  )}
                </tr>
              </thead>
              <tbody>
                {data.clientesCriticos.map((c, idx) => (
                  <tr
                    key={idx}
                    className="border-b border-slate-800/50 hover:bg-slate-900/50 transition-colors"
                  >
                    <td className="py-3 px-4 text-slate-100 font-medium">{c.cliente}</td>
                    {data.clientesCriticos[0]?.vendedor && (
                      <td className="py-3 px-4 text-slate-400 text-xs">{c.vendedor || "—"}</td>
                    )}
                    <td className="py-3 px-4 text-slate-200 text-right font-medium">
                      {c.faturamento.toLocaleString("pt-BR", {
                        style: "currency",
                        currency: "BRL",
                      })}
                    </td>
                    <td className="py-3 px-4 text-slate-300 text-right">{c.pedidos}</td>
                    {data.clientesCriticos[0]?.variacao !== undefined && (
                      <td
                        className={clsx(
                          "py-3 px-4 text-right font-semibold",
                          c.variacao === undefined || c.variacao === null
                            ? "text-slate-500"
                            : c.variacao < -10
                            ? "text-red-400"
                            : c.variacao < 0
                            ? "text-yellow-400"
                            : "text-emerald-400"
                        )}
                      >
                        {c.variacao !== undefined && c.variacao !== null
                          ? `${c.variacao >= 0 ? "+" : ""}${c.variacao.toFixed(1)}%`
                          : "—"}
                      </td>
                    )}
                    {data.clientesCriticos[0]?.insight && (
                      <td className="py-3 px-4 text-slate-400 text-xs">{c.insight || "—"}</td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Card 5: Insights e Recomendações */}
      {data.insightsRecomendacoes && data.insightsRecomendacoes.length > 0 && (
        <div className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900/95 to-slate-950/95 p-6 shadow-xl">
          <div className="flex items-center gap-3 mb-4">
            <div className="rounded-xl bg-purple-500/10 p-2 border border-purple-500/20">
              <Lightbulb className="w-5 h-5 text-purple-400" />
            </div>
            <h3 className="text-lg font-semibold text-slate-100">Insights e Recomendações</h3>
          </div>
          <ul className="space-y-3">
            {data.insightsRecomendacoes.map((insight, idx) => (
              <li key={idx} className="flex items-start gap-3">
                <span className="text-purple-400 mt-1">•</span>
                <p className="text-sm text-slate-300 leading-relaxed flex-1">{insight}</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Card Técnico (colapsável) */}
      {data.jsonTecnico && (
        <details className="rounded-2xl border border-slate-800 bg-slate-900/50 p-4">
          <summary className="text-xs text-slate-400 hover:text-slate-200 cursor-pointer font-medium flex items-center gap-2">
            <span>⚙️</span>
            Ver detalhes técnicos (JSON)
          </summary>
          <pre className="mt-4 max-h-96 overflow-auto rounded-lg bg-slate-950/80 p-4 text-[10px] text-slate-400 border border-slate-800">
            {JSON.stringify(data.jsonTecnico, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
};
