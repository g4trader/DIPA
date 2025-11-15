import React, { useState } from "react";
import { ChevronDown } from "lucide-react";
import { clsx } from "clsx";
import { CopilotAnswerPayload } from "@/types/agent";

type Props = {
  payload: CopilotAnswerPayload;
};

/**
 * Componente de card de resposta do DIPAM COPILOT™
 * Renderiza respostas estruturadas com Resumo executivo, KPIs, Top vendedores, Insights e Observações
 */
export const CopilotAnswerCard: React.FC<Props> = ({ payload }) => {
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
    respostaMarkdown,
  } = payload;

  const rawData = respostaMarkdown ? { respostaMarkdown, ...payload } : payload;

  return (
    <div className="relative rounded-3xl border border-slate-800 bg-gradient-to-b from-slate-900/90 to-slate-950/95 shadow-2xl overflow-hidden">
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
            <pre className="mt-2 max-h-64 overflow-auto rounded-xl bg-slate-950/80 p-3 text-[11px] text-slate-300">
              {JSON.stringify(rawData, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  );
};
