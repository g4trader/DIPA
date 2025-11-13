"use client";

import React, { Fragment } from "react";
import { clsx } from "clsx";
import { Sparkles, ArrowRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { KpiStats } from "./KpiStats";
import { DipaChart } from "./DipaChart";
import { RegionTable } from "./RegionTable";
import type { QueryResult } from "./types";
import { ds } from "@/styles/ui";

type InsightCardProps = {
  busy: boolean;
  insightPulse: boolean;
  insightFresh: boolean;
  activeResult?: QueryResult;
  insights: { index: number; question: string }[];
  activeInsightIndex: number | null;
  onSelectInsight: (index: number) => void;
  onGenerateInitial: () => void;
};

export function InsightCard({
  busy,
  insightPulse,
  insightFresh,
  activeResult,
  insights,
  activeInsightIndex,
  onSelectInsight,
  onGenerateInitial
}: InsightCardProps) {
  const displayTitle = activeResult ? INTENT_LABELS[activeResult.intent] ?? activeResult.intent : "Nenhum insight selecionado";

  return (
    <Card
      className={clsx(
        ds.card,
        "relative overflow-hidden shadow-2xl shadow-blue-900/30 transition-all duration-500",
        busy && "opacity-90",
        insightPulse && "ring-2 ring-blue-500/60 shadow-[0_0_45px_rgba(59,130,246,0.45)] motion-safe:animate-pulse"
      )}
    >
      <CardContent className="flex flex-col gap-6 md:p-10">
        <Header month={activeResult?.month} title={displayTitle} insightFresh={insightFresh && Boolean(activeResult)} />

        {insights.length > 1 ? (
          <div className="flex flex-wrap gap-2">
            {insights.map(({ index, question }) => (
              <InsightChip
                key={index}
                label={question.length > 48 ? `${question.slice(0, 48)}…` : question}
                active={index === activeInsightIndex}
                onClick={() => onSelectInsight(index)}
              />
            ))}
          </div>
        ) : null}

        <p className="text-sm text-slate-400">
          {busy && !activeResult
            ? "Gerando insight..."
            : activeResult?.narrative ?? "Selecione ou gere um insight para visualizar os detalhes."}
        </p>

        {activeResult ? (
          <Fragment>
            <KpiStats items={activeResult.kpis} />
            <DipaChart chart={activeResult.chart} title="Curva analítica" />
            <RegionTable result={activeResult} />
          </Fragment>
        ) : (
          <EmptyState onGenerateInitial={onGenerateInitial} />
        )}
      </CardContent>
    </Card>
  );
}

function Header({
  month,
  insightFresh,
  title
}: {
  month?: string;
  insightFresh: boolean;
  title: string;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-4">
      <div className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Insight ativo</p>
        <h2 className="text-2xl font-semibold text-slate-100">{title}</h2>
      </div>
      <div className="flex flex-col items-end gap-2">
        {month ? (
          <span className="inline-flex items-center rounded-full border border-blue-500/40 bg-blue-500/15 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-blue-200">
            {month}
          </span>
        ) : null}
        {insightFresh ? (
          <span className="inline-flex items-center gap-2 rounded-full border border-blue-500/40 bg-blue-500/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-blue-200">
            <span className="h-2 w-2 animate-ping rounded-full bg-blue-400" />
            Atualizado agora
          </span>
        ) : null}
      </div>
    </div>
  );
}

const INTENT_LABELS: Record<string, string> = {
  target_vs_actual: "Meta vs realizado",
  seller_performance: "Performance por consultor",
  mix_products: "Mix de produtos",
  promotion_mix: "Produtos em promoção",
  top_products: "Top SKUs",
  avg_ticket: "Ticket médio",
  sales_overview: "Visão geral de vendas"
};

function InsightChip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={clsx(
        "rounded-full px-3 py-1 text-xs font-medium transition duration-200 ease-out focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-300 active:scale-95 motion-safe:transition-transform",
        active
          ? "bg-blue-600 text-white shadow-lg shadow-blue-500/30"
          : "bg-slate-700/80 text-slate-300 hover:-translate-y-0.5 hover:shadow-[0_0_12px_rgba(59,130,246,0.35)]"
      )}
    >
      {label}
    </button>
  );
}

function EmptyState({ onGenerateInitial }: { onGenerateInitial: () => void }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-blue-500/40 bg-slate-900/40 px-6 py-14 text-center shadow-inner shadow-blue-900/20">
      <Sparkles className="h-10 w-10 text-blue-400" />
      <h2 className="text-lg font-semibold text-slate-100">Nenhum insight selecionado</h2>
      <p className="max-w-sm text-sm text-slate-400">
        Gere um prompt no laboratório para visualizar KPIs, gráficos e tabelas nesta área.
      </p>
      <Button onClick={onGenerateInitial} className="shadow-lg shadow-blue-900/40">
        <ArrowRight className="mr-2 h-4 w-4" />
        Gerar insight inicial
      </Button>
    </div>
  );
}

