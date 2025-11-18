import React, { useState, useMemo } from "react";
import { TrendingUp, TrendingDown, Minus, Target, Users, AlertCircle, Lightbulb, Package, ChevronDown, Brain, Zap, DollarSign, Percent } from "lucide-react";
import { CopilotStructuredResponse } from "@/types/agent";
import { clsx } from "clsx";
import BigNumberCard from "./BigNumberCard";
import { InsightsBlock } from "./InsightsBlock";
import { DataTable } from "./DataTable";
import { ExecutiveSectionCard } from "./ExecutiveSectionCard";
import { parseMarkdownExecutivo } from "./markdownParser";
import { FileText } from "lucide-react";

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
  // Prioridade: respostaMarkdown completo se disponível
  const respostaMarkdown = data.respostaMarkdown;
  
  // Extrai KPIs das seções, insights preditivos e data.kpis
  const kpis = useMemo(() => {
    const kpisList: Array<{ label: string; value: string | number; icon: React.ReactNode; color: string; trend?: "up" | "down" | "neutral"; variation?: string }> = [];
    
    // PRIMEIRO: Se há KPIs já extraídos no structured.kpis, usa eles
    if (data.kpis && Array.isArray(data.kpis) && data.kpis.length > 0) {
      for (const kpi of data.kpis) {
        kpisList.push({
          label: kpi.label || "KPI",
          value: kpi.value || 0,
          icon: kpi.icon ? <span>{kpi.icon}</span> : <DollarSign className="w-4 h-4" />,
          color: kpi.color === "positive" ? "text-emerald-400" : kpi.color === "negative" ? "text-red-400" : "text-slate-100",
          trend: kpi.color === "positive" ? "up" : kpi.color === "negative" ? "down" : "neutral",
          variation: kpi.variation
        });
      }
      return kpisList; // Retorna imediatamente se já tem KPIs extraídos
    }
    
    // SEGUNDO: Busca dados de vendedores para calcular KPIs
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
    
    // TERCEIRO: Tenta extrair KPIs de tabela_metas se disponível
    const metasSecao = data.secoes?.find(s => s.tipo === "tabela_metas");
    if (metasSecao?.dados && metasSecao.dados.length > 0 && kpisList.length === 0) {
      const dados = metasSecao.dados as any[];
      const metaTotal = dados.reduce((sum, item) => sum + (item.meta_total || item.meta || 0), 0);
      const realizadoTotal = dados.reduce((sum, item) => sum + (item.realizado_total || item.realizado || 0), 0);
      const atingimentoMedio = metaTotal > 0 ? (realizadoTotal / metaTotal) * 100 : 0;
      
      kpisList.push({
        label: "Meta Total",
        value: metaTotal.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }),
        icon: <Target className="w-4 h-4" />,
        color: "text-slate-100",
        trend: "neutral"
      });
      
      kpisList.push({
        label: "Realizado Total",
        value: realizadoTotal.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }),
        icon: <DollarSign className="w-4 h-4" />,
        color: realizadoTotal >= metaTotal ? "text-emerald-400" : "text-slate-100",
        trend: realizadoTotal >= metaTotal ? "up" : "neutral"
      });
      
      kpisList.push({
        label: "Atingimento Médio",
        value: `${atingimentoMedio.toFixed(1)}%`,
        icon: <Percent className="w-4 h-4" />,
        color: atingimentoMedio >= 100 ? "text-emerald-400" : atingimentoMedio >= 95 ? "text-yellow-400" : "text-red-400",
        trend: atingimentoMedio >= 100 ? "up" : atingimentoMedio >= 95 ? "neutral" : "down",
        variation: atingimentoMedio < 100 ? `${(atingimentoMedio - 100).toFixed(1)}%` : `+${(atingimentoMedio - 100).toFixed(1)}%`
      });
    }
    
    return kpisList;
  }, [data.secoes, data.insights_preditivos, data.kpis]);
  
  const toggleSection = (index: number) => {
    setExpandedSections(prev => ({ ...prev, [index]: !prev[index] }));
  };
  
  // Helper para verificar se deve mostrar insights (não mostrar se for apenas mensagem de erro)
  const insightsText = data.insightsRecomendacoes?.join(' ')?.trim() ?? '';
  const deveMostrarInsights =
    insightsText.length > 0 &&
    !/erro no processamento avançado da resposta/i.test(insightsText);
  
  // Parse markdown executivo para extrair seções estruturadas
  const parsedMarkdown = useMemo(() => {
    if (respostaMarkdown) {
      return parseMarkdownExecutivo(respostaMarkdown);
    }
    return null;
  }, [respostaMarkdown]);
  
  // Prepara KPIs para BigNumberCard (combinando kpis existentes + parsedMarkdown)
  const bigNumberKPIs = useMemo(() => {
    const kpisList: Array<{ label: string; value: string | number; icon: React.ReactNode; trend?: "up" | "down" | "neutral"; color?: "blue" | "green" | "red" | "yellow" | "orange" }> = [];
    
    // Usa KPIs já calculados
    if (kpis.length > 0) {
      for (const kpi of kpis) {
        let color: "blue" | "green" | "red" | "yellow" | "orange" = "blue";
        if (kpi.color.includes("emerald")) color = "green";
        else if (kpi.color.includes("yellow")) color = "yellow";
        else if (kpi.color.includes("red") || kpi.color.includes("orange")) color = "red";
        
        kpisList.push({
          label: kpi.label,
          value: kpi.value,
          icon: kpi.icon,
          trend: kpi.trend,
          color,
        });
      }
    }
    
    // Adiciona KPIs do markdown parseado se disponível
    if (parsedMarkdown?.kpis && parsedMarkdown.kpis.length > 0) {
      for (const kpi of parsedMarkdown.kpis) {
        kpisList.push({
          label: kpi.label,
          value: kpi.value,
          icon: <span>{kpi.icon || "📊"}</span>,
          color: "blue",
        });
      }
    }
    
    return kpisList;
  }, [kpis, parsedMarkdown]);
  
  // Prepara dados da tabela (top 10 alvos ou tabela principal)
  const tableData = useMemo(() => {
    // Tenta usar topAlvos do markdown parseado
    if (parsedMarkdown?.topAlvos && parsedMarkdown.topAlvos.length > 0) {
      return parsedMarkdown.topAlvos;
    }
    
    // Fallback: usa tabela_principal se disponível (type assertion segura)
    const dataAny = data as any;
    const tabelaPrincipal = dataAny.tabela_principal || dataAny.tabelaPrincipal;
    if (tabelaPrincipal && Array.isArray(tabelaPrincipal) && tabelaPrincipal.length > 0) {
      return tabelaPrincipal;
    }
    
    // Fallback: tenta extrair de seções
    const tabelaSecao = data.secoes?.find(s => s.tipo === "tabela");
    if (tabelaSecao?.dados && Array.isArray(tabelaSecao.dados)) {
      return tabelaSecao.dados;
    }
    
    return [];
  }, [parsedMarkdown, data]);
  
  // Type assertion segura para acessar propriedades opcionais
  const dataAny = data as any;
  
  return (
    <div className="max-w-[1200px] mx-auto px-4 py-6">
      {/* 1. Título da Consulta (se disponível) */}
      {dataAny.intent && (
        <div className="flex items-center gap-3 mb-8">
          <Target className="w-6 h-6 text-blue-400" />
          <h1 className="text-2xl font-bold text-white">
            {dataAny.intent_label || dataAny.intent}
          </h1>
        </div>
      )}
      
      {/* 2. Resumo Executivo (PRIMEIRO) */}
      {parsedMarkdown?.resumoExecutivo && (
        <div className="mb-10">
          <ExecutiveSectionCard
            title="Resumo Executivo"
            icon={<FileText className="w-5 h-5" />}
          >
            <p className="text-sm opacity-90 leading-relaxed whitespace-pre-line">
              {parsedMarkdown.resumoExecutivo}
            </p>
          </ExecutiveSectionCard>
        </div>
      )}
      
      {/* 3. Big Numbers Cards (KPIs) */}
      {bigNumberKPIs.length > 0 && (
        <div className="mb-10">
          <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {bigNumberKPIs.map((kpi, idx) => (
              <BigNumberCard
                key={idx}
                label={kpi.label}
                value={kpi.value}
                icon={kpi.icon}
                trend={kpi.trend}
                color={kpi.color}
              />
            ))}
          </div>
        </div>
      )}
      
      {/* 4. Insights Blocks (sempre empilhados verticalmente) */}
      {(parsedMarkdown?.principaisAchados?.length > 0 || 
        parsedMarkdown?.implicacoesComerciais?.length > 0 || 
        parsedMarkdown?.planoAcao?.length > 0) && (
        <div className="mb-10">
          <div className="mt-8 flex flex-col gap-6">
            {parsedMarkdown.principaisAchados && parsedMarkdown.principaisAchados.length > 0 && (
              <InsightsBlock
                title="Principais Achados"
                items={parsedMarkdown.principaisAchados}
                icon="🔍"
                color="blue"
              />
            )}
            {parsedMarkdown.implicacoesComerciais && parsedMarkdown.implicacoesComerciais.length > 0 && (
              <InsightsBlock
                title="Implicações Comerciais"
                items={parsedMarkdown.implicacoesComerciais}
                icon="⚠️"
                color="orange"
              />
            )}
            {parsedMarkdown.planoAcao && parsedMarkdown.planoAcao.length > 0 && (
              <InsightsBlock
                title="Plano de Ação Imediato"
                items={parsedMarkdown.planoAcao}
                icon="🚀"
                color="green"
              />
            )}
          </div>
        </div>
      )}
      
      {/* 5. Alvos Prioritários (lista E tabela se disponível) */}
      {parsedMarkdown?.alvosPrioritarios && parsedMarkdown.alvosPrioritarios.length > 0 && (
        <div className="mb-10">
          <ExecutiveSectionCard
            title="Alvos Prioritários (TOP 10)"
            icon={<Target className="w-5 h-5" />}
          >
            <ul className="space-y-2">
              {parsedMarkdown.alvosPrioritarios.map((alvo, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm opacity-90">
                  <span className="text-purple-400 mt-1 flex-shrink-0">•</span>
                  <span className="flex-1">{alvo}</span>
                </li>
              ))}
            </ul>
          </ExecutiveSectionCard>
          
          {/* Tabela de alvos se disponível */}
          {parsedMarkdown.topAlvos && parsedMarkdown.topAlvos.length > 0 && (
            <div className="mt-6">
              {/* 
                Nota: A coluna "Rota" está vazia porque o backend ainda não envia essa informação
                em topAlvos. Quando o DW expuser a dimensão de rota, basta preencher aqui.
                O parser (markdownParser.ts) preserva todos os campos que vêm do backend.
              */}
              <DataTable
                rows={parsedMarkdown.topAlvos}
                title="Alvos Prioritários — Detalhamento"
                highlightFirstColumn={true}
              />
            </div>
          )}
        </div>
      )}
      
      {/* 6. Tabela de dados analíticos (se não for alvos prioritários) */}
      {tableData.length > 0 && (!parsedMarkdown?.topAlvos || parsedMarkdown.topAlvos.length === 0) && (
        <div className="mb-10">
          <DataTable
            rows={tableData}
            title="Dados Analíticos"
            highlightFirstColumn={true}
          />
        </div>
      )}
      
      {/* Fallback: Markdown completo se não foi parseado */}
      {respostaMarkdown && !parsedMarkdown && (
        <div className="rounded-2xl border border-[#1D2532] bg-[#0B0F17] p-6 shadow-xl">
          <div className="prose prose-invert max-w-none whitespace-pre-line space-y-6">
            <div className="text-sm leading-relaxed text-slate-300">
              {respostaMarkdown.split("\n").map((line, idx) => {
                // Renderiza headings
                if (line.match(/^##+\s+/)) {
                  const level = line.match(/^(##+)/)?.[1].length || 2;
                  const text = line.replace(/^##+\s+/, "").trim();
                  const HeadingTag = `h${Math.min(level, 6)}` as keyof JSX.IntrinsicElements;
                  return (
                    <HeadingTag
                      key={idx}
                      className={`${level === 2 ? 'text-2xl' : level === 3 ? 'text-xl' : 'text-lg'} font-semibold text-slate-100 mt-8 mb-4 first:mt-0`}
                    >
                      {text}
                    </HeadingTag>
                  );
                }
                // Renderiza listas
                if (line.match(/^[-*]\s+/)) {
                  const text = line.replace(/^[-*]\s+/, "").trim();
                  return (
                    <div key={idx} className="flex items-start gap-2 mb-2">
                      <span className="text-blue-400 mt-1">•</span>
                      <span>{text}</span>
                    </div>
                  );
                }
                // Renderiza parágrafos
                if (line.trim()) {
                  return (
                    <p key={idx} className="mb-3 last:mb-0">
                      {line.trim()}
                    </p>
                  );
                }
                return <br key={idx} />;
              })}
            </div>
          </div>
        </div>
      )}
      
      {/* Fallback: Resumo Executivo simples se não houver markdown */}
      {!respostaMarkdown && resumoExecutivo && (
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
      
      {/* 6. Insights e Recomendações (se houver) */}
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
            
            // Seção: Tabela de Metas (por mês ou agregada)
            if (secao.tipo === "tabela_metas" && secao.dados && secao.dados.length > 0) {
              const isExpanded = expandedSections[secaoIdx] ?? true;
              
              return (
                <div
                  key={secaoIdx}
                  className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900/95 to-slate-950/95 p-6 shadow-xl"
                >
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="rounded-xl bg-blue-500/10 p-2 border border-blue-500/20">
                        <Target className="w-5 h-5 text-blue-400" />
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
                            {secao.dados[0]?.mes_ano && (
                              <th className="text-left py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">Mês</th>
                            )}
                            {secao.dados[0]?.mes && (
                              <th className="text-left py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">Mês</th>
                            )}
                            <th className="text-right py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">Meta Total</th>
                            <th className="text-right py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">Realizado Total</th>
                            <th className="text-right py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">Gap</th>
                            <th className="text-right py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide">Atingimento</th>
                          </tr>
                        </thead>
                        <tbody>
                          {secao.dados.map((item: any, idx: number) => {
                            const meta = item.meta_total || item.meta || 0;
                            const realizado = item.realizado_total || item.realizado || 0;
                            const gap = realizado - meta;
                            const atingimento = meta > 0 ? (realizado / meta) * 100 : 0;
                            const mes_ano = item.mes_ano || item.mes || `Linha ${idx + 1}`;
                            
                            return (
                              <tr
                                key={idx}
                                className="border-b border-slate-800/50 hover:bg-slate-900/50 transition-colors"
                              >
                                {(secao.dados[0]?.mes_ano || secao.dados[0]?.mes) && (
                                  <td className="py-3 px-4 text-slate-100 font-medium">{mes_ano}</td>
                                )}
                                <td className="py-3 px-4 text-slate-300 text-right">
                                  {meta.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
                                </td>
                                <td className="py-3 px-4 text-slate-200 text-right font-medium">
                                  {realizado.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
                                </td>
                                <td
                                  className={clsx(
                                    "py-3 px-4 text-right font-semibold",
                                    gap >= 0 ? "text-emerald-400" : "text-red-400"
                                  )}
                                >
                                  {gap >= 0 ? "+" : ""}
                                  {gap.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
                                </td>
                                <td className="py-3 px-4">
                                  <div className="flex items-center gap-2 justify-end">
                                    <div className="flex-1 max-w-[100px] h-2 bg-slate-800 rounded-full overflow-hidden">
                                      <div
                                        className={clsx(
                                          "h-full transition-all",
                                          atingimento >= 100
                                            ? "bg-emerald-500"
                                            : atingimento >= 95
                                            ? "bg-yellow-500"
                                            : "bg-red-500"
                                        )}
                                        style={{ width: `${Math.min(atingimento, 100)}%` }}
                                      />
                                    </div>
                                    <span
                                      className={clsx(
                                        "text-right font-semibold min-w-[50px]",
                                        atingimento >= 100
                                          ? "text-emerald-400"
                                          : atingimento >= 95
                                          ? "text-yellow-400"
                                          : "text-red-400"
                                      )}
                                    >
                                      {atingimento.toFixed(1)}%
                                    </span>
                                  </div>
                                </td>
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
            
            // Seção: Tabela Detalhada (genérica)
            if (secao.tipo === "tabela_detalhada" && secao.dados && secao.dados.length > 0) {
              const isExpanded = expandedSections[secaoIdx] ?? true;
              
              return (
                <div
                  key={secaoIdx}
                  className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900/95 to-slate-950/95 p-6 shadow-xl"
                >
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="rounded-xl bg-indigo-500/10 p-2 border border-indigo-500/20">
                        <Package className="w-5 h-5 text-indigo-400" />
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
                    <div className="w-full bg-[#0B0F17] rounded-xl border border-[#1D2532] overflow-hidden">
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b border-slate-700">
                              {Object.keys(secao.dados[0] || {}).map((key, idx) => (
                                <th
                                  key={idx}
                                  className="text-left py-3 px-4 text-slate-400 font-semibold text-xs uppercase tracking-wide"
                                >
                                  {key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {secao.dados.map((item: any, idx: number) => (
                              <tr
                                key={idx}
                                className="border-b border-slate-800/50 hover:bg-[#151B26] transition-all"
                              >
                              {Object.values(item).map((val: any, cellIdx: number) => (
                                <td key={cellIdx} className="py-3 px-4 text-slate-300">
                                  {typeof val === "number"
                                    ? val.toString() // ❌ Não formata automaticamente números como moeda - mantém ID numérico cru
                                    : val || "—"}
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
              <div className="w-full bg-[#0B0F17] rounded-xl border border-[#1D2532] overflow-hidden">
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
                          className="border-b border-slate-800/50 hover:bg-[#151B26] transition-all"
                        >
                        {linha.map((celula: any, celulaIdx: number) => (
                          <td key={celulaIdx} className="py-2 px-3 text-slate-300">
                            {typeof celula === "number"
                              ? celula.toString() // ❌ Não formata automaticamente números como moeda - mantém ID numérico cru
                              : celula || "—"}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
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

      {/* KPIs do formato antigo (se disponível e não foram extraídos das seções) */}
      {data.kpis && data.kpis.length > 0 && kpis.length === 0 && (
        <div className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900/95 to-slate-950/95 p-6 shadow-xl">
          <div className="flex items-center gap-3 mb-4">
            <div className="rounded-xl bg-emerald-500/10 p-2 border border-emerald-500/20">
              <TrendingUp className="w-5 h-5 text-emerald-400" />
            </div>
            <h3 className="text-lg font-semibold text-slate-100">KPIs do Mês</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {data.kpis.map((kpi: any, idx: number) => (
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
                        (typeof kpi.variation === "string" && (kpi.variation.startsWith("+") || parseFloat(kpi.variation) > 0))
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                          : (typeof kpi.variation === "string" && (kpi.variation.startsWith("-") || parseFloat(kpi.variation) < 0))
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

      {/* Compatibilidade: Renderiza formato antigo se não houver secoes */}
      {(!data.secoes || data.secoes.length === 0) && (
        <>
          {/* Card 2: KPIs do Mês (formato antigo) - já renderizado acima se houver */}
          {data.kpis && data.kpis.length > 0 && kpis.length > 0 && (
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

      {/* Card 5: Insights e Recomendações - Só renderiza se não for apenas mensagem de erro */}
      {deveMostrarInsights && data.insightsRecomendacoes && data.insightsRecomendacoes.length > 0 && (
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
