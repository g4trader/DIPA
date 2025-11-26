"use client";

import React from "react";
import { Q2Response } from "@/types/q2";
import { formatCurrencyBR, formatPercentBR, formatNumberBR } from "@/lib/formatters";
import { BigNumber } from "./dashboard/BigNumber";
import { DataTable } from "./DataTable";

type Props = {
  data: Q2Response;
};

/**
 * Componente de resultado Q2 para o agent (/ask)
 * 
 * Renderiza apenas o resultado (sem input de pergunta) no mesmo padrão visual da Q1.
 * Este componente é usado dentro do CopilotAnswerCard quando a resposta é Q2.
 */
export function Q2QuedaFaturamentoResultCard({ data }: Props) {
  // Converte top_clientes para formato de tabela
  const tabelaClientes = React.useMemo(() => {
    if (!data.top_clientes || data.top_clientes.length === 0) {
      return null;
    }

    const colunas = ["Cliente", "Queda (R$)", "Queda (%)", "Rota"];
    const linhas = data.top_clientes.map((cliente) => [
      cliente.nome,
      formatCurrencyBR(cliente.queda_absoluta),
      formatPercentBR(cliente.queda_percentual),
      cliente.rota || "N/A",
    ]);

    return {
      rows: linhas.map((linha) => {
        const row: Record<string, any> = {};
        colunas.forEach((col, idx) => {
          row[col] = linha[idx];
        });
        return row;
      }),
      columns: colunas,
      title: "Top Clientes com Queda de Faturamento",
    };
  }, [data.top_clientes]);

  return (
    <div className="space-y-6">
      {/* Texto executivo */}
      {data.texto_executivo && (
        <div className="bg-white/5 border border-white/10 rounded-lg p-4">
          <h2 className="text-lg font-semibold text-white mb-3">Resumo Executivo</h2>
          <div className="prose prose-invert max-w-none">
            <p className="text-sm text-white/80 whitespace-pre-line leading-relaxed">
              {data.texto_executivo}
            </p>
          </div>
        </div>
      )}

      {/* Período analisado */}
      <div className="bg-white/5 border border-white/10 rounded-lg p-4">
        <p className="text-sm text-white/60 mb-1">Período analisado</p>
        <p className="text-lg font-semibold text-white">{data.periodo.descricao}</p>
      </div>

      {/* Big Numbers */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <BigNumber
          value={data.resumo.total_clientes_queda}
          label="Clientes com Queda"
          subtle={
            data.resumo.percentual_clientes_queda
              ? `${formatPercentBR(data.resumo.percentual_clientes_queda, 1)} dos clientes`
              : undefined
          }
        />
        <div className="bg-[#0F172A] border border-white/10 rounded-xl p-6 shadow-lg">
          <p className="text-sm text-white/60 uppercase tracking-wide font-medium mb-2">
            Queda Média
          </p>
          <p className="text-4xl font-bold text-white">
            {formatCurrencyBR(data.resumo.queda_media_absoluta)}
          </p>
          <p className="text-sm text-white/50 mt-1">
            {formatPercentBR(data.resumo.queda_media_percentual)}
          </p>
        </div>
        <div className="bg-[#0F172A] border border-white/10 rounded-xl p-6 shadow-lg">
          <p className="text-sm text-white/60 uppercase tracking-wide font-medium mb-2">
            Queda Máxima
          </p>
          <p className="text-4xl font-bold text-white">
            {formatCurrencyBR(data.resumo.queda_maxima_absoluta)}
          </p>
          <p className="text-sm text-white/50 mt-1">
            {formatPercentBR(data.resumo.queda_maxima_percentual)}
          </p>
        </div>
        <BigNumber
          value={data.rotas.length}
          label="Rotas Impactadas"
          subtle="Top rotas"
        />
      </div>

      {/* Grid: Tabela de clientes + Lista de rotas */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Tabela de top clientes */}
        <div className="lg:col-span-2">
          {tabelaClientes ? (
            <DataTable
              rows={tabelaClientes.rows}
              title={tabelaClientes.title}
              subtitle={`${data.top_clientes.length} cliente(s) encontrado(s)`}
            />
          ) : (
            <div className="bg-white/5 border border-white/10 rounded-lg p-6">
              <p className="text-sm text-white/60">Nenhum cliente encontrado</p>
            </div>
          )}
        </div>

        {/* Lista de rotas */}
        <div className="lg:col-span-1">
          <div className="bg-white/5 border border-white/10 rounded-lg p-6">
            <h2 className="text-lg font-semibold text-white mb-4">
              Rotas Mais Impactadas
            </h2>
            {data.rotas.length > 0 ? (
              <div className="space-y-3">
                {data.rotas.map((rota, idx) => (
                  <div
                    key={rota.rota}
                    className="bg-white/5 border border-white/10 rounded-lg p-3"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-white">
                        {rota.rota}
                      </span>
                      <span className="text-xs text-white/60">#{idx + 1}</span>
                    </div>
                    <div className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="text-white/60">Clientes:</span>
                        <span className="text-white">
                          {formatNumberBR(rota.qtd_clientes_queda)}
                        </span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-white/60">Queda total:</span>
                        <span className="text-red-400 font-medium">
                          {formatCurrencyBR(rota.queda_total)}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-white/60">Nenhuma rota encontrada</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

