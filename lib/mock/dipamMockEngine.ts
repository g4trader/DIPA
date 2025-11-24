import { AskParams, AskResponse } from "@/lib/dipamApi";
import { CopilotStructuredResponse } from "@/types/agent";
import { safeNumber } from "@/lib/formatters";
import { getQ1ClientesMock, getQ1EstatisticasMock } from "./mockData";

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
    
    // Tenta usar dados carregados dinamicamente primeiro
    let dadosCarregados = false;
    
    const q1ClientesMock = getQ1ClientesMock();
    if (q1ClientesMock && Array.isArray(q1ClientesMock) && q1ClientesMock.length > 0) {
      q1Dados = q1ClientesMock;
      console.log(`[dipamMockEngine] ✅ Dados Q1 carregados dinamicamente: ${q1Dados.length} clientes`);
      dadosCarregados = true;
    } else {
      console.log(`[dipamMockEngine] ⚠️  Import estático vazio, tentando require()...`);
      
      // Fallback: tenta require()
      try {
        const q1ClientesModule = require("../../mock/data/q1_clientes_sem_compra.json");
        q1Dados = Array.isArray(q1ClientesModule) ? q1ClientesModule : (q1ClientesModule?.default || q1ClientesModule);
        if (q1Dados && q1Dados.length > 0) {
          console.log(`[dipamMockEngine] ✅ Dados Q1 importados via require(): ${q1Dados.length} clientes`);
          dadosCarregados = true;
        }
      } catch (e2: any) {
        console.log(`[dipamMockEngine] ⚠️  require() falhou: ${e2.message}, tentando readFileSync...`);
      }
    }
    
    // Se ainda não carregou, tenta readFileSync
    if (!dadosCarregados) {
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
    
    // Tenta usar estatísticas carregadas dinamicamente primeiro
    let statsCarregadas = false;
    
    const q1EstatisticasMock = getQ1EstatisticasMock();
    if (q1EstatisticasMock && q1EstatisticasMock.total_clientes) {
      q1Estatisticas = q1EstatisticasMock;
      console.log(`[dipamMockEngine] ✅ Estatísticas Q1 carregadas dinamicamente`);
      statsCarregadas = true;
    } else {
      console.log(`[dipamMockEngine] ⚠️  Import estático de estatísticas vazio, tentando require()...`);
      
      // Fallback: tenta require()
      try {
        const q1StatsModule = require("../../mock/data/q1_estatisticas.json");
        q1Estatisticas = q1StatsModule?.default || q1StatsModule;
        console.log(`[dipamMockEngine] ✅ Estatísticas Q1 importadas via require()`);
        statsCarregadas = true;
      } catch (e2: any) {
        console.log(`[dipamMockEngine] ⚠️  require() de estatísticas falhou: ${e2.message}, tentando readFileSync...`);
      }
    }
    
    // Se ainda não carregou estatísticas, tenta readFileSync
    if (!statsCarregadas) {
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
 * Calcula percentual de forma segura
 */
function calcularPercentual(valor: number, total: number): string {
  if (total === 0 || !total) return "0.0";
  if (!valor || valor === 0) return "0.0";
  return ((valor / total) * 100).toFixed(1);
}

/**
 * Monta resumo executivo mock para Q1 (formato curto, 3-4 linhas)
 */
function montarResumoExecutivoQ1(
  totalClientes: number,
  faixas: ReturnType<typeof classificarPorFaixas>
): string {
  const total = typeof totalClientes === "number" && !isNaN(totalClientes) ? totalClientes : 0;
  
  const faixasValidas = {
    "61_120": typeof faixas["61_120"] === "number" ? faixas["61_120"] : 0,
    "121_180": typeof faixas["121_180"] === "number" ? faixas["121_180"] : 0,
    "181_300": typeof faixas["181_300"] === "number" ? faixas["181_300"] : 0,
    "acima_300": typeof faixas["acima_300"] === "number" ? faixas["acima_300"] : 0,
  };
  
  if (total === 0) {
    return "Não foram identificados clientes ativos sem compra há mais de 60 dias no momento. " +
      "Recomendamos monitorar regularmente este indicador para identificar oportunidades de reativação.";
  }
  
  const pct61_120 = calcularPercentual(faixasValidas["61_120"], total);
  const pct121_180 = calcularPercentual(faixasValidas["121_180"], total);
  const pct181_300 = calcularPercentual(faixasValidas["181_300"], total);
  const pctAcima300 = calcularPercentual(faixasValidas["acima_300"], total);
  
  return `Identificamos ${total.toLocaleString("pt-BR")} clientes ativos sem compra há mais de 60 dias. ` +
    `Destes, ${faixasValidas["61_120"]} estão na faixa de 61-120 dias (${pct61_120}%), ` +
    `${faixasValidas["121_180"]} entre 121-180 dias (${pct121_180}%), ` +
    `${faixasValidas["181_300"]} entre 181-300 dias (${pct181_300}%) ` +
    `e ${faixasValidas["acima_300"]} com mais de 300 dias sem compra (${pctAcima300}%). ` +
    `O foco de curto prazo deve ser nos clientes com 61-120 dias, que representam a maior oportunidade de reativação.`;
}

/**
 * Gera markdown executivo completo para Q1 (mesma estrutura da Q1 real)
 * Inclui: Resumo Executivo, Impactos Comerciais, Plano Prioritário de Ação
 */
function gerarMarkdownExecutivoQ1(
  totalClientes: number,
  faixas: ReturnType<typeof classificarPorFaixas>,
  dados: any[]
): string {
  const total = typeof totalClientes === "number" && !isNaN(totalClientes) ? totalClientes : 0;
  
  const faixasValidas = {
    "61_120": typeof faixas["61_120"] === "number" ? faixas["61_120"] : 0,
    "121_180": typeof faixas["121_180"] === "number" ? faixas["121_180"] : 0,
    "181_300": typeof faixas["181_300"] === "number" ? faixas["181_300"] : 0,
    "acima_300": typeof faixas["acima_300"] === "number" ? faixas["acima_300"] : 0,
  };
  
  if (total === 0) {
    return `## Resumo Executivo

Não foram identificados clientes ativos sem compra há mais de 60 dias no momento. Recomendamos monitorar regularmente este indicador para identificar oportunidades de reativação.

## Impactos Comerciais

A ausência de clientes inativos indica saúde da carteira neste recorte específico. Mantenha o monitoramento para detectar precocemente possíveis migrações.

## Plano Prioritário de Ação (Próximos 7 dias)

- Manter rotina de monitoramento semanal deste indicador
- Validar se a ausência de inativos é resultado de ações de reativação recentes
- Documentar boas práticas que mantiveram a carteira ativa`;
  }
  
  const pct61_120 = calcularPercentual(faixasValidas["61_120"], total);
  const pct121_180 = calcularPercentual(faixasValidas["121_180"], total);
  const pct181_300 = calcularPercentual(faixasValidas["181_300"], total);
  const pctAcima300 = calcularPercentual(faixasValidas["acima_300"], total);
  
  // Analisa distribuição por rotas/supervisões (se disponível)
  const rotasUnicas = new Set<string>();
  const supervisoesUnicas = new Set<string>();
  dados.forEach((cliente: any) => {
    if (cliente.rota_id) rotasUnicas.add(String(cliente.rota_id));
    if (cliente.supervisor_nome || cliente.supervisor_codigo) {
      supervisoesUnicas.add(String(cliente.supervisor_nome || cliente.supervisor_codigo));
    }
  });
  
  const totalRotas = rotasUnicas.size;
  const totalSupervisoes = supervisoesUnicas.size;
  
  // Gera markdown estruturado (formato executivo enxuto, 3-4 linhas máximo no Resumo Executivo)
  // IMPORTANTE: Segue exatamente o formato da produção real (llm_integration_intent.py linha 735-777)
  const markdown = `## Resumo Executivo

Identificamos ${total.toLocaleString("pt-BR")} clientes ativos sem compra há mais de 60 dias. ${faixasValidas["61_120"]} clientes (${pct61_120}%) estão na faixa de 61-120 dias, representando a maior oportunidade de reativação imediata. ${faixasValidas["121_180"]} clientes (${pct121_180}%) estão entre 121-180 dias, ${faixasValidas["181_300"]} (${pct181_300}%) entre 181-300 dias e ${faixasValidas["acima_300"]} (${pctAcima300}%) com mais de 300 dias sem compra.

## Impactos Comerciais

- **Perda de receita recorrente**: A ausência de compras por período prolongado impacta diretamente o faturamento mensal e a previsibilidade de receita.
- **Risco de migração de carteira**: Clientes inativos por mais de 120 dias apresentam maior probabilidade de migração para concorrentes ou mudança de padrão de compra.
- **Concentração operacional**: A distribuição dos clientes inativos está presente em ${totalRotas > 0 ? `${totalRotas} rotas distintas` : "múltiplas rotas"}, ${totalSupervisoes > 0 ? `envolvendo ${totalSupervisoes} supervisões` : "com impacto em diferentes supervisões"}, indicando necessidade de ação coordenada.
- **Oportunidade de recuperação**: A faixa de 61-120 dias concentra ${pct61_120}% dos clientes inativos, representando a melhor janela de oportunidade para reativação com menor esforço comercial.

## Plano Prioritário de Ação (Próximos 7 dias)

- **Prioridade 1 (61-120 dias - ${faixasValidas["61_120"]} clientes)**: Recontato imediato pela equipe comercial, campanhas de reativação com SKU âncora por rota, e alocação de energia de curto prazo da equipe para esta faixa.
- **Prioridade 2 (121-180 dias - ${faixasValidas["121_180"]} clientes)**: Ações coordenadas com supervisão, acompanhamento de rotas específicas e análise de causas raiz da inatividade.
- **Prioridade 3 (181-300 dias - ${faixasValidas["181_300"]} clientes)**: Avaliação caso a caso, priorizando clientes com histórico de ticket médio elevado ou importância estratégica.
- **Não priorizar (>300 dias - ${faixasValidas["acima_300"]} clientes)**: Carteira fria com baixa probabilidade de reativação. Manter em monitoramento passivo, sem alocação de recursos comerciais ativos.`;
  
  return markdown;
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
 * 
 * IMPORTANTE: Este mock simula apenas a parte DW (dados_dw).
 * O texto executivo é gerado localmente usando a mesma lógica do LLM,
 * mas sem chamar o LLM (já que estamos no frontend).
 */
function executarMockQ1(payload: AskParams): AskResponse {
  // Carrega dados mock (sempre recarrega para garantir dados atualizados)
  const { q1Dados, q1Estatisticas } = carregarDadosMock();
  
  const dados = q1Dados || [];
  
  // Debug: log dos dados carregados (apenas em desenvolvimento)
  if (process.env.NODE_ENV === "development") {
    console.log("[Q1 MOCK] total_clientes_q1", dados.length, "linhas tabela_principal", dados.length);
    console.log("[MOCK][Q1] Dados carregados:", {
      total_clientes_dados: dados.length,
      total_clientes_json: q1Estatisticas?.total_clientes || 0,
      faixas_json: q1Estatisticas?.faixas || {},
      dados_sample: dados.slice(0, 2),
    });
  }
  
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
  
  // Monta resumo executivo (formato curto)
  const resumoExecutivo = montarResumoExecutivoQ1(totalClientes, faixas);
  
  // Gera markdown executivo completo (mesma estrutura da Q1 real)
  const respostaMarkdown = gerarMarkdownExecutivoQ1(totalClientes, faixas, dados);
  
  // Monta tabela principal com título "Dados Analíticos - Consulta Geral" (mesma estrutura da Q1 real)
  // Garante que todos os valores numéricos são números válidos
  // IMPORTANTE: Usa a mesma lógica do mapper_handler_refatorado.py (linha 261-273)
  const tabelaPrincipal = {
    titulo: "Dados Analíticos - Consulta Geral",
    colunas: ["Cliente ID", "Nome", "Dias sem Compra", "Vendedor", "Supervisor"],
    linhas: dados.map((cliente: any) => {
      // Usa mesma lógica de fallback do mapper real (mapper_handler_refatorado.py linha 268-269)
      const vendedor = cliente.vendedor_nome || cliente.vendedor_codigo || cliente.rota_id || "";
      const supervisor = cliente.supervisor_nome || cliente.supervisor_codigo || "";
      
      return [
        safeNumber(cliente.cliente_id, 0),
        String(cliente.nome || ""),
        safeNumber(cliente.dias_sem_compra, 0),
        String(vendedor || "—"),
        String(supervisor || "—"),
      ];
    }),
  };
  
  // Monta structured response (mesma estrutura da Q1 real)
  const structured: CopilotStructuredResponse = {
    resumo_executivo: resumoExecutivo,
    respostaMarkdown: respostaMarkdown, // Adiciona markdown completo
    secoes: [
      {
        tipo: "tabela_detalhada",
        titulo: "Dados Analíticos - Consulta Geral",
        dados: dados.map((cliente: any) => {
          // Converte para formato de seção (dicionário)
          const vendedor = cliente.vendedor_nome || cliente.vendedor_codigo || cliente.rota_id || "—";
          const supervisor = cliente.supervisor_nome || cliente.supervisor_codigo || "—";
          
          return {
            "Cliente ID": safeNumber(cliente.cliente_id, 0),
            "Nome": String(cliente.nome || ""),
            "Dias sem Compra": safeNumber(cliente.dias_sem_compra, 0),
            "Vendedor": String(vendedor),
            "Supervisor": String(supervisor),
          };
        }),
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
  
  // Monta resposta completa (mesma estrutura da Q1 real)
  // IMPORTANTE: O mock simula apenas a parte DW, mas retorna estrutura compatível com o frontend
  // O frontend busca tabela_principal em jsonTecnico.tabela_principal
  const resposta: AskResponse = {
    question: payload.pergunta,
    intent: "clientes_sem_compra",
    confidence: 0.92, // Confiança fixa para mock (em produção, seria calculada por _calcular_confianca_q1)
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
    // Adiciona respostaMarkdown para o frontend processar os blocos executivos
    // Este markdown é gerado localmente usando a mesma lógica do LLM, mas sem chamar o LLM
    respostaMarkdown: respostaMarkdown,
    // Adiciona big_number explicitamente para compatibilidade
    // IMPORTANTE: big_number = total_clientes_q1 (COUNT(DISTINCT cliente_id))
    contexto: {
      big_number: totalClientes, // Total de clientes únicos (mesmo que total_clientes_q1)
      total_clientes: totalClientes,
      total_clientes_q1: totalClientes, // Adiciona campo explícito para compatibilidade
      faixas: faixas,
      // Adiciona jsonTecnico com tabela_principal (formato esperado pelo frontend)
      // Estrutura igual ao que o mapper_handler_refatorado.py retorna
      jsonTecnico: {
        tabela_principal: [tabelaPrincipal], // Array com a tabela (formato esperado pelo frontend)
      },
      // Adiciona dados_dw estruturados (mesma estrutura do orquestrador)
      dados_dw: {
        status: "ok",
        mensagem: `Dados consultados com sucesso. ${totalClientes} registro(s) encontrado(s).`,
        dados: dados, // Lista de clientes (mesma estrutura do orquestrador)
        classificacao_faixas: {
          total: totalClientes,
          faixa_61_120: faixas["61_120"],
          faixa_121_180: faixas["121_180"],
          faixa_181_300: faixas["181_300"],
          faixa_mais_300: faixas["acima_300"],
          percentual_61_120: totalClientes > 0 ? (faixas["61_120"] / totalClientes) * 100 : 0,
          percentual_121_180: totalClientes > 0 ? (faixas["121_180"] / totalClientes) * 100 : 0,
          percentual_181_300: totalClientes > 0 ? (faixas["181_300"] / totalClientes) * 100 : 0,
          percentual_mais_300: totalClientes > 0 ? (faixas["acima_300"] / totalClientes) * 100 : 0,
        },
      },
    },
  };
  
  return resposta;
}
