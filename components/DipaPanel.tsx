"use client";

import React, { useEffect, useRef, useState } from "react";
import Image from "next/image";
import { clsx } from "clsx";
import { Button } from "@/components/ui/button";
import type { TParsedQuery } from "@/app/api/query/schema";
import logoDipam from "@/assets/logo_dipam.avif";
import { ds } from "@/styles/ui";
import { ChatHistory } from "@/components/panel/ChatHistory";
import type { PanelMessage, BateuMetaContext, AnaliseProdutosContext, ProdutoInfo, IntentId, QueryResult } from "@/components/panel/types";
import { Loader2, History, X } from "lucide-react";
import { askDipamAgent, DipamApiError } from "@/lib/dipamApi";
import { DipamAnswerCard } from "@/components/DipamAnswerCard";
import { CopilotAnswerCard } from "@/components/CopilotAnswerCard";
import { CopilotAnswerPayload } from "@/types/agent";

type Region =
  | "Porto Alegre"
  | "Grande Porto Alegre"
  | "Vale dos Sinos"
  | "Serra Gaúcha"
  | "Litoral Norte"
  | "Região Carbonífera";

type Seller = {
  id: string;
  name: string;
  region: Region;
  city: string;
  monthlyTarget: number;
};

type Product = {
  id: string;
  sku: string;
  name: string;
  brand: string;
  category: string;
  promo: boolean;
};

type Client = {
  id: string;
  name: string;
  region: Region;
  city: string;
};

type Sale = {
  id: string;
  date: string;
  month: string;
  orderId: string;
  sellerId: string;
  clientId: string;
  region: Region;
  city: string;
  productId: string;
  qty: number;
  unitPrice: number;
  discount: number;
};

type Intent = IntentId;

const REGIONS: Region[] = [
  "Porto Alegre",
  "Grande Porto Alegre",
  "Vale dos Sinos",
  "Serra Gaúcha",
  "Litoral Norte",
  "Região Carbonífera"
];

const BRANDS = ["Nissin", "Red Bull", "AB Mauri", "Mars", "Ypê", "Hemmer", "Marilan", "Ajinomoto", "Condor"] as const;

const CATEGORIES = [
  "Massas instantâneas",
  "Bebidas energéticas",
  "Panificação e confeitaria",
  "Confeitos e petcare",
  "Limpeza doméstica",
  "Condimentos e conservas",
  "Biscoitos e snacks",
  "Temperos e caldos",
  "Utensílios de limpeza"
] as const;

const MONTHS = ["2025-07", "2025-08", "2025-09", "2025-10", "2025-11"] as const;
const DEFAULT_MONTH: (typeof MONTHS)[number] = "2025-11";
const USE_LLM = process.env.NEXT_PUBLIC_USE_LLM === "true";
const COLOR_ACCENT = "#3B82F6";
const COLOR_POSITIVE = "#22C55E";
const COLOR_NEUTRAL = "#64748B";

function seededRandom(seed: number) {
  return () => {
    // Park-Miller
    seed = (seed * 16807) % 2147483647;
    return (seed - 1) / 2147483646;
  };
}

function genData() {
  const rnd = seededRandom(20251111);
  const sellers: Seller[] = Array.from({ length: 24 }).map((_, idx) => {
    const region = REGIONS[Math.floor(rnd() * REGIONS.length)];
    const base = 150_000 + rnd() * 250_000;
    return {
      id: `S${idx + 1}`,
      name: `Consultor ${String.fromCharCode(65 + (idx % 26))}${idx + 1}`,
      region,
      city: "—",
      monthlyTarget: Math.round(base)
    };
  });

  const products: Product[] = Array.from({ length: 160 }).map((_, idx) => {
    const brand = BRANDS[Math.floor(rnd() * BRANDS.length)];
    const category = CATEGORIES[Math.floor(rnd() * CATEGORIES.length)];
    return {
      id: `P${idx + 1}`,
      sku: `${brand.slice(0, 3).toUpperCase()}-${1000 + idx}`,
      name: `${brand} ${category.split(" ")[0]} ${idx + 1}`,
      brand,
      category,
      promo: rnd() < 0.28
    };
  });

  const clients: Client[] = Array.from({ length: 420 }).map((_, idx) => ({
    id: `C${idx + 1}`,
    name: `Cliente ${idx + 1}`,
    region: REGIONS[Math.floor(rnd() * REGIONS.length)],
    city: "—"
  }));

  const sales: Sale[] = [];
  let orderSequence = 1010;

  for (const month of MONTHS) {
    const dailyBase = 6500 + Math.floor(rnd() * 1200);
    for (let record = 0; record < dailyBase; record++) {
      const seller = sellers[Math.floor(rnd() * sellers.length)];
      const client = clients[Math.floor(rnd() * clients.length)];
      const product = products[Math.floor(rnd() * products.length)];
      const qty = 1 + Math.floor(rnd() * 12);
      const unitPrice = Math.round((12 + rnd() * 75) * 100) / 100;
      const discount = [0, 0.03, 0.05, 0.08, 0.1][Math.floor(rnd() * 5)];
      const day = String(1 + Math.floor(rnd() * 28)).padStart(2, "0");

      sales.push({
        id: `L${month}-${record}`,
        orderId: `O${orderSequence++}`,
        date: `${month}-${day}T10:00:00`,
        month,
        sellerId: seller.id,
        clientId: client.id,
        region: client.region,
        city: "—",
        productId: product.id,
        qty,
        unitPrice,
        discount
      });
    }
  }

  return { sellers, products, clients, sales };
}

const DATA = genData();

// Tipo de mensagem para o chat GenAI
type Role = "user" | "assistant";

interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  // Payload estruturado da resposta do Copilot
  payload?: CopilotAnswerPayload;
}

function formatCurrency(value: number) {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatPercent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

function extractMonth(query: string, fallback: string) {
  const match = query.match(/2025-(07|08|09|10|11)/);
  if (match) return match[0];
  const monthMatch = query.match(/\bjulho\b|\bagosto\b|\bsetembro\b|\boutubro\b|\bnovembro\b/i);
  if (monthMatch) {
    const map: Record<string, string> = {
      julho: "2025-07",
      agosto: "2025-08",
      setembro: "2025-09",
      outubro: "2025-10",
      novembro: "2025-11"
    };
    return map[monthMatch[0].toLowerCase()];
  }
  return fallback;
}

function detectBrandFromQuery(query: string): string | undefined {
  const normalized = query.toLowerCase();
  return BRANDS.find((brand) => normalized.includes(brand.toLowerCase()));
}

function extractProductNameFromQuery(query: string): string | undefined {
  const brand = detectBrandFromQuery(query);
  if (!brand) return undefined;

  const lower = query.toLowerCase();
  const brandLower = brand.toLowerCase();
  const brandIndex = lower.indexOf(brandLower);
  if (brandIndex === -1) return undefined;

  const brandEnd = brandIndex + brand.length;
  const remainder = query.slice(brandEnd);
  const stopMatch = remainder.match(/\s+(?:neste|nesse|nesta|neste|no|na|em|para)\b/i);
  const stopIndex = stopMatch ? brandEnd + (stopMatch.index ?? 0) : query.length;
  const phrase = query
    .slice(brandIndex, stopIndex)
    .replace(/[?.,]+$/g, "")
    .trim();

  return phrase.length ? phrase : undefined;
}

function formatUnits(value: number) {
  return value.toLocaleString("pt-BR");
}

// Função helper para verificar se o contexto contém dados de "quem bateu meta"
function isBateuMetaContext(contexto?: Record<string, any>): contexto is BateuMetaContext {
  return (
    contexto !== undefined &&
    contexto.mes_ano !== undefined &&
    contexto.resumo !== undefined &&
    contexto.top_vendedores !== undefined &&
    Array.isArray(contexto.top_vendedores)
  );
}

// Função helper para verificar se o contexto contém dados de análise de produtos
function isAnaliseProdutosContext(contexto?: Record<string, any>): contexto is AnaliseProdutosContext {
  return (
    contexto !== undefined &&
    contexto.tipo === "analise_produtos" &&
    contexto.periodo_dias !== undefined &&
    contexto.produtos !== undefined &&
    Array.isArray(contexto.produtos)
  );
}

// Função helper para formatar mês/ano
function formatMesAno(mesAno: string): string {
  try {
    const [ano, mes] = mesAno.split("-");
    const meses = [
      "janeiro", "fevereiro", "março", "abril", "maio", "junho",
      "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
    ];
    const mesIndex = parseInt(mes, 10) - 1;
    return `${meses[mesIndex]} de ${ano}`;
  } catch {
    return mesAno;
  }
}

// Função helper para formatar percentual que já está em formato 0-100
function formatPercentValue(value: number): string {
  return `${value.toFixed(1)}%`;
}

// Função helper para extrair estratégias sugeridas do texto da resposta
function extractEstrategiasSugeridas(texto: string): string[] {
  const estrategias: string[] = [];
  
  // Procura por seções de recomendação com bullets ou listas
  const lines = texto.split("\n");
  let inRecommendations = false;
  
  for (const line of lines) {
    const trimmed = line.trim();
    
    // Detecta início de seção de recomendações
    if (trimmed.includes("Recomendações") || trimmed.includes("Estratégias") || trimmed.includes("💡")) {
      inRecommendations = true;
      continue;
    }
    
    // Se estiver na seção de recomendações, extrai itens da lista
    if (inRecommendations) {
      // Detecta bullets (•, -, *, etc.)
      if (trimmed.match(/^[•\-\*]\s+/)) {
        const item = trimmed.replace(/^[•\-\*]\s+/, "").trim();
        if (item && item.length > 10) {  // Só adiciona se for uma frase completa
          estrategias.push(item);
        }
      }
      // Detecta listas numeradas
      else if (trimmed.match(/^\d+\.\s+/)) {
        const item = trimmed.replace(/^\d+\.\s+/, "").trim();
        if (item && item.length > 10) {
          estrategias.push(item);
        }
      }
      // Se encontrar uma linha vazia após recomendações, para
      else if (trimmed === "" && estrategias.length > 0) {
        break;
      }
    }
  }
  
  // Se não encontrou na seção de recomendações, tenta buscar no texto geral
  if (estrategias.length === 0) {
    // Procura por padrões comuns de estratégias
    const estrategiaPatterns = [
      /refor[çc]ar.*mix.*rota/i,
      /reativ[ao].*clientes/i,
      /campanhas.*pdv/i,
      /produtos.*baixa.*elasticidade/i,
      /estrat[ée]gias.*promo[çc][ãa]o/i,
      /marketing.*direcionado/i
    ];
    
    for (const pattern of estrategiaPatterns) {
      const matches = texto.match(new RegExp(`[^.]*${pattern.source}[^.]*`, "i"));
      if (matches) {
        estrategias.push(matches[0].trim());
      }
    }
  }
  
  return estrategias.length > 0 ? estrategias : [
    "Avaliar estratégias de promoção para estes produtos",
    "Revisar o mix de produtos e possível descontinuação",
    "Considerar ações de marketing direcionadas para aumentar o giro"
  ];
}

function buildInsightSummaryView(result?: QueryResult) {
  const summary = result?.summary;
  if (!summary) return null;

  const {
    subject,
    action = "Consolidamos",
    totalRevenue,
    totalUnits,
    revenueLabel = "receita",
    unitsLabel = "unidades",
    entityLabel = "indicador",
    entityLabelPlural = `${entityLabel}s`,
    entityGender = "m",
    best,
    worst
  } = summary;

  const paragraphs: React.ReactNode[] = [];

  if (totalUnits !== undefined && totalRevenue !== undefined) {
    paragraphs.push(
      <p key="intro">
        {action} <strong>{formatUnits(totalUnits)} {unitsLabel}</strong>
        {subject ? ` ${subject}` : ""}, com {revenueLabel} total de <strong>{formatCurrency(totalRevenue)}</strong>.
      </p>
    );
  } else if (totalRevenue !== undefined) {
    paragraphs.push(
      <p key="intro">
        {action}{subject ? ` ${subject}` : ""}, com {revenueLabel} total de <strong>{formatCurrency(totalRevenue)}</strong>.
      </p>
    );
  } else if (totalUnits !== undefined) {
    paragraphs.push(
      <p key="intro">
        {action} <strong>{formatUnits(totalUnits)} {unitsLabel}</strong>{subject ? ` ${subject}` : ""}.
      </p>
    );
  }

  if (best) {
    const article = entityGender === "f" ? "A melhor" : "O melhor";
    const hasUnits = best.units !== undefined && unitsLabel;
    const hasRevenue = best.revenue !== undefined;
    paragraphs.push(
      <p key="best">
        {article} {entityLabel} foi <strong>{best.name}</strong>
        {hasUnits ? (
          <>
            {" com "}
            <strong>{formatUnits(best.units!)} {unitsLabel}</strong>
          </>
        ) : null}
        {hasRevenue ? (
          <>
            {hasUnits ? " e " : " com "}
            <strong>{formatCurrency(best.revenue!)}</strong>
          </>
        ) : null}
        .
      </p>
    );
  }

  if (worst && (!best || best.name !== worst.name)) {
    const article = entityGender === "f" ? "A" : "O";
    const hasUnits = worst.units !== undefined && unitsLabel;
    const hasRevenue = worst.revenue !== undefined;
    paragraphs.push(
      <p key="worst">
        {article} {entityLabel} com menor resultado foi <strong>{worst.name}</strong>
        {hasUnits ? (
          <>
            {" com "}
            <strong>{formatUnits(worst.units!)} {unitsLabel}</strong>
          </>
        ) : null}
        {hasRevenue ? (
          <>
            {hasUnits ? " e " : " com "}
            <strong>{formatCurrency(worst.revenue!)}</strong>
          </>
        ) : null}
        .
      </p>
    );
  }

  if (!paragraphs.length) {
    return null;
  }

  return { paragraphs };
}

function intentFromQuery(query: string): Intent {
  const normalized = query.toLowerCase();
  const hasBrand = BRANDS.some((brand) => normalized.includes(brand.toLowerCase()));
  if (hasBrand && (normalized.includes("quanto") || normalized.includes("vendido") || normalized.includes("receita"))) {
    return "brand_sales";
  }
  if (normalized.includes("meta") || normalized.includes("alvo") || normalized.includes("target")) return "target_vs_actual";
  if (normalized.includes("vendedor") || normalized.includes("consultor") || normalized.includes("performance")) return "seller_performance";
  if (normalized.includes("mix") && normalized.includes("promo")) return "promotion_mix";
  if (normalized.includes("mix") || normalized.includes("categoria")) return "mix_products";
  if (normalized.includes("ticket")) return "avg_ticket";
  if (normalized.includes("top") || normalized.includes("maiores produtos") || normalized.includes("ranking de produtos")) return "top_products";
  return "sales_overview";
}

function revenueFromSale(sale: Sale) {
  return sale.qty * sale.unitPrice * (1 - sale.discount);
}

function runQuery(intent: Intent, month: string, filters: Partial<TParsedQuery> = {}): QueryResult {
  const monthSales = DATA.sales.filter((sale) => sale.month === month);
  const totalRevenue = monthSales.reduce((acc, sale) => acc + revenueFromSale(sale), 0);
  const totalUnits = monthSales.reduce((acc, sale) => acc + sale.qty, 0);
  const totalOrders = new Set(monthSales.map((sale) => sale.orderId)).size;
  const uniqueClients = new Set(monthSales.map((sale) => sale.clientId)).size;

  const baseResult: QueryResult = {
    intent,
    month,
    kpis: [],
    narrative: "",
    table: [],
    summary: undefined
  };

  switch (intent) {
    case "target_vs_actual": {
      const sellerMap = DATA.sellers.reduce<Record<string, Seller>>((acc, seller) => ({ ...acc, [seller.id]: seller }), {});
      const sellerUnitsMap = monthSales.reduce<Record<string, number>>((acc, sale) => {
        acc[sale.sellerId] = (acc[sale.sellerId] || 0) + sale.qty;
        return acc;
      }, {});
      const bySeller = monthSales.reduce<Record<string, { seller: Seller; revenue: number }>>((acc, sale) => {
        acc[sale.sellerId] ||= { seller: sellerMap[sale.sellerId], revenue: 0 };
        acc[sale.sellerId].revenue += revenueFromSale(sale);
        return acc;
      }, {});
      const detailedRows = Object.values(bySeller)
        .map((entry) => {
          const attainment = entry.revenue / entry.seller.monthlyTarget;
          return {
            seller: entry.seller,
            region: entry.seller.region,
            target: entry.seller.monthlyTarget,
            revenue: entry.revenue,
            attainment,
            units: sellerUnitsMap[entry.seller.id] ?? 0
          };
        })
        .sort((a, b) => b.revenue - a.revenue);
      const rows = detailedRows.slice(0, 12);
      const totalTarget = rows.reduce((acc, row) => acc + row.target, 0);

      baseResult.kpis = [
        { label: "Receita realizada", value: formatCurrency(rows.reduce((acc, row) => acc + row.revenue, 0)) },
        { label: "Meta agregada", value: formatCurrency(totalTarget) },
        { label: "Cumprimento médio", value: formatPercent(rows.reduce((acc, row) => acc + row.attainment, 0) / rows.length) }
      ];

      baseResult.summary = {
        subject: `nos consultores de ${month}`,
        action: "Consolidamos",
        totalRevenue: detailedRows.reduce((acc, row) => acc + row.revenue, 0),
        totalUnits,
        revenueLabel: "receita",
        unitsLabel: "unidades",
        entityLabel: "consultor",
        entityLabelPlural: "consultores",
        entityGender: "m",
        best: rows[0]
          ? {
              name: rows[0].seller.name,
              revenue: rows[0].revenue,
              units: rows[0].units
            }
          : undefined,
        worst: rows.length > 1
          ? {
              name: rows[rows.length - 1].seller.name,
              revenue: rows[rows.length - 1].revenue,
              units: rows[rows.length - 1].units
            }
          : undefined
      };

      baseResult.table = rows.map((row) => ({
        columns: ["Consultor", "Região", "Meta", "Realizado", "%"],
        rows: [
          row.seller.name,
          row.region,
          formatCurrency(row.target),
          formatCurrency(row.revenue),
          formatPercent(row.attainment)
        ]
      }));

      baseResult.chart = {
        type: "bar",
        data: rows.map((row) => ({
          name: row.seller.name,
          Meta: Math.round(row.target),
          Realizado: Math.round(row.revenue)
        })),
        xKey: "name",
        series: [
          { key: "Meta", label: "Meta", color: COLOR_NEUTRAL },
          { key: "Realizado", label: "Realizado", color: COLOR_POSITIVE }
        ]
      };

      baseResult.narrative = `Comparativo de meta vs. realizado para ${rows.length} consultores em ${month}.`;
      return baseResult;
    }

    case "seller_performance": {
      const sellerMap = DATA.sellers.reduce<Record<string, Seller>>((acc, seller) => ({ ...acc, [seller.id]: seller }), {});
      const prevMonth = (() => {
        const idx = MONTHS.indexOf(month as (typeof MONTHS)[number]);
        return idx > 0 ? MONTHS[idx - 1] : month;
      })();
      const prevMap = DATA.sales
        .filter((sale) => sale.month === prevMonth)
        .reduce<Record<string, number>>((acc, sale) => {
          acc[sale.sellerId] = (acc[sale.sellerId] || 0) + revenueFromSale(sale);
          return acc;
        }, {});
      const sellerUnitsMap = monthSales.reduce<Record<string, number>>((acc, sale) => {
        acc[sale.sellerId] = (acc[sale.sellerId] || 0) + sale.qty;
        return acc;
      }, {});

      const rows = monthSales
        .reduce<Record<string, { seller: Seller; revenue: number }>>((acc, sale) => {
          acc[sale.sellerId] ||= { seller: sellerMap[sale.sellerId], revenue: 0 };
          acc[sale.sellerId].revenue += revenueFromSale(sale);
          return acc;
        }, {});

      const ranking = Object.values(rows)
        .map((entry) => {
          const previous = prevMap[entry.seller.id] || 1;
          const delta = entry.revenue / previous - 1;
          return {
            seller: entry.seller,
            sellerId: entry.seller.id,
            region: entry.seller.region,
            revenue: entry.revenue,
            delta
          };
        })
        .sort((a, b) => b.revenue - a.revenue)
        .slice(0, 10);

      baseResult.kpis = [
        { label: "Receita total", value: formatCurrency(totalRevenue) },
        { label: "Consultores ativos", value: String(Object.keys(rows).length) },
        { label: "Melhor crescimento", value: formatPercent(Math.max(...ranking.map((row) => row.delta))) }
      ];

      baseResult.summary = {
        subject: `no desempenho dos consultores em ${month}`,
        action: "Consolidamos",
        totalRevenue,
        totalUnits,
        revenueLabel: "receita",
        unitsLabel: "unidades",
        entityLabel: "consultor",
        entityLabelPlural: "consultores",
        entityGender: "m",
        best: ranking[0]
          ? {
              name: ranking[0].seller.name,
              revenue: ranking[0].revenue,
              units: sellerUnitsMap[ranking[0].sellerId]
            }
          : undefined,
        worst: ranking.length > 1
          ? {
              name: ranking[ranking.length - 1].seller.name,
              revenue: ranking[ranking.length - 1].revenue,
              units: sellerUnitsMap[ranking[ranking.length - 1].sellerId]
            }
          : undefined
      };

      baseResult.table = ranking.map((row, index) => ({
        columns: ["#", "Consultor", "Região", "Receita", "Crescimento"],
        rows: [
          index + 1,
          row.seller.name,
          row.region,
          formatCurrency(row.revenue),
          formatPercent(row.delta)
        ]
      }));

      baseResult.chart = {
        type: "bar",
        data: ranking.map((row) => ({
          name: row.seller.name,
          Receita: Math.round(row.revenue),
          Crescimento: Number((row.delta * 100).toFixed(1))
        })),
        xKey: "name",
        series: [
          { key: "Receita", label: "Receita", color: COLOR_ACCENT },
          { key: "Crescimento", label: "Crescimento (%)", color: COLOR_POSITIVE }
        ]
      };

      baseResult.narrative = `Top ${ranking.length} consultores por receita em ${month}, comparando crescimento com ${prevMonth}.`;
      return baseResult;
    }

    case "mix_products": {
      const productMap = DATA.products.reduce<Record<string, Product>>((acc, product) => ({ ...acc, [product.id]: product }), {});
      const byCategory = monthSales.reduce<Record<string, { category: string; revenue: number; units: number }>>(
        (acc, sale) => {
          const category = productMap[sale.productId].category;
          acc[category] ||= { category, revenue: 0, units: 0 };
          acc[category].revenue += revenueFromSale(sale);
          acc[category].units += sale.qty;
          return acc;
        },
        {}
      );

      const rows = Object.values(byCategory)
        .sort((a, b) => b.revenue - a.revenue)
        .slice(0, 10);

      baseResult.kpis = [
        { label: "Categorias ativas", value: String(Object.keys(byCategory).length) },
        { label: "Receita total", value: formatCurrency(totalRevenue) },
        { label: "Unidades totais", value: totalUnits.toLocaleString("pt-BR") }
      ];

      baseResult.summary = {
        subject: `no mix de categorias em ${month}`,
        action: "Consolidamos",
        totalRevenue,
        totalUnits,
        revenueLabel: "receita",
        unitsLabel: "unidades",
        entityLabel: "categoria",
        entityLabelPlural: "categorias",
        entityGender: "f",
        best: rows[0]
          ? {
              name: rows[0].category,
              revenue: rows[0].revenue,
              units: rows[0].units
            }
          : undefined,
        worst: rows.length > 1
          ? {
              name: rows[rows.length - 1].category,
              revenue: rows[rows.length - 1].revenue,
              units: rows[rows.length - 1].units
            }
          : undefined
      };

      baseResult.table = rows.map((row, index) => ({
        columns: ["#", "Categoria", "Receita", "Unidades", "Share"],
        rows: [
          index + 1,
          row.category,
          formatCurrency(row.revenue),
          row.units.toLocaleString("pt-BR"),
          formatPercent(row.revenue / totalRevenue)
        ]
      }));

      baseResult.chart = {
        type: "area",
        data: rows.map((row) => ({
          name: row.category,
          Receita: Math.round(row.revenue),
          Unidades: row.units
        })),
        xKey: "name",
        series: [
          { key: "Receita", label: "Receita", color: COLOR_ACCENT },
          { key: "Unidades", label: "Unidades", color: COLOR_POSITIVE }
        ]
      };

      baseResult.narrative = `Mix de categorias em ${month} evidencia top ${rows.length} grupos com maior contribuição em receita.`;
      return baseResult;
    }

    case "promotion_mix": {
      const productMap = DATA.products.reduce<Record<string, Product>>((acc, product) => ({ ...acc, [product.id]: product }), {});
      const aggregated = monthSales.reduce(
        (acc, sale) => {
          const isPromo = productMap[sale.productId].promo;
          const bucket = isPromo ? "Promocional" : "Linha base";
          acc[bucket].revenue += revenueFromSale(sale);
          acc[bucket].units += sale.qty;
          return acc;
        },
        {
          Promocional: { revenue: 0, units: 0 },
          "Linha base": { revenue: 0, units: 0 }
        }
      );

      const segments = Object.entries(aggregated).map(([label, stats]) => ({
        label,
        revenue: stats.revenue,
        units: stats.units
      }));
      const rankedSegments = [...segments].sort((a, b) => b.revenue - a.revenue);

      baseResult.kpis = [
        { label: "Receita total", value: formatCurrency(totalRevenue) },
        { label: "Share promocional", value: formatPercent(aggregated.Promocional.revenue / totalRevenue) },
        { label: "Unidades promocionais", value: aggregated.Promocional.units.toLocaleString("pt-BR") }
      ];

      baseResult.summary = {
        subject: `entre os segmentos de promoção em ${month}`,
        action: "Consolidamos",
        totalRevenue,
        totalUnits,
        revenueLabel: "receita",
        unitsLabel: "unidades",
        entityLabel: "segmento",
        entityLabelPlural: "segmentos",
        entityGender: "m",
        best: rankedSegments[0]
          ? {
              name: rankedSegments[0].label,
              revenue: rankedSegments[0].revenue,
              units: rankedSegments[0].units
            }
          : undefined,
        worst: rankedSegments.length > 1
          ? {
              name: rankedSegments[rankedSegments.length - 1].label,
              revenue: rankedSegments[rankedSegments.length - 1].revenue,
              units: rankedSegments[rankedSegments.length - 1].units
            }
          : undefined
      };

      baseResult.table = segments.map((segment) => ({
        columns: ["Segmento", "Receita", "Unidades", "Participação"],
        rows: [
          segment.label,
          formatCurrency(segment.revenue),
          segment.units.toLocaleString("pt-BR"),
          formatPercent(segment.revenue / totalRevenue)
        ]
      }));

      baseResult.chart = {
        type: "bar",
        data: segments.map((segment) => ({
          name: segment.label,
          Receita: Math.round(segment.revenue),
          Unidades: segment.units
        })),
        xKey: "name",
        series: [
          { key: "Receita", label: "Receita", color: COLOR_ACCENT },
          { key: "Unidades", label: "Unidades", color: COLOR_POSITIVE }
        ]
      };

      baseResult.narrative = `Participação de produtos promocionais vs linha base em ${month}.`;
      return baseResult;
    }

    case "top_products": {
      const productMap = DATA.products.reduce<Record<string, Product>>((acc, product) => ({ ...acc, [product.id]: product }), {});
      const rows = monthSales
        .reduce<Record<string, { product: Product; revenue: number; units: number }>>((acc, sale) => {
          const product = productMap[sale.productId];
          acc[product.id] ||= { product, revenue: 0, units: 0 };
          acc[product.id].revenue += revenueFromSale(sale);
          acc[product.id].units += sale.qty;
          return acc;
        }, {});

      const top = Object.values(rows)
        .sort((a, b) => b.revenue - a.revenue)
        .slice(0, 15);

      baseResult.kpis = [
        { label: "Receita total", value: formatCurrency(totalRevenue) },
        { label: "Produtos ativos", value: String(Object.keys(rows).length) },
        { label: "Receita top 5", value: formatCurrency(top.slice(0, 5).reduce((acc, row) => acc + row.revenue, 0)) }
      ];

      baseResult.summary = {
        subject: `no mix de produtos em ${month}`,
        action: "Vendemos",
        totalRevenue,
        totalUnits,
        revenueLabel: "receita",
        unitsLabel: "unidades",
        entityLabel: "produto",
        entityLabelPlural: "produtos",
        entityGender: "m",
        best: top[0]
          ? {
              name: top[0].product.name,
              revenue: top[0].revenue,
              units: top[0].units
            }
          : undefined,
        worst: top.length > 1
          ? {
              name: top[top.length - 1].product.name,
              revenue: top[top.length - 1].revenue,
              units: top[top.length - 1].units
            }
          : undefined
      };

      baseResult.table = top.map((entry, index) => ({
        columns: ["#", "Produto", "Categoria", "Receita", "Unidades"],
        rows: [
          index + 1,
          entry.product.name,
          entry.product.category,
          formatCurrency(entry.revenue),
          entry.units.toLocaleString("pt-BR")
        ]
      }));

      baseResult.chart = {
        type: "bar",
        data: top.map((entry) => ({
          name: entry.product.name,
          Receita: Math.round(entry.revenue),
          Unidades: entry.units
        })),
        xKey: "name",
        series: [
          { key: "Receita", label: "Receita", color: COLOR_ACCENT },
          { key: "Unidades", label: "Unidades", color: COLOR_POSITIVE }
        ]
      };

      baseResult.narrative = `Top ${top.length} produtos em ${month} considerando receita e volume vendidos.`;
      return baseResult;
    }

    case "brand_sales": {
      const brand = filters.brand;
      if (!brand) {
        baseResult.narrative = `Marca não informada.`;
        baseResult.kpis = [{ label: "Mensagem", value: "Selecione uma marca para visualizar os resultados." }];
        return baseResult;
      }

      const { productName } = filters as { productName?: string };
      const productLabel = productName ?? brand;
      const productMap = DATA.products.reduce<Record<string, Product>>((acc, product) => ({ ...acc, [product.id]: product }), {});
      const brandSales = monthSales.filter((sale) => productMap[sale.productId].brand.toLowerCase() === brand.toLowerCase());

      let relevantSales = brandSales;
      if (productName) {
        const normalizedProduct = productName.toLowerCase();
        const productExact = brandSales.filter(
          (sale) => productMap[sale.productId].name.toLowerCase() === normalizedProduct
        );
        if (productExact.length > 0) {
          relevantSales = productExact;
        }
      }

      if (relevantSales.length === 0) {
        baseResult.kpis = [{ label: "Receita", value: formatCurrency(0) }];
        baseResult.table = [];
        baseResult.narrative = `Nenhuma venda encontrada para ${productLabel} em ${month}.`;
        return baseResult;
      }

      const sellerMap = DATA.sellers.reduce<Record<string, Seller>>((acc, seller) => ({ ...acc, [seller.id]: seller }), {});
      const bySeller = relevantSales.reduce<Record<string, { seller: Seller; revenue: number; units: number }>>((acc, sale) => {
        const seller = sellerMap[sale.sellerId];
        if (!seller) return acc;
        acc[sale.sellerId] ||= { seller, revenue: 0, units: 0 };
        acc[sale.sellerId].revenue += revenueFromSale(sale);
        acc[sale.sellerId].units += sale.qty;
        return acc;
      }, {});

      const sellerRows = Object.values(bySeller).sort((a, b) => b.revenue - a.revenue);
      const totalProductRevenue = sellerRows.reduce((acc, row) => acc + row.revenue, 0);
      const totalProductUnits = sellerRows.reduce((acc, row) => acc + row.units, 0);

      baseResult.kpis = [
        { label: "Receita do produto", value: formatCurrency(totalProductRevenue) },
        { label: "Unidades vendidas", value: totalProductUnits.toLocaleString("pt-BR") },
        { label: "Vendedores ativos", value: sellerRows.length.toString() }
      ];

      baseResult.summary = {
        subject: `de ${productLabel} neste período`,
        action: "Vendemos",
        totalRevenue: totalProductRevenue,
        totalUnits: totalProductUnits,
        revenueLabel: "receita",
        unitsLabel: "unidades",
        entityLabel: "consultor",
        entityLabelPlural: "consultores",
        entityGender: "m",
        best: sellerRows[0]
          ? {
              name: sellerRows[0].seller.name,
              revenue: sellerRows[0].revenue,
              units: sellerRows[0].units
            }
          : undefined,
        worst: sellerRows.length > 1
          ? {
              name: sellerRows[sellerRows.length - 1].seller.name,
              revenue: sellerRows[sellerRows.length - 1].revenue,
              units: sellerRows[sellerRows.length - 1].units
            }
          : undefined
      };

      baseResult.table = sellerRows.map((entry, index) => ({
        columns: ["#", "Vendedor", "Receita", "Unidades"],
        rows: [
          index + 1,
          entry.seller.name,
          formatCurrency(entry.revenue),
          entry.units.toLocaleString("pt-BR")
        ]
      }));

      baseResult.chart = {
        type: "bar",
        data: sellerRows.map((entry) => ({
          name: entry.seller.name,
          Receita: Math.round(entry.revenue)
        })),
        xKey: "name",
        series: [{ key: "Receita", label: "Receita", color: COLOR_ACCENT }]
      };

      baseResult.narrative = `Receita de ${productLabel} detalhada por vendedor em ${month}.`;
      return baseResult;
    }

    case "avg_ticket": {
      const byRegion = monthSales.reduce<Record<string, { revenue: number; orders: Set<string>; units: number }>>((acc, sale) => {
        acc[sale.region] ||= { revenue: 0, orders: new Set(), units: 0 };
        acc[sale.region].revenue += revenueFromSale(sale);
        acc[sale.region].orders.add(sale.orderId);
        acc[sale.region].units += sale.qty;
        return acc;
      }, {});

      const rows = Object.entries(byRegion)
        .map(([region, stats]) => ({
          region,
          ticket: stats.revenue / stats.orders.size,
          orders: stats.orders.size,
          revenue: stats.revenue,
          units: stats.units
        }))
        .sort((a, b) => b.ticket - a.ticket);

      baseResult.kpis = [
        { label: "Ticket médio geral", value: formatCurrency(totalRevenue / totalOrders) },
        { label: "Pedidos no mês", value: totalOrders.toLocaleString("pt-BR") },
        { label: "Clientes ativos", value: uniqueClients.toLocaleString("pt-BR") }
      ];

      baseResult.summary = {
        subject: `no ticket médio por região em ${month}`,
        action: "Consolidamos",
        totalRevenue,
        totalUnits: totalOrders,
        revenueLabel: "ticket médio",
        unitsLabel: "pedidos",
        entityLabel: "região",
        entityLabelPlural: "regiões",
        entityGender: "f",
        best: rows[0]
          ? {
              name: rows[0].region,
              revenue: rows[0].ticket,
              units: rows[0].orders
            }
          : undefined,
        worst: rows.length > 1
          ? {
              name: rows[rows.length - 1].region,
              revenue: rows[rows.length - 1].ticket,
              units: rows[rows.length - 1].orders
            }
          : undefined
      };

      baseResult.table = rows.map((row, index) => ({
        columns: ["#", "Região", "Ticket médio", "Pedidos"],
        rows: [
          index + 1,
          row.region,
          formatCurrency(row.ticket),
          row.orders.toLocaleString("pt-BR")
        ]
      }));

      baseResult.chart = {
        type: "area",
        data: rows.map((row) => ({
          name: row.region,
          Ticket: Math.round(row.ticket),
          Pedidos: row.orders
        })),
        xKey: "name",
        series: [
          { key: "Ticket", label: "Ticket médio", color: COLOR_ACCENT },
          { key: "Pedidos", label: "Pedidos", color: COLOR_POSITIVE }
        ]
      };

      baseResult.narrative = `Ticket médio por região para ${month}, destacando ${rows[0]?.region ?? "todas"} como maior valor.`;
      return baseResult;
    }

    case "sales_overview":
    default: {
      const byRegion = monthSales.reduce<Record<string, { revenue: number; units: number }>>((acc, sale) => {
        acc[sale.region] ||= { revenue: 0, units: 0 };
        acc[sale.region].revenue += revenueFromSale(sale);
        acc[sale.region].units += sale.qty;
        return acc;
      }, {});

      const regionData = Object.entries(byRegion)
        .map(([region, stats]) => ({
          region,
          revenue: stats.revenue,
          units: stats.units
        }))
        .sort((a, b) => b.revenue - a.revenue);

      baseResult.kpis = [
        { label: "Receita total", value: formatCurrency(totalRevenue) },
        { label: "Unidades", value: totalUnits.toLocaleString("pt-BR") },
        { label: "Pedidos", value: totalOrders.toLocaleString("pt-BR") }
      ];

      baseResult.summary = {
        subject: `no panorama das regiões em ${month}`,
        action: "Consolidamos",
        totalRevenue,
        totalUnits,
        revenueLabel: "receita",
        unitsLabel: "unidades",
        entityLabel: "região",
        entityLabelPlural: "regiões",
        entityGender: "f",
        best: regionData[0]
          ? {
              name: regionData[0].region,
              revenue: regionData[0].revenue,
              units: regionData[0].units
            }
          : undefined,
        worst: regionData.length > 1
          ? {
              name: regionData[regionData.length - 1].region,
              revenue: regionData[regionData.length - 1].revenue,
              units: regionData[regionData.length - 1].units
            }
          : undefined
      };

      baseResult.table = regionData.map((row, index) => ({
        columns: ["#", "Região", "Receita", "Participação"],
        rows: [
          index + 1,
          row.region,
          formatCurrency(row.revenue),
          formatPercent(row.revenue / totalRevenue)
        ]
      }));

      baseResult.chart = {
        type: "area",
        data: regionData.map((row) => ({
          name: row.region,
          Receita: Math.round(row.revenue)
        })),
        xKey: "name",
        series: [{ key: "Receita", label: "Receita", color: COLOR_ACCENT }]
      };

      baseResult.narrative = `Resumo consolidado de vendas para ${month}, destacando regiões com maior participação de receita.`;
      return baseResult;
    }
  }
}

function runQueryStructured(filters: TParsedQuery, fallbackMonth = "2025-11", rawQuestion?: string): QueryResult {
  const normalizedParts = [
    `intent:${filters.intent}`,
    filters.month ? `month:${filters.month}` : undefined,
    filters.region ? `region:${filters.region}` : undefined,
    filters.brand ? `brand:${filters.brand}` : undefined,
    filters.sellerId ? `seller:${filters.sellerId}` : undefined,
    filters.promoOnly ? "promoOnly:true" : undefined
  ].filter(Boolean);

  const syntheticQuestion = normalizedParts.join(" ");
  const month = filters.month ?? extractMonth(syntheticQuestion, fallbackMonth);
  const productName = filters.brand ? extractProductNameFromQuery(rawQuestion ?? "") : undefined;
  const runtimeFilters: Partial<TParsedQuery> & { productName?: string } = { ...filters };
  if (productName) {
    runtimeFilters.productName = productName;
  }

  return runQuery(filters.intent, month, runtimeFilters);
}

// Componente de lista de mensagens
function MessagesList({ 
  messages, 
  expandedContext, 
  setExpandedContext 
}: { 
  messages: ChatMessage[]; 
  expandedContext: string | null; 
  setExpandedContext: (id: string | null) => void;
}) {
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages]);

  return (
    <div className="flex-1 flex flex-col gap-4 py-6 overflow-y-auto">
      {messages.map((message, index) => (
        <div key={message.id} className="w-full">
          {message.role === 'user' ? (
            <div className="flex justify-end">
              <div className="max-w-[85%] sm:max-w-[75%] rounded-2xl bg-blue-600/90 px-4 py-3 text-sm sm:text-base text-white shadow-lg shadow-blue-900/30">
                {message.content}
              </div>
            </div>
          ) : (
            <div className="flex justify-start">
              <div className="w-full max-w-[85%] sm:max-w-[90%]">
                {/* Usa CopilotAnswerCard se tiver payload estruturado, senão usa DipamAnswerCard */}
                {message.payload ? (
                  <CopilotAnswerCard payload={message.payload} />
                ) : (
                  <DipamAnswerCard
                    pergunta={messages[index - 1]?.role === 'user' ? messages[index - 1].content : "Pergunta não disponível"}
                    intent={message.payload?.intent || "outros"}
                    confianca={message.payload?.confidence ?? 0.5}
                    respostaMarkdown={message.content || ""}
                    contexto={{}}
                    showDetalhes={expandedContext === message.id}
                    onToggleDetalhes={() => {
                      setExpandedContext(expandedContext === message.id ? null : message.id);
                    }}
                  />
                )}
              </div>
            </div>
          )}
        </div>
      ))}
      <div ref={messagesEndRef} />
    </div>
  );
}

// Componente de input fixo no rodapé
function ChatInputBar({ 
  input, 
  setInput, 
  isLoading, 
  onSubmit 
}: { 
  input: string; 
  setInput: (value: string) => void; 
  isLoading: boolean; 
  onSubmit: (e: React.FormEvent) => void;
}) {
  const inputRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    if (!isLoading) {
      inputRef.current?.focus();
    }
  }, [isLoading]);

  return (
    <footer className="sticky bottom-0 left-0 right-0 border-t border-slate-800 bg-slate-950/95 backdrop-blur z-20">
      <form
        onSubmit={onSubmit}
        className="max-w-5xl mx-auto flex items-center gap-3 px-4 py-3"
      >
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => {
            const target = e.target as HTMLTextAreaElement;
            setInput(target.value);
            // Auto-resize
            target.style.height = 'auto';
            target.style.height = `${Math.min(target.scrollHeight, 160)}px`;
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              onSubmit(e as any);
            }
          }}
          placeholder="Digite sua pergunta..."
          rows={1}
          className="flex-1 resize-none rounded-2xl bg-slate-900/80 border border-slate-700 px-4 py-3 text-sm text-slate-50 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500 max-h-[160px] overflow-y-auto placeholder:text-slate-400"
          disabled={isLoading}
        />
        <button
          type="submit"
          className="inline-flex items-center justify-center rounded-2xl bg-sky-500 hover:bg-sky-400 px-5 py-2 text-sm font-medium text-slate-950 transition disabled:opacity-50 disabled:cursor-not-allowed"
          disabled={!input.trim() || isLoading}
        >
          {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Enviar"}
        </button>
      </form>
    </footer>
  );
}

export default function DipaPanel() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [expandedContext, setExpandedContext] = useState<string | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);

  const hasConversation = messages.length > 0;

  useEffect(() => {
    const updateViewport = () => {
      setIsMobile(window.innerWidth < 768);
    };

    updateViewport();
    window.addEventListener("resize", updateViewport);
    return () => window.removeEventListener("resize", updateViewport);
  }, []);

  // Função comum para enviar pergunta (usada tanto no landing quanto no chat)
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const question = input.trim();
    if (!question || busy) return;

    // Limpa erros anteriores
    setError(null);
    
    // Limpa o input imediatamente
    setInput("");
    
    // Adiciona mensagem do usuário
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: question
    };
    
    setMessages((msgs) => [...msgs, userMessage]);
    setBusy(true);
    setHistoryOpen(false);

    try {
      // Chama a API do Dipam AI
      const response = await askDipamAgent({
        pergunta: question,
        usuarioId: "fabiano",
        papel: "diretor"
      });

      // Adiciona resposta do agente
      // Usa payload estruturado do backend se disponível, senão constrói a partir da resposta
      const copilotPayload: CopilotAnswerPayload = response.payload || {
          intent: response.intent,
        intentLabel: response.intent === "consulta_meta" 
          ? "Consulta de Meta" 
          : response.intent === "consulta_vendedores_performance"
          ? "Consulta Vendedores Performance"
          : "Consulta Geral",
        confidence: response.confidence,
        question: response.question,
        resumoExecutivo: response.resumoExecutivo,
        kpis: response.kpis,
        topVendedores: response.topVendedores,
        insights: Array.isArray(response.insights) 
          ? response.insights.join("\n") 
          : (typeof response.insights === "string" ? response.insights : undefined),
        observacoes: Array.isArray(response.observacoes) 
          ? response.observacoes.join("\n") 
          : (typeof response.observacoes === "string" ? response.observacoes : undefined),
        // FASE 5: Inclui structured se disponível diretamente na resposta
        structured: response.structured,
      };
      
      // Se não houver structured no payload mas houver no response, adiciona
      if (!copilotPayload.structured && response.structured) {
        copilotPayload.structured = response.structured;
      }
      
      const agentMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: response.resumoExecutivo || response.question || "",
        // Payload estruturado para renderização no CopilotAnswerCard
        payload: copilotPayload
      };
      
      setMessages((msgs) => [...msgs, agentMessage]);
      
    } catch (error) {
      console.error("Erro ao chamar API do Dipam AI:", error);
      
      const errorMessage = error instanceof DipamApiError 
        ? error.message 
        : "Erro ao conectar com o agente. Verifique se a API está rodando.";
      
      setError(errorMessage);
      
      // Adiciona mensagem de erro como resposta do agente
      const errorAgentMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `❌ ${errorMessage}`
      };
      
      setMessages((msgs) => [...msgs, errorAgentMessage]);
    } finally {
      setBusy(false);
      // Mantém foco no input após resposta
      setTimeout(() => {
        inputRef.current?.focus();
      }, 100);
    }
  };

  // Scroll automático já é gerenciado pelo MessagesList

  // Renderização condicional: Landing vs Chat
  if (!hasConversation) {
    // LANDING: Tela inicial sem conversa
  return (
      <div className={clsx("min-h-screen flex flex-col", ds.colors.background, "text-slate-200")}>
        <header className="flex-shrink-0 border-b border-slate-800/80 bg-slate-900/90 backdrop-blur z-10">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 sm:py-6 lg:px-8">
          <div className="flex items-center gap-2 sm:gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-blue-500/40 bg-blue-500/20 shadow-lg shadow-blue-900/40 sm:h-12 sm:w-12">
              <Image src={logoDipam} alt="Logotipo Dipam" className="h-7 w-7 object-contain sm:h-8 sm:w-8" priority />
            </div>
            <div>
              <h1 className="text-2xl font-semibold text-slate-100 sm:text-[2.5rem] sm:leading-tight">DIPAM COPILOT™</h1>
              <p className="mt-0.5 text-xs text-slate-400 sm:mt-1 sm:text-sm">Inteligência comercial em tempo real</p>
            </div>
          </div>
          <div className="flex items-center gap-2 sm:gap-3">
            <Button
              type="button"
              variant="ghost"
              className="gap-2 text-xs font-medium text-slate-300 hover:text-slate-100 sm:text-sm"
              onClick={() => setHistoryOpen(true)}
            >
              <History className="h-4 w-4" />
              Histórico
            </Button>
            <span className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-[10px] font-medium uppercase tracking-wide text-slate-300 sm:text-xs">
              Protótipo
            </span>
          </div>
        </div>
      </header>

      {/* LANDING: Input centralizado grande */}
      <main className="flex-1 flex flex-col items-center justify-center px-4">
        <div className="w-full max-w-2xl text-center space-y-6">
          <h1 className="text-2xl font-semibold text-slate-100">Como posso ajudar?</h1>
          <p className="text-sm text-slate-400">
            Faça uma pergunta sobre metas, vendas, clientes ou oportunidades.
          </p>

          <form onSubmit={handleSubmit}>
            <div className="bg-slate-900/60 border border-slate-700 rounded-2xl px-4 py-3 flex items-end gap-3">
          <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => {
                  const target = e.target as HTMLTextAreaElement;
                  setInput(target.value);
                  // Auto-resize
                  target.style.height = 'auto';
                  target.style.height = `${Math.min(target.scrollHeight, 160)}px`;
                }}
                placeholder="Digite sua pergunta..."
                className="w-full bg-transparent outline-none resize-none text-slate-100 text-sm max-h-40 placeholder:text-slate-400"
                rows={3}
                disabled={busy}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmit(e);
                  }
                }}
              />
              <button
                type="submit"
                className="shrink-0 px-4 py-2 rounded-full bg-blue-600 hover:bg-blue-500 text-sm font-medium text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                disabled={!input.trim() || busy}
              >
                {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Perguntar"}
              </button>
          </div>
          </form>
        </div>
      </main>
    </div>
    );
  }

  // CHAT: Layout após primeira pergunta
  return (
    <div className={clsx("min-h-screen flex flex-col", ds.colors.background, "text-slate-200")}>
      <header className="flex-shrink-0 border-b border-slate-800/80 bg-slate-900/90 backdrop-blur z-10">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 sm:py-6 lg:px-8">
          <div className="flex items-center gap-2 sm:gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-blue-500/40 bg-blue-500/20 shadow-lg shadow-blue-900/40 sm:h-12 sm:w-12">
              <Image src={logoDipam} alt="Logotipo Dipam" className="h-7 w-7 object-contain sm:h-8 sm:w-8" priority />
            </div>
            <div>
              <h1 className="text-2xl font-semibold text-slate-100 sm:text-[2.5rem] sm:leading-tight">DIPAM COPILOT™</h1>
              <p className="mt-0.5 text-xs text-slate-400 sm:mt-1 sm:text-sm">Inteligência comercial em tempo real</p>
            </div>
          </div>
          <div className="flex items-center gap-2 sm:gap-3">
            <Button
              type="button"
              variant="ghost"
              className="gap-2 text-xs font-medium text-slate-300 hover:text-slate-100 sm:text-sm"
              onClick={() => setHistoryOpen(true)}
            >
              <History className="h-4 w-4" />
              Histórico
            </Button>
            <span className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-[10px] font-medium uppercase tracking-wide text-slate-300 sm:text-xs">
              Protótipo
            </span>
          </div>
        </div>
      </header>

      {/* Área de mensagens scrollável */}
      <main className="flex-1 flex justify-center overflow-hidden">
        <div className="w-full max-w-4xl flex flex-col px-4 pb-24">
          {busy && messages.length > 0 && (
            <div className="flex justify-start mb-4">
              <div className="w-full max-w-[85%] sm:max-w-[90%] rounded-3xl border border-slate-700/70 bg-slate-900/70 p-6 shadow-xl shadow-blue-900/30 sm:p-8 animate-pulse">
                <div className="flex flex-col gap-2 text-left">
                  <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-500">Resposta do DIPAM COPILOT™</p>
                  <div className="mt-2 h-5 w-2/3 rounded-full bg-slate-700/70" />
                </div>
                <div className="mt-6 space-y-3 text-left">
                  <div className="h-4 rounded-full bg-slate-800/70" />
                  <div className="h-4 w-11/12 rounded-full bg-slate-800/60" />
                  <div className="h-4 w-4/5 rounded-full bg-slate-800/50" />
                </div>
              </div>
                      </div>
          )}
          <MessagesList 
            messages={messages} 
            expandedContext={expandedContext}
            setExpandedContext={setExpandedContext}
          />
                                  </div>
      </main>

      {/* Input fixo no rodapé */}
      <ChatInputBar
        input={input}
        setInput={setInput}
        isLoading={busy}
        onSubmit={handleSubmit}
      />


      {historyOpen ? (
        <div className="fixed inset-0 z-40 flex items-start justify-center sm:justify-end">
          <div className="absolute inset-0 bg-black/40" onClick={() => setHistoryOpen(false)} />
          <div className="relative mt-24 w-full max-w-md rounded-3xl border border-slate-700 bg-slate-900/95 p-6 shadow-2xl backdrop-blur">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-100">Histórico recente</h3>
              <button
                type="button"
                onClick={() => setHistoryOpen(false)}
                className="rounded-full border border-slate-700/60 bg-slate-800/70 p-1.5 text-slate-300 transition hover:border-blue-500/40 hover:text-slate-100"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="mt-4 max-h-[60vh] overflow-y-auto pr-1">
              <ChatHistory 
                messages={messages.map(m => ({
                  role: m.role === 'user' ? 'user' as const : 'assistant' as const,
                  text: m.content,
                  timestamp: m.id,
                  intent: m.role === 'assistant' && m.payload ? m.payload.intent : undefined,
                  confianca: m.role === 'assistant' && m.payload ? m.payload.confidence : undefined,
                  contexto: m.role === 'assistant' && m.payload ? m.payload : undefined
                }))} 
                emptyMessage="Nenhuma interação ainda." 
              />
            </div>
          </div>
        </div>
      ) : null}

      {/* Preview analítico removido - não mais necessário com novo layout de chat */}
    </div>
  );
}
