"use client";

import React, { useMemo, useState } from "react";
import Image from "next/image";
import { clsx } from "clsx";
import { Button } from "@/components/ui/button";
import type { TParsedQuery } from "@/app/api/query/schema";
import logoDipam from "@/assets/logo_dipam.avif";
import { ds } from "@/styles/ui";
import { ChatHistory } from "@/components/panel/ChatHistory";
import { KpiStats } from "@/components/panel/KpiStats";
import { DipaChart } from "@/components/panel/DipaChart";
import { RegionTable } from "@/components/panel/RegionTable";
import type { ChartConfig, PanelMessage, QueryResult, IntentId } from "@/components/panel/types";
import { Loader2, History, X, PanelRightOpen } from "lucide-react";

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

function buildBrandSalesSummaryView(result?: QueryResult) {
  if (!result?.summary || result.summary.kind !== "brand_sales") {
    return null;
  }

  const { productLabel, totalRevenue, totalUnits, sellers } = result.summary;
  if (!sellers.length) {
    return null;
  }

  const ordered = [...sellers].sort((a, b) => b.revenue - a.revenue);
  const best = ordered[0];
  const worst = ordered[ordered.length - 1];

  return {
    productLabel,
    totalRevenueFormatted: formatCurrency(totalRevenue),
    totalUnitsFormatted: totalUnits.toLocaleString("pt-BR"),
    best: {
      name: best.name,
      revenueFormatted: formatCurrency(best.revenue),
      unitsFormatted: best.units.toLocaleString("pt-BR")
    },
    worst: {
      name: worst.name,
      revenueFormatted: formatCurrency(worst.revenue),
      unitsFormatted: worst.units.toLocaleString("pt-BR")
    },
    hasMultipleSellers: ordered.length > 1
  };
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

      baseResult.summary = {
        kind: "brand_sales",
        productLabel,
        totalRevenue: totalProductRevenue,
        totalUnits: totalProductUnits,
        sellers: sellerRows.map((entry) => ({
          name: entry.seller.name,
          revenue: entry.revenue,
          units: entry.units
        }))
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

export default function DipaPanel() {
  const [question, setQuestion] = useState("");
  const [answers, setAnswers] = useState<PanelMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);

  const latestAssistant = useMemo(() => {
    for (let index = answers.length - 1; index >= 0; index -= 1) {
      const entry = answers[index];
      if (entry.role === "assistant") {
        return entry;
      }
    }
    return undefined;
  }, [answers]);

  const latestQuestion = useMemo(() => {
    for (let index = answers.length - 1; index >= 0; index -= 1) {
      const entry = answers[index];
      if (entry.role === "user") {
        return entry.text;
      }
    }
    return undefined;
  }, [answers]);

  const handleExampleSelection = (value: string) => {
    setQuestion(value);
    void ask(value);
  };

  const handleRandomExample = () => {
    const example = EXAMPLES[Math.floor(Math.random() * EXAMPLES.length)];
    setQuestion(example);
    void ask(example);
  };

  const ask = async (input: string) => {
    if (!input.trim()) return;

    const fallbackMonth = extractMonth(input, DEFAULT_MONTH);
    const fallbackIntent = intentFromQuery(input);
    const detectedBrand = detectBrandFromQuery(input);
    const detectedProduct = extractProductNameFromQuery(input);

    setBusy(true);
    setAnswers((state) => [...state, { role: "user", text: input }]);
    setPreviewOpen(false);
    setHistoryOpen(false);

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
      setAnswers((state) => [
        ...state,
        {
          role: "assistant",
          text: result.narrative,
          result
        }
      ]);
    }

    setBusy(false);
  };

  const hasResponse = Boolean(latestAssistant);
  const latestResult = latestAssistant?.result;
  const isSubmitDisabled = busy || !question.trim();
  const summaryView = buildBrandSalesSummaryView(latestResult);

  return (
    <div className={clsx("min-h-screen", ds.colors.background, "text-slate-200") }>
      <header className="border-b border-slate-800/80 bg-slate-900/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-blue-500/40 bg-blue-500/20 shadow-lg shadow-blue-900/40">
              <Image src={logoDipam} alt="Logotipo Dipam" className="h-8 w-8 object-contain" priority />
            </div>
            <div>
              <h1 className="text-3xl font-semibold text-slate-100 sm:text-[2.5rem] sm:leading-tight">DIPA COPILOT™</h1>
              <p className="mt-1 text-sm text-slate-400">Inteligência comercial em tempo real</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Button
              type="button"
              variant="ghost"
              className="gap-2 text-sm font-medium text-slate-300 hover:text-slate-100"
              onClick={() => setHistoryOpen(true)}
            >
              <History className="h-4 w-4" />
              Histórico
            </Button>
            <span className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-xs font-medium uppercase tracking-wide text-slate-300">
              Protótipo
            </span>
          </div>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-4xl flex-col items-center gap-12 px-4 py-16 sm:px-6 lg:px-8">
        <form
          className="w-full space-y-6 text-center"
          onSubmit={(event) => {
            event.preventDefault();
            void ask(question);
          }}
        >
          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Qual decisão comercial você quer acelerar agora?"
            className="h-44 w-full rounded-3xl border border-slate-700 bg-slate-900/80 px-6 py-4 text-lg leading-relaxed text-slate-100 shadow-inner shadow-slate-950/40 placeholder:text-slate-500 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/30"
          />

          <div className="flex flex-wrap justify-center gap-2 text-xs text-slate-400">
            {EXAMPLES.map((example) => (
              <button
                key={example}
                type="button"
                onClick={() => handleExampleSelection(example)}
                className="rounded-full border border-slate-700/60 bg-slate-800/60 px-4 py-1.5 transition duration-150 ease-out hover:border-blue-500/50 hover:text-slate-100"
              >
                {example}
              </button>
            ))}
          </div>

          <div className="flex justify-center">
            <Button
              type="submit"
              disabled={isSubmitDisabled}
              className="gap-2 rounded-full px-8 py-3 text-base font-semibold"
            >
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Perguntar ao copiloto"}
            </Button>
          </div>
        </form>

        {hasResponse && latestAssistant ? (
          <div className="w-full max-w-3xl space-y-6">
            <div className="rounded-3xl border border-slate-700/70 bg-slate-900/70 p-8 shadow-xl shadow-blue-900/30">
              <div className="flex flex-col gap-2 text-left">
                <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-500">Resposta do DIPA COPILOT™</p>
                {latestQuestion ? (
                  <h2 className="text-lg font-semibold text-slate-100">{latestQuestion}</h2>
                ) : null}
              </div>
              {summaryView ? (
                <div className="mt-6 space-y-3 text-left text-lg leading-relaxed text-slate-100">
                  <p>
                    Vendemos <strong>{summaryView.totalUnitsFormatted} unidades</strong> de {summaryView.productLabel} neste período, com faturamento bruto de <strong>{summaryView.totalRevenueFormatted}</strong>.
                  </p>
                  <p>
                    O melhor consultor foi <strong>{summaryView.best.name}</strong>, com <strong>{summaryView.best.unitsFormatted} unidades</strong> e <strong>{summaryView.best.revenueFormatted}</strong>.
                  </p>
                  {summaryView.hasMultipleSellers ? (
                    <p>
                      O consultor com menor resultado foi <strong>{summaryView.worst.name}</strong>, com <strong>{summaryView.worst.unitsFormatted} unidades</strong> e <strong>{summaryView.worst.revenueFormatted}</strong>.
                    </p>
                  ) : null}
                </div>
              ) : (
                <p className="mt-6 text-left text-lg leading-relaxed text-slate-100">{latestAssistant.text}</p>
              )}
            </div>

            {latestResult ? (
              <div className="flex justify-center">
                <Button
                  type="button"
                  variant="secondary"
                  className="gap-2 rounded-full px-6 py-3 text-sm font-medium"
                  onClick={() => setPreviewOpen(true)}
                >
                  <PanelRightOpen className="h-4 w-4" />
                  Ver preview analítico detalhado
                </Button>
              </div>
            ) : null}
          </div>
        ) : null}
      </main>

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
              <ChatHistory messages={answers} emptyMessage="Nenhuma interação ainda." />
            </div>
          </div>
        </div>
      ) : null}

      {previewOpen && latestResult ? (
        <div className="fixed inset-0 z-50 flex">
          <div className="absolute inset-0 bg-black/45" onClick={() => setPreviewOpen(false)} />
          <div className="relative ml-auto flex h-full w-full max-w-md flex-col border-l border-slate-800 bg-slate-900/95 shadow-2xl backdrop-blur-xl">
            <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Preview analítico</p>
                <h3 className="text-base font-semibold text-slate-100">Detalhes estruturados</h3>
              </div>
              <button
                type="button"
                onClick={() => setPreviewOpen(false)}
                className="rounded-full border border-slate-700/60 bg-slate-800/80 p-1.5 text-slate-300 transition hover:border-blue-500/40 hover:text-slate-100"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto space-y-6 px-6 py-6">
              <KpiStats items={latestResult.kpis} />
              <DipaChart chart={latestResult.chart} title="Indicadores visuais" />
              <RegionTable result={latestResult} />
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
