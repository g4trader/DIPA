"use client";

import React from "react";

type ResumoExecutivoProps = {
  content: string;
  className?: string;
  id?: string;
};

/**
 * ResumoExecutivo - Redesign com HIE (Hierarquia de Informação Executiva)
 * 
 * Melhorias:
 * - Reduz poluição visual
 * - Cards leves, margens menores, mais densidade de informação
 * - Sem ícones desnecessários
 * - Foco em: faturamento, clientes impactados, variação, ranking
 */
export function ResumoExecutivo({
  content,
  className = "",
  id,
}: ResumoExecutivoProps) {
  if (!content) return null;

  return (
    <div
      id={id}
      className={`bg-[#0F172A] border border-white/5 rounded-xl p-5 shadow-lg ${className}`}
    >
      <h3 className="text-lg font-semibold text-white mb-3">Resumo Executivo</h3>
      <div className="text-sm text-white/80 leading-relaxed space-y-2">
        {content.split("\n\n").map((paragraph, idx) => (
          <p key={idx} className="text-white/80">
            {paragraph.trim()}
          </p>
        ))}
      </div>
    </div>
  );
}

