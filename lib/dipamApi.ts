/**
 * Cliente HTTP para integração com a API do Dipam AI
 * 
 * Este módulo fornece funções tipadas para comunicação com o backend FastAPI
 * do Dipam AI, incluindo endpoints para perguntas ao agente e preview de dados.
 */

/**
 * URL base da API do Dipam AI
 * 
 * Lê da variável de ambiente NEXT_PUBLIC_API_BASE_URL (padrão) ou
 * NEXT_PUBLIC_DIPAM_API_URL (compatibilidade) ou usa
 * http://localhost:8000 como fallback apenas em desenvolvimento
 */
export const DIPAM_API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.NEXT_PUBLIC_DIPAM_API_URL ||
  (typeof window !== "undefined" ? "http://localhost:8000" : "http://localhost:8000");

/**
 * Parâmetros para a função askDipamAgent
 */
export type AskParams = {
  /** Pergunta a ser enviada ao agente */
  pergunta: string;
  /** ID do usuário (opcional) */
  usuarioId?: string;
  /** Papel do usuário: diretor, supervisor, vendedor ou outro (opcional) */
  papel?: "diretor" | "supervisor" | "vendedor" | string;
};

/**
 * KPIs estruturados para resposta do agente
 */
export type KpisData = {
  /** Label do mês/ano (ex.: "agosto de 2025") */
  mesAnoLabel: string;
  /** Número de vendedores que bateram a meta */
  vendedoresQueBateram: number;
  /** Atingimento médio percentual */
  atingimentoMedio: number;
};

/**
 * Dados de um vendedor no ranking
 */
export type TopVendedor = {
  /** Posição no ranking */
  rank: number;
  /** Nome do vendedor (ex.: "ROTA 77") */
  nome: string;
  /** Rota do vendedor (opcional) */
  rota?: string;
  /** Supervisor (opcional) */
  supervisor?: string;
  /** Meta do vendedor */
  meta: number;
  /** Realizado do vendedor */
  realizado: number;
  /** Atingimento percentual */
  atingimento: number;
};

/**
 * Resposta da API para uma pergunta ao agente
 * 
 * Este tipo corresponde ao formato retornado pelo endpoint /ask
 * após as mudanças implementadas no backend para extrair dados estruturados.
 */
/**
 * Payload estruturado para resposta do Copilot
 */
export type CopilotAnswerPayload = {
  intent: string;
  intentLabel: string;
  confidence: number;
  question: string;
  resumoExecutivo?: string;
  insights?: string;
  observacoes?: string;
  kpis?: KpisData;
  topVendedores?: TopVendedor[];
  respostaMarkdown?: string;
};

export type AskResponse = {
  /** Pergunta original do usuário */
  question: string;
  /** Intent detectado pela análise da pergunta */
  intent: string;
  /** Nível de confiança da resposta (0-1) */
  confidence: number;
  /** Resumo executivo extraído da resposta */
  resumoExecutivo: string;
  /** KPIs estruturados (opcional) */
  kpis?: KpisData;
  /** Top vendedores (opcional) */
  topVendedores?: TopVendedor[];
  /** Lista de insights/recomendações (opcional) */
  insights?: string[] | string;
  /** Lista de observações sobre os dados (opcional) */
  observacoes?: string[] | string;
  /** Contexto adicional retornado pelo agente */
  contexto?: Record<string, any>;
  /** Timestamp da resposta */
  timestamp: string;
  /** Payload estruturado para o CopilotAnswerCard */
  payload?: CopilotAnswerPayload;
};

/**
 * Parâmetros para a função previewVendedor
 */
export type PreviewVendedorParams = {
  /** Nome ou ID do vendedor */
  vendedor: string;
  /** Mês e ano no formato YYYY-MM */
  mesAno: string;
};

/**
 * Resposta da API para preview de vendedor
 */
export type PreviewVendedorResponse = {
  /** Nome ou ID do vendedor */
  vendedor: string;
  /** Mês e ano no formato YYYY-MM */
  mes_ano: string;
  /** Dados do vendedor para o período */
  dados: Record<string, any>;
  /** Timestamp da resposta */
  timestamp: string;
};

/**
 * Classe de erro customizada para erros da API do Dipam AI
 */
export class DipamApiError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public response?: any
  ) {
    super(message);
    this.name = "DipamApiError";
    Object.setPrototypeOf(this, DipamApiError.prototype);
  }
}

/**
 * Faz uma requisição ao endpoint /ask da API do Dipam AI
 * 
 * Envia uma pergunta ao agente inteligente e retorna a resposta estruturada
 * com intent, contexto e nível de confiança.
 * 
 * @param params - Parâmetros da pergunta incluindo pergunta, usuarioId e papel
 * @returns Promise com a resposta do agente
 * @throws DipamApiError em caso de erro de rede ou status HTTP != 200
 * 
 * @example
 * ```ts
 * const resposta = await askDipamAgent({
 *   pergunta: "Qual foi a receita total em outubro?",
 *   usuarioId: "user123",
 *   papel: "diretor"
 * });
 * console.log(resposta.resposta);
 * ```
 */
export async function askDipamAgent(
  params: AskParams
): Promise<AskResponse> {
  try {
    const response = await fetch(`${DIPAM_API_BASE_URL}/ask`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        pergunta: params.pergunta,
        usuario_id: params.usuarioId,
        papel: params.papel,
      }),
    });

    if (!response.ok) {
      let errorMessage = `Erro ao fazer requisição: ${response.status} ${response.statusText}`;
      let errorData: any = null;

      try {
        errorData = await response.json();
        if (errorData?.detail || errorData?.error || errorData?.message) {
          errorMessage =
            errorData.detail || errorData.error || errorData.message;
        }
      } catch {
        // Se não conseguir parsear o JSON de erro, usa a mensagem padrão
      }

      throw new DipamApiError(errorMessage, response.status, errorData);
    }

    const data = (await response.json()) as AskResponse;
    return data;
  } catch (error) {
    if (error instanceof DipamApiError) {
      throw error;
    }

    // Erro de rede ou outro erro não esperado
    if (error instanceof TypeError && error.message.includes("fetch")) {
      throw new DipamApiError(
        `Erro de conexão com a API: ${error.message}. Verifique se a API está rodando em ${DIPAM_API_BASE_URL}`,
        undefined,
        error
      );
    }

    throw new DipamApiError(
      `Erro inesperado ao fazer requisição: ${error instanceof Error ? error.message : String(error)}`,
      undefined,
      error
    );
  }
}

/**
 * Faz uma requisição ao endpoint /preview/vendedor da API do Dipam AI
 * 
 * Retorna dados de preview de um vendedor específico para um mês/ano.
 * 
 * @param params - Parâmetros incluindo vendedor e mesAno (formato YYYY-MM)
 * @returns Promise com os dados do vendedor para o período
 * @throws DipamApiError em caso de erro de rede ou status HTTP != 200
 * 
 * @example
 * ```ts
 * const preview = await previewVendedor({
 *   vendedor: "João Silva",
 *   mesAno: "2025-10"
 * });
 * console.log(preview.dados);
 * ```
 */
export async function previewVendedor(
  params: PreviewVendedorParams
): Promise<PreviewVendedorResponse> {
  try {
    const url = `${DIPAM_API_BASE_URL}/preview/vendedor/${encodeURIComponent(
      params.vendedor
    )}/${params.mesAno}`;

    const response = await fetch(url, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      let errorMessage = `Erro ao fazer requisição: ${response.status} ${response.statusText}`;
      let errorData: any = null;

      try {
        errorData = await response.json();
        if (errorData?.detail || errorData?.error || errorData?.message) {
          errorMessage =
            errorData.detail || errorData.error || errorData.message;
        }
      } catch {
        // Se não conseguir parsear o JSON de erro, usa a mensagem padrão
      }

      throw new DipamApiError(errorMessage, response.status, errorData);
    }

    const data = (await response.json()) as PreviewVendedorResponse;
    return data;
  } catch (error) {
    if (error instanceof DipamApiError) {
      throw error;
    }

    // Erro de rede ou outro erro não esperado
    if (error instanceof TypeError && error.message.includes("fetch")) {
      throw new DipamApiError(
        `Erro de conexão com a API: ${error.message}. Verifique se a API está rodando em ${DIPAM_API_BASE_URL}`,
        undefined,
        error
      );
    }

    throw new DipamApiError(
      `Erro inesperado ao fazer requisição: ${error instanceof Error ? error.message : String(error)}`,
      undefined,
      error
    );
  }
}



