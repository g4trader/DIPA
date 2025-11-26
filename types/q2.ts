/**
 * Tipos TypeScript para Q2 (Queda de Faturamento)
 * 
 * Estrutura baseada na resposta do endpoint /api/copilot/q2
 */

/**
 * Período analisado
 */
export type Q2Periodo = {
  /** Descrição do período (ex: "set/25 x out/25") */
  descricao: string;
  /** Data inicial do mês anterior */
  data_ini_mes_anterior?: string;
  /** Data final do mês anterior */
  data_fim_mes_anterior?: string;
  /** Data inicial do mês atual */
  data_ini_mes_atual?: string;
  /** Data final do mês atual */
  data_fim_mes_atual?: string;
};

/**
 * Resumo de métricas agregadas
 */
export type Q2Resumo = {
  /** Total de clientes com queda */
  total_clientes_queda: number;
  /** Percentual de clientes com queda */
  percentual_clientes_queda?: number;
  /** Queda média absoluta em R$ */
  queda_media_absoluta: number;
  /** Queda média percentual */
  queda_media_percentual: number;
  /** Queda máxima absoluta em R$ */
  queda_maxima_absoluta: number;
  /** Queda máxima percentual */
  queda_maxima_percentual: number;
};

/**
 * Cliente com queda de faturamento
 */
export type Q2TopCliente = {
  /** Nome do cliente */
  nome: string;
  /** ID do cliente */
  cliente_id?: number;
  /** Queda absoluta em R$ */
  queda_absoluta: number;
  /** Queda percentual */
  queda_percentual: number;
  /** Faturamento no mês anterior */
  faturamento_mes_anterior?: number;
  /** Faturamento no mês atual */
  faturamento_mes_atual?: number;
  /** Código da rota */
  rota?: string;
  /** Nome do vendedor */
  vendedor_nome?: string;
  /** Nome do supervisor */
  supervisor_nome?: string;
};

/**
 * Agregação por rota
 */
export type Q2Rota = {
  /** Código da rota */
  rota: string;
  /** Quantidade de clientes com queda */
  qtd_clientes_queda: number;
  /** Queda total da rota em R$ */
  queda_total: number;
};

/**
 * Resposta completa do endpoint Q2
 */
export type Q2Response = {
  /** Tipo de resposta (sempre "Q2_QUEDA_FATURAMENTO") */
  tipo: string;
  /** Período analisado */
  periodo: Q2Periodo;
  /** Texto executivo formatado */
  texto_executivo: string;
  /** Resumo de métricas agregadas */
  resumo: Q2Resumo;
  /** Top clientes com queda (máximo 10) */
  top_clientes: Q2TopCliente[];
  /** Rotas mais impactadas (máximo 5) */
  rotas: Q2Rota[];
  /** Dados brutos do DW/orquestrador (opcional) */
  dados_brutos?: Record<string, any>;
};

/**
 * Request para o endpoint Q2
 */
export type Q2Request = {
  /** Pergunta do usuário sobre queda de faturamento */
  pergunta: string;
};

