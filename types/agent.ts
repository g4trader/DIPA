/**
 * Tipos TypeScript para respostas do agente DIPAM COPILOT™
 */

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
 * Payload estruturado para resposta do Copilot
 * Este é o formato que o backend deve retornar e o frontend usa para renderizar o card
 */
export interface CopilotAnswerPayload {
  /** Intent detectado (ex.: "consulta_vendedores_performance") */
  intent: string;
  /** Label legível do intent (ex.: "Consulta Vendedores Performance") */
  intentLabel: string;
  /** Nível de confiança da resposta (0-1) */
  confidence: number;
  /** Pergunta original do usuário */
  question: string;

  /** Resumo executivo em markdown ou texto simples */
  resumoExecutivo?: string;
  /** Insights e recomendações em markdown ou texto simples */
  insights?: string;
  /** Observações sobre os dados em markdown ou texto simples */
  observacoes?: string;

  /** KPIs do mês analisado */
  kpis?: KpisData;

  /** Top vendedores (até 5) */
  topVendedores?: TopVendedor[];

  /** Campo bruto opcional, se precisar renderizar markdown completo */
  respostaMarkdown?: string;
}

/**
 * Resposta estruturada do agente DIPAM COPILOT™
 * 
 * Este tipo corresponde ao formato retornado pelo endpoint /ask
 * após as mudanças implementadas no backend para extrair dados estruturados.
 * 
 * @deprecated Use CopilotAnswerPayload ao invés deste tipo
 */
export type AgentUiResponse = {
  /** Pergunta original do usuário */
  question: string;
  /** Intenção detectada (ex.: "consulta_meta", "consulta_vendedores_performance") */
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
  insights?: string[];
  /** Lista de observações sobre os dados (opcional) */
  observacoes?: string[];
  /** Contexto de dados usado (opcional) */
  contexto?: Record<string, any>;
  /** Timestamp da resposta (opcional) */
  timestamp?: string;
};
