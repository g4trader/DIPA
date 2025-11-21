"use client";

import React from "react";

/**
 * LayoutResposta - Layout universal fixo para respostas do DIPAM Copilot
 * 
 * Ordem fixa:
 * 1. Big Number — "Total de Clientes"
 * 2. Resumo Executivo
 * 3. Tabela "Dados Analíticos — Consulta Geral" (20 registros/página)
 * 4. Demais blocos do dashboard (insights, alvos, rotas, etc.)
 */
type LayoutRespostaProps = {
  bigNumber?: React.ReactNode;
  resumoExecutivo?: React.ReactNode;
  tabelaGeral?: React.ReactNode;
  blocosComplementares?: React.ReactNode;
  className?: string;
};

export function LayoutResposta({
  bigNumber,
  resumoExecutivo,
  tabelaGeral,
  blocosComplementares,
  className = "",
}: LayoutRespostaProps) {
  return (
    <div className={`space-y-6 ${className}`}>
      {/* 1. Big Number — "Total de Clientes" */}
      {bigNumber && (
        <div className="w-full" data-testid="layout-big-number">
          {bigNumber}
        </div>
      )}

      {/* 2. Resumo Executivo */}
      {resumoExecutivo && (
        <div className="w-full" data-testid="layout-resumo-executivo">
          {resumoExecutivo}
        </div>
      )}

      {/* 3. Tabela "Dados Analíticos — Consulta Geral" (20 registros/página) */}
      {tabelaGeral && (
        <div className="w-full" data-testid="layout-tabela-geral">
          {tabelaGeral}
        </div>
      )}

      {/* 4. Demais blocos do dashboard (insights, alvos, rotas, etc.) */}
      {blocosComplementares && (
        <div className="w-full space-y-6" data-testid="layout-blocos-complementares">
          {blocosComplementares}
        </div>
      )}
    </div>
  );
}

