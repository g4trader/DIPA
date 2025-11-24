/**
 * Carregamento dos dados mock Q1
 * Tenta múltiplas estratégias para garantir que os dados sejam carregados
 */

let q1ClientesMock: any[] | null = null;
let q1EstatisticasMock: any | null = null;

// Obtém __dirname se disponível (Node.js)
let __dirname: string | undefined;
try {
  if (typeof window === "undefined") {
    const path = require("path");
    const { fileURLToPath } = require("url");
    __dirname = path.dirname(fileURLToPath(import.meta.url || "file://" + __filename));
  }
} catch (e) {
  // Ignora erro se __dirname não estiver disponível
}

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
          
          // Tenta múltiplos caminhos possíveis (Vercel pode ter estrutura diferente)
          const caminhos = [
            // Caminho padrão (desenvolvimento)
            path.join(basePath, "mock", "data", "q1_clientes_sem_compra.json"),
            // Standalone build (produção local e Vercel)
            path.join(basePath, ".next", "standalone", "mock", "data", "q1_clientes_sem_compra.json"),
            // Alternativa: caminho relativo ao arquivo atual
            path.join(__dirname || basePath, "..", "..", "mock", "data", "q1_clientes_sem_compra.json"),
            // Vercel pode usar caminho diferente
            path.join("/var", "task", ".next", "standalone", "mock", "data", "q1_clientes_sem_compra.json"),
            path.join("/var", "task", "mock", "data", "q1_clientes_sem_compra.json"),
          ];
          
          // Debug: lista arquivos disponíveis no basePath
          try {
            const basePath = process.cwd();
            console.log(`[mockData] 🔍 Debug: basePath = ${basePath}`);
            if (fs.existsSync(basePath)) {
              const files = fs.readdirSync(basePath, { withFileTypes: true });
              console.log(`[mockData] 🔍 Arquivos na raiz:`, files.slice(0, 10).map(f => f.name));
            }
            if (fs.existsSync(path.join(basePath, ".next", "standalone"))) {
              const standaloneFiles = fs.readdirSync(path.join(basePath, ".next", "standalone"), { withFileTypes: true });
              console.log(`[mockData] 🔍 Arquivos em .next/standalone:`, standaloneFiles.slice(0, 10).map(f => f.name));
            }
          } catch (debugErr) {
            // Ignora erros de debug
          }
          
          for (const caminho of caminhos) {
            try {
              // Verifica se o arquivo existe antes de tentar ler
              if (fs.existsSync(caminho)) {
                console.log(`[mockData] 🔍 Arquivo encontrado: ${caminho}`);
                const raw = fs.readFileSync(caminho, "utf-8");
                const data = JSON.parse(raw);
                q1ClientesMock = Array.isArray(data) ? data : (data?.dados || []);
                if (q1ClientesMock && q1ClientesMock.length > 0) {
                  console.log(`[mockData] ✅ Dados carregados via readFileSync: ${q1ClientesMock.length} clientes de ${caminho}`);
                  return q1ClientesMock;
                }
              } else {
                console.log(`[mockData] ⚠️  Arquivo não existe: ${caminho}`);
              }
            } catch (e2: any) {
              // Continua tentando próximo caminho
              console.log(`[mockData] ⚠️  Erro ao ler ${caminho}: ${e2.message}`);
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
          
          // Tenta múltiplos caminhos possíveis (Vercel pode ter estrutura diferente)
          const caminhos = [
            // Caminho padrão (desenvolvimento)
            path.join(basePath, "mock", "data", "q1_estatisticas.json"),
            // Standalone build (produção local e Vercel)
            path.join(basePath, ".next", "standalone", "mock", "data", "q1_estatisticas.json"),
            // Alternativa: caminho relativo ao arquivo atual
            path.join(__dirname || basePath, "..", "..", "mock", "data", "q1_estatisticas.json"),
            // Vercel pode usar caminho diferente
            path.join("/var", "task", ".next", "standalone", "mock", "data", "q1_estatisticas.json"),
            path.join("/var", "task", "mock", "data", "q1_estatisticas.json"),
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

