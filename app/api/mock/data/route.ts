import { NextResponse } from "next/server";
import { readFileSync } from "fs";
import { join } from "path";

/**
 * API route para servir dados mock Q1
 * Isso garante que os JSONs sejam acessíveis na Vercel
 */
export async function GET() {
  try {
    const basePath = process.cwd();
    let q1Clientes: any[] = [];
    let q1Estatisticas: any = null;

    // Tenta diferentes caminhos possíveis
    const caminhosClientes = [
      join(basePath, "mock", "data", "q1_clientes_sem_compra.json"),
      join(basePath, ".next", "standalone", "mock", "data", "q1_clientes_sem_compra.json"),
      join(basePath, "mock", "data", "q1_dados_dw.json"), // Fallback
    ];

    // Tenta carregar clientes
    for (const caminho of caminhosClientes) {
      try {
        const dadosRaw = readFileSync(caminho, "utf-8");
        const dadosParsed = JSON.parse(dadosRaw);
        q1Clientes = Array.isArray(dadosParsed) ? dadosParsed : (dadosParsed?.dados || []);
        if (q1Clientes.length > 0) {
          console.log(`[mock/data] ✅ Clientes carregados: ${q1Clientes.length} de ${caminho}`);
          break;
        }
      } catch (e: any) {
        // Continua tentando próximo caminho
        console.log(`[mock/data] ⚠️  Não encontrado em ${caminho}: ${e.message}`);
      }
    }

    // Tenta carregar estatísticas
    const caminhosStats = [
      join(basePath, "mock", "data", "q1_estatisticas.json"),
      join(basePath, ".next", "standalone", "mock", "data", "q1_estatisticas.json"),
    ];

    for (const caminho of caminhosStats) {
      try {
        const statsRaw = readFileSync(caminho, "utf-8");
        q1Estatisticas = JSON.parse(statsRaw);
        console.log(`[mock/data] ✅ Estatísticas carregadas de ${caminho}`);
        break;
      } catch (e: any) {
        console.log(`[mock/data] ⚠️  Não encontrado em ${caminho}: ${e.message}`);
      }
    }

    return NextResponse.json({
      clientes: q1Clientes,
      estatisticas: q1Estatisticas,
      loaded: q1Clientes.length > 0 && q1Estatisticas !== null,
      total_clientes: q1Clientes.length,
      basePath: basePath,
    });
  } catch (error) {
    console.error("[mock/data] Erro:", error);
    if (error instanceof Error) {
      console.error("[mock/data] Stack:", error.stack);
    }
    return NextResponse.json(
      { 
        error: "Erro ao carregar dados mock",
        message: error instanceof Error ? error.message : String(error),
        basePath: process.cwd(),
      },
      { status: 500 }
    );
  }
}

