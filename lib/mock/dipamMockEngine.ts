import { AskParams, AskResponse } from "@/lib/dipamApi";
import { CopilotStructuredResponse } from "@/types/agent";
import { safeNumber } from "@/lib/formatters";

// Tenta importar JSONs diretamente (funciona no build do Next.js/Vercel)
let q1ClientesData: any[] | null = null;
let q1EstatisticasData: any | null = null;

try {
  // Importação direta de JSON (funciona no build do Next.js)
  // Usa caminho relativo ao invés de alias para garantir que funcione
  const q1ClientesModule = require("../../mock/data/q1_clientes_sem_compra.json");
  q1ClientesData = Array.isArray(q1ClientesModule) ? q1ClientesModule : (q1ClientesModule?.default || q1ClientesModule);
  console.log(`[dipamMockEngine] ✅ Dados Q1 importados diretamente: ${q1ClientesData?.length || 0} clientes`);
} catch (e: any) {
  // Se falhar, tentará carregar via readFileSync
  console.log(`[dipamMockEngine] ⚠️  Não foi possível importar JSON diretamente: ${e.message}, tentando readFileSync...`);
}

try {
  const q1StatsModule = require("../../mock/data/q1_estatisticas.json");
  q1EstatisticasData = q1StatsModule?.default || q1StatsModule;
  console.log(`[dipamMockEngine] ✅ Estatísticas Q1 importadas diretamente`);
} catch (e: any) {
  // Se falhar, tentará carregar via readFileSync
  console.log(`[dipamMockEngine] ⚠️  Não foi possível importar estatísticas diretamente: ${e.message}`);
}

// APIs do Node.js - só disponíveis no servidor (fallback)
let readFileSync: any;
let join: any;

// Carrega APIs do Node.js apenas no servidor
if (typeof window === "undefined") {
  readFileSync = require("fs").readFileSync;
  join = require("path").join;
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
  
  try {
    // Usa process.cwd() que funciona tanto em dev quanto em produção
    const basePath = process.cwd();
    
    // Tenta diferentes caminhos possíveis (Vercel pode ter estrutura diferente)
    // Prioriza q1_clientes_sem_compra.json (dados reais dos CSVs), fallback para q1_dados_dw.json
    const caminhosPossiveis = [
      join(basePath, "mock", "data", "q1_clientes_sem_compra.json"),
      join(basePath, "mock", "data", "q1_dados_dw.json"), // Fallback para dados antigos
      join(basePath, ".next", "server", "mock", "data", "q1_clientes_sem_compra.json"),
      join(basePath, "..", "mock", "data", "q1_clientes_sem_compra.json"),
    ];
    
    let q1Dados: any[] = [];
    let q1Estatisticas: any = {
      total_clientes: 0,
      faixas: {
        faixa_61_120: 0,
        faixa_121_180: 0,
        faixa_181_300: 0,
        faixa_maior_300: 0,
      },
    };
    
    // Prioriza dados importados diretamente (funciona no build do Next.js/Vercel)
    if (q1ClientesData && Array.isArray(q1ClientesData) && q1ClientesData.length > 0) {
      q1Dados = q1ClientesData;
      console.log(`[dipamMockEngine] ✅ Dados Q1 carregados via import direto: ${q1Dados.length} clientes`);
    } else {
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
        } catch (e: any) {
          // Continua tentando próximo caminho
          if (process.env.NODE_ENV === "development") {
            console.log(`[dipamMockEngine] ⚠️  Não encontrado em ${caminho}: ${e.message}`);
          }
        }
      }
      
      // Se não conseguiu carregar do arquivo, usa fallback
      if (!dadosCarregados || q1Dados.length === 0) {
        console.warn("[dipamMockEngine] ⚠️  Arquivo não encontrado, usando dados mock fallback.");
        q1Dados = DADOS_MOCK_FALLBACK;
      }
    }
    
    // Prioriza estatísticas importadas diretamente
    if (q1EstatisticasData && q1EstatisticasData.total_clientes) {
      q1Estatisticas = q1EstatisticasData;
      console.log(`[dipamMockEngine] ✅ Estatísticas Q1 carregadas via import direto`);
    } else {
      // Fallback: tenta carregar via readFileSync
      const caminhosEstatisticas = [
        join(basePath, "mock", "data", "q1_estatisticas.json"),
        join(basePath, ".next", "server", "mock", "data", "q1_estatisticas.json"),
        join(basePath, "..", "mock", "data", "q1_estatisticas.json"),
      ];
      
      let statsCarregadas = false;
      for (const caminho of caminhosEstatisticas) {
        try {
          const statsRaw = readFileSync(caminho, "utf-8");
          q1Estatisticas = JSON.parse(statsRaw);
          console.log(`[dipamMockEngine] ✅ Estatísticas Q1 carregadas via readFileSync de ${caminho}`);
          statsCarregadas = true;
          break;
        } catch (e) {
          // Continua tentando próximo caminho
        }
      }
      
      // Se não conseguiu carregar estatísticas, calcula a partir dos dados
      if (!statsCarregadas && q1Dados.length > 0) {
        const faixas = classificarPorFaixas(q1Dados);
        
        q1Estatisticas = {
          total_clientes: q1Dados.length,
          faixas,
        };
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
    
    return { q1Dados, q1Estatisticas };
  } catch (error) {
    console.error("[dipamMockEngine] ❌ Erro ao carregar dados mock, usando fallback:", error);
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

// Carrega dados mock uma vez no carregamento do módulo
const { q1Dados, q1Estatisticas } = carregarDadosMock();

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
  // Lê dados mock (já normalizados no carregamento)
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

