/**
 * Dados mock Q1
 * 
 * Tenta carregar do arquivo gerado (mockDataGenerated.ts) primeiro.
 * Se não encontrar, tenta carregar do JSON.
 * Se não encontrar, usa fallback.
 */

// Tenta importar dados gerados (incluídos diretamente no código)
let q1ClientesMock: any[] | null = null;
let q1EstatisticasMock: any | null = null;

// Tenta importar dados gerados
try {
  const generated = require("./mockDataGenerated");
  if (generated.q1ClientesMock && Array.isArray(generated.q1ClientesMock) && generated.q1ClientesMock.length > 0) {
    q1ClientesMock = generated.q1ClientesMock;
    q1EstatisticasMock = generated.q1EstatisticasMock;
    console.log(`[mockData] ✅ Dados carregados do arquivo gerado: ${q1ClientesMock.length} clientes`);
  }
} catch (e: any) {
  console.log(`[mockData] ⚠️  Arquivo gerado não encontrado: ${e.message}, tentando outras estratégias...`);
}

export function getQ1ClientesMock(): any[] {
  if (q1ClientesMock === null) {
    // Tenta carregar do arquivo JSON (desenvolvimento)
    try {
      if (typeof window === "undefined") {
        const fs = require("fs");
        const path = require("path");
        const basePath = process.cwd();
        const caminhos = [
          path.join(basePath, "mock", "data", "q1_clientes_sem_compra.json"),
          path.join(basePath, ".next", "standalone", "mock", "data", "q1_clientes_sem_compra.json"),
        ];
        
        for (const caminho of caminhos) {
          try {
            if (fs.existsSync(caminho)) {
              const raw = fs.readFileSync(caminho, "utf-8");
              const data = JSON.parse(raw);
              q1ClientesMock = Array.isArray(data) ? data : (data?.dados || []);
              if (q1ClientesMock && q1ClientesMock.length > 0) {
                console.log(`[mockData] ✅ Dados carregados do arquivo JSON: ${q1ClientesMock.length} clientes de ${caminho}`);
                return q1ClientesMock;
              }
            }
          } catch (e) {
            // Continua tentando próximo caminho
          }
        }
      }
    } catch (e) {
      // Ignora erro
    }
    
    // Se não conseguiu, usa fallback
    console.log(`[mockData] ⚠️  Não foi possível carregar dados, usando fallback`);
    q1ClientesMock = [];
  }
  return q1ClientesMock || [];
}

export function getQ1EstatisticasMock(): any {
  if (q1EstatisticasMock === null) {
    // Tenta carregar do arquivo JSON (desenvolvimento)
    try {
      if (typeof window === "undefined") {
        const fs = require("fs");
        const path = require("path");
        const basePath = process.cwd();
        const caminhos = [
          path.join(basePath, "mock", "data", "q1_estatisticas.json"),
          path.join(basePath, ".next", "standalone", "mock", "data", "q1_estatisticas.json"),
        ];
        
        for (const caminho of caminhos) {
          try {
            if (fs.existsSync(caminho)) {
              const raw = fs.readFileSync(caminho, "utf-8");
              q1EstatisticasMock = JSON.parse(raw);
              if (q1EstatisticasMock && q1EstatisticasMock.total_clientes) {
                console.log(`[mockData] ✅ Estatísticas carregadas do arquivo JSON de ${caminho}`);
                return q1EstatisticasMock;
              }
            }
          } catch (e) {
            // Continua tentando próximo caminho
          }
        }
      }
    } catch (e) {
      // Ignora erro
    }
    
    // Se não conseguiu, usa fallback
    console.log(`[mockData] ⚠️  Não foi possível carregar estatísticas, usando fallback`);
    q1EstatisticasMock = {
      total_clientes: 0,
      faixas: { "61_120": 0, "121_180": 0, "181_300": 0, "acima_300": 0 },
    };
  }
  return q1EstatisticasMock || {};
}
