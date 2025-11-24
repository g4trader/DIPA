import { AskParams, AskResponse } from "@/lib/dipamApi";
import { CopilotStructuredResponse } from "@/types/agent";

// Importa dados mock (serão criados pelo script Python)
// Next.js suporta imports JSON estáticos com resolveJsonModule: true
// @ts-ignore - JSON imports podem não ter tipos em tempo de compilação
import q1DadosRaw from "@/mock/data/q1_dados_dw.json";
// @ts-ignore
import q1EstatisticasRaw from "@/mock/data/q1_estatisticas.json";

// Normaliza dados mock
const q1Dados: any[] = Array.isArray(q1DadosRaw) 
  ? q1DadosRaw 
  : ((q1DadosRaw as any)?.dados || []);

const q1Estatisticas: any = q1EstatisticasRaw || {
  total_clientes: 0,
  faixas: {
    faixa_61_120: 0,
    faixa_121_180: 0,
    faixa_181_300: 0,
    faixa_maior_300: 0,
  },
};

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
  faixa_61_120: number;
  faixa_121_180: number;
  faixa_181_300: number;
  faixa_maior_300: number;
} {
  const faixas = {
    faixa_61_120: 0,
    faixa_121_180: 0,
    faixa_181_300: 0,
    faixa_maior_300: 0,
  };
  
  for (const cliente of dados) {
    const dias = cliente.dias_sem_compra || 0;
    
    if (61 <= dias && dias <= 120) {
      faixas.faixa_61_120++;
    } else if (121 <= dias && dias <= 180) {
      faixas.faixa_121_180++;
    } else if (181 <= dias && dias <= 300) {
      faixas.faixa_181_300++;
    } else if (dias > 300) {
      faixas.faixa_maior_300++;
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
  // Evita divisão por zero
  const calcularPercentual = (valor: number, total: number): string => {
    if (total === 0) return "0.0";
    return ((valor / total) * 100).toFixed(1);
  };
  
  if (totalClientes === 0) {
    return "Não foram identificados clientes ativos sem compra há mais de 60 dias no momento. " +
      "Recomendamos monitorar regularmente este indicador para identificar oportunidades de reativação.";
  }
  
  return `Identificamos ${totalClientes.toLocaleString("pt-BR")} clientes ativos sem compra há mais de 60 dias. ` +
    `Destes, ${faixas.faixa_61_120} estão na faixa de 61-120 dias (${calcularPercentual(faixas.faixa_61_120, totalClientes)}%), ` +
    `${faixas.faixa_121_180} entre 121-180 dias (${calcularPercentual(faixas.faixa_121_180, totalClientes)}%), ` +
    `${faixas.faixa_181_300} entre 181-300 dias (${calcularPercentual(faixas.faixa_181_300, totalClientes)}%) ` +
    `e ${faixas.faixa_maior_300} com mais de 300 dias sem compra (${calcularPercentual(faixas.faixa_maior_300, totalClientes)}%). ` +
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
  // Lê dados mock (já normalizados no import)
  const dados = q1Dados || [];
  
  // Debug: log dos dados carregados
  if (process.env.NODE_ENV === "development") {
    console.log("[dipamMockEngine] Dados Q1 carregados:", dados.length, "clientes");
  }
  
  // Calcula faixas
  const faixas = classificarPorFaixas(dados);
  
  // Monta resumo executivo
  const resumoExecutivo = montarResumoExecutivoQ1(dados.length, faixas);
  
  // Monta tabela principal
  const tabelaPrincipal = {
    colunas: ["Cliente ID", "Nome", "Dias sem Compra", "Vendedor", "Supervisor"],
    linhas: dados.map((cliente: any) => [
      cliente.cliente_id || "",
      cliente.nome || "",
      cliente.dias_sem_compra || 0,
      cliente.vendedor_nome || cliente.vendedor_codigo || cliente.rota_id || "",
      cliente.supervisor_nome || cliente.supervisor_codigo || "",
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
  };
  
  return resposta;
}

