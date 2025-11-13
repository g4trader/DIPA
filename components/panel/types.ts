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
};

export type PanelMessage = {
  role: "user" | "assistant";
  text: string;
  result?: QueryResult;
};

