"use client";

import React, { useMemo, useEffect, useRef } from "react";
import { CopilotStructuredResponse } from "@/types/agent";
import { LayoutResposta } from "./dashboard/LayoutResposta";
import { BigNumber } from "./dashboard/BigNumber";
import { ResumoExecutivo } from "./dashboard/ResumoExecutivo";
import { DataTable } from "./DataTable";
import { DashboardSkeleton } from "./skeletons/DashboardSkeleton";
import { useDashboardLoading } from "@/hooks/useDashboardLoading";
import { trackBigNumberRender, trackTableRender } from "@/lib/telemetry";
import { InsightsBlock } from "./InsightsBlock";

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
    const rows = primeiraTabela.linhas.map((linha: any[]) => {
      const row: Record<string, any> = {};
      primeiraTabela.colunas.forEach((col: string, idx: number) => {
        row[col] = linha[idx];
      });
      return row;
    });
    
    return {
      rows,
      title: primeiraTabela.titulo || "Dados Analíticos — Consulta Geral",
    };
  }, [data]);

  // Calcula total de clientes para Big Number
  const totalClientes = useMemo(() => {
    if (tabelaPrincipal) {
      return tabelaPrincipal.rows.length;
    }
    
    // Fallback: tenta extrair de outras fontes
    const dataAny = data as any;
    const detalheTabela = data.detalhe_tabela || dataAny.detalheTabela;
    if (detalheTabela?.linhas) {
      return detalheTabela.linhas.length;
    }
    
    return 0;
  }, [tabelaPrincipal, data]);

  // Resumo executivo
  const resumoExecutivo = useMemo(() => {
    return data.resumo_executivo || data.resumoExecutivo || "";
  }, [data]);

  // Blocos complementares (insights, etc.)
  const blocosComplementares = useMemo(() => {
    const blocos: React.ReactNode[] = [];
    
    // Insights
    if (data.insightsRecomendacoes && data.insightsRecomendacoes.length > 0) {
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
    
    return blocos.length > 0 ? <>{blocos}</> : null;
  }, [data.insightsRecomendacoes]);

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

  // Loading state
  if (isLoading || loadingState.isLoading) {
    return <DashboardSkeleton />;
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

