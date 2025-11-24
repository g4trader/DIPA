/**
 * Carregamento dos dados mock Q1
 * Tenta múltiplas estratégias para garantir que os dados sejam carregados
 */

let q1ClientesMock: any[] | null = null;
let q1EstatisticasMock: any | null = null;

// Função para carregar dados (lazy loading)
export function getQ1ClientesMock(): any[] {
  if (q1ClientesMock === null) {
    try {
      // Estratégia 1: require() com caminho relativo
      try {
        const data = require("../../mock/data/q1_clientes_sem_compra.json");
        q1ClientesMock = Array.isArray(data) ? data : (data?.default || data);
        if (q1ClientesMock && q1ClientesMock.length > 0) {
          console.log(`[mockData] ✅ Dados carregados via require(): ${q1ClientesMock.length} clientes`);
          return q1ClientesMock;
        }
      } catch (e1: any) {
        console.log(`[mockData] ⚠️  require() falhou: ${e1.message}`);
      }
      
      // Estratégia 2: readFileSync (se disponível)
      if (typeof window === "undefined") {
        try {
          const fs = require("fs");
          const path = require("path");
          const basePath = process.cwd();
          const caminhos = [
            path.join(basePath, "mock", "data", "q1_clientes_sem_compra.json"),
            path.join(basePath, ".next", "standalone", "mock", "data", "q1_clientes_sem_compra.json"),
          ];
          
          for (const caminho of caminhos) {
            try {
              const raw = fs.readFileSync(caminho, "utf-8");
              const data = JSON.parse(raw);
              q1ClientesMock = Array.isArray(data) ? data : (data?.dados || []);
              if (q1ClientesMock && q1ClientesMock.length > 0) {
                console.log(`[mockData] ✅ Dados carregados via readFileSync: ${q1ClientesMock.length} clientes de ${caminho}`);
                return q1ClientesMock;
              }
            } catch (e2: any) {
              // Continua tentando próximo caminho
            }
          }
        } catch (e3: any) {
          console.log(`[mockData] ⚠️  readFileSync não disponível: ${e3.message}`);
        }
      }
      
      // Se chegou aqui, não conseguiu carregar
      console.error("[mockData] ❌ Não foi possível carregar q1_clientes_sem_compra.json");
      q1ClientesMock = [];
    } catch (e) {
      console.error("[mockData] Erro geral ao carregar q1_clientes_sem_compra.json:", e);
      q1ClientesMock = [];
    }
  }
  return q1ClientesMock || [];
}

export function getQ1EstatisticasMock(): any {
  if (q1EstatisticasMock === null) {
    try {
      // Estratégia 1: require() com caminho relativo
      try {
        const data = require("../../mock/data/q1_estatisticas.json");
        q1EstatisticasMock = data?.default || data;
        if (q1EstatisticasMock && q1EstatisticasMock.total_clientes) {
          console.log(`[mockData] ✅ Estatísticas carregadas via require()`);
          return q1EstatisticasMock;
        }
      } catch (e1: any) {
        console.log(`[mockData] ⚠️  require() de estatísticas falhou: ${e1.message}`);
      }
      
      // Estratégia 2: readFileSync (se disponível)
      if (typeof window === "undefined") {
        try {
          const fs = require("fs");
          const path = require("path");
          const basePath = process.cwd();
          const caminhos = [
            path.join(basePath, "mock", "data", "q1_estatisticas.json"),
            path.join(basePath, ".next", "standalone", "mock", "data", "q1_estatisticas.json"),
          ];
          
          for (const caminho of caminhos) {
            try {
              const raw = fs.readFileSync(caminho, "utf-8");
              q1EstatisticasMock = JSON.parse(raw);
              if (q1EstatisticasMock && q1EstatisticasMock.total_clientes) {
                console.log(`[mockData] ✅ Estatísticas carregadas via readFileSync de ${caminho}`);
                return q1EstatisticasMock;
              }
            } catch (e2: any) {
              // Continua tentando próximo caminho
            }
          }
        } catch (e3: any) {
          console.log(`[mockData] ⚠️  readFileSync não disponível: ${e3.message}`);
        }
      }
      
      // Se chegou aqui, não conseguiu carregar
      console.error("[mockData] ❌ Não foi possível carregar q1_estatisticas.json");
      q1EstatisticasMock = {};
    } catch (e) {
      console.error("[mockData] Erro geral ao carregar q1_estatisticas.json:", e);
      q1EstatisticasMock = {};
    }
  }
  return q1EstatisticasMock || {};
}

