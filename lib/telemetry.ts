/**
 * Telemetria leve no frontend
 * 
 * Registra:
 * - tempo até exibição do Big Number
 * - tempo até renderização da tabela
 * - quantos registros foram renderizados
 * - se houve fallback do cache
 * - se teve erro de rede
 */

type TelemetryEvent = {
  event: "frontend_performance";
  big_number_ms: number;
  table_ms: number;
  records: number;
  cache_fallback?: boolean;
  network_error?: boolean;
  timestamp: string;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Envia métricas de performance para o backend
 */
export async function sendFrontendMetrics(data: {
  big_number_ms: number;
  table_ms: number;
  records: number;
  cache_fallback?: boolean;
  network_error?: boolean;
}): Promise<void> {
  try {
    const event: TelemetryEvent = {
      event: "frontend_performance",
      ...data,
      timestamp: new Date().toISOString(),
    };

    // Envia de forma assíncrona (não bloqueia UI)
    fetch(`${API_URL}/metrics/frontend`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(event),
      keepalive: true, // Permite que a requisição continue mesmo após navegação
    }).catch((err) => {
      // Silenciosamente ignora erros de telemetria
      console.debug("Telemetry error (non-blocking):", err);
    });
  } catch (err) {
    // Silenciosamente ignora erros de telemetria
    console.debug("Telemetry error (non-blocking):", err);
  }
}

/**
 * Registra tempo até exibição do Big Number
 */
export function trackBigNumberRender(durationMs: number, records: number) {
  sendFrontendMetrics({
    big_number_ms: durationMs,
    table_ms: 0, // Será atualizado quando a tabela renderizar
    records,
  });
}

/**
 * Registra tempo até renderização da tabela
 */
export function trackTableRender(
  durationMs: number,
  records: number,
  cacheFallback = false
) {
  sendFrontendMetrics({
    big_number_ms: 0, // Já foi registrado anteriormente
    table_ms: durationMs,
    records,
    cache_fallback: cacheFallback,
  });
}

/**
 * Registra erro de rede
 */
export function trackNetworkError(records: number) {
  sendFrontendMetrics({
    big_number_ms: 0,
    table_ms: 0,
    records,
    network_error: true,
  });
}

