"use client";

import React, { useMemo } from "react";
import { ChevronDown, ChevronUp, Sparkles, TrendingUp, AlertCircle, Target, Lightbulb, BarChart3, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";

export type DipamAnswerCardProps = {
  pergunta: string;
  intent: string;
  confianca: number;
  respostaMarkdown: string; // conteúdo de result.resposta
  contexto?: Record<string, any>;
  onToggleDetalhes?: () => void;
  showDetalhes?: boolean;
};

/**
 * Renderiza Markdown simples para o formato estruturado do DIPAM COPILOT™
 * Versão premium com melhor hierarquia visual e seções destacadas
 */
function renderMarkdown(markdown: string) {
  if (!markdown || typeof markdown !== 'string') {
    return [];
  }
  const lines = markdown.split("\n");
  const elements: React.ReactNode[] = [];
  let currentParagraph: string[] = [];
  let inList = false;
  let listItems: string[] = [];

  const flushParagraph = () => {
    if (currentParagraph.length > 0) {
      const text = currentParagraph.join(" ").trim();
      if (text) {
        elements.push(
          <p key={`p-${elements.length}`} className="text-slate-200/90 leading-relaxed mb-5 text-[15px]">
            {text}
          </p>
        );
      }
      currentParagraph = [];
    }
  };

  const flushList = () => {
    if (listItems.length > 0) {
      elements.push(
        <ul key={`ul-${elements.length}`} className="space-y-3.5 mb-7 ml-1">
          {listItems.map((item, idx) => (
            <li key={idx} className="flex items-start gap-4 text-slate-200/90 group/item">
              <span className="mt-2 flex-shrink-0 h-1.5 w-1.5 rounded-full bg-gradient-to-br from-blue-400 to-purple-400 shadow-sm shadow-blue-400/50 group-hover/item:scale-125 transition-transform" />
              <span className="leading-relaxed text-[15px] flex-1">{item.trim()}</span>
            </li>
          ))}
        </ul>
      );
      listItems = [];
    }
    inList = false;
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    // Detecta headings (## ou ###)
    const headingMatch = line.match(/^(##+)\s+(.+)$/);
    if (headingMatch) {
      flushParagraph();
      flushList();
      
      const level = headingMatch[1].length;
      const text = headingMatch[2].trim();
      
      // Renderiza heading com ícone baseado no texto e cores premium
      let icon: React.ReactNode = null;
      let iconColor = "text-blue-400";
      let bgGradient = "from-blue-500/10 to-blue-600/5";
      const headingLower = text.toLowerCase();
      
      if (headingLower.includes("resumo executivo") || headingLower.includes("resumo")) {
        icon = <Target className="h-5 w-5" />;
        iconColor = "text-blue-400";
        bgGradient = "from-blue-500/10 via-blue-600/5 to-indigo-500/5";
      } else if (headingLower.includes("número") || headingLower.includes("números") || headingLower.includes("números-chave")) {
        icon = <BarChart3 className="h-5 w-5" />;
        iconColor = "text-emerald-400";
        bgGradient = "from-emerald-500/10 via-green-600/5 to-teal-500/5";
      } else if (headingLower.includes("insight") || headingLower.includes("insights") || headingLower.includes("relevantes")) {
        icon = <Lightbulb className="h-5 w-5" />;
        iconColor = "text-amber-400";
        bgGradient = "from-amber-500/10 via-yellow-600/5 to-orange-500/5";
      } else if (headingLower.includes("ação") || headingLower.includes("ações") || headingLower.includes("recomenda") || headingLower.includes("recomendadas")) {
        icon = <Zap className="h-5 w-5" />;
        iconColor = "text-orange-400";
        bgGradient = "from-orange-500/10 via-red-600/5 to-rose-500/5";
      } else if (headingLower.includes("observa") || headingLower.includes("dados")) {
        icon = <AlertCircle className="h-5 w-5" />;
        iconColor = "text-slate-400";
        bgGradient = "from-slate-500/10 to-slate-600/5";
      }
      
      if (level === 2) {
        // Seção principal (##) - destaque máximo
        elements.push(
          <div 
            key={`h2-${elements.length}`} 
            className={`mt-10 first:mt-0 mb-6 pt-5 pb-4 px-5 rounded-xl bg-gradient-to-r ${bgGradient} border-l-4 ${
              iconColor.includes("blue") ? "border-blue-400/60" :
              iconColor.includes("emerald") ? "border-emerald-400/60" :
              iconColor.includes("amber") ? "border-amber-400/60" :
              iconColor.includes("orange") ? "border-orange-400/60" :
              "border-slate-400/60"
            } shadow-lg shadow-black/20 backdrop-blur-sm`}
          >
            <h2 className={`text-2xl font-bold text-slate-50 flex items-center gap-3 tracking-tight`}>
              <span className={`${iconColor} drop-shadow-sm`}>
                {icon}
              </span>
              <span className="bg-gradient-to-r from-slate-50 to-slate-200 bg-clip-text text-transparent">
                {text}
              </span>
            </h2>
          </div>
        );
      } else if (level === 3) {
        // Subseção (###) - destaque médio
        elements.push(
          <div key={`h3-${elements.length}`} className="mt-8 mb-4">
            <h3 className={`text-lg font-semibold text-slate-100 flex items-center gap-2.5 mb-3`}>
              <span className={iconColor}>
                {icon}
              </span>
              {text}
            </h3>
            <div className="h-px w-20 bg-gradient-to-r from-slate-600/60 to-transparent mt-2" />
          </div>
        );
      }
      continue;
    }

    // Detecta list items (- ou *)
    if (line.match(/^[-*]\s+/)) {
      if (!inList) {
        flushParagraph();
        inList = true;
      }
      const itemText = line.replace(/^[-*]\s+/, "");
      listItems.push(itemText);
      continue;
    }

    // Se estiver em lista e a linha não é item, fecha a lista
    if (inList && line) {
      flushList();
    }

    // Parágrafo normal
    if (line) {
      currentParagraph.push(line);
    } else {
      flushParagraph();
    }
  }

  flushParagraph();
  flushList();

  return elements;
}

/**
 * Componente premium de card de resposta do DIPAM COPILOT™
 * Visual inspirado em produtos de BI + IA de ponta
 */
export function DipamAnswerCard({
  pergunta,
  intent,
  confianca,
  respostaMarkdown,
  contexto,
  onToggleDetalhes,
  showDetalhes = false,
}: DipamAnswerCardProps) {
  // Garantir valores padrão para evitar erros
  const safeMarkdown = respostaMarkdown || "";
  const safeConfianca = typeof confianca === 'number' ? confianca : 0.5;
  const safeIntent = intent || "outros";
  const safePergunta = pergunta || "Pergunta não disponível";
  
  const renderedContent = useMemo(() => renderMarkdown(safeMarkdown), [safeMarkdown]);

  // Calcula cor do badge de confiança com gradientes premium
  const getConfidenceColor = (conf: number) => {
    if (conf >= 0.85) return "bg-gradient-to-r from-emerald-500/20 to-green-600/10 text-emerald-300 border-emerald-500/40 shadow-sm shadow-emerald-500/10";
    if (conf >= 0.70) return "bg-gradient-to-r from-amber-500/20 to-yellow-600/10 text-amber-300 border-amber-500/40 shadow-sm shadow-amber-500/10";
    if (conf >= 0.50) return "bg-gradient-to-r from-orange-500/20 to-red-600/10 text-orange-300 border-orange-500/40 shadow-sm shadow-orange-500/10";
    return "bg-gradient-to-r from-red-500/20 to-rose-600/10 text-red-300 border-red-500/40 shadow-sm shadow-red-500/10";
  };

  // Formata o nome da intent de forma mais amigável
  const formatIntent = (intentStr: string) => {
    const intentMap: Record<string, string> = {
      consulta_meta: "Consulta de Meta",
      clientes_churn_produto: "Churn de Clientes",
      clientes_oportunidades: "Oportunidades",
      desempenho_supervisores: "Desempenho",
      oportunidades_diretoria: "Visão Executiva",
      clientes_risco_churn: "Risco de Churn",
      produtos_baixa_venda: "Análise de Produtos",
    };
    return intentMap[intentStr] || intentStr.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
  };

  return (
    <div className="group relative rounded-3xl border border-slate-700/80 bg-gradient-to-br from-slate-900/95 via-slate-900/90 to-slate-800/85 p-8 sm:p-10 shadow-2xl shadow-blue-900/25 hover:shadow-2xl hover:shadow-blue-900/40 transition-all duration-500 backdrop-blur-xl">
      {/* Badge de IA no canto superior direito - Premium */}
      <div className="absolute top-5 right-5 flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-gradient-to-r from-blue-500/15 to-purple-500/10 border border-blue-500/30 backdrop-blur-md shadow-lg shadow-blue-500/20">
        <Sparkles className="h-3.5 w-3.5 text-blue-400 animate-pulse" />
        <span className="text-xs font-bold text-blue-300 tracking-wider uppercase">IA</span>
      </div>

      {/* Header com pergunta - Hierarquia visual premium */}
      <div className="pr-24 mb-8">
        <div className="flex items-start gap-4 mb-5">
          <div className="flex-shrink-0 mt-0.5">
            <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-blue-500/25 via-purple-500/20 to-indigo-500/25 border border-blue-400/40 flex items-center justify-center shadow-lg shadow-blue-500/20 backdrop-blur-sm">
              <Sparkles className="h-6 w-6 text-blue-300" />
            </div>
          </div>
          <div className="flex-1 min-w-0 pt-1">
            <p className="text-[10px] font-bold uppercase tracking-[0.35em] text-blue-400/80 mb-2 drop-shadow-sm">
              DIPAM COPILOT™
            </p>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-50 leading-tight tracking-tight bg-gradient-to-r from-slate-50 via-slate-100 to-slate-200 bg-clip-text text-transparent">
              {safePergunta}
            </h1>
          </div>
        </div>

        {/* Chips de Intent e Confiança - Design premium */}
        <div className="flex flex-wrap gap-3">
          <span className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-slate-800/70 to-slate-900/70 border border-slate-700/60 text-xs font-semibold text-slate-200 shadow-md backdrop-blur-sm">
            <Target className="h-3.5 w-3.5 text-blue-400" />
            <span className="tracking-wide">{formatIntent(safeIntent)}</span>
          </span>
          <span
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl border text-xs font-bold backdrop-blur-sm ${getConfidenceColor(safeConfianca)}`}
          >
            <TrendingUp className="h-3.5 w-3.5" />
            <span className="tracking-wide">{(safeConfianca * 100).toFixed(1)}% confiança</span>
          </span>
        </div>
      </div>

      {/* Corpo da resposta com Markdown renderizado - Espaçamento premium */}
      <div className="prose prose-invert prose-slate max-w-none space-y-8">
        <div className="space-y-1 text-left">
          {renderedContent.length > 0 ? (
            renderedContent
          ) : (
            // Fallback: renderiza texto simples se não houver Markdown estruturado
            <div className="text-slate-200/90 leading-relaxed whitespace-pre-wrap text-[15px] space-y-4">
              {safeMarkdown}
            </div>
          )}
        </div>
      </div>

      {/* Botão para ver detalhes técnicos (contexto) - Design premium */}
      {contexto && Object.keys(contexto).length > 0 && onToggleDetalhes && (
        <div className="mt-10 pt-8 border-t border-slate-700/60">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            className="w-full gap-2.5 text-xs font-semibold hover:bg-slate-800/80 transition-all duration-200 hover:scale-[1.02] border border-slate-700/60 backdrop-blur-sm shadow-md"
            onClick={onToggleDetalhes}
          >
            {showDetalhes ? (
              <>
                <ChevronUp className="h-4 w-4" />
                <span className="tracking-wide">Ocultar detalhes de dados</span>
              </>
            ) : (
              <>
                <ChevronDown className="h-4 w-4" />
                <span className="tracking-wide">Ver detalhes de dados</span>
              </>
            )}
          </Button>

          {showDetalhes && (
            <div className="mt-5 rounded-xl border border-slate-700/60 bg-slate-950/90 p-5 backdrop-blur-sm shadow-inner">
              <pre className="text-xs text-slate-300 overflow-x-auto font-mono leading-relaxed">
                {JSON.stringify(contexto, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Efeito de brilho sutil no hover - Premium touch */}
      <div className="absolute inset-0 rounded-3xl bg-gradient-to-br from-blue-500/0 via-purple-500/0 to-indigo-500/0 group-hover:from-blue-500/8 group-hover:via-purple-500/5 group-hover:to-indigo-500/8 transition-all duration-500 pointer-events-none" />
      
      {/* Borda animada sutil */}
      <div className="absolute inset-0 rounded-3xl border border-slate-600/20 group-hover:border-blue-500/30 transition-colors duration-500 pointer-events-none" />
    </div>
  );
}


