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
 * Dados de um cliente problemático/crítico
 */
export type ClienteProblema = {
  /** ID do cliente */
  cliente_id?: number;
  /** Nome do cliente */
  nome_cliente: string;
  /** Nome do vendedor responsável */
  vendedor_nome?: string;
  /** Faturamento no mês (R$) */
  faturamento_mes: number;
  /** Quantidade de pedidos no mês */
  qtd_pedidos?: number;
  /** Faturamento médio por pedido (R$) */
  faturamento_medio_pedido?: number;
  /** Faturamento médio dos últimos 3 meses (R$) - opcional */
  faturamento_media_3m?: number;
  /** Variação percentual vs média dos últimos 3 meses - opcional */
  variacao_percentual?: number;
  /** Indica se há histórico disponível */
  tem_historico?: boolean;
};

/**
 * KPI individual estruturado para dashboard
 */
export type KpiItem = {
  /** Label do KPI (ex.: "Meta Total") */
  label: string;
  /** Valor do KPI (pode ser número ou string formatada) */
  value: string | number;
  /** Variação percentual (opcional) - ex.: "+5.2%" ou "-10.5%" */
  variation?: string;
  /** Cor do valor (opcional) - "positive" (verde), "negative" (vermelho), "neutral" (cinza) */
  color?: "positive" | "negative" | "neutral";
  /** Ícone opcional (emoji ou nome de ícone) */
  icon?: string;
};

/**
 * Item do ranking de vendedores
 */
export type RankingVendedorItem = {
  /** Nome do vendedor */
  vendedor: string;
  /** Meta do vendedor (R$) */
  meta: number;
  /** Realizado do vendedor (R$) */
  realizado: number;
  /** Atingimento percentual */
  atingimento: number;
  /** Gap (realizado - meta, pode ser negativo) */
  gap: number;
  /** Supervisor (opcional) */
  supervisor?: string;
  /** Rank no ranking */
  rank?: number;
};

/**
 * Cliente crítico/problemático
 */
export type ClienteCriticoItem = {
  /** Nome do cliente */
  cliente: string;
  /** Faturamento no mês (R$) */
  faturamento: number;
  /** Quantidade de pedidos */
  pedidos: number;
  /** Insight sobre o cliente (opcional) - ex.: "cliente comprava 3 SKUs, este mês apenas 1" */
  insight?: string;
  /** Vendedor responsável (opcional) */
  vendedor?: string;
  /** Variação percentual vs média (opcional) */
  variacao?: number;
};

/**
 * Resposta estruturada do Copilot (formato dashboard)
 * Este é o formato que o backend deve retornar quando há dados estruturados
 */
export interface CopilotStructuredResponse {
  /** Resumo executivo em texto (2-4 parágrafos) */
  resumoExecutivo?: string;
  /** KPIs do mês/período */
  kpis?: KpiItem[];
  /** Ranking de vendedores */
  rankingVendedores?: RankingVendedorItem[];
  /** Clientes críticos/problemáticos */
  clientesCriticos?: ClienteCriticoItem[];
  /** Insights e recomendações (lista de strings) */
  insightsRecomendacoes?: string[];
  /** JSON técnico completo (opcional, para debug) */
  jsonTecnico?: any;
}

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

  /** Resposta estruturada (dashboard format) - NOVO: prioridade sobre texto */
  structured?: CopilotStructuredResponse;

  /** Resumo executivo em markdown ou texto simples (DEPRECATED: usar structured.resumoExecutivo) */
  resumoExecutivo?: string;
  /** Insights e recomendações em markdown ou texto simples (DEPRECATED: usar structured.insightsRecomendacoes) */
  insights?: string;
  /** Observações sobre os dados em markdown ou texto simples */
  observacoes?: string;

  /** KPIs do mês analisado (DEPRECATED: usar structured.kpis) */
  kpis?: KpisData;

  /** Top vendedores (até 5) (DEPRECATED: usar structured.rankingVendedores) */
  topVendedores?: TopVendedor[];

  /** Clientes problemáticos/críticos (até 15) (DEPRECATED: usar structured.clientesCriticos) */
  clientesProblema?: ClienteProblema[];

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
