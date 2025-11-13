"use client";

import React, { Fragment, useEffect, useMemo, useRef, useState } from "react";
import Image from "next/image";
import { clsx } from "clsx";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowRight, Loader2, Sparkles } from "lucide-react";
import type { TParsedQuery } from "@/app/api/query/schema";
import logoDipam from "@/assets/logo_dipam.avif";
import { ds } from "@/styles/ui";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip as RTooltip,
  XAxis,
  YAxis
} from "recharts";

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

type Intent =
  | "target_vs_actual"
  | "seller_performance"
  | "mix_products"
  | "promotion_mix"
  | "top_products"
  | "avg_ticket"
  | "sales_overview"
  | "brand_sales";

const INTENT_LABELS: Record<Intent, string> = {
  target_vs_actual: "Meta vs realizado",
  seller_performance: "Performance de vendedores",
  mix_products: "Mix de produtos",
  promotion_mix: "Mix promocional",
  top_products: "Top produtos",
  avg_ticket: "Ticket médio",
  sales_overview: "Visão geral",
  brand_sales: "Vendas por marca"
};

type ChartConfig = {
  type: "area" | "bar";
  data: Record<string, string | number>[];
  xKey: string;
  series: { key: string; label: string; color: string }[];
};

type QueryResult = {
  intent: Intent;
  month: string;
  kpis: { label: string; value: string; helper?: string }[];
  narrative: string;
  table: {
    columns: string[];
    rows: (string | number)[];
  }[];
  chart?: ChartConfig;
};

type Message = {
  role: "user" | "assistant";
  text: string;
  result?: QueryResult;
};

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

function ChatBubble({ role, text }: { role: "user" | "assistant"; text: string }) {
  const isUser = role === "user";
  const bubbleClass = isUser ? ds.chat.user : ds.chat.assistant;

  return (
    <div className={clsx("flex", isUser ? "justify-end" : "justify-start")}>
      <div className={clsx(bubbleClass, "flex flex-col gap-1 transition duration-150")}>
        <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-300 opacity-70">
          {isUser ? "Você" : "DIPA"}
        </span>
        <p className="text-sm leading-relaxed">{text}</p>
      </div>
    </div>
  );
}

function PromptChip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={clsx(ds.chip.base, active ? ds.chip.active : ds.chip.default)}
    >
      {label}
    </button>
  );
}

function InsightChip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={clsx(ds.chip.base, "text-xs", active ? ds.chip.active : ds.chip.default)}
    >
      {label}
    </button>
  );
}

function KpiStat({ label, value, helper }: { label: string; value: string; helper?: string }) {
  return (
    <div className="space-y-2 rounded-xl border border-slate-700 bg-slate-800/70 p-4 shadow-inner shadow-blue-900/20">
      <p className={ds.typography.kpiLabel}>{label}</p>
      <p className={ds.typography.kpiValue}>{value}</p>
      {helper ? <p className="text-xs text-slate-400">{helper}</p> : null}
    </div>
  );
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

const EXAMPLES = [
  "Comparar meta vs realizado de 2025-11 por vendedor",
  "Mostrar o mix de produtos promocionais em 2025-10",
  "Quais são os top produtos por receita em 2025-08?",
  "Resumo geral de vendas para 2025-11",
  "Ticket médio por região em 2025-09",
  "Quanto foi vendido de Nissin Miojo Galinha Caipira neste mês"
];

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
    table: []
  };

  switch (intent) {
    case "target_vs_actual": {
      const sellerMap = DATA.sellers.reduce<Record<string, Seller>>((acc, seller) => ({ ...acc, [seller.id]: seller }), {});
      const bySeller = monthSales.reduce<Record<string, { seller: Seller; revenue: number }>>((acc, sale) => {
        acc[sale.sellerId] ||= { seller: sellerMap[sale.sellerId], revenue: 0 };
        acc[sale.sellerId].revenue += revenueFromSale(sale);
        return acc;
      }, {});

      const rows = Object.values(bySeller)
        .map((entry) => {
          const attainment = entry.revenue / entry.seller.monthlyTarget;
          return {
            seller: entry.seller.name,
            region: entry.seller.region,
            target: entry.seller.monthlyTarget,
            revenue: entry.revenue,
            attainment
          };
        })
        .sort((a, b) => b.revenue - a.revenue)
        .slice(0, 12);

      const totalTarget = rows.reduce((acc, row) => acc + row.target, 0);

      baseResult.kpis = [
        { label: "Receita realizada", value: formatCurrency(rows.reduce((acc, row) => acc + row.revenue, 0)) },
        { label: "Meta agregada", value: formatCurrency(totalTarget) },
        { label: "Cumprimento médio", value: formatPercent(rows.reduce((acc, row) => acc + row.attainment, 0) / rows.length) }
      ];

      baseResult.table = rows.map((row) => ({
        columns: ["Consultor", "Região", "Meta", "Realizado", "%"],
        rows: [
          row.seller,
          row.region,
          formatCurrency(row.target),
          formatCurrency(row.revenue),
          formatPercent(row.attainment)
        ]
      }));

      baseResult.chart = {
        type: "bar",
        data: rows.map((row) => ({
          name: row.seller,
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
            seller: entry.seller.name,
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

      baseResult.table = ranking.map((row, index) => ({
        columns: ["#", "Consultor", "Região", "Receita", "Crescimento"],
        rows: [
          index + 1,
          row.seller,
          row.region,
          formatCurrency(row.revenue),
          formatPercent(row.delta)
        ]
      }));

      baseResult.chart = {
        type: "bar",
        data: ranking.map((row) => ({
          name: row.seller,
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

      baseResult.kpis = [
        { label: "Receita total", value: formatCurrency(totalRevenue) },
        { label: "Share promocional", value: formatPercent(aggregated.Promocional.revenue / totalRevenue) },
        { label: "Unidades promocionais", value: aggregated.Promocional.units.toLocaleString("pt-BR") }
      ];

      baseResult.table = Object.entries(aggregated).map(([label, stats]) => ({
        columns: ["Segmento", "Receita", "Unidades", "Participação"],
        rows: [
          label,
          formatCurrency(stats.revenue),
          stats.units.toLocaleString("pt-BR"),
          formatPercent(stats.revenue / totalRevenue)
        ]
      }));

      baseResult.chart = {
        type: "bar",
        data: Object.entries(aggregated).map(([label, stats]) => ({
          name: label,
          Receita: Math.round(stats.revenue),
          Unidades: stats.units
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
      const byRegion = monthSales.reduce<Record<string, { revenue: number; orders: Set<string> }>>((acc, sale) => {
        acc[sale.region] ||= { revenue: 0, orders: new Set() };
        acc[sale.region].revenue += revenueFromSale(sale);
        acc[sale.region].orders.add(sale.orderId);
        return acc;
      }, {});

      const rows = Object.entries(byRegion)
        .map(([region, stats]) => ({
          region,
          ticket: stats.revenue / stats.orders.size,
          orders: stats.orders.size
        }))
        .sort((a, b) => b.ticket - a.ticket);

      baseResult.kpis = [
        { label: "Ticket médio geral", value: formatCurrency(totalRevenue / totalOrders) },
        { label: "Pedidos no mês", value: totalOrders.toLocaleString("pt-BR") },
        { label: "Clientes ativos", value: uniqueClients.toLocaleString("pt-BR") }
      ];

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
      const byRegion = monthSales.reduce<Record<string, { revenue: number }>>((acc, sale) => {
        acc[sale.region] ||= { revenue: 0 };
        acc[sale.region].revenue += revenueFromSale(sale);
        return acc;
      }, {});

      const regionData = Object.entries(byRegion)
        .map(([region, stats]) => ({
          region,
          revenue: stats.revenue
        }))
        .sort((a, b) => b.revenue - a.revenue);

      baseResult.kpis = [
        { label: "Receita total", value: formatCurrency(totalRevenue) },
        { label: "Unidades", value: totalUnits.toLocaleString("pt-BR") },
        { label: "Pedidos", value: totalOrders.toLocaleString("pt-BR") }
      ];

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

function KPIGrid({ items }: { items: QueryResult["kpis"] }) {
  if (!items.length) return null;

  return (
    <Card className="min-w-0">
      <CardContent className="grid gap-4 sm:grid-cols-3">
        {items.map((item) => (
          <KpiStat key={item.label} label={item.label} value={item.value} helper={item.helper} />
        ))}
      </CardContent>
    </Card>
  );
}

function ResultTable({ result }: { result: QueryResult }) {
  if (!result.table.length) return null;

  const numericColumnStart = Math.max(result.table[0].columns.length - 2, 1);

  return (
    <Card className="min-w-0">
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-800 text-left text-sm text-slate-300">
            <thead className="bg-slate-900/80 text-xs font-semibold uppercase tracking-wide text-slate-400">
              <tr>
                {result.table[0].columns.map((column, idx) => (
                  <th
                    key={column}
                    className={clsx("px-4 py-3", idx >= numericColumnStart && "text-right")}
                  >
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {result.table.map((row, rowIndex) => (
                <tr key={`${rowIndex}-${row.rows[0]}`} className="odd:bg-slate-900/50 even:bg-slate-900/30">
                  {row.rows.map((value, cellIndex) => (
                    <td
                      key={`${rowIndex}-${cellIndex}`}
                      className={clsx(
                        "px-4 py-3 text-sm text-slate-300",
                        cellIndex >= numericColumnStart && "text-right font-semibold text-slate-50"
                      )}
                    >
                      {value}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

function ResultChart({ result }: { result?: QueryResult["chart"] }) {
  if (!result) return null;

  const renderSeries = () => {
    if (result.type === "area") {
      return result.series.map((serie) => (
        <Area key={serie.key} type="monotone" dataKey={serie.key} stroke={serie.color} fill={serie.color} fillOpacity={0.12} />
      ));
    }
    return result.series.map((serie) => (
      <Bar key={serie.key} dataKey={serie.key} fill={serie.color} radius={[10, 10, 0, 0]} />
    ));
  };

  return (
    <Card className="min-w-0">
      <CardContent className="h-80 w-full overflow-hidden p-0">
        <ResponsiveContainer width="100%" height="100%">
          {result.type === "area" ? (
            <AreaChart data={result.data} margin={{ top: 16, right: 24, left: 12, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={ds.chart.grid} />
              <XAxis dataKey={result.xKey} tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: ds.chart.axis }} />
              <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: ds.chart.axis }} />
              <RTooltip contentStyle={{ background: ds.chart.tooltip, border: `1px solid ${ds.chart.tooltipBorder}`, borderRadius: 12 }} />
              <Legend />
              {renderSeries()}
            </AreaChart>
          ) : (
            <BarChart data={result.data} margin={{ top: 16, right: 24, left: 12, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={ds.chart.grid} />
              <XAxis dataKey={result.xKey} tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: ds.chart.axis }} />
              <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: ds.chart.axis }} />
              <RTooltip contentStyle={{ background: ds.chart.tooltip, border: `1px solid ${ds.chart.tooltipBorder}`, borderRadius: 12 }} />
              <Legend />
              {renderSeries()}
            </BarChart>
          )}
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

function PromptChips({
  examples,
  activeValue,
  onSelect
}: {
  examples: string[];
  activeValue: string;
  onSelect: (example: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {examples.map((example) => (
        <PromptChip key={example} label={example} active={example === activeValue} onClick={() => onSelect(example)} />
      ))}
    </div>
  );
}

function InsightChips({
  insights,
  activeIndex,
  onSelect
}: {
  insights: { index: number; question: string }[];
  activeIndex: number | null;
  onSelect: (index: number) => void;
}) {
  if (!insights.length) {
    return <p className="text-xs text-slate-500">Nenhum insight gerado ainda.</p>;
  }

  return (
    <div className="flex flex-wrap gap-2">
      {insights.map((entry) => (
        <InsightChip
          key={entry.index}
          label={entry.question.length > 48 ? `${entry.question.slice(0, 48)}…` : entry.question}
          active={entry.index === activeIndex}
          onClick={() => onSelect(entry.index)}
        />
      ))}
    </div>
  );
}

function ChatHistory({ messages }: { messages: Message[] }) {
  if (!messages.length) {
    return <p className="text-sm text-slate-500">Nenhuma interação ainda. Gere um insight para iniciar.</p>;
  }

  return (
    <div className="space-y-3">
      {messages.map((message, index) => (
        <ChatBubble key={`${message.role}-${index}`} role={message.role} text={message.text} />
      ))}
    </div>
  );
}

export default function DipaPanel() {
  const [question, setQuestion] = useState("Comparar meta vs realizado por vendedor em 2025-11 na Grande Porto Alegre");
  const [answers, setAnswers] = useState<Message[]>([]);
  const [busy, setBusy] = useState(false);
  const [activeResult, setActiveResult] = useState<QueryResult | undefined>();
  const [activeInsightIndex, setActiveInsightIndex] = useState<number | null>(null);
  const [secondaryQuestionQueued, setSecondaryQuestionQueued] = useState(false);
  const [insightPulse, setInsightPulse] = useState(false);
  const pulseTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const assistantInsights = useMemo(() => {
    return answers
      .map((message, index) => ({ message, index }))
      .filter((entry) => entry.message.role === "assistant" && entry.message.result)
      .map((entry) => {
        const previousQuestion = answers
          .slice(0, entry.index)
          .reverse()
          .find((item) => item.role === "user");
        return {
          ...entry,
          question: previousQuestion?.text ?? "Insight gerado"
        };
      });
  }, [answers]);

  const ask = async (input: string) => {
    if (!input.trim()) return;

    const fallbackMonth = extractMonth(input, DEFAULT_MONTH);
    const fallbackIntent = intentFromQuery(input);
    const detectedBrand = detectBrandFromQuery(input);
    const detectedProduct = extractProductNameFromQuery(input);

    setBusy(true);
    setAnswers((state) => [...state, { role: "user", text: input }]);

    let result: QueryResult | undefined;

    try {
      await new Promise((resolve) => setTimeout(resolve, 350));

      if (USE_LLM) {
        const res = await fetch("/api/query", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: input })
        });

        if (!res.ok) {
          throw new Error("parser failed");
        }

        const payload = (await res.json()) as { data: TParsedQuery };
        result = runQueryStructured(payload.data, fallbackMonth, input);
      } else {
        const heuristicFilters: Partial<TParsedQuery> & { productName?: string } = {};
        if (detectedBrand) heuristicFilters.brand = detectedBrand;
        if (detectedProduct) heuristicFilters.productName = detectedProduct;
        result = runQuery(fallbackIntent, fallbackMonth, heuristicFilters);
      }
    } catch (error) {
      console.error("LLM parser error. Falling back to heuristics.", error);
      const heuristicFilters: Partial<TParsedQuery> & { productName?: string } = {};
      if (detectedBrand) heuristicFilters.brand = detectedBrand;
      if (detectedProduct) heuristicFilters.productName = detectedProduct;
      result = runQuery(fallbackIntent, fallbackMonth, heuristicFilters);
    }

    if (result) {
      let nextIndex: number | null = null;
      setAnswers((state) => {
        const newAnswers: Message[] = [
          ...state,
          {
            role: "assistant",
            text: result.narrative,
            result
          }
        ];
        nextIndex = newAnswers.length - 1;
        return newAnswers;
      });
      setActiveResult(result);
      if (nextIndex !== null) {
        setActiveInsightIndex(nextIndex);
      }
      if (pulseTimeout.current) {
        clearTimeout(pulseTimeout.current);
      }
      setInsightPulse(true);
      pulseTimeout.current = setTimeout(() => setInsightPulse(false), 600);
    }

    setBusy(false);
  };

  useEffect(() => {
    if (answers.length === 0) {
      void ask(question);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!secondaryQuestionQueued) {
      const assistantMessages = answers.filter((message) => message.role === "assistant");
      if (assistantMessages.length >= 1) {
        setSecondaryQuestionQueued(true);
        void ask("Quais as 3 marcas com maior share de receita em 2025-11?");
      }
    }
  }, [answers, secondaryQuestionQueued]);

  useEffect(() => {
    if (assistantInsights.length === 0) {
      setActiveInsightIndex(null);
      setActiveResult(undefined);
      return;
    }
    if (activeInsightIndex === null) {
      const latest = assistantInsights[assistantInsights.length - 1];
      setActiveInsightIndex(latest.index);
      if (latest.message.result) {
        setActiveResult(latest.message.result);
      }
    }
  }, [assistantInsights, activeInsightIndex]);

  useEffect(() => {
    return () => {
      if (pulseTimeout.current) {
        clearTimeout(pulseTimeout.current);
      }
    };
  }, []);

  return (
    <div className={clsx("min-h-screen", ds.colors.background, "text-slate-200")}>
      <header className="border-b border-slate-800/80 bg-slate-900/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-blue-500/40 bg-blue-500/20 shadow-lg shadow-blue-900/40">
              <Image src={logoDipam} alt="Logotipo Dipam" className="h-8 w-8 object-contain" priority />
            </div>
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-blue-400">Assistente Generativo</p>
              <h1 className="text-2xl font-semibold text-slate-100 sm:text-[2rem] sm:leading-tight">DIPA GenAI</h1>
            </div>
          </div>
          <span className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-xs font-medium uppercase tracking-wide text-slate-300">
            Protótipo
          </span>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-6 lg:grid lg:grid-cols-12">
          <section className="order-1 flex flex-col gap-6 lg:col-span-5 xl:col-span-4">
            <Card className={clsx(ds.card, "shadow-2xl shadow-blue-900/30")}>
              <CardContent className="flex flex-col gap-6 md:p-8">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Laboratório de prompts</p>
                    <p className="mt-2 text-sm text-slate-400">
                      Consulte o DIPA GenAI para investigar metas, produtos e oportunidades comerciais em tempo real.
                    </p>
                  </div>
                  <Sparkles className="h-5 w-5 text-blue-400" />
                </div>

                <PromptChips
                  examples={EXAMPLES}
                  activeValue={question}
                  onSelect={(value) => {
                    setQuestion(value);
                    void ask(value);
                  }}
                />

                <form
                  onSubmit={(event) => {
                    event.preventDefault();
                    void ask(question);
                  }}
                  className="space-y-4"
                >
                  <div className="space-y-2">
                    <label htmlFor="prompt-input" className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                      Pergunta
                    </label>
                    <textarea
                      id="prompt-input"
                      value={question}
                      onChange={(event) => setQuestion(event.target.value)}
                      placeholder="Ex.: Quanto vendemos de Nissin Miojo Galinha Caipira neste mês?"
                      className="min-h-[160px] w-full resize-y rounded-2xl border border-slate-700 bg-slate-900/80 px-4 py-3 text-sm leading-relaxed text-slate-100 shadow-inner shadow-blue-950/40 placeholder:text-slate-500 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40"
                    />
                    <div className="flex justify-end text-xs text-slate-500">{question.length} caracteres</div>
                  </div>

                  <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
                    <Button
                      type="button"
                      variant="secondary"
                      className="w-full sm:w-auto"
                      onClick={() => {
                        const example = EXAMPLES[Math.floor(Math.random() * EXAMPLES.length)];
                        setQuestion(example);
                        void ask(example);
                      }}
                      disabled={busy}
                    >
                      <Sparkles className="mr-2 h-4 w-4 text-blue-300" />
                      Sugestão
                    </Button>
                    <Button
                      type="submit"
                      className="w-full sm:w-auto shadow-md shadow-blue-900/50 transition"
                      disabled={busy}
                    >
                      {busy ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Gerando insight…
                        </>
                      ) : (
                        <>
                          <ArrowRight className="mr-2 h-4 w-4" />
                          Gerar insight
                        </>
                      )}
                    </Button>
                  </div>
                </form>

                <div className="hidden border-t border-slate-800 pt-6 lg:block">
                  <div className="mb-3 flex items-center justify-between">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Histórico</p>
                    <span className="text-xs text-slate-500">{answers.length} mensagens</span>
                  </div>
                  <div className="max-h-72 space-y-3 overflow-y-auto pr-2 scrollbar-thin scrollbar-track-slate-900 scrollbar-thumb-slate-700/80">
                    <ChatHistory messages={answers} />
                  </div>
                </div>
              </CardContent>
            </Card>
          </section>

          <section className="order-2 flex flex-col gap-6 lg:col-span-7 xl:col-span-8">
            <Card className={clsx(ds.card, "shadow-xl shadow-blue-900/30")}>
              <CardContent className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between md:gap-6">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Insights gerados</p>
                  <p className="text-sm text-slate-500">Pré-visualização</p>
                </div>
                <InsightChips
                  insights={assistantInsights.map(({ index, question }) => ({ index, question }))}
                  activeIndex={activeInsightIndex}
                  onSelect={(index) => setActiveInsightIndex(index)}
                />
              </CardContent>
            </Card>

            <Card
              className={clsx(
                ds.card,
                "shadow-xl shadow-blue-900/30 transition",
                busy && "animate-pulse",
                insightPulse && "ring-2 ring-blue-500/60 shadow-[0_0_25px_rgba(59,130,246,0.45)]"
              )}
            >
              <CardContent className="space-y-4 sm:p-8">
                <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Insight selecionado</p>
                    <h2 className="text-lg font-semibold text-slate-100">
                      {activeResult ? INTENT_LABELS[activeResult.intent] : "Nenhum insight selecionado"}
                    </h2>
                  </div>
                  {activeResult ? (
                    <span className="inline-flex items-center rounded-full border border-blue-500/50 bg-blue-500/20 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-blue-200">
                      {activeResult.month}
                    </span>
                  ) : null}
                </div>
                <p className="text-sm text-slate-400">
                  {busy && !activeResult
                    ? "Gerando insight..."
                    : activeResult?.narrative ?? "Selecione ou gere um insight para visualizar os detalhes."}
                </p>
              </CardContent>
            </Card>

            {activeResult ? (
              <Fragment>
                <KPIGrid items={activeResult.kpis} />
                <div className="grid gap-6 xl:grid-cols-2">
                  <ResultChart result={activeResult.chart} />
                  <ResultTable result={activeResult} />
                </div>
              </Fragment>
            ) : (
              <Card className={clsx(ds.card, "border-dashed border-blue-500/40 bg-slate-900/40 text-center shadow-inner shadow-blue-900/20")}>
                <CardContent className="flex flex-col items-center gap-3 py-14">
                  <Sparkles className="h-10 w-10 text-blue-400" />
                  <h2 className="text-lg font-semibold text-slate-100">Nenhum insight selecionado</h2>
                  <p className="max-w-sm text-sm text-slate-400">
                    Gere um prompt no laboratório para visualizar KPIs, gráficos e tabelas nesta área.
                  </p>
                  <Button onClick={() => void ask(question)} className="shadow-lg shadow-blue-900/40">
                    <ArrowRight className="mr-2 h-4 w-4" />
                    Gerar insight inicial
                  </Button>
                </CardContent>
              </Card>
            )}

            <Card className={clsx(ds.card, "shadow-lg shadow-blue-900/30 lg:hidden")}>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Histórico</p>
                  <span className="text-xs text-slate-500">{answers.length} mensagens</span>
                </div>
                <ChatHistory messages={answers} />
              </CardContent>
            </Card>
          </section>
        </div>
      </main>
    </div>
  );
}
