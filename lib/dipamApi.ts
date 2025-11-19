/**
 * Cliente HTTP para integração com a API do Dipam AI
 * 
 * Este módulo fornece funções tipadas para comunicação com o backend FastAPI
 * do Dipam AI, incluindo endpoints para perguntas ao agente e preview de dados.
 */

import { CopilotStructuredResponse } from "@/types/agent";

/**
 * URL base da API do Dipam AI
 * 
 * Lê da variável de ambiente NEXT_PUBLIC_BACKEND_URL (padrão) ou
 * NEXT_PUBLIC_API_BASE_URL (compatibilidade).
 * 
 * IMPORTANTE: 
 * - Em produção, a variável DEVE estar configurada no Vercel
 * - Fallback padrão: URL oficial do Cloud Run (trivihair)
 * - Remove barras no final para evitar URLs duplicadas (ex: ...run.app//ask)
 * - URL oficial: https://dipam-ai-backend-642830139828.us-central1.run.app
 * 
 * ⚠️ NUNCA usar a URL antiga: https://dipam-ai-backend-6arhlm3mha-uc.a.run.app
 */
const BASE_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "https://dipam-ai-backend-642830139828.us-central1.run.app";

// Remove barra extra no final, se houver
const cleanedUrl = BASE_URL.replace(/\/+$/, "");

// Debug apenas em desenvolvimento
if (process.env.NODE_ENV === "development") {
  console.log("🔧 BACKEND_URL:", cleanedUrl);
}

// Validação: em produção, a URL DEVE estar configurada
if (!cleanedUrl && process.env.NODE_ENV === "production") {
  console.error(
    "❌ ERRO CRÍTICO: NEXT_PUBLIC_BACKEND_URL não está configurada no Vercel!",
    "Configure a variável de ambiente: NEXT_PUBLIC_BACKEND_URL=https://dipam-ai-backend-642830139828.us-central1.run.app"
  );
  throw new Error(
    "NEXT_PUBLIC_BACKEND_URL não está configurada. Configure no Vercel: NEXT_PUBLIC_BACKEND_URL=https://dipam-ai-backend-642830139828.us-central1.run.app"
  );
}

export const DIPAM_API_BASE_URL = cleanedUrl;

/**
 * Constrói uma URL completa a partir do caminho
 * 
 * Garante que não há barras duplicadas na URL final
 * 
 * @param path - Caminho do endpoint (ex: "/ask" ou "ask")
 * @returns URL completa (ex: "https://api.example.com/ask")
 */
function buildUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${DIPAM_API_BASE_URL}${normalizedPath}`;
}

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
  /** Resposta estruturada com seções, tabelas e insights preditivos (FASE 3 + FASE 5) */
  structured?: CopilotStructuredResponse;
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
  /** Resposta estruturada direta (FASE 3 + FASE 5) */
  structured?: CopilotAnswerPayload["structured"];
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
  const url = buildUrl("/ask");
  try {
    const response = await fetch(url, {
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
      let errorMessage = 'Erro ao processar sua pergunta. Tente novamente em instantes.';
      let errorData: any = null;

      try {
        const body = await response.json();
        errorData = body;
        if (body?.detail || body?.message || body?.error) {
          // Extrai mensagem de erro legível
          const detail = body.detail || body.message || body.error;
          if (typeof detail === 'string') {
            errorMessage = detail;
          } else if (typeof detail === 'object') {
            // Se detail for um objeto, tenta extrair mensagem
            errorMessage = detail.message || detail.error || JSON.stringify(detail);
          }
        }
      } catch {
        // Se não conseguir parsear JSON, tenta texto
        try {
          const text = await response.text();
          if (text && text.trim()) {
            errorMessage = text.substring(0, 200); // Limita tamanho
          }
        } catch {
          // Mantém mensagem padrão se tudo falhar
        }
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
        `Erro de conexão com a API: ${error.message}. Verifique se a API está rodando em ${url}`,
        undefined,
        error
      );
    }

    // Garante que sempre retorna uma string legível, nunca [object Object]
    const errorMsg = error instanceof Error ? error.message : String(error);
    throw new DipamApiError(
      `Erro inesperado ao fazer requisição: ${errorMsg}`,
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
  const url = buildUrl(
    `/preview/vendedor/${encodeURIComponent(params.vendedor)}/${params.mesAno}`
  );
  try {
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
        `Erro de conexão com a API: ${error.message}. Verifique se a API está rodando em ${url}`,
        undefined,
        error
      );
    }

    // Garante que sempre retorna uma string legível, nunca [object Object]
    const errorMsg = error instanceof Error ? error.message : String(error);
    throw new DipamApiError(
      `Erro inesperado ao fazer requisição: ${errorMsg}`,
      undefined,
      error
    );
  }
}



