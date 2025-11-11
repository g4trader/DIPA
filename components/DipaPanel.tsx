"use client";

import React, { useEffect, useMemo, useState } from "react";
import Image from "next/image";
import { clsx } from "clsx";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowRight, Loader2, Sparkles } from "lucide-react";
import type { TParsedQuery } from "@/app/api/query/schema";
import logoDipam from "@/assets/logo_dipam.avif";
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
  | "sales_overview";

const INTENT_LABELS: Record<Intent, string> = {
  target_vs_actual: "Meta vs realizado",
  seller_performance: "Performance de vendedores",
  mix_products: "Mix de produtos",
  promotion_mix: "Mix promocional",
  top_products: "Top produtos",
  avg_ticket: "Ticket médio",
  sales_overview: "Visão geral"
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
  "Ticket médio por região em 2025-09"
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

function intentFromQuery(query: string): Intent {
  const normalized = query.toLowerCase();
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

function runQuery(intent: Intent, month: string): QueryResult {
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
          { key: "Meta", label: "Meta", color: "#cbd5f5" },
          { key: "Realizado", label: "Realizado", color: "#34d399" }
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
          { key: "Receita", label: "Receita", color: "#34d399" },
          { key: "Crescimento", label: "Crescimento (%)", color: "#60a5fa" }
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
          { key: "Receita", label: "Receita", color: "#34d399" },
          { key: "Unidades", label: "Unidades", color: "#fbbf24" }
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
          { key: "Receita", label: "Receita", color: "#f87171" },
          { key: "Unidades", label: "Unidades", color: "#60a5fa" }
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
          { key: "Receita", label: "Receita", color: "#34d399" },
          { key: "Unidades", label: "Unidades", color: "#facc15" }
        ]
      };

      baseResult.narrative = `Top ${top.length} produtos em ${month} considerando receita e volume vendidos.`;
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
          { key: "Ticket", label: "Ticket médio", color: "#34d399" },
          { key: "Pedidos", label: "Pedidos", color: "#60a5fa" }
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
        series: [{ key: "Receita", label: "Receita", color: "#34d399" }]
      };

      baseResult.narrative = `Resumo consolidado de vendas para ${month}, destacando regiões com maior participação de receita.`;
      return baseResult;
    }
  }
}

function runQueryStructured(filters: TParsedQuery, fallbackMonth = "2025-11"): QueryResult {
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

  return runQuery(filters.intent, month);
}

function KPIGrid({ items }: { items: QueryResult["kpis"] }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {items.map((item) => (
        <Card key={item.label} className="border-slate-200 bg-white/90">
          <CardContent className="space-y-1">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">{item.label}</p>
            <p className="text-xl font-semibold text-slate-900">{item.value}</p>
            {item.helper ? <p className="text-xs text-slate-500">{item.helper}</p> : null}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function ResultTable({ result }: { result: QueryResult }) {
  if (!result.table.length) return null;

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <table className="min-w-full divide-y divide-slate-200 text-left text-sm text-slate-600">
        <thead className="bg-slate-50 text-xs uppercase tracking-[0.12em] text-slate-500">
          <tr>
            {result.table[0].columns.map((column) => (
              <th key={column} className="px-4 py-3 font-semibold">
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {result.table.map((row, rowIndex) => (
            <tr key={`${rowIndex}-${row.rows[0]}`} className="hover:bg-slate-50/60">
              {row.rows.map((value, cellIndex) => (
                <td key={`${rowIndex}-${cellIndex}`} className="px-4 py-3 text-sm text-slate-700">
                  {value}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ResultChart({ result }: { result?: QueryResult["chart"] }) {
  if (!result) return null;

  const renderSeries = () => {
    if (result.type === "area") {
      return result.series.map((serie) => (
        <Area key={serie.key} type="monotone" dataKey={serie.key} stroke={serie.color} fill={serie.color} fillOpacity={0.25} />
      ));
    }
    return result.series.map((serie) => (
      <Bar key={serie.key} dataKey={serie.key} fill={serie.color} radius={[6, 6, 0, 0]} />
    ));
  };

  return (
    <Card className="border-slate-200 bg-white">
      <CardContent className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          {result.type === "area" ? (
            <AreaChart data={result.data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey={result.xKey} tickLine={false} axisLine={false} tick={{ fontSize: 12 }} />
              <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 12 }} />
              <RTooltip cursor={{ fill: "#f1f5f9" }} />
              <Legend />
              {renderSeries()}
            </AreaChart>
          ) : (
            <BarChart data={result.data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey={result.xKey} tickLine={false} axisLine={false} tick={{ fontSize: 12 }} />
              <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 12 }} />
              <RTooltip cursor={{ fill: "#f1f5f9" }} />
              <Legend />
              {renderSeries()}
            </BarChart>
          )}
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

function QuickExamples({ onSelect }: { onSelect: (example: string) => void }) {
  return (
    <div className="flex flex-wrap gap-2">
      {EXAMPLES.map((example) => (
        <Button
          key={example}
          variant="outline"
          size="sm"
          className="border-sky-400/40 bg-slate-900/40 text-sky-100 hover:bg-slate-900/60"
          onClick={() => onSelect(example)}
        >
          {example}
        </Button>
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
        result = runQueryStructured(payload.data, fallbackMonth);
      } else {
        result = runQuery(fallbackIntent, fallbackMonth);
      }
    } catch (error) {
      console.error("LLM parser error. Falling back to heuristics.", error);
      result = runQuery(fallbackIntent, fallbackMonth);
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
    if (activeInsightIndex === null) return;
    const active = assistantInsights.find((entry) => entry.index === activeInsightIndex);
    if (active?.message.result) {
      setActiveResult(active.message.result);
    }
  }, [activeInsightIndex, assistantInsights]);

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 via-white to-sky-50">
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <header className="flex flex-col gap-6 pb-10">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-center gap-4">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-white shadow-lg ring-1 ring-sky-200">
                <Image src={logoDipam} alt="Logotipo Dipam" className="h-12 w-12 object-contain" priority />
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-sky-500">Assistente Generativo</p>
                <h1 className="text-3xl font-semibold text-slate-900 sm:text-[2.4rem] sm:leading-tight">DIPA GenIA</h1>
              </div>
            </div>
          </div>
        </header>

        <div className="grid gap-8 lg:grid-cols-[minmax(0,580px)_minmax(0,1fr)] xl:grid-cols-[minmax(0,620px)_minmax(0,1fr)]">
          <div className="flex flex-col">
            <Card className="h-full border-transparent bg-slate-950 text-white shadow-2xl shadow-sky-200/40">
              <CardContent className="flex h-full flex-col gap-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-[0.18em] text-sky-300">Laboratório de prompts</p>
                    <h2 className="text-xl font-semibold text-white">Converse com o DIPA</h2>
                    <p className="text-sm text-slate-300">
                      Faça perguntas abertas, refine filtros e acompanhe o preview ao lado em tempo real.
                    </p>
                  </div>
                  <Sparkles className="h-5 w-5 text-sky-300" />
                </div>

                <div className="space-y-2">
                  <p className="text-xs uppercase tracking-[0.18em] text-sky-300">Sugestões</p>
                  <QuickExamples
                    onSelect={(value) => {
                      setQuestion(value);
                      void ask(value);
                    }}
                  />
                </div>

                <form
                  onSubmit={(event) => {
                    event.preventDefault();
                    void ask(question);
                  }}
                  className="space-y-3"
                >
                  <textarea
                    value={question}
                    onChange={(event) => setQuestion(event.target.value)}
                    placeholder="Comparar meta vs realizado por vendedor em 2025-11 na Grande Porto Alegre"
                    className="min-h-[180px] w-full resize-y rounded-2xl border border-sky-500/30 bg-slate-950/80 px-4 py-3 text-sm leading-relaxed text-white shadow-inner placeholder:text-slate-400 focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-300"
                  />
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <span className="text-xs text-slate-400">{question.length} caracteres</span>
                    <div className="flex gap-2">
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => {
                          const example = EXAMPLES[Math.floor(Math.random() * EXAMPLES.length)];
                          setQuestion(example);
                          void ask(example);
                        }}
                      >
                        <Sparkles className="mr-2 h-4 w-4 text-sky-300" />
                        Sugestão
                      </Button>
                      <Button type="submit" disabled={busy} className="min-w-[140px]">
                        {busy ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Gerando...
                          </>
                        ) : (
                          <>
                            <ArrowRight className="mr-2 h-4 w-4" />
                            Gerar insight
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                </form>

                <div className="space-y-3">
                  <div className="flex items-center justify-between text-xs uppercase tracking-[0.18em] text-sky-200">
                    <span>Histórico</span>
                    <span>{answers.length} mensagens</span>
                  </div>
                  <div className="relative h-[340px] overflow-y-auto rounded-2xl border border-sky-500/25 bg-slate-900/70 p-5">
                    <div className="space-y-4">
                      {answers.length === 0 ? (
                        <p className="text-sm text-slate-300">
                          Nenhuma interação ainda. Use uma sugestão acima ou descreva o insight que deseja gerar.
                        </p>
                      ) : (
                        answers.map((message, index) => (
                          <div key={index} className={clsx("flex", message.role === "user" ? "justify-end" : "justify-start")}>
                            <div
                              className={clsx(
                                "max-w-[90%] rounded-2xl px-4 py-3 text-sm shadow-lg transition",
                                message.role === "user"
                                  ? "bg-sky-500 text-white"
                                  : "bg-slate-950/80 text-slate-100 ring-1 ring-sky-500/25"
                              )}
                            >
                              <div className="mb-1 flex items-center gap-2 text-xs uppercase tracking-[0.18em]">
                                <span className={clsx(message.role === "user" ? "text-sky-100" : "text-sky-300")}>
                                  {message.role === "user" ? "Você" : "DIPA"}
                                </span>
                                <span className={clsx("text-slate-500", message.role === "user" ? "text-sky-200/80" : "")}>•</span>
                                <span className="text-slate-500">Agora</span>
                              </div>
                              <p className="leading-relaxed">{message.text}</p>
                              {message.role === "assistant" && message.result ? (
                                <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-300">
                                  <Button
                                    variant={index === activeInsightIndex ? "default" : "outline"}
                                    size="sm"
                                    onClick={() => {
                                      if (message.result) {
                                        setActiveInsightIndex(index);
                                        setActiveResult(message.result);
                                      }
                                    }}
                                  >
                                    {index === activeInsightIndex ? "Visualizando" : "Ver insight"}
                                  </Button>
                                  <span>{INTENT_LABELS[message.result.intent]}</span>
                                  <span>•</span>
                                  <span>{message.result.month}</span>
                                </div>
                              ) : null}
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                    {busy && (
                      <div className="pointer-events-none absolute inset-x-4 bottom-4 flex items-center gap-2 rounded-full bg-slate-950/90 px-3 py-1 text-xs text-slate-300 shadow">
                        <Loader2 className="h-3.5 w-3.5 animate-spin text-sky-300" />
                        Gerando insight...
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="flex flex-col gap-6">
            <Card className="border-transparent bg-white shadow-lg shadow-sky-100/70">
              <CardContent className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-[0.18em] text-sky-600">Insights gerados</p>
                    <h2 className="text-lg font-semibold text-slate-900">Pré-visualização</h2>
                  </div>
                  <span className="rounded-full bg-sky-100 px-3 py-1 text-xs font-semibold text-sky-700">
                    {assistantInsights.length} ativos
                  </span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {assistantInsights.length === 0 ? (
                    <span className="text-xs text-slate-500">Envie uma pergunta para ver a lista de análises geradas.</span>
                  ) : (
                    assistantInsights.map((entry) => (
                      <button
                        key={entry.index}
                        type="button"
                        onClick={() => setActiveInsightIndex(entry.index)}
                        className={clsx(
                          "rounded-full border px-3 py-1 text-xs font-medium transition",
                          entry.index === activeInsightIndex
                            ? "border-transparent bg-sky-600 text-white shadow"
                            : "border-slate-200 bg-white text-slate-600 hover:border-sky-300 hover:text-sky-600"
                        )}
                      >
                        {entry.question.length > 48 ? `${entry.question.slice(0, 48)}…` : entry.question}
                      </button>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>

            {activeResult ? (
              <div className="space-y-6">
                <Card className="border-transparent bg-white shadow-md shadow-slate-200/50">
                  <CardContent className="space-y-3">
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div>
                        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Insight selecionado</p>
                        <h3 className="text-xl font-semibold text-slate-900">{INTENT_LABELS[activeResult.intent]}</h3>
                        <p className="mt-1 text-sm text-slate-500">{activeResult.narrative}</p>
                      </div>
                      <span className="rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-sky-700">
                        {activeResult.month}
                      </span>
                    </div>
                  </CardContent>
                </Card>

                <KPIGrid items={activeResult.kpis} />
                <ResultChart result={activeResult.chart} />
                <ResultTable result={activeResult} />
              </div>
            ) : (
              <Card className="border-dashed border-sky-200 bg-white/70">
                <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
                  <Sparkles className="h-10 w-10 text-sky-500" />
                  <h2 className="text-lg font-semibold text-sky-900">Nenhum insight selecionado</h2>
                  <p className="max-w-md text-sm text-sky-800">
                    Gere um prompt no painel ao lado para visualizar KPIs, gráficos e detalhes tabulares aqui.
                  </p>
                  <Button onClick={() => void ask(question)} className="mt-2">
                    <ArrowRight className="mr-2 h-4 w-4" />
                    Gerar insight inicial
                  </Button>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
