"use client";

export type IntentId =
  | "target_vs_actual"
  | "seller_performance"
  | "mix_products"
  | "promotion_mix"
  | "top_products"
  | "avg_ticket"
  | "sales_overview"
  | "brand_sales";

export type ChartSeries = {
  key: string;
  label: string;
  color: string;
};

export type ChartConfig = {
  type: "area" | "bar";
  data: Record<string, string | number>[];
  xKey: string;
  series: ChartSeries[];
};

export type SummaryEntity = {
  name: string;
  revenue?: number;
  units?: number;
};

export type InsightSummary = {
  subject: string;
  action?: string;
  totalRevenue?: number;
  totalUnits?: number;
  revenueLabel?: string;
  unitsLabel?: string;
  entityLabel?: string;
  entityLabelPlural?: string;
  entityGender?: "m" | "f";
  best?: SummaryEntity;
  worst?: SummaryEntity;
};

export type TableEntry = {
  columns: string[];
  rows: (string | number)[];
};

export type QueryResult = {
  intent: IntentId;
  month: string;
  kpis: { label: string; value: string; helper?: string }[];
  narrative: string;
  table: TableEntry[];
  chart?: ChartConfig;
  summary?: InsightSummary;
};

export type PanelMessage = {
  role: "user" | "assistant";
  text: string;
  result?: QueryResult;
  // Campos adicionais para integração com API do Dipam AI
  intent?: string;
  confianca?: number;
  contexto?: Record<string, any>;
  timestamp?: string;
};

// Tipos para dados de "quem bateu meta"
export type VendedorMetaInfo = {
  vendedor: string;
  rota?: string;
  supervisor?: string;
  meta: number;
  realizado: number;
  atingimento: number;
};

export type BateuMetaResumo = {
  total_vendedores_bateram: number;
  meta_total: number;
  realizado_total: number;
  atingimento_medio: number;
};

export type BateuMetaContext = {
  mes_ano: string;
  resumo: BateuMetaResumo;
  top_vendedores: VendedorMetaInfo[];
  demais_vendedores?: VendedorMetaInfo[];
};

// Tipos para análise de produtos com baixa venda
export type ProdutoInfo = {
  codigo: string;
  produto: string;
  unidades: number;
  caixas: number;
  faturamento: number;
};

export type AnaliseProdutosContext = {
  tipo: "analise_produtos";
  periodo_dias: number;
  produtos: ProdutoInfo[];
  criterio: string;
  total_produtos?: number;
};

