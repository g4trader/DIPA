import { NextResponse } from "next/server";

/**
 * API route para servir dados mock Q1
 * Isso garante que os JSONs sejam acessíveis na Vercel
 */
export async function GET() {
  try {
    // Tenta importar os JSONs
    let q1Clientes: any[] = [];
    let q1Estatisticas: any = null;

    try {
      const clientesModule = require("@/mock/data/q1_clientes_sem_compra.json");
      q1Clientes = Array.isArray(clientesModule) 
        ? clientesModule 
        : (clientesModule?.default || clientesModule);
    } catch (e) {
      console.error("[mock/data] Erro ao carregar q1_clientes_sem_compra.json:", e);
    }

    try {
      const statsModule = require("@/mock/data/q1_estatisticas.json");
      q1Estatisticas = statsModule?.default || statsModule;
    } catch (e) {
      console.error("[mock/data] Erro ao carregar q1_estatisticas.json:", e);
    }

    return NextResponse.json({
      clientes: q1Clientes,
      estatisticas: q1Estatisticas,
      loaded: q1Clientes.length > 0 && q1Estatisticas !== null,
    });
  } catch (error) {
    console.error("[mock/data] Erro:", error);
    return NextResponse.json(
      { error: "Erro ao carregar dados mock" },
      { status: 500 }
    );
  }
}

