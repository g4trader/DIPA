"use client";

import React, { useEffect, useState } from "react";
import { clsx } from "clsx";
import { Loader2, User, AlertCircle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { ds } from "@/styles/ui";
import { previewVendedor, DipamApiError, type PreviewVendedorResponse } from "@/lib/dipamApi";

/**
 * Props para o componente VendedorPreviewCard
 */
type VendedorPreviewCardProps = {
  /** Nome ou ID do vendedor */
  vendedor: string;
  /** Mês e ano no formato YYYY-MM (ex: '2025-11') */
  mesAno: string;
  /** Classe CSS adicional */
  className?: string;
};

/**
 * Componente que exibe um preview de dados de um vendedor específico
 * para um determinado mês/ano, buscando dados da API do Dipam AI.
 * 
 * Este componente é útil para supervisores visualizarem informações
 * detalhadas sobre o desempenho de seus vendedores.
 * 
 * @example
 * ```tsx
 * <VendedorPreviewCard vendedor="João Silva" mesAno="2025-11" />
 * ```
 */
export function VendedorPreviewCard({ vendedor, mesAno, className }: VendedorPreviewCardProps) {
  const [data, setData] = useState<PreviewVendedorResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Reseta estados quando as props mudam
    setLoading(true);
    setError(null);
    setData(null);

    // Faz a chamada à API
    const fetchPreview = async () => {
      try {
        const response = await previewVendedor({
          vendedor,
          mesAno
        });
        setData(response);
      } catch (err) {
        console.error("Erro ao buscar preview do vendedor:", err);
        const errorMessage = err instanceof DipamApiError
          ? err.message
          : "Erro ao carregar dados do vendedor. Verifique se a API está rodando.";
        setError(errorMessage);
      } finally {
        setLoading(false);
      }
    };

    void fetchPreview();
  }, [vendedor, mesAno]);

  // Formata o mês/ano para exibição
  const formatMesAno = (mesAno: string) => {
    const [ano, mes] = mesAno.split("-");
    const meses = [
      "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
      "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ];
    return `${meses[parseInt(mes) - 1]} ${ano}`;
  };

  return (
    <Card className={clsx(ds.card, "shadow-xl shadow-blue-900/20", className)}>
      <CardContent className="flex flex-col gap-6 p-6 md:p-8">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-blue-500/40 bg-blue-500/20">
              <User className="h-5 w-5 text-blue-300" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Preview do Vendedor
              </p>
              <h2 className="mt-1 text-xl font-semibold text-slate-100">{vendedor}</h2>
            </div>
          </div>
          <span className="rounded-full border border-blue-500/40 bg-blue-500/15 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-blue-200">
            {formatMesAno(mesAno)}
          </span>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="flex flex-col items-center justify-center gap-4 py-12">
            <Loader2 className="h-8 w-8 animate-spin text-blue-400" />
            <p className="text-sm text-slate-400">Carregando dados do vendedor...</p>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="flex flex-col items-center justify-center gap-4 rounded-xl border border-red-500/40 bg-red-500/10 px-6 py-8">
            <AlertCircle className="h-8 w-8 text-red-400" />
            <div className="text-center">
              <p className="text-sm font-semibold text-red-300">Erro ao carregar dados</p>
              <p className="mt-1 text-xs text-red-400/80">{error}</p>
            </div>
          </div>
        )}

        {/* Data Display */}
        {data && !loading && (
          <div className="space-y-6">
            {/* Informações básicas */}
            <div className="grid gap-4 sm:grid-cols-2">
              <InfoCard label="Vendedor" value={data.vendedor} />
              <InfoCard label="Período" value={formatMesAno(data.mes_ano)} />
            </div>

            {/* Dados estruturados */}
            {data.dados && Object.keys(data.dados).length > 0 && (
              <div className="space-y-4">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Dados do Período
                </h3>
                
                {/* Renderiza os dados baseado no tipo */}
                <div className="grid gap-4">
                  {Object.entries(data.dados).map(([key, value]) => (
                    <DataRow key={key} label={formatLabel(key)} value={value} />
                  ))}
                </div>
              </div>
            )}

            {/* Timestamp */}
            {data.timestamp && (
              <div className="pt-4 border-t border-slate-700/60">
                <p className="text-[10px] text-slate-500">
                  Atualizado em: {new Date(data.timestamp).toLocaleString("pt-BR")}
                </p>
              </div>
            )}
          </div>
        )}

        {/* Empty State (sem erro e sem dados) */}
        {!loading && !error && data && (!data.dados || Object.keys(data.dados).length === 0) && (
          <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-slate-700/60 bg-slate-900/40 px-6 py-12 text-center">
            <User className="h-8 w-8 text-slate-500" />
            <p className="text-sm text-slate-400">Nenhum dado disponível para este período.</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * Componente auxiliar para exibir informações simples em card
 */
function InfoCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-slate-700/60 bg-slate-900/60 px-4 py-3">
      <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">
        {label}
      </p>
      <p className="mt-2 text-lg font-semibold text-slate-100">{value}</p>
    </div>
  );
}

/**
 * Componente auxiliar para exibir uma linha de dados
 */
function DataRow({ label, value }: { label: string; value: any }) {
  const formatValue = (val: any): string => {
    if (val === null || val === undefined) return "—";
    if (typeof val === "number") {
      // Se for um número grande, pode ser um valor monetário
      if (val >= 1000) {
        return val.toLocaleString("pt-BR", { 
          style: "currency", 
          currency: "BRL",
          minimumFractionDigits: 2,
          maximumFractionDigits: 2
        });
      }
      return val.toLocaleString("pt-BR");
    }
    if (typeof val === "boolean") return val ? "Sim" : "Não";
    if (typeof val === "object") return JSON.stringify(val, null, 2);
    return String(val);
  };

  return (
    <div className="flex items-center justify-between rounded-lg border border-slate-700/60 bg-slate-900/40 px-4 py-3">
      <span className="text-sm font-medium text-slate-300">{label}</span>
      <span className="text-sm font-semibold text-slate-100">{formatValue(value)}</span>
    </div>
  );
}

/**
 * Formata labels de snake_case ou camelCase para texto legível
 */
function formatLabel(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/([A-Z])/g, " $1")
    .replace(/^./, (str) => str.toUpperCase())
    .trim();
}



