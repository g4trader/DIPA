import { AskParams, AskResponse } from "@/lib/dipamApi";
import { CopilotStructuredResponse } from "@/types/agent";
import { safeNumber } from "@/lib/formatters";

// APIs do Node.js - só disponíveis no servidor
let readFileSync: any;
let join: any;
let __dirname: any;

// Carrega APIs do Node.js apenas no servidor
if (typeof window === "undefined") {
  readFileSync = require("fs").readFileSync;
  join = require("path").join;
  const path = require("path");
  __dirname = path.dirname(__filename || __dirname || ".");
}

// Dados mock fallback (hardcoded) caso os arquivos não sejam encontrados
const DADOS_MOCK_FALLBACK = [
  {
    cliente_id: 1,
    nome: "Cliente Exemplo 1",
    segmento: "Segmento A",
    rota_id: "ROTA 301",
    vendedor_nome: "Vendedor Exemplo",
    vendedor_codigo: "V001",
    supervisor_nome: "Supervisor Exemplo",
    supervisor_codigo: "S001",
    data_ultima_compra: "2024-01-01",
    dias_sem_compra: 90
  },
  {
    cliente_id: 2,
    nome: "Cliente Exemplo 2",
    segmento: "Segmento B",
    rota_id: "ROTA 302",
    vendedor_nome: "Vendedor 2",
    vendedor_codigo: "V002",
    supervisor_nome: "Supervisor 2",
    supervisor_codigo: "S002",
    data_ultima_compra: "2024-02-15",
    dias_sem_compra: 150
  },
  {
    cliente_id: 3,
    nome: "Cliente Exemplo 3",
    segmento: "Segmento C",
    rota_id: "ROTA 303",
    vendedor_nome: "Vendedor 3",
    vendedor_codigo: "V003",
    supervisor_nome: "Supervisor 3",
    supervisor_codigo: "S003",
    data_ultima_compra: "2023-12-01",
    dias_sem_compra: 250
  },
  {
    cliente_id: 4,
    nome: "Cliente Exemplo 4",
    segmento: "Segmento A",
    rota_id: "ROTA 301",
    vendedor_nome: "Vendedor Exemplo",
    vendedor_codigo: "V001",
    supervisor_nome: "Supervisor Exemplo",
    supervisor_codigo: "S001",
    data_ultima_compra: "2023-06-01",
    dias_sem_compra: 400
  },
  {
    cliente_id: 5,
    nome: "Cliente Exemplo 5",
    segmento: "Segmento B",
    rota_id: "ROTA 302",
    vendedor_nome: "Vendedor 2",
    vendedor_codigo: "V002",
    supervisor_nome: "Supervisor 2",
    supervisor_codigo: "S002",
    data_ultima_compra: "2024-03-01",
    dias_sem_compra: 100
  }
];

// Cache para dados carregados (evita recarregar a cada requisição)
let q1ClientesDataCache: any[] | null = null;
let q1EstatisticasDataCache: any | null = null;
let dadosCarregadosCache = false;

/**
 * Classifica clientes por faixas de dias sem compra
 */
function classificarPorFaixas(dados: any[]): {
  "61_120": number;
  "121_180": number;
  "181_300": number;
  "acima_300": number;
} {
  const faixas = {
    "61_120": 0,
    "121_180": 0,
    "181_300": 0,
    "acima_300": 0,
  };
  
  for (const cliente of dados) {
    const dias = cliente.dias_sem_compra || 0;
    
    if (61 <= dias && dias <= 120) {
      faixas["61_120"]++;
    } else if (121 <= dias && dias <= 180) {
      faixas["121_180"]++;
    } else if (181 <= dias && dias <= 300) {
      faixas["181_300"]++;
    } else if (dias > 300) {
      faixas["acima_300"]++;
    }
  }
  
  return faixas;
}

// Função para carregar dados mock do sistema de arquivos
// Isso funciona tanto em desenvolvimento quanto em produção (Vercel)
// IMPORTANTE: Só funciona no servidor (API routes), não no cliente
function carregarDadosMock() {
  // Se estiver no cliente, retorna fallback imediatamente
  if (typeof window !== "undefined" || !readFileSync || !join) {
    console.warn("[dipamMockEngine] Executando no cliente, usando fallback");
    const faixasFallback = classificarPorFaixas(DADOS_MOCK_FALLBACK);
    return {
      q1Dados: DADOS_MOCK_FALLBACK,
      q1Estatisticas: {
        total_clientes: DADOS_MOCK_FALLBACK.length,
        faixas: faixasFallback,
      },
    };
  }
  
  // Se já carregou antes, verifica se são dados reais ou fallback
  // Se forem dados de fallback (5 clientes), tenta recarregar
  if (dadosCarregadosCache && q1ClientesDataCache && q1EstatisticasDataCache) {
    // Se os dados do cache são do fallback (5 clientes), ignora o cache e tenta recarregar
    if (q1ClientesDataCache.length === 5 && q1ClientesDataCache[0]?.nome === "Cliente Exemplo 1") {
      console.log(`[dipamMockEngine] ⚠️  Cache contém dados de fallback, tentando recarregar...`);
      // Limpa o cache para forçar recarregamento
      dadosCarregadosCache = false;
      q1ClientesDataCache = null;
      q1EstatisticasDataCache = null;
    } else {
      console.log(`[dipamMockEngine] ✅ Retornando dados do cache: ${q1ClientesDataCache.length} clientes`);
      return {
        q1Dados: q1ClientesDataCache,
        q1Estatisticas: q1EstatisticasDataCache,
      };
    }
  }
  
  try {
    // Usa process.cwd() que funciona tanto em dev quanto em produção
    const basePath = process.cwd();
    
    console.log(`[dipamMockEngine] 🔍 Tentando carregar dados mock... basePath: ${basePath}`);
    
    // Tenta diferentes caminhos possíveis (Vercel pode ter estrutura diferente)
    // Prioriza q1_clientes_sem_compra.json (dados reais dos CSVs), fallback para q1_dados_dw.json
    const caminhosPossiveis = [
      // Caminho padrão (desenvolvimento e produção local)
      join(basePath, "mock", "data", "q1_clientes_sem_compra.json"),
      // Vercel standalone build (produção) - caminho mais provável na Vercel
      join(basePath, ".next", "standalone", "mock", "data", "q1_clientes_sem_compra.json"),
      // Vercel serverless (alternativa)
      join(basePath, "mock", "data", "q1_clientes_sem_compra.json"),
      // Fallback para dados antigos
      join(basePath, "mock", "data", "q1_dados_dw.json"),
      join(basePath, ".next", "server", "mock", "data", "q1_clientes_sem_compra.json"),
      join(basePath, "..", "mock", "data", "q1_clientes_sem_compra.json"),
    ];
    
    // Se __dirname estiver disponível, tenta caminho relativo ao arquivo
    if (__dirname) {
      caminhosPossiveis.push(join(__dirname, "..", "..", "mock", "data", "q1_clientes_sem_compra.json"));
    }
    
    // Log todos os caminhos que serão tentados
    console.log(`[dipamMockEngine] 📂 Caminhos que serão tentados:`, caminhosPossiveis.slice(0, 3));
    
    let q1Dados: any[] = [];
    let q1Estatisticas: any = {
      total_clientes: 0,
      faixas: {
        "61_120": 0,
        "121_180": 0,
        "181_300": 0,
        "acima_300": 0,
      },
    };
    
    // Tenta importar diretamente primeiro (funciona no build do Next.js)
    try {
      // Tenta caminho relativo ao arquivo atual
      const q1ClientesModule = require("../../mock/data/q1_clientes_sem_compra.json");
      q1Dados = Array.isArray(q1ClientesModule) ? q1ClientesModule : (q1ClientesModule?.default || q1ClientesModule);
      if (q1Dados && q1Dados.length > 0) {
        console.log(`[dipamMockEngine] ✅ Dados Q1 importados via require(): ${q1Dados.length} clientes`);
      } else {
        throw new Error("Dados vazios após require()");
      }
    } catch (e: any) {
      console.log(`[dipamMockEngine] ⚠️  require() falhou: ${e.message}, tentando readFileSync...`);
      
      // Fallback: tenta carregar via readFileSync
      let dadosCarregados = false;
      for (const caminho of caminhosPossiveis) {
        try {
          const dadosRaw = readFileSync(caminho, "utf-8");
          const dadosParsed = JSON.parse(dadosRaw);
          q1Dados = Array.isArray(dadosParsed) ? dadosParsed : (dadosParsed?.dados || []);
          console.log(`[dipamMockEngine] ✅ Dados Q1 carregados via readFileSync: ${q1Dados.length} clientes de ${caminho}`);
          dadosCarregados = true;
          break;
        } catch (e2: any) {
          // Continua tentando próximo caminho
          console.log(`[dipamMockEngine] ⚠️  Não encontrado em ${caminho}: ${e2.message}`);
          // Em produção, log mais detalhado
          if (process.env.VERCEL || process.env.NODE_ENV === "production") {
            console.log(`[dipamMockEngine] 🔍 Detalhes do erro:`, {
              code: e2.code,
              errno: e2.errno,
              syscall: e2.syscall,
              path: caminho,
            });
          }
        }
      }
      
      // Se não conseguiu carregar do arquivo, tenta via fetch (API route)
      if (!dadosCarregados || q1Dados.length === 0) {
        console.log("[dipamMockEngine] ⚠️  Arquivo não encontrado via readFileSync, tentando via API route...");
        // Não tenta via fetch aqui porque estamos no servidor e pode causar loop
        // O fetch só funcionaria se estivéssemos em um contexto diferente
      }
      
      // Se ainda não conseguiu, usa fallback mas NÃO salva no cache
      if (!dadosCarregados || q1Dados.length === 0) {
        console.warn("[dipamMockEngine] ⚠️  Todos os métodos falharam, usando dados mock fallback.");
        console.warn("[dipamMockEngine] ⚠️  NÃO salvando fallback no cache - será tentado novamente na próxima requisição");
        q1Dados = DADOS_MOCK_FALLBACK;
        // NÃO salva no cache para que tente novamente na próxima vez
        return {
          q1Dados: DADOS_MOCK_FALLBACK,
          q1Estatisticas: {
            total_clientes: DADOS_MOCK_FALLBACK.length,
            faixas: classificarPorFaixas(DADOS_MOCK_FALLBACK),
          },
        };
      }
    }
    
    // Tenta carregar q1_estatisticas.json (dados reais dos CSVs)
    try {
      const q1StatsModule = require("../../mock/data/q1_estatisticas.json");
      q1Estatisticas = q1StatsModule?.default || q1StatsModule;
      console.log(`[dipamMockEngine] ✅ Estatísticas Q1 importadas via require()`);
    } catch (e: any) {
      console.log(`[dipamMockEngine] ⚠️  require() de estatísticas falhou: ${e.message}, tentando readFileSync...`);
      
      const caminhosEstatisticas = [
        // Caminho padrão (desenvolvimento e produção local)
        join(basePath, "mock", "data", "q1_estatisticas.json"),
        // Vercel standalone build (produção)
        join(basePath, ".next", "standalone", "mock", "data", "q1_estatisticas.json"),
        join(basePath, ".next", "server", "mock", "data", "q1_estatisticas.json"),
        join(basePath, "..", "mock", "data", "q1_estatisticas.json"),
      ];
      
      if (__dirname) {
        caminhosEstatisticas.push(join(__dirname, "..", "..", "mock", "data", "q1_estatisticas.json"));
      }
      
      let statsCarregadas = false;
      for (const caminho of caminhosEstatisticas) {
        try {
          const statsRaw = readFileSync(caminho, "utf-8");
          q1Estatisticas = JSON.parse(statsRaw);
          console.log(`[dipamMockEngine] ✅ Estatísticas Q1 carregadas via readFileSync de ${caminho}`);
          statsCarregadas = true;
          break;
        } catch (e2: any) {
          console.log(`[dipamMockEngine] ⚠️  Não encontrado em ${caminho}: ${e2.message}`);
        }
      }
      
      // Se não conseguiu carregar estatísticas, calcula a partir dos dados
      if (!statsCarregadas && q1Dados.length > 0) {
        const faixas = classificarPorFaixas(q1Dados);
        
        q1Estatisticas = {
          total_clientes: q1Dados.length,
          faixas,
        };
        console.log(`[dipamMockEngine] ✅ Estatísticas calculadas a partir dos dados`);
      }
    }
    
    // Normaliza estrutura de faixas (compatibilidade com formato antigo e novo)
    if (q1Estatisticas.faixas) {
      // Se está no formato antigo (faixa_61_120), converte para novo (61_120)
      if (q1Estatisticas.faixas.faixa_61_120 !== undefined) {
        q1Estatisticas.faixas = {
          "61_120": q1Estatisticas.faixas.faixa_61_120 || 0,
          "121_180": q1Estatisticas.faixas.faixa_121_180 || 0,
          "181_300": q1Estatisticas.faixas.faixa_181_300 || 0,
          "acima_300": q1Estatisticas.faixas.faixa_maior_300 || q1Estatisticas.faixas.faixa_acima_300 || 0,
        };
      }
    }
    
    // Só salva no cache se forem dados reais (não fallback)
    if (q1Dados.length > 5 || (q1Dados.length > 0 && q1Dados[0]?.nome !== "Cliente Exemplo 1")) {
      q1ClientesDataCache = q1Dados;
      q1EstatisticasDataCache = q1Estatisticas;
      dadosCarregadosCache = true;
      console.log(`[dipamMockEngine] ✅ Dados REAIS carregados e cacheados: ${q1Dados.length} clientes, total: ${q1Estatisticas.total_clientes}`);
    } else {
      console.warn(`[dipamMockEngine] ⚠️  Dados parecem ser fallback (${q1Dados.length} clientes), NÃO salvando no cache`);
    }
    
    return { q1Dados, q1Estatisticas };
  } catch (error) {
    console.error("[dipamMockEngine] ❌ Erro ao carregar dados mock, usando fallback:", error);
    if (error instanceof Error) {
      console.error("[dipamMockEngine] Stack:", error.stack);
    }
    // Retorna dados fallback em caso de erro
    const faixasFallback = classificarPorFaixas(DADOS_MOCK_FALLBACK);
    return {
      q1Dados: DADOS_MOCK_FALLBACK,
      q1Estatisticas: {
        total_clientes: DADOS_MOCK_FALLBACK.length,
        faixas: faixasFallback,
      },
    };
  }
}

/**
 * Detecta se a pergunta é sobre Q1 (clientes sem compra há mais de 60 dias)
 */
function detectarQ1(pergunta: string): boolean {
  const perguntaLower = pergunta.toLowerCase();
  
  // Padrões que indicam Q1
  const padroesQ1 = [
    "sem compra por mais de 60 dias",
    "sem compra há mais de 60 dias",
    "sem nenhuma compra por mais de 60 dias",
    "sem nenhuma compra há mais de 60 dias",
    "clientes ativos sem compra",
    "clientes sem compra",
    "mais de 60 dias sem comprar",
    "há mais de 60 dias sem comprar",
    "60 dias sem compra",
  ];
  
  return padroesQ1.some(padrao => perguntaLower.includes(padrao));
}

/**
 * Monta resumo executivo mock para Q1
 */
function montarResumoExecutivoQ1(
  totalClientes: number,
  faixas: ReturnType<typeof classificarPorFaixas>
): string {
  // Valida e normaliza totalClientes
  const total = typeof totalClientes === "number" && !isNaN(totalClientes) ? totalClientes : 0;
  
  // Valida e normaliza faixas
  const faixasValidas = {
    "61_120": typeof faixas["61_120"] === "number" ? faixas["61_120"] : 0,
    "121_180": typeof faixas["121_180"] === "number" ? faixas["121_180"] : 0,
    "181_300": typeof faixas["181_300"] === "number" ? faixas["181_300"] : 0,
    "acima_300": typeof faixas["acima_300"] === "number" ? faixas["acima_300"] : 0,
  };
  
  // Evita divisão por zero
  const calcularPercentual = (valor: number, total: number): string => {
    if (total === 0 || !total) return "0.0";
    if (!valor || valor === 0) return "0.0";
    return ((valor / total) * 100).toFixed(1);
  };
  
  if (total === 0) {
    return "Não foram identificados clientes ativos sem compra há mais de 60 dias no momento. " +
      "Recomendamos monitorar regularmente este indicador para identificar oportunidades de reativação.";
  }
  
  return `Identificamos ${total.toLocaleString("pt-BR")} clientes ativos sem compra há mais de 60 dias. ` +
    `Destes, ${faixasValidas["61_120"]} estão na faixa de 61-120 dias (${calcularPercentual(faixasValidas["61_120"], total)}%), ` +
    `${faixasValidas["121_180"]} entre 121-180 dias (${calcularPercentual(faixasValidas["121_180"], total)}%), ` +
    `${faixasValidas["181_300"]} entre 181-300 dias (${calcularPercentual(faixasValidas["181_300"], total)}%) ` +
    `e ${faixasValidas["acima_300"]} com mais de 300 dias sem compra (${calcularPercentual(faixasValidas["acima_300"], total)}%). ` +
    `Recomendamos ações de reativação prioritárias para os clientes com maior tempo sem compra.`;
}

/**
 * Executa mock ask - função principal do motor mock
 */
export async function executarMockAsk(payload: AskParams): Promise<AskResponse> {
  const { pergunta } = payload;
  
  // Detecta se é Q1
  if (detectarQ1(pergunta)) {
    return executarMockQ1(payload);
  }
  
  // Para outras perguntas, retorna resposta padrão
  return {
    question: pergunta,
    intent: "outros",
    confidence: 0.5,
    resumoExecutivo: "Este é um ambiente de demonstração (modo mock). Apenas a consulta Q1 (clientes sem compra há mais de 60 dias) está mockada. Para outras consultas, use o ambiente de produção.",
    timestamp: new Date().toISOString(),
  };
}

/**
 * Executa mock específico para Q1
 */
function executarMockQ1(payload: AskParams): AskResponse {
  // Carrega dados mock (sempre recarrega para garantir dados atualizados)
  const { q1Dados, q1Estatisticas } = carregarDadosMock();
  
  const dados = q1Dados || [];
  
  // Debug: log dos dados carregados (sempre em desenvolvimento, também em produção para debug)
  console.log("[MOCK][Q1] Dados carregados:", {
    total_clientes_dados: dados.length,
    total_clientes_json: q1Estatisticas?.total_clientes || 0,
    faixas_json: q1Estatisticas?.faixas || {},
    dados_sample: dados.slice(0, 2),
  });
  
  // Usa estatísticas carregadas ou calcula
  let faixas: ReturnType<typeof classificarPorFaixas>;
  let totalClientes: number;
  
  if (q1Estatisticas && q1Estatisticas.faixas && typeof q1Estatisticas.total_clientes === "number") {
    // Usa estatísticas do JSON
    faixas = q1Estatisticas.faixas as any;
    totalClientes = q1Estatisticas.total_clientes;
  } else {
    // Calcula a partir dos dados
    faixas = classificarPorFaixas(dados);
    totalClientes = Array.isArray(dados) ? dados.length : 0;
  }
  
  // Garante que totalClientes é um número válido
  if (typeof totalClientes !== "number" || isNaN(totalClientes)) {
    totalClientes = 0;
  }
  
  // Garante que faixas está no formato correto
  if (!faixas || typeof faixas !== "object") {
    faixas = classificarPorFaixas(dados);
  }
  
  // Monta resumo executivo
  const resumoExecutivo = montarResumoExecutivoQ1(totalClientes, faixas);
  
  // Monta tabela principal
  // Garante que todos os valores numéricos são números válidos
  const tabelaPrincipal = {
    colunas: ["Cliente ID", "Nome", "Dias sem Compra", "Vendedor", "Supervisor"],
    linhas: dados.map((cliente: any) => [
      safeNumber(cliente.cliente_id, 0),
      String(cliente.nome || ""),
      safeNumber(cliente.dias_sem_compra, 0),
      String(cliente.vendedor_nome || cliente.vendedor_codigo || cliente.rota_id || ""),
      String(cliente.supervisor_nome || cliente.supervisor_codigo || ""),
    ]),
  };
  
  // Monta structured response
  const structured: CopilotStructuredResponse = {
    resumo_executivo: resumoExecutivo,
    secoes: [
      {
        titulo: "Clientes sem Compra há Mais de 60 Dias",
        tipo: "lista_clientes",
        dados: dados.slice(0, 10), // Top 10 para preview
      },
    ],
    detalhe_tabela: tabelaPrincipal,
    contexto_debug: {
      intent: "clientes_sem_compra",
      entidades: {},
      fonte_dados: "mock_data",
      total_registros: dados.length,
      tempo_processamento_ms: 0,
    },
  };
  
  // Log de sanidade antes de retornar
  console.log("[MOCK][Q1] Estatísticas finais:", {
    big_number: totalClientes,
    total_clientes_json: q1Estatisticas?.total_clientes || 0,
    faixas: faixas,
    total_registros_tabela: dados.length,
  });
  
  // Monta resposta completa
  const resposta: AskResponse = {
    question: payload.pergunta,
    intent: "clientes_sem_compra",
    confidence: 0.92, // Confiança fixa para mock
    resumoExecutivo: resumoExecutivo,
    timestamp: new Date().toISOString(),
    payload: {
      intent: "clientes_sem_compra",
      intentLabel: "Clientes sem Compra há Mais de 60 Dias",
      confidence: 0.92,
      question: payload.pergunta,
      structured: structured,
    },
    structured: structured,
    // Adiciona big_number explicitamente para compatibilidade
    contexto: {
      big_number: totalClientes,
      total_clientes: totalClientes,
      faixas: faixas,
    },
  };
  
  return resposta;
}
