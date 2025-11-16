import React, { useState, useMemo } from "react";
import { TrendingUp, TrendingDown, Minus, Target, Users, AlertCircle, Lightbulb, Package, ChevronDown, Brain, Zap, DollarSign, Percent } from "lucide-react";
import { CopilotStructuredResponse } from "@/types/agent";
import { clsx } from "clsx";

type Props = {
  data: CopilotStructuredResponse;
};

/**
 * Componente de Dashboard Estruturado para respostas do DIPAM COPILOT™ (FASE 3 + FASE 5)
 * Renderiza cards visuais modernos baseados em secoes estruturadas com KPIs e insights preditivos
 */
export const ResponseDashboard: React.FC<Props> = ({ data }) => {
  const [showDetails, setShowDetails] = useState(false);
  const [expandedSections, setExpandedSections] = useState<Record<number, boolean>>({});
  
  // Compatibilidade: usa resumo_executivo ou resumoExecutivo
  const resumoExecutivo = data.resumo_executivo || data.resumoExecutivo;
  
  // Extrai KPIs das seções e insights preditivos
  const kpis = useMemo(() => {
    const kpisList: Array<{ label: string; value: string | number; icon: React.ReactNode; color: string; trend?: "up" | "down" | "neutral" }> = [];
    
    // Busca dados de vendedores para calcular KPIs
    const vendedoresSecao = data.secoes?.find(s => s.tipo === "lista_vendedores");
    if (vendedoresSecao?.dados && vendedoresSecao.dados.length > 0) {
      const vendedores = vendedoresSecao.dados as any[];
      const metaTotal = vendedores.reduce((sum, v) => sum + (v.meta_total || 0), 0);
      const realizadoTotal = vendedores.reduce((sum, v) => sum + (v.realizado_total || 0), 0);
      const atingimentoMedio = metaTotal > 0 ? (realizadoTotal / metaTotal) * 100 : 0;
      const vendedoresEmRisco = vendedores.filter(v => v.meta_risk_flag || (v.atingimento_pct && v.atingimento_pct < 95)).length;
      
      kpisList.push({
        label: "Faturamento do Mês",
        value: realizadoTotal.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }),
        icon: <DollarSign className="w-4 h-4" />,
        color: "text-slate-100",
        trend: "neutral"
      });
      
      kpisList.push({
        label: "Atingimento da Meta",
        value: `${atingimentoMedio.toFixed(1)}%`,
        icon: <Percent className="w-4 h-4" />,
        color: atingimentoMedio >= 100 ? "text-emerald-400" : atingimentoMedio >= 95 ? "text-yellow-400" : "text-red-400",
        trend: atingimentoMedio >= 100 ? "up" : atingimentoMedio >= 95 ? "neutral" : "down"
      });
      
      kpisList.push({
        label: "Vendedores em Risco",
        value: vendedoresEmRisco,
        icon: <AlertCircle className="w-4 h-4" />,
        color: vendedoresEmRisco > 0 ? "text-red-400" : "text-emerald-400",
        trend: vendedoresEmRisco > 0 ? "down" : "up"
      });
    }
    
    // Adiciona KPIs de insights preditivos
    if (data.insights_preditivos) {
      if (data.insights_preditivos.churn?.total_clientes_risco_alto) {
        kpisList.push({
          label: "Clientes em Alto Risco de Churn",
          value: data.insights_preditivos.churn.total_clientes_risco_alto,
          icon: <AlertCircle className="w-4 h-4" />,
          color: "text-orange-400",
          trend: "down"
        });
      }
      
      if (data.insights_preditivos.meta_risk?.vendedores_risco_alto) {
        // Atualiza ou adiciona vendedores em risco com dados preditivos
        const existingIdx = kpisList.findIndex(k => k.label === "Vendedores em Risco");
        if (existingIdx >= 0) {
          kpisList[existingIdx].value = data.insights_preditivos.meta_risk.vendedores_risco_alto;
        }
      }
    }
    
    return kpisList;
  }, [data.secoes, data.insights_preditivos]);
  
  const toggleSection = (index: number) => {
    setExpandedSections(prev => ({ ...prev, [index]: !prev[index] }));
  };
  
  return (
    <div className="space-y-6">
      {/* KPIs no Topo */}
      {kpis.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {kpis.map((kpi, idx) => (
            <div
              key={idx}
              className={clsx(
                "rounded-2xl border bg-gradient-to-br p-5 shadow-lg transition-all hover:shadow-xl",
                kpi.color.includes("emerald")
                  ? "border-emerald-500/30 from-emerald-500/10 to-emerald-500/5"
                  : kpi.color.includes("yellow")
                  ? "border-yellow-500/30 from-yellow-500/10 to-yellow-500/5"
                  : kpi.color.includes("red") || kpi.color.includes("orange")
                  ? "border-red-500/30 from-red-500/10 to-red-500/5"
                  : "border-slate-800 from-slate-900/80 to-slate-950/80"
              )}
            >
              <div className="flex items-start justify-between mb-2">
                <div className={clsx("rounded-lg p-2", kpi.color.includes("emerald") ? "bg-emerald-500/20" : kpi.color.includes("yellow") ? "bg-yellow-500/20" : kpi.color.includes("red") || kpi.color.includes("orange") ? "bg-red-500/20" : "bg-slate-800/50")}>
                  {kpi.icon}
                </div>
                {kpi.trend && (
                  <div className={clsx(
                    "rounded-full p-1",
                    kpi.trend === "up" ? "bg-emerald-500/20 text-emerald-400" : kpi.trend === "down" ? "bg-red-500/20 text-red-400" : "bg-slate-700/50 text-slate-400"
                  )}>
                    {kpi.trend === "up" ? <TrendingUp className="w-3 h-3" /> : kpi.trend === "down" ? <TrendingDown className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
                  </div>
                )}
              </div>
              <p className="text-xs font-medium text-slate-400 uppercase tracking-wide mb-1">{kpi.label}</p>
              <p className={clsx("text-2xl font-bold", kpi.color)}>
                {typeof kpi.value === "number" ? kpi.value.toLocaleString("pt-BR") : kpi.value}
              </p>
            </div>
          ))}
        </div>
      )}
      
      {/* Card 1: Resumo Executivo */}
      {resumoExecutivo && (
        <div className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900/95 to-slate-950/95 p-6 shadow-xl">
          <div className="flex items-start gap-4">
            <div className="rounded-xl bg-blue-500/10 p-3 border border-blue-500/20">
              <Target className="w-6 h-6 text-blue-400" />
            </div>
            <div className="flex-1 space-y-3">
              <h3 className="text-lg font-semibold text-slate-100">Resumo Executivo</h3>
              <div className="text-sm leading-relaxed text-slate-300 whitespace-pre-line">
                {resumoExecutivo.split("\n\n").map((para, idx) => (
                  <p key={idx} className="mb-3 last:mb-0">
                    {para.trim()}
                  </p>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Seção: Insights Preditivos (FASE 5) */}
      {data.insights_preditivos && (
        <div className="rounded-2xl border border-purple-500/30 bg-gradient-to-br from-purple-500/10 to-purple-900/10 p-6 shadow-xl">
          <div className="flex items-center gap-3 mb-4">
            <div className="rounded-xl bg-purple-500/20 p-2 border border-purple-500/40">
              <Brain className="w-5 h-5 text-purple-400" />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-slate-100">Insights Preditivos</h3>
              <p className="text-xs text-purple-300/80 mt-0.5">Inteligência Artificial • Previsões ML</p>
            </div>
            <span className="rounded-full bg-purple-500/20 border border-purple-500/40 px-3 py-1 text-xs text-purple-300 font-medium">
              IA Preditiva
            </span>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {data.insights_preditivos.churn && data.insights_preditivos.churn.total_clientes_risco_alto > 0 && (
              <div className="rounded-xl border border-orange-500/30 bg-orange-500/10 p-4">
                <div className="flex items-center gap-2 mb-2">
                  <AlertCircle className="w-4 h-4 text-orange-400" />
                  <p className="text-xs font-medium text-orange-300 uppercase tracking-wide">Churn</p>
                </div>
                <p className="text-2xl font-bold text-orange-400 mb-1">
                  {data.insights_preditivos.churn.total_clientes_risco_alto}
                </p>
                <p className="text-xs text-slate-300">Clientes em alto risco de churn</p>
              </div>
            )}
            
            {data.insights_preditivos.meta_risk && data.insights_preditivos.meta_risk.vendedores_risco_alto > 0 && (
              <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Target className="w-4 h-4 text-red-400" />
                  <p className="text-xs font-medium text-red-300 uppercase tracking-wide">Risco de Meta</p>
                </div>
                <p className="text-2xl font-bold text-red-400 mb-1">
                  {data.insights_preditivos.meta_risk.vendedores_risco_alto}
                </p>
                <p className="text-xs text-slate-300">Vendedores com alta probabilidade de não bater meta</p>
              </div>
            )}
            
            {data.insights_preditivos.oportunidades && data.insights_preditivos.oportunidades.total_clientes_potencial > 0 && (
              <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4">
                <div className="flex items-center gap-2 mb-2">
                  <TrendingUp className="w-4 h-4 text-emerald-400" />
                  <p className="text-xs font-medium text-emerald-300 uppercase tracking-wide">Oportunidades</p>
                </div>
                <p className="text-2xl font-bold text-emerald-400 mb-1">
                  {data.insights_preditivos.oportunidades.total_clientes_potencial}
                </p>
                <p className="text-xs text-slate-300">Clientes com grande potencial de crescimento</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Renderiza seções baseado em data.secoes (FASE 3) */}
      {data.secoes && data.secoes.length > 0 && (
        <>
          {data.secoes.map((secao, secaoIdx) => {
            const isExpanded = expandedSections[secaoIdx] ?? true; // Por padrão expandido
            
            // Seção: Lista de Vendedores
            if (secao.tipo === "lista_vendedores" && secao.dados && secao.dados.length > 0) {
              return (
                <div
                  key={secaoIdx}
                  className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900/95 to-slate-950/95 p-6 shadow-xl"
                >
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="rounded-xl bg-amber-500/10 p-2 border border-amber-500/20">
                        <Users className="w-5 h-5 text-amber-400" />
                      </div>
                      <h3 className="text-lg font-semibold text-slate-100">{secao.titulo}</h3>
                    </div>
                    <button
                      onClick={() => toggleSection(secaoIdx)}
                      className="text-xs text-slate-400 hover:text-slate-200 transition-colors flex items-center gap-1"
                    >
                      {isExpanded ? "Recolher" : "Expandir"}
                      <ChevronDown className={clsx("w-3 h-3 transition-transform", isExpanded && "rotate-180")} />
                    </button>
                  </div>
                  
                  {isExpanded && (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-slate-700">
                            <th className="text-left py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">#</th>
                            <th className="text-left py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">Vendedor</th>
                            <th className="text-right py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">Meta</th>
                            <th className="text-right py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">Realizado</th>
                            <th className="text-right py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">Atingimento</th>
                            <th className="text-right py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">Gap</th>
                            {secao.dados[0]?.meta_risk_score !== undefined && (
                              <th className="text-right py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">Risco</th>
                            )}
                          </tr>
                        </thead>
                        <tbody>
                          {secao.dados.map((v: any, idx: number) => {
                            const atingimento = v.atingimento_pct || 0;
                            const atingimentoPercent = Math.min(Math.max(atingimento, 0), 100);
                            
                            return (
                              <tr
                                key={idx}
                                className={clsx(
                                  "border-b border-slate-800/50 hover:bg-slate-900/50 transition-colors",
                                  v.meta_risk_flag && "bg-red-500/5"
                                )}
                              >
                                <td className="py-3 px-4 text-slate-400 font-medium">{idx + 1}</td>
                                <td className="py-3 px-4 text-slate-100 font-medium">{v.vendedor_nome}</td>
                                <td className="py-3 px-4 text-slate-300 text-right">
                                  {v.meta_total.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
                                </td>
                                <td className="py-3 px-4 text-slate-200 text-right font-medium">
                                  {v.realizado_total.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
                                </td>
                                <td className="py-3 px-4">
                                  <div className="flex items-center gap-2 justify-end">
                                    <div className="flex-1 max-w-[100px] h-2 bg-slate-800 rounded-full overflow-hidden">
                                      <div
                                        className={clsx(
                                          "h-full transition-all",
                                          atingimento >= 100
                                            ? "bg-emerald-500"
                                            : atingimento >= 80
                                            ? "bg-yellow-500"
                                            : "bg-red-500"
                                        )}
                                        style={{ width: `${atingimentoPercent}%` }}
                                      />
                                    </div>
                                    <span
                                      className={clsx(
                                        "text-right font-semibold min-w-[50px]",
                                        atingimento >= 100
                                          ? "text-emerald-400"
                                          : atingimento >= 80
                                          ? "text-yellow-400"
                                          : "text-red-400"
                                      )}
                                    >
                                      {atingimento.toFixed(1)}%
                                    </span>
                                  </div>
                                </td>
                                <td
                                  className={clsx(
                                    "py-3 px-4 text-right font-semibold",
                                    v.gap_valor >= 0 ? "text-emerald-400" : "text-red-400"
                                  )}
                                >
                                  {v.gap_valor ? (v.gap_valor >= 0 ? "+" : "") + v.gap_valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }) : "—"}
                                </td>
                                {v.meta_risk_score !== undefined && (
                                  <td className="py-3 px-4 text-right">
                                    <span
                                      className={clsx(
                                        "text-xs font-semibold px-2 py-1 rounded-full",
                                        v.meta_risk_score >= 80
                                          ? "bg-red-500/10 text-red-400 border border-red-500/20"
                                          : v.meta_risk_score >= 60
                                          ? "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20"
                                          : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                      )}
                                    >
                                      {v.meta_risk_score.toFixed(1)}
                                    </span>
                                  </td>
                                )}
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              );
            }
            
            // Seção: Lista de Clientes (com badges de churn)
            if (secao.tipo === "lista_clientes" && secao.dados && secao.dados.length > 0) {
              const isExpanded = expandedSections[secaoIdx] ?? true;
              
              return (
                <div
                  key={secaoIdx}
                  className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900/95 to-slate-950/95 p-6 shadow-xl"
                >
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="rounded-xl bg-orange-500/10 p-2 border border-orange-500/20">
                        <AlertCircle className="w-5 h-5 text-orange-400" />
                      </div>
                      <h3 className="text-lg font-semibold text-slate-100">{secao.titulo}</h3>
                    </div>
                    <button
                      onClick={() => toggleSection(secaoIdx)}
                      className="text-xs text-slate-400 hover:text-slate-200 transition-colors flex items-center gap-1"
                    >
                      {isExpanded ? "Recolher" : "Expandir"}
                      <ChevronDown className={clsx("w-3 h-3 transition-transform", isExpanded && "rotate-180")} />
                    </button>
                  </div>
                  
                  {isExpanded && (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-slate-700">
                            <th className="text-left py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">Cliente</th>
                            {secao.dados[0]?.vendedor_nome && (
                              <th className="text-left py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">Vendedor</th>
                            )}
                            <th className="text-right py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">Faturamento</th>
                            {secao.dados[0]?.variacao_pct_vs_3m !== undefined && (
                              <th className="text-right py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">Variação</th>
                            )}
                            {secao.dados[0]?.churn_score !== undefined && (
                              <th className="text-right py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">Risco Churn</th>
                            )}
                            {secao.dados[0]?.dias_desde_ultima_compra !== undefined && (
                              <th className="text-right py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">Última Compra</th>
                            )}
                          </tr>
                        </thead>
                        <tbody>
                          {secao.dados.map((c: any, idx: number) => {
                            const churnScore = c.churn_score || 0;
                            const probChurn = c.prob_churn || churnScore / 100;
                            const churnLevel = probChurn >= 0.7 ? "alto" : probChurn >= 0.4 ? "medio" : "baixo";
                            
                            return (
                              <tr
                                key={idx}
                                className={clsx(
                                  "border-b border-slate-800/50 hover:bg-slate-900/50 transition-colors",
                                  (c.churn_flag || probChurn >= 0.7) && "bg-red-500/5"
                                )}
                              >
                                <td className="py-3 px-4 text-slate-100 font-medium">{c.cliente_nome}</td>
                                {secao.dados[0]?.vendedor_nome && (
                                  <td className="py-3 px-4 text-slate-400 text-xs">{c.vendedor_nome || "—"}</td>
                                )}
                                <td className="py-3 px-4 text-slate-200 text-right font-medium">
                                  {c.faturamento_total.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
                                </td>
                                {c.variacao_pct_vs_3m !== undefined && (
                                  <td
                                    className={clsx(
                                      "py-3 px-4 text-right font-semibold",
                                      c.variacao_pct_vs_3m < -10
                                        ? "text-red-400"
                                        : c.variacao_pct_vs_3m < 0
                                        ? "text-yellow-400"
                                        : "text-emerald-400"
                                    )}
                                  >
                                    {c.variacao_pct_vs_3m >= 0 ? "+" : ""}
                                    {c.variacao_pct_vs_3m.toFixed(1)}%
                                  </td>
                                )}
                                {(c.churn_score !== undefined || c.prob_churn !== undefined) && (
                                  <td className="py-3 px-4 text-right">
                                    <span
                                      className={clsx(
                                        "text-xs font-semibold px-2 py-1 rounded-full",
                                        churnLevel === "alto"
                                          ? "bg-red-500/10 text-red-400 border border-red-500/20"
                                          : churnLevel === "medio"
                                          ? "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20"
                                          : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                      )}
                                    >
                                      {churnLevel === "alto" ? "Alto" : churnLevel === "medio" ? "Médio" : "Baixo"}
                                    </span>
                                    <p className="text-[10px] text-slate-500 mt-1">
                                      {(probChurn * 100).toFixed(0)}%
                                    </p>
                                  </td>
                                )}
                                {c.dias_desde_ultima_compra !== undefined && (
                                  <td className="py-3 px-4 text-slate-400 text-right text-xs">
                                    {c.dias_desde_ultima_compra} dias
                                  </td>
                                )}
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              );
            }
            
            // Seção: Lista de Produtos
            if (secao.tipo === "lista_produtos" && secao.dados && secao.dados.length > 0) {
              return (
                <div
                  key={secaoIdx}
                  className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900/95 to-slate-950/95 p-6 shadow-xl"
                >
                  <div className="flex items-center gap-3 mb-4">
                    <div className="rounded-xl bg-purple-500/10 p-2 border border-purple-500/20">
                      <Package className="w-5 h-5 text-purple-400" />
                    </div>
                    <h3 className="text-lg font-semibold text-slate-100">{secao.titulo}</h3>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-slate-700">
                          <th className="text-left py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">Produto</th>
                          <th className="text-right py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">Faturamento</th>
                          {secao.dados[0]?.variacao_pct_vs_3m !== undefined && (
                            <th className="text-right py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">Variação</th>
                          )}
                          {secao.dados[0]?.queda_score !== undefined && (
                            <th className="text-right py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">Queda Score</th>
                          )}
                        </tr>
                      </thead>
                      <tbody>
                        {secao.dados.map((p: any, idx: number) => (
                          <tr
                            key={idx}
                            className={clsx(
                              "border-b border-slate-800/50 hover:bg-slate-900/50 transition-colors",
                              p.queda_flag && "bg-red-500/5"
                            )}
                          >
                            <td className="py-3 px-4 text-slate-100 font-medium">{p.desc_produto || p.codigo_produto}</td>
                            <td className="py-3 px-4 text-slate-200 text-right font-medium">
                              {p.faturamento_total.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
                            </td>
                            {p.variacao_pct_vs_3m !== undefined && (
                              <td
                                className={clsx(
                                  "py-3 px-4 text-right font-semibold",
                                  p.variacao_pct_vs_3m < -10
                                    ? "text-red-400"
                                    : p.variacao_pct_vs_3m < 0
                                    ? "text-yellow-400"
                                    : "text-emerald-400"
                                )}
                              >
                                {p.variacao_pct_vs_3m >= 0 ? "+" : ""}
                                {p.variacao_pct_vs_3m.toFixed(1)}%
                              </td>
                            )}
                            {p.queda_score !== undefined && (
                              <td className="py-3 px-4 text-right">
                                <span
                                  className={clsx(
                                    "text-xs font-semibold px-2 py-1 rounded-full",
                                    p.queda_score >= 80
                                      ? "bg-red-500/10 text-red-400 border border-red-500/20"
                                      : p.queda_score >= 60
                                      ? "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20"
                                      : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                  )}
                                >
                                  {p.queda_score.toFixed(1)}
                                </span>
                              </td>
                            )}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              );
            }
            
            // Seção: Recomendações
            if (secao.tipo === "lista_recomendacoes" && secao.dados && secao.dados.length > 0) {
              return (
                <div
                  key={secaoIdx}
                  className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900/95 to-slate-950/95 p-6 shadow-xl"
                >
                  <div className="flex items-center gap-3 mb-4">
                    <div className="rounded-xl bg-purple-500/10 p-2 border border-purple-500/20">
                      <Lightbulb className="w-5 h-5 text-purple-400" />
                    </div>
                    <h3 className="text-lg font-semibold text-slate-100">{secao.titulo}</h3>
                  </div>
                  <ul className="space-y-3">
                    {secao.dados.map((rec: any, idx: number) => (
                      <li key={idx} className="flex items-start gap-3">
                        <span
                          className={clsx(
                            "mt-1 text-lg",
                            rec.prioridade === "alta"
                              ? "text-red-400"
                              : rec.prioridade === "media"
                              ? "text-yellow-400"
                              : "text-slate-400"
                          )}
                        >
                          •
                        </span>
                        <p className="text-sm text-slate-300 leading-relaxed flex-1">{rec.descricao}</p>
                      </li>
                    ))}
                  </ul>
                </div>
              );
            }
            
            // Seção: Texto (alertas, etc.)
            if (secao.tipo === "texto" && secao.dados && secao.dados.length > 0) {
              return (
                <div
                  key={secaoIdx}
                  className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900/95 to-slate-950/95 p-6 shadow-xl"
                >
                  <h3 className="text-lg font-semibold text-slate-100 mb-4">{secao.titulo}</h3>
                  <div className="text-sm text-slate-300 whitespace-pre-line">
                    {secao.dados.map((item: any, idx: number) => (
                      <p key={idx} className="mb-2 last:mb-0">
                        {item.texto || item.descricao || JSON.stringify(item)}
                      </p>
                    ))}
                  </div>
                </div>
              );
            }
            
            return null;
          })}
        </>
      )}

      {/* Tabela de Oportunidades (se houver insights preditivos) */}
      {data.insights_preditivos?.oportunidades && data.insights_preditivos.oportunidades.top_clientes && data.insights_preditivos.oportunidades.top_clientes.length > 0 && (
        <div className="rounded-2xl border border-emerald-500/30 bg-gradient-to-br from-emerald-500/10 to-emerald-900/10 p-6 shadow-xl">
          <div className="flex items-center gap-3 mb-4">
            <div className="rounded-xl bg-emerald-500/20 p-2 border border-emerald-500/40">
              <TrendingUp className="w-5 h-5 text-emerald-400" />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-slate-100">Oportunidades de Crescimento</h3>
              <p className="text-xs text-emerald-300/80 mt-0.5">Clientes com potencial de upsell/cross-sell</p>
            </div>
            <span className="rounded-full bg-emerald-500/20 border border-emerald-500/40 px-3 py-1 text-xs text-emerald-300 font-medium">
              IA Preditiva
            </span>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="text-left py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">Cliente</th>
                  <th className="text-left py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">Vendedor</th>
                  <th className="text-right py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">Score</th>
                  <th className="text-right py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">Fat. Atual</th>
                  <th className="text-right py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">Fat. Potencial</th>
                  <th className="text-right py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">Comparação</th>
                </tr>
              </thead>
              <tbody>
                {data.insights_preditivos.oportunidades.top_clientes.map((op: any, idx: number) => {
                  const percentual = op.percentual_vs_max || (op.fat_atual / op.fat_max_12m * 100);
                  
                  return (
                    <tr
                      key={idx}
                      className="border-b border-slate-800/50 hover:bg-slate-900/50 transition-colors"
                    >
                      <td className="py-3 px-4 text-slate-100 font-medium">{op.cliente_nome}</td>
                      <td className="py-3 px-4 text-slate-400 text-xs">{op.vendedor_id ? `Vendedor ${op.vendedor_id}` : "—"}</td>
                      <td className="py-3 px-4 text-right">
                        <span className="text-xs font-semibold px-2 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          {(op.score_oportunidade * 100).toFixed(0)}%
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-200 text-right font-medium">
                        {op.fat_atual.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
                      </td>
                      <td className="py-3 px-4 text-slate-300 text-right">
                        {op.fat_max_12m.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2 justify-end">
                          <div className="flex-1 max-w-[120px] h-2 bg-slate-800 rounded-full overflow-hidden">
                            <div
                              className="bg-emerald-500 h-full transition-all"
                              style={{ width: `${Math.min(percentual, 100)}%` }}
                            />
                          </div>
                          <span className="text-xs text-slate-400 min-w-[45px] text-right">
                            {percentual.toFixed(0)}%
                          </span>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Botão "Ver detalhamento" com tabela completa */}
      {data.detalhe_tabela && data.detalhe_tabela.linhas && data.detalhe_tabela.linhas.length > 0 && (
        <div className="border-t border-slate-800 pt-4">
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="flex items-center gap-2 text-xs text-slate-400 hover:text-slate-200 transition-colors"
          >
            Ver detalhamento completo
            <ChevronDown className={clsx("w-3 h-3 transition-transform", showDetails && "rotate-180")} />
          </button>
          {showDetails && (
            <div className="mt-4 rounded-xl bg-slate-950/80 p-4">
              {data.detalhe_tabela.titulo && (
                <h4 className="text-xs font-semibold text-slate-300 mb-3 uppercase tracking-wide">
                  {data.detalhe_tabela.titulo}
                </h4>
              )}
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-slate-700">
                      {data.detalhe_tabela.colunas.map((col, idx) => (
                        <th
                          key={idx}
                          className="text-left py-2 px-3 text-slate-400 font-semibold uppercase tracking-wide"
                        >
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.detalhe_tabela.linhas.map((linha, linhaIdx) => (
                      <tr
                        key={linhaIdx}
                        className="border-b border-slate-800/50 hover:bg-slate-900/50 transition-colors"
                      >
                        {linha.map((celula: any, celulaIdx: number) => (
                          <td key={celulaIdx} className="py-2 px-3 text-slate-300">
                            {typeof celula === "number"
                              ? celula.toLocaleString("pt-BR", {
                                  style: celula > 1000 ? "currency" : "decimal",
                                  currency: "BRL",
                                })
                              : celula || "—"}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Contexto de debug (sempre colapsado por padrão) */}
      {data.contexto_debug && (
        <details className="rounded-2xl border border-slate-800 bg-slate-900/50 p-4" open={false}>
          <summary className="text-xs text-slate-400 hover:text-slate-200 cursor-pointer font-medium flex items-center gap-2">
            <span>⚙️</span>
            Ver contexto técnico (debug)
          </summary>
          <div className="mt-4 space-y-2 text-xs text-slate-400">
            <p>
              <span className="font-semibold">Intent:</span> {data.contexto_debug.intent}
            </p>
            <p>
              <span className="font-semibold">Fonte de dados:</span> {data.contexto_debug.fonte_dados}
            </p>
            {data.contexto_debug.mes_ano_resolvido && (
              <p>
                <span className="font-semibold">Mês/ano resolvido:</span> {data.contexto_debug.mes_ano_resolvido}
              </p>
            )}
            {data.contexto_debug.total_registros !== undefined && (
              <p>
                <span className="font-semibold">Total de registros:</span> {data.contexto_debug.total_registros}
              </p>
            )}
            {data.contexto_debug.tempo_processamento_ms !== undefined && (
              <p>
                <span className="font-semibold">Tempo de processamento:</span> {data.contexto_debug.tempo_processamento_ms.toFixed(1)}ms
              </p>
            )}
            <details className="mt-2" open={false}>
              <summary className="cursor-pointer text-slate-500 hover:text-slate-300">
                Ver entidades e JSON completo
              </summary>
              <pre className="mt-2 max-h-64 overflow-auto rounded-lg bg-slate-950/80 p-3 text-[10px] text-slate-400 border border-slate-800">
                {JSON.stringify(data.contexto_debug, null, 2)}
              </pre>
            </details>
          </div>
        </details>
      )}

      {/* Compatibilidade: Renderiza formato antigo se não houver secoes */}
      {(!data.secoes || data.secoes.length === 0) && (
        <>
          {/* Card 2: KPIs do Mês (formato antigo) */}
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

        </>
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
