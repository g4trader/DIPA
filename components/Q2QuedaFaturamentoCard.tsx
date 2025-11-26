"use client";

import React, { useState } from "react";
import { Q2Response } from "@/types/q2";
import { callQ2Endpoint, Q2ApiError } from "@/lib/q2Api";
import { formatCurrencyBR, formatPercentBR, formatNumberBR } from "@/lib/formatters";
import { Card } from "./ui/dipam/Card";
import { BigNumber } from "./dashboard/BigNumber";

/**
 * Componente de card para análise Q2 (Queda de Faturamento)
 * 
 * Exibe:
 * - Campo de pergunta com botão "Rodar Q2"
 * - Período analisado
 * - Texto executivo
 * - Big numbers (métricas principais)
 * - Tabela de top clientes
 * - Lista de rotas mais impactadas
 */
export function Q2QuedaFaturamentoCard() {
  const [pergunta, setPergunta] = useState(
    "Quais clientes tiveram queda de faturamento de setembro para outubro?"
  );
  const [data, setData] = useState<Q2Response | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAllClientes, setShowAllClientes] = useState(false);

  const handleRunQ2 = async () => {
    if (!pergunta.trim()) {
      setError("Por favor, digite uma pergunta.");
      return;
    }

    setLoading(true);
    setError(null);
    setData(null);

    try {
      const response = await callQ2Endpoint(pergunta);
      setData(response);
    } catch (err) {
      if (err instanceof Q2ApiError) {
        setError(
          err.statusCode === 400
            ? "A pergunta não é sobre queda de faturamento. Por favor, reformule sua pergunta."
            : err.message
        );
      } else {
        setError("Erro ao processar sua pergunta. Por favor, tente novamente.");
      }
      console.error("Erro ao chamar Q2:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !loading) {
      handleRunQ2();
    }
  };

  // Limita exibição de clientes (10 por padrão, todos se showAllClientes)
  const clientesExibidos = data?.top_clientes
    ? showAllClientes
      ? data.top_clientes
      : data.top_clientes.slice(0, 10)
    : [];

  return (
    <div className="w-full max-w-7xl mx-auto p-4 md:p-6 space-y-6">
      {/* Card principal */}
      <Card className="space-y-6">
        {/* Cabeçalho */}
        <div className="border-b border-white/10 pb-4">
          <h1 className="text-2xl md:text-3xl font-bold text-white mb-2">
            Análise de Queda de Faturamento (Q2)
          </h1>
          <p className="text-sm text-white/60">
            Identifique clientes com queda de faturamento entre períodos
          </p>
        </div>

        {/* Campo de pergunta */}
        <div className="space-y-3">
          <label htmlFor="q2-pergunta" className="block text-sm font-medium text-white/80">
            Pergunta
          </label>
          <div className="flex gap-3">
            <input
              id="q2-pergunta"
              type="text"
              value={pergunta}
              onChange={(e) => setPergunta(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={loading}
              className="flex-1 px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
              placeholder="Digite sua pergunta sobre queda de faturamento..."
            />
            <button
              onClick={handleRunQ2}
              disabled={loading || !pergunta.trim()}
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-[#0F172A]"
            >
              {loading ? "Processando..." : "Rodar Q2"}
            </button>
          </div>
        </div>

        {/* Estado de loading */}
        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="flex flex-col items-center gap-3">
              <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
              <p className="text-sm text-white/60">Processando sua pergunta...</p>
            </div>
          </div>
        )}

        {/* Estado de erro */}
        {error && !loading && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}

        {/* Resultados */}
        {data && !loading && (
          <div className="space-y-6">
            {/* Período analisado */}
            <div className="bg-white/5 border border-white/10 rounded-lg p-4">
              <p className="text-sm text-white/60 mb-1">Período analisado</p>
              <p className="text-lg font-semibold text-white">{data.periodo.descricao}</p>
            </div>

            {/* Texto executivo */}
            <div className="bg-white/5 border border-white/10 rounded-lg p-4">
              <h2 className="text-lg font-semibold text-white mb-3">Resumo Executivo</h2>
              <div className="prose prose-invert max-w-none">
                <p className="text-sm text-white/80 whitespace-pre-line leading-relaxed">
                  {data.texto_executivo}
                </p>
              </div>
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
                <Card className="p-0">
                  <div className="p-4 border-b border-white/10">
                    <h2 className="text-lg font-semibold text-white">
                      Top Clientes com Queda
                    </h2>
                    <p className="text-xs text-white/60 mt-1">
                      {data.top_clientes.length} cliente(s) encontrado(s)
                    </p>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-white/5">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-medium text-white/60 uppercase tracking-wider">
                            Cliente
                          </th>
                          <th className="px-4 py-3 text-right text-xs font-medium text-white/60 uppercase tracking-wider">
                            Queda (R$)
                          </th>
                          <th className="px-4 py-3 text-right text-xs font-medium text-white/60 uppercase tracking-wider">
                            Queda (%)
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-white/60 uppercase tracking-wider">
                            Rota
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5">
                        {clientesExibidos.length > 0 ? (
                          clientesExibidos.map((cliente, idx) => (
                            <tr
                              key={cliente.cliente_id || idx}
                              className="hover:bg-white/5 transition-colors"
                            >
                              <td className="px-4 py-3 text-sm text-white">
                                {cliente.nome}
                              </td>
                              <td className="px-4 py-3 text-sm text-right text-red-400 font-medium">
                                {formatCurrencyBR(cliente.queda_absoluta)}
                              </td>
                              <td className="px-4 py-3 text-sm text-right text-red-400 font-medium">
                                {formatPercentBR(cliente.queda_percentual)}
                              </td>
                              <td className="px-4 py-3 text-sm text-white/60">
                                {cliente.rota || "N/A"}
                              </td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td colSpan={4} className="px-4 py-8 text-center text-sm text-white/60">
                              Nenhum cliente encontrado
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                  {data.top_clientes.length > 10 && (
                    <div className="p-4 border-t border-white/10">
                      <button
                        onClick={() => setShowAllClientes(!showAllClientes)}
                        className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
                      >
                        {showAllClientes
                          ? "Mostrar menos"
                          : `Ver todos (${data.top_clientes.length} clientes)`}
                      </button>
                    </div>
                  )}
                </Card>
              </div>

              {/* Lista de rotas */}
              <div className="lg:col-span-1">
                <Card>
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
                            <span className="text-xs text-white/60">
                              #{idx + 1}
                            </span>
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
                </Card>
              </div>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}

