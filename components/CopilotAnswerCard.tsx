import React, { useState, forwardRef } from "react";
import { ChevronDown, Download } from "lucide-react";
import { clsx } from "clsx";
import { CopilotAnswerPayload } from "@/types/agent";
import { ResponseDashboard } from "./ResponseDashboard";
import { generateExecutivePdf } from "./pdf/generateExecutivePdf";

type Props = {
  payload: CopilotAnswerPayload;
};

/**
 * Componente de card de resposta do DIPAM COPILOT™
 * Renderiza respostas estruturadas com Resumo executivo, KPIs, Top vendedores, Insights e Observações
 */
export const CopilotAnswerCard = forwardRef<HTMLDivElement, Props>(({ payload }, ref) => {
  const [showDetails, setShowDetails] = useState(false);

  const {
    intent,
    intentLabel,
    confidence,
    question,
    resumoExecutivo,
    insights,
    observacoes,
    kpis,
    topVendedores,
    clientesProblema,
    respostaMarkdown,
  } = payload;

  const rawData = respostaMarkdown ? { respostaMarkdown, ...payload } : payload;

  // Handler para gerar PDF
  const handleDownloadPdf = () => {
    if (!payload.structured) return;
    
    const structured = payload.structured;
    const dataAny = structured as any;
    
    // Prepara dados para o PDF
    const pdfData = {
      pergunta: question || intentLabel || intent || 'Consulta DIPAM COPILOT™',
      resumoExecutivo: structured.resumo_executivo || structured.resumoExecutivo || resumoExecutivo,
      kpis: structured.kpis?.map((kpi: any) => ({
        label: kpi.label,
        valor: kpi.value,
      })) || [],
      principaisAchados: dataAny.principaisAchados,
      implicacoes: dataAny.implicacoesComerciais,
      planoAcao: dataAny.planoAcao,
      alvosPrioritariosLista: dataAny.alvosPrioritarios,
      tabelaTop10: dataAny.topAlvos?.map((alvo: any) => ({
        cliente: alvo.Cliente || alvo.cliente || alvo.item || '—',
        diasSemCompra: alvo["Dias sem compra"] || alvo.diasSemCompra || alvo.dias || 0,
        rota: alvo.Rota || alvo.rota || null,
      })),
      tabelaPrincipal: structured.detalhe_tabela ? {
        colunas: structured.detalhe_tabela.colunas || [],
        linhas: structured.detalhe_tabela.linhas || [],
      } : null,
    };
    
    generateExecutivePdf(pdfData);
  };

  // NOVO: Se houver resposta estruturada, renderiza dashboard diretamente
  if (payload.structured) {
    // Garante que respostaMarkdown seja passado para o ResponseDashboard se disponível
    const structuredWithMarkdown = respostaMarkdown
      ? { ...payload.structured, respostaMarkdown }
      : payload.structured;

    return (
      <div ref={ref} id="dipam-card-resposta-principal" className="relative rounded-3xl border border-slate-800 bg-gradient-to-b from-slate-900/90 to-slate-950/95 shadow-2xl overflow-hidden">
        {/* Header do card */}
        <div id="dipam-card-header" className="flex items-center gap-2 px-6 pt-5 pb-4 border-b border-slate-800/70 bg-slate-950/70">
          <div id="dipam-card-header-icon" className="inline-flex h-8 w-8 items-center justify-center rounded-2xl bg-sky-500/10 border border-sky-500/40 text-sky-300 text-xs font-semibold">
            ⚡
          </div>
          <div id="dipam-card-header-brand" className="flex flex-col">
            <span id="dipam-card-header-brand-name" className="text-[11px] uppercase tracking-[0.2em] text-slate-500">
              DIPAM COPILOT™
            </span>
            <span id="dipam-card-header-brand-tagline" className="text-xs text-slate-400">Inteligência comercial em tempo real</span>
          </div>
          <div id="dipam-card-header-badges" className="ml-auto inline-flex items-center gap-2">
            <span id="dipam-card-header-badge-intent" className="rounded-full bg-slate-800/80 px-3 py-1 text-[11px] text-slate-300">
              {intentLabel || intent}
            </span>
            <span id="dipam-card-header-badge-confidence" className="rounded-full bg-emerald-500/10 border border-emerald-400/40 px-3 py-1 text-[11px] text-emerald-300">
              {Math.round(confidence * 100)}% confiança
            </span>
            {/* Botão de download PDF - mesmo estilo dos badges */}
            <button
              onClick={handleDownloadPdf}
              className="inline-flex items-center gap-1.5 rounded-full bg-slate-800/80 px-3 py-1 text-[11px] text-slate-300 hover:bg-slate-700/80 transition-colors"
              title="Baixar relatório em PDF"
            >
              <Download className="w-3 h-3" />
              <span>Baixar PDF</span>
            </button>
          </div>
        </div>

        {/* Conteúdo principal - Dashboard estruturado */}
        <div id="dipam-card-content" className="px-6 pt-4 pb-6">
          {/* Renderiza dashboard estruturado (pergunta removida - já aparece no chat) */}
          <ResponseDashboard data={structuredWithMarkdown} question={question} />
        </div>
      </div>
    );
  }

  // FALLBACK: Renderização antiga (apenas para debug/compatibilidade)
  return (
    <div ref={ref} className="relative rounded-3xl border border-slate-800 bg-gradient-to-b from-slate-900/90 to-slate-950/95 shadow-2xl overflow-hidden">
      {/* Header do card */}
      <div className="flex items-center gap-2 px-6 pt-5 pb-3 border-b border-slate-800/70 bg-slate-950/70">
        <div className="inline-flex h-8 w-8 items-center justify-center rounded-2xl bg-sky-500/10 border border-sky-500/40 text-sky-300 text-xs font-semibold">
          ⚡
        </div>
        <div className="flex flex-col">
          <span className="text-[11px] uppercase tracking-[0.2em] text-slate-500">
            DIPAM COPILOT™
          </span>
          <span className="text-xs text-slate-400">
            Inteligência comercial em tempo real
          </span>
        </div>
        <div className="ml-auto inline-flex items-center gap-2">
          <span className="rounded-full bg-slate-800/80 px-3 py-1 text-[11px] text-slate-300">
            {intentLabel || intent}
          </span>
          <span className="rounded-full bg-emerald-500/10 border border-emerald-400/40 px-3 py-1 text-[11px] text-emerald-300">
            {Math.round(confidence * 100)}% confiança
          </span>
        </div>
      </div>

      {/* Conteúdo principal */}
      <div className="px-6 pt-4 pb-6 space-y-6">
        {/* Título (pergunta) */}
        <h2 className="text-lg md:text-xl font-semibold text-slate-50">
          {question}
        </h2>

        {/* Resumo executivo */}
        {resumoExecutivo && (
          <section className="space-y-2">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-100">
              <span className="text-sky-400">●</span>
              Resumo executivo
            </h3>
            <p className="text-sm leading-relaxed text-slate-200 whitespace-pre-line">
              {resumoExecutivo}
            </p>
          </section>
        )}

        {/* KPIs do mês */}
        {kpis && (
          <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/80 px-5 py-4">
              <p className="text-[11px] uppercase tracking-wide text-slate-500">
                Mês / Ano
              </p>
              <p className="text-base font-semibold text-slate-100">
                {kpis.mesAnoLabel}
              </p>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/80 px-5 py-4">
              <p className="text-[11px] uppercase tracking-wide text-slate-500">
                Vendedores que bateram
              </p>
              <p className="text-xl font-semibold text-emerald-400">
                {kpis.vendedoresQueBateram}
              </p>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/80 px-5 py-4">
              <p className="text-[11px] uppercase tracking-wide text-slate-500">
                Atingimento Médio
              </p>
              <p className="text-xl font-semibold text-emerald-400">
                {kpis.atingimentoMedio.toFixed(1)}%
              </p>
            </div>
          </section>
        )}

        {/* Top 5 vendedores */}
        {topVendedores && topVendedores.length > 0 && (
          <section className="space-y-3">
            <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
              <span className="text-amber-400 text-lg">🏆</span>
              Top 5 vendedores
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {topVendedores.slice(0, 5).map((v) => (
                <div
                  key={v.rank}
                  className="rounded-2xl border border-slate-800 bg-slate-900/80 px-5 py-4"
                >
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-xs text-amber-400 font-semibold">
                      #{v.rank}
                    </span>
                    <span className="text-xs text-emerald-400 font-semibold">
                      ↑ {v.atingimento.toFixed(1)}%
                    </span>
                  </div>

                  <p className="text-sm font-semibold text-slate-50">{v.nome}</p>
                  {v.supervisor && (
                    <p className="text-[11px] text-slate-400 mt-1">
                      Supervisor: {v.supervisor}
                    </p>
                  )}

                  <div className="mt-3 grid grid-cols-2 gap-2 text-[11px]">
                    <div>
                      <p className="text-slate-500 uppercase tracking-wide">Meta</p>
                      <p className="text-slate-200">
                        {v.meta.toLocaleString("pt-BR", {
                          style: "currency",
                          currency: "BRL",
                        })}
                      </p>
                    </div>
                    <div>
                      <p className="text-slate-500 uppercase tracking-wide">Realizado</p>
                      <p className="text-emerald-400">
                        {v.realizado.toLocaleString("pt-BR", {
                          style: "currency",
                          currency: "BRL",
                        })}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Insights e recomendações */}
        {insights && (
          <section className="space-y-2">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-100">
              <span className="text-amber-400 text-lg">📈</span>
              Insights e recomendações
            </h3>
            <p className="text-sm leading-relaxed text-slate-200 whitespace-pre-line">
              {insights}
            </p>
          </section>
        )}

        {/* Observações sobre os dados */}
        {observacoes && (
          <section className="space-y-2">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-100">
              <span className="text-orange-400 text-lg">⚠️</span>
              Observações sobre os dados
            </h3>
            <p className="text-sm leading-relaxed text-slate-300 whitespace-pre-line">
              {observacoes}
            </p>
          </section>
        )}
      </div>

      {/* Rodapé "Ver detalhes de dados" */}
      {rawData && (
        <div className="border-t border-slate-800 px-6 py-3">
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="mx-auto flex items-center gap-2 text-xs text-slate-400 hover:text-slate-200 transition-colors"
          >
            Ver detalhes de dados
            <ChevronDown
              className={clsx("w-3 h-3 transition-transform", showDetails && "rotate-180")}
            />
          </button>
          {showDetails && (
            <div className="mt-4 space-y-4">
              {/* Tabela de vendedores se disponível */}
              {topVendedores && topVendedores.length > 0 && (
                <div className="rounded-xl bg-slate-950/80 p-4">
                  <h4 className="text-xs font-semibold text-slate-300 mb-3 uppercase tracking-wide">
                    Ranking Completo de Vendedores
                  </h4>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="border-b border-slate-700">
                          <th className="text-left py-2 px-3 text-slate-400 font-semibold">#</th>
                          <th className="text-left py-2 px-3 text-slate-400 font-semibold">Vendedor</th>
                          {topVendedores[0]?.supervisor && (
                            <th className="text-left py-2 px-3 text-slate-400 font-semibold">Supervisor</th>
                          )}
                          <th className="text-right py-2 px-3 text-slate-400 font-semibold">Meta</th>
                          <th className="text-right py-2 px-3 text-slate-400 font-semibold">Realizado</th>
                          <th className="text-right py-2 px-3 text-slate-400 font-semibold">Atingimento</th>
                        </tr>
                      </thead>
                      <tbody>
                        {topVendedores.map((v) => (
                          <tr
                            key={v.rank}
                            className="border-b border-slate-800/50 hover:bg-slate-900/50 transition-colors"
                          >
                            <td className="py-2 px-3 text-slate-300">{v.rank}</td>
                            <td className="py-2 px-3 text-slate-100 font-medium">{v.nome}</td>
                            {topVendedores[0]?.supervisor && (
                              <td className="py-2 px-3 text-slate-400 text-xs">
                                {v.supervisor || "—"}
                              </td>
                            )}
                            <td className="py-2 px-3 text-slate-300 text-right">
                              {v.meta.toLocaleString("pt-BR", {
                                style: "currency",
                                currency: "BRL",
                              })}
                            </td>
                            <td className="py-2 px-3 text-slate-200 text-right font-medium">
                              {v.realizado.toLocaleString("pt-BR", {
                                style: "currency",
                                currency: "BRL",
                              })}
                            </td>
                            <td
                              className={clsx(
                                "py-2 px-3 text-right font-semibold",
                                v.atingimento >= 100
                                  ? "text-emerald-400"
                                  : v.atingimento >= 80
                                  ? "text-yellow-400"
                                  : "text-red-400"
                              )}
                            >
                              {v.atingimento.toFixed(1)}%
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* KPIs detalhados se disponível */}
              {kpis && (
                <div className="rounded-xl bg-slate-950/80 p-4">
                  <h4 className="text-xs font-semibold text-slate-300 mb-3 uppercase tracking-wide">
                    KPIs Detalhados
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div className="space-y-1">
                      <p className="text-[10px] text-slate-500 uppercase">Período</p>
                      <p className="text-sm text-slate-100 font-medium">{kpis.mesAnoLabel}</p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-[10px] text-slate-500 uppercase">Vendedores que Bateram</p>
                      <p className="text-sm text-emerald-400 font-semibold">
                        {kpis.vendedoresQueBateram}
                      </p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-[10px] text-slate-500 uppercase">Atingimento Médio</p>
                      <p className="text-sm text-emerald-400 font-semibold">
                        {kpis.atingimentoMedio.toFixed(2)}%
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Tabela de clientes problemáticos se disponível */}
              {clientesProblema && clientesProblema.length > 0 && (
                <div className="rounded-xl bg-slate-950/80 p-4">
                  <h4 className="text-xs font-semibold text-slate-300 mb-3 uppercase tracking-wide">
                    Clientes com Maior Oportunidade/Perda
                  </h4>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="border-b border-slate-700">
                          <th className="text-left py-2 px-3 text-slate-400 font-semibold">Cliente</th>
                          {clientesProblema[0]?.vendedor_nome && (
                            <th className="text-left py-2 px-3 text-slate-400 font-semibold">Vendedor</th>
                          )}
                          <th className="text-right py-2 px-3 text-slate-400 font-semibold">Faturamento</th>
                          {clientesProblema[0]?.qtd_pedidos !== undefined && (
                            <th className="text-right py-2 px-3 text-slate-400 font-semibold">Pedidos</th>
                          )}
                          {clientesProblema[0]?.variacao_percentual !== undefined && (
                            <th className="text-right py-2 px-3 text-slate-400 font-semibold">Variação</th>
                          )}
                        </tr>
                      </thead>
                      <tbody>
                        {clientesProblema.map((c, idx) => (
                          <tr
                            key={idx}
                            className="border-b border-slate-800/50 hover:bg-slate-900/50 transition-colors"
                          >
                            <td className="py-2 px-3 text-slate-100 font-medium">{c.nome_cliente}</td>
                            {clientesProblema[0]?.vendedor_nome && (
                              <td className="py-2 px-3 text-slate-400 text-xs">
                                {c.vendedor_nome || "—"}
                              </td>
                            )}
                            <td className="py-2 px-3 text-slate-200 text-right font-medium">
                              {c.faturamento_mes.toLocaleString("pt-BR", {
                                style: "currency",
                                currency: "BRL",
                              })}
                            </td>
                            {clientesProblema[0]?.qtd_pedidos !== undefined && (
                              <td className="py-2 px-3 text-slate-300 text-right">
                                {c.qtd_pedidos || 0}
                              </td>
                            )}
                            {clientesProblema[0]?.variacao_percentual !== undefined && (
                              <td
                                className={clsx(
                                  "py-2 px-3 text-right font-semibold",
                                  c.variacao_percentual === undefined || c.variacao_percentual === null
                                    ? "text-slate-500"
                                    : c.variacao_percentual < -10
                                    ? "text-red-400"
                                    : c.variacao_percentual < 0
                                    ? "text-yellow-400"
                                    : "text-emerald-400"
                                )}
                              >
                                {c.variacao_percentual !== undefined && c.variacao_percentual !== null
                                  ? `${c.variacao_percentual >= 0 ? "+" : ""}${c.variacao_percentual.toFixed(1)}%`
                                  : "—"}
                              </td>
                            )}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* JSON bruto para debug (colapsável) */}
              <details className="rounded-xl bg-slate-950/80 p-4">
                <summary className="text-xs text-slate-400 hover:text-slate-200 cursor-pointer mb-2">
                  Ver dados técnicos (JSON) 🔧
                </summary>
                <pre className="mt-2 max-h-64 overflow-auto rounded-lg bg-slate-900/80 p-3 text-[10px] text-slate-400">
                  {JSON.stringify(rawData, null, 2)}
                </pre>
              </details>
            </div>
          )}
        </div>
      )}
    </div>
  );
});

CopilotAnswerCard.displayName = "CopilotAnswerCard";
