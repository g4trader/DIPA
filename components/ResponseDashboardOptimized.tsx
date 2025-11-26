"use client";

import React, { useMemo, useEffect, useRef, useState } from "react";
import { CopilotStructuredResponse } from "@/types/agent";
import { LayoutResposta } from "./dashboard/LayoutResposta";
import { BigNumber } from "./dashboard/BigNumber";
import { ResumoExecutivo } from "./dashboard/ResumoExecutivo";
import { DataTable } from "./DataTable";
import { DashboardSkeleton } from "./skeletons/DashboardSkeleton";
import { useDashboardLoading } from "@/hooks/useDashboardLoading";
import { trackBigNumberRender, trackTableRender } from "@/lib/telemetry";
import { InsightsBlock } from "./InsightsBlock";
import { formatNumberBR } from "@/lib/formatters";

type Props = {
  data: CopilotStructuredResponse;
  question?: string;
  isLoading?: boolean;
};

/**
 * ResponseDashboardOptimized - Versão otimizada do dashboard
 * 
 * Usa LayoutResposta com ordem fixa:
 * 1. Big Number
 * 2. Resumo Executivo
 * 3. Tabela (20 registros/página)
 * 4. Blocos complementares
 */
export const ResponseDashboardOptimized: React.FC<Props> = ({
  data,
  question,
  isLoading = false,
}) => {
  const loadingState = useDashboardLoading();
  const bigNumberRef = useRef<HTMLDivElement>(null);
  const tableRef = useRef<HTMLDivElement>(null);
  const bigNumberRendered = useRef(false);
  const tableRendered = useRef(false);

  // ✅ T3: Detecta se é Q1 (clientes sem compra)
  const isQ1 = useMemo(() => {
    const dataAny = data as any;
    return (
      dataAny.intent === "clientes_sem_compra" ||
      dataAny.intent_label?.toLowerCase().includes("clientes sem compra") ||
      dataAny.jsonTecnico?.intent === "clientes_sem_compra" ||
      dataAny.jsonTecnico?.contexto?.intent === "clientes_sem_compra"
    );
  }, [data]);

  // Extrai tabela principal do jsonTecnico
  const tabelaPrincipal = useMemo(() => {
    const dataAny = data as any;
    const jsonTecnico = dataAny.jsonTecnico || dataAny.structured?.jsonTecnico;
    
    if (!jsonTecnico) return null;
    
    const tabela = jsonTecnico.tabela_principal || jsonTecnico.tabelaPrincipal;
    if (!tabela || !Array.isArray(tabela) || tabela.length === 0) return null;
    
    // Pega primeira tabela
    const primeiraTabela = Array.isArray(tabela) ? tabela[0] : tabela;
    if (!primeiraTabela.colunas || !primeiraTabela.linhas) return null;
    
    // Converte para formato DataTable
    let rows = primeiraTabela.linhas.map((linha: any[]) => {
      const row: Record<string, any> = {};
      primeiraTabela.colunas.forEach((col: string, idx: number) => {
        row[col] = linha[idx];
      });
      return row;
    });
    
    // ✅ T3: Para Q1, ordena em ordem crescente de "DIAS SEM COMPRA"
    if (isQ1) {
      // Encontra o índice da coluna "DIAS SEM COMPRA" (pode ter variações no nome)
      const diasColName = primeiraTabela.colunas.find((col: string) => 
        col.toLowerCase().includes("dias") && col.toLowerCase().includes("compra")
      ) || primeiraTabela.colunas.find((col: string) => 
        col.toLowerCase().includes("dias")
      );
      
      if (diasColName) {
        rows = [...rows].sort((a, b) => {
          const diasA = Number(a[diasColName] ?? 0);
          const diasB = Number(b[diasColName] ?? 0);
          // Ordem crescente (menor primeiro)
          return diasA - diasB;
        });
      }
    }
    
    return {
      rows,
      title: primeiraTabela.titulo || "Dados Analíticos — Consulta Geral",
    };
  }, [data, isQ1]);

  // Calcula total de clientes para Big Number
  // ✅ Q1 LIGHT MODE: Prioriza metrics.total_clientes (fonte oficial do backend)
  // Em modo LIGHT, metrics.total_clientes (932) pode ser diferente de rows.length (100)
  // Isso é esperado e não deve gerar warning
  const totalClientes = useMemo(() => {
    const dataAny = data as any;
    
    // Verifica se é modo LIGHT/partial (esperado ter mismatch)
    const isLightMode = 
      dataAny.contexto?.dw_mode === "LIGHT" || 
      dataAny.contexto?.is_partial === true ||
      dataAny.jsonTecnico?.contexto?.dw_mode === "LIGHT" ||
      dataAny.jsonTecnico?.contexto?.is_partial === true;
    
    // 1. Prioridade: metrics.total_clientes (campo explícito do backend)
    // ✅ SEMPRE usa este valor quando presente, mesmo que diferente de rows.length
    if (dataAny.metrics?.total_clientes !== undefined && dataAny.metrics?.total_clientes !== null) {
      const totalMetrics = dataAny.metrics.total_clientes;
      
      // ✅ T4: Só emite warning se NÃO for modo LIGHT/partial
      if (tabelaPrincipal && tabelaPrincipal.rows.length !== totalMetrics && !isLightMode) {
        console.warn(
          `⚠️  INCONSISTÊNCIA DETECTADA: metrics.total_clientes (${totalMetrics}) != tabelaPrincipal.rows.length (${tabelaPrincipal.rows.length})`
        );
      }
      
      // ✅ T1: Sempre retorna metrics.total_clientes quando presente
      return totalMetrics;
    }
    
    // 2. Fallback: tabelaPrincipal.rows.length
    if (tabelaPrincipal) {
      return tabelaPrincipal.rows.length;
    }
    
    // 3. Fallback: detalhe_tabela
    const detalheTabela = data.detalhe_tabela || dataAny.detalheTabela;
    if (detalheTabela?.linhas) {
      return detalheTabela.linhas.length;
    }
    
    // 4. Fallback: jsonTecnico.total_clientes_unicos
    const jsonTecnico = dataAny.jsonTecnico || dataAny.structured?.jsonTecnico;
    if (jsonTecnico?.total_clientes_unicos !== undefined && jsonTecnico?.total_clientes_unicos !== null) {
      return jsonTecnico.total_clientes_unicos;
    }
    
    return 0;
  }, [tabelaPrincipal, data]);
  
  // ✅ T1: Calcula total exibido (rows.length) separadamente
  const totalExibidos = useMemo(() => {
    return tabelaPrincipal?.rows.length || 0;
  }, [tabelaPrincipal]);
  
  // ✅ T2: Calcula texto "Mostrando X de Y clientes em foco" para Q1
  const tabelaSubtitle = useMemo(() => {
    if (!isQ1 || !tabelaPrincipal) return undefined;
    
    // Só mostra se totalClientes > totalExibidos (modo LIGHT/partial)
    if (totalClientes > totalExibidos && totalExibidos > 0) {
      return `Mostrando ${formatNumberBR(totalExibidos)} de ${formatNumberBR(totalClientes)} clientes em foco`;
    }
    
    return undefined;
  }, [isQ1, tabelaPrincipal, totalClientes, totalExibidos]);

  // Resumo executivo
  const resumoExecutivo = useMemo(() => {
    return data.resumo_executivo || data.resumoExecutivo || "";
  }, [data]);

  // Blocos complementares (insights, etc.) - ✅ CORREÇÃO: Renderização defensiva
  const blocosComplementares = useMemo(() => {
    const blocos: React.ReactNode[] = [];
    
    // Insights - ✅ CORREÇÃO: Verificação defensiva com try/catch implícito
    try {
      if (Array.isArray(data.insightsRecomendacoes) && data.insightsRecomendacoes.length > 0) {
        const insightsText = data.insightsRecomendacoes.join(" ").trim();
        if (insightsText.length > 0 && !/erro no processamento avançado/i.test(insightsText)) {
          blocos.push(
            <InsightsBlock
              key="insights"
              insights={data.insightsRecomendacoes}
            />
          );
        }
      }
    } catch (error) {
      // ✅ CORREÇÃO: Se houver erro ao processar insights, não quebra o dashboard
      console.warn("Erro ao processar insights:", error);
    }
    
    return blocos.length > 0 ? <>{blocos}</> : null;
  }, [data.insightsRecomendacoes]);

  // ✅ CORREÇÃO: Determina se os dados estão prontos baseado na presença de dados reais
  // Não depende apenas do hook de loading, que pode ficar travado
  const isDataReady = useMemo(() => {
    // Se isLoading prop for true, ainda está carregando
    if (isLoading) return false;
    
    // Verifica se há dados válidos na resposta
    const dataAny = data as any;
    
    // Se houver tabela principal, dados estão prontos
    if (tabelaPrincipal && tabelaPrincipal.rows.length > 0) return true;
    
    // Se houver resumo executivo, dados estão prontos
    if (resumoExecutivo && resumoExecutivo.trim().length > 0) return true;
    
    // Se houver insights, dados estão prontos
    if (data.insightsRecomendacoes && data.insightsRecomendacoes.length > 0) return true;
    
    // Se houver jsonTecnico, dados estão prontos
    if (dataAny.jsonTecnico || dataAny.structured?.jsonTecnico) return true;
    
    // Se houver detalhe_tabela, dados estão prontos
    if (data.detalhe_tabela || dataAny.detalheTabela) return true;
    
    return false;
  }, [isLoading, data, tabelaPrincipal, resumoExecutivo]);

  // Telemetria: Big Number
  useEffect(() => {
    if (bigNumberRef.current && !bigNumberRendered.current && totalClientes > 0) {
      bigNumberRendered.current = true;
      const duration = loadingState.markBigNumberReady();
      if (duration > 0) {
        trackBigNumberRender(duration, totalClientes);
      }
    }
  }, [totalClientes, loadingState]);

  // Telemetria: Tabela
  useEffect(() => {
    if (tableRef.current && !tableRendered.current && tabelaPrincipal) {
      tableRendered.current = true;
      loadingState.startTableLoading();
      const duration = loadingState.markTableReady();
      if (duration > 0) {
        trackTableRender(duration, tabelaPrincipal.rows.length, false);
      }
    }
  }, [tabelaPrincipal, loadingState]);

  // ✅ CORREÇÃO: Se não houver tabela mas houver dados, marca como pronto
  useEffect(() => {
    if (isDataReady && !tabelaPrincipal && loadingState.isLoading) {
      // Se os dados estão prontos mas não há tabela, marca como não carregando
      // Isso evita skeleton infinito quando não há tabela
      loadingState.markTableReady();
    }
  }, [isDataReady, tabelaPrincipal, loadingState]);

  // ✅ PERFORMANCE: Estado de "processando detalhes" se demorar mais de 7s
  const [showProcessingMessage, setShowProcessingMessage] = React.useState(false);
  
  useEffect(() => {
    if (isLoading && !isDataReady) {
      // Mostra mensagem após 7 segundos se ainda estiver carregando
      const timer = setTimeout(() => {
        setShowProcessingMessage(true);
      }, 7000);
      
      return () => clearTimeout(timer);
    } else {
      setShowProcessingMessage(false);
    }
  }, [isLoading, isDataReady]);
  
  // ✅ CORREÇÃO: Loading state - prioriza isDataReady sobre loadingState.isLoading
  // Se os dados estão prontos, não mostra skeleton mesmo que loadingState.isLoading seja true
  if (isLoading && !isDataReady) {
    return (
      <>
        <DashboardSkeleton />
        {showProcessingMessage && (
          <div className="mt-4 p-4 bg-blue-500/10 border border-blue-500/20 rounded-xl text-blue-300 text-sm">
            ⏳ Ainda estou processando detalhes adicionais, mas você já pode trabalhar com os clientes prioritários.
          </div>
        )}
      </>
    );
  }
  
  // Se não há dados prontos E o loading state ainda está ativo, mostra skeleton
  // Mas se há dados prontos, mostra o conteúdo mesmo que loadingState.isLoading seja true
  if (!isDataReady && loadingState.isLoading) {
    return (
      <>
        <DashboardSkeleton />
        {showProcessingMessage && (
          <div className="mt-4 p-4 bg-blue-500/10 border border-blue-500/20 rounded-xl text-blue-300 text-sm">
            ⏳ Ainda estou processando detalhes adicionais, mas você já pode trabalhar com os clientes prioritários.
          </div>
        )}
      </>
    );
  }

  // Error state
  if (loadingState.error) {
    return (
      <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6 text-red-400">
        <p>Erro ao carregar dados: {loadingState.error.message}</p>
      </div>
    );
  }

  return (
    <LayoutResposta
      bigNumber={
        totalClientes > 0 ? (
          <div ref={bigNumberRef}>
            <BigNumber
              value={totalClientes}
              label="Total de Clientes"
              id="big-number-total-clientes"
            />
          </div>
        ) : null
      }
      resumoExecutivo={
        resumoExecutivo ? (
          <ResumoExecutivo
            content={resumoExecutivo}
            id="resumo-executivo"
          />
        ) : null
      }
      tabelaGeral={
        tabelaPrincipal ? (
          <div ref={tableRef}>
            <DataTable
              rows={tabelaPrincipal.rows}
              title={tabelaPrincipal.title}
              subtitle={tabelaSubtitle}
              id="tabela-dados-analiticos"
              itemsPerPage={20}
            />
          </div>
        ) : null
      }
      blocosComplementares={blocosComplementares}
    />
  );
};

