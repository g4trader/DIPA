"use client";

import React from "react";
import { Q2QuedaFaturamentoCard } from "@/components/Q2QuedaFaturamentoCard";

/**
 * Página Q2 - Análise de Queda de Faturamento
 * 
 * Rota: /copilot/q2
 * 
 * Exibe o componente Q2QuedaFaturamentoCard integrado à interface COPILOT
 */
export default function Q2Page() {
  return (
    <div className="min-h-screen bg-[#0A0E1A] py-8">
      <div className="container mx-auto">
        <Q2QuedaFaturamentoCard />
      </div>
    </div>
  );
}

