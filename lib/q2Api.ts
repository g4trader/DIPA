/**
 * Cliente HTTP para integração com o endpoint Q2 (Queda de Faturamento)
 */

import { Q2Request, Q2Response } from "@/types/q2";
import { DIPAM_API_BASE_URL } from "./dipamApi";

/**
 * Constrói URL do endpoint Q2
 */
function buildQ2Url(): string {
  // Se estiver em modo mock, retorna endpoint local
  const ENV = process.env.NEXT_PUBLIC_DIPAM_ENV || "prod";
  if (ENV === "mock") {
    return "/api/mock/q2";
  }
  
  // Em produção, usa backend real
  return `${DIPAM_API_BASE_URL}/api/copilot/q2`;
}

/**
 * Erro customizado para chamadas Q2
 */
export class Q2ApiError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public response?: any
  ) {
    super(message);
    this.name = "Q2ApiError";
  }
}

/**
 * Chama o endpoint Q2 com uma pergunta
 * 
 * @param pergunta - Pergunta sobre queda de faturamento
 * @returns Resposta Q2 com dados estruturados
 * @throws Q2ApiError se houver erro na chamada
 */
export async function callQ2Endpoint(pergunta: string): Promise<Q2Response> {
  const url = buildQ2Url();
  
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ pergunta } as Q2Request),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Q2ApiError(
        errorData.detail || `Erro ao chamar endpoint Q2: ${response.statusText}`,
        response.status,
        errorData
      );
    }

    const data: Q2Response = await response.json();
    return data;
  } catch (error) {
    if (error instanceof Q2ApiError) {
      throw error;
    }
    
    // Erro de rede ou parsing
    throw new Q2ApiError(
      `Erro ao processar resposta do endpoint Q2: ${error instanceof Error ? error.message : "Erro desconhecido"}`,
      undefined,
      error
    );
  }
}

