"use client";

import React, { useEffect, useMemo, useState } from "react";
import { clsx } from "clsx";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Slider } from "@/components/ui/slider";
import { ArrowRight, Loader2, Sparkles } from "lucide-react";
import type { TParsedQuery } from "@/app/api/query/schema";
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

const MONTHS = ["2025-09", "2025-10", "2025-11", "2025-12"] as const;
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
  "Quais são os top produtos por receita em 2025-12?",
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
  const match = query.match(/2025-(0[1-9]|1[0-2])/);
  if (match) return match[0];
  const monthMatch = query.match(/\bsetembro\b|\boutubro\b|\bnovembro\b|\bdezembro\b/i);
  if (monthMatch) {
    const map: Record<string, string> = {
      setembro: "2025-09",
      outubro: "2025-10",
      novembro: "2025-11",
      dezembro: "2025-12"
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
        <Button key={example} variant="outline" size="sm" onClick={() => onSelect(example)}>
          {example}
        </Button>
      ))}
    </div>
  );
}

export default function DipaPanel() {
  const [question, setQuestion] = useState(EXAMPLES[0]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [busy, setBusy] = useState(false);
  const [activeResult, setActiveResult] = useState<QueryResult | undefined>();
  const [selectedMonth, setSelectedMonth] = useState<(typeof MONTHS)[number]>("2025-11");
  const [selectedConsultor, setSelectedConsultor] = useState<string>("S1");
  const [targetAdjustment, setTargetAdjustment] = useState(0);
  const [scenarioGrowth, setScenarioGrowth] = useState(3);
  const [scenarioDiscount, setScenarioDiscount] = useState(5);

  const consultoresOptions = useMemo(() => DATA.sellers.map((seller) => ({ value: seller.id, label: seller.name })), []);

  const ask = async (input: string) => {
    if (!input.trim()) return;

    const fallbackMonth = extractMonth(input, selectedMonth);
    const fallbackIntent = intentFromQuery(input);

    setBusy(true);
    setMessages((state) => [...state, { role: "user", text: input }]);

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
      setActiveResult(result);
      setMessages((state) => [
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

  useEffect(() => {
    if (messages.length === 0) {
      ask(EXAMPLES[3]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleScenarioUpdate = () => {
    const seller = DATA.sellers.find((item) => item.id === selectedConsultor);
    if (!seller) return;
    const delta = seller.monthlyTarget * (targetAdjustment / 100);
    const message = `Novo alvo para ${seller.name}: ${formatCurrency(seller.monthlyTarget + delta)} (${targetAdjustment.toFixed(
      0
    )}% vs atual).`;
    setMessages((state) => [...state, { role: "assistant", text: message }]);
  };

  const handleWhatIf = () => {
    const message = `Cenário what-if: crescimento ${scenarioGrowth}% com desconto médio ${scenarioDiscount}%.`;
    setMessages((state) => [...state, { role: "assistant", text: message }]);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 via-white to-slate-100">
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <header className="flex flex-col gap-3 pb-6">
          <span className="inline-flex w-fit items-center rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium uppercase tracking-[0.18em] text-emerald-700">
            DIPA • Assistente de IA
          </span>
          <div>
            <h1 className="text-2xl font-semibold text-slate-900 sm:text-3xl">Painel de Performance Dipam</h1>
            <p className="mt-1 max-w-3xl text-sm text-slate-600">
              Explore metas, resultados comerciais e simulações rápidas com dados mock construídos para análises em tempo real.
            </p>
          </div>
        </header>

        <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
          <div className="space-y-6">
            <Card className="border-slate-200 bg-white/95">
              <CardContent className="space-y-4">
                <div className="flex items-center gap-2 text-sm font-medium text-slate-600">
                  <Sparkles className="h-4 w-4 text-emerald-500" />
                  Pergunte ao assistente
                </div>
                <form
                  onSubmit={(event) => {
                    event.preventDefault();
                    ask(question);
                  }}
                  className="space-y-3"
                >
                  <Input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ex.: Comparar meta vs realizado" />
                  <div className="flex gap-2">
                    <Button type="submit" className="flex-1" disabled={busy}>
                      {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Executar"}
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => {
                        const example = EXAMPLES[Math.floor(Math.random() * EXAMPLES.length)];
                        setQuestion(example);
                      }}
                    >
                      <Sparkles className="mr-2 h-4 w-4 text-emerald-500" />
                      Surpreenda-me
                    </Button>
                  </div>
                </form>
                <div className="space-y-2">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Exemplos rápidos</p>
                  <QuickExamples
                    onSelect={(value) => {
                      setQuestion(value);
                      ask(value);
                    }}
                  />
                </div>
              </CardContent>
            </Card>

            <Card className="border-slate-200 bg-white/95">
              <CardContent className="space-y-4">
                <Tabs defaultValue="metas">
                  <TabsList className="flex gap-2 bg-slate-100 p-1">
                    <TabsTrigger value="metas" className="flex-1 bg-white">
                      Metas
                    </TabsTrigger>
                    <TabsTrigger value="whatif" className="flex-1 bg-white">
                      What-if
                    </TabsTrigger>
                  </TabsList>

                  <TabsContent value="metas" className="space-y-4">
                    <div>
                      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Consultor</p>
                      <select
                        value={selectedConsultor}
                        onChange={(event) => setSelectedConsultor(event.target.value)}
                        className="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                      >
                        {consultoresOptions.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <div className="flex items-center justify-between text-sm text-slate-600">
                        <span>Revisar meta (%):</span>
                        <span className="font-semibold text-slate-800">{targetAdjustment}%</span>
                      </div>
                      <Slider defaultValue={[0]} max={25} step={1} onValueChange={([value]: number[]) => setTargetAdjustment(value)} />
                    </div>
                    <Button variant="outline" className="w-full" onClick={handleScenarioUpdate}>
                      Atualizar meta
                    </Button>
                  </TabsContent>

                  <TabsContent value="whatif" className="space-y-4">
                    <div>
                      <div className="flex items-center justify-between text-sm text-slate-600">
                        <span>Crescimento projetado</span>
                        <span className="font-semibold text-slate-800">{scenarioGrowth}%</span>
                      </div>
                      <Slider defaultValue={[scenarioGrowth]} max={20} step={1} onValueChange={([value]: number[]) => setScenarioGrowth(value)} />
                    </div>
                    <div>
                      <div className="flex items-center justify-between text-sm text-slate-600">
                        <span>Desconto médio</span>
                        <span className="font-semibold text-slate-800">{scenarioDiscount}%</span>
                      </div>
                      <Slider defaultValue={[scenarioDiscount]} max={20} step={1} onValueChange={([value]: number[]) => setScenarioDiscount(value)} />
                    </div>
                    <Button variant="outline" className="w-full" onClick={handleWhatIf}>
                      Simular cenário
                    </Button>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>

            <Card className="border-slate-200 bg-white/95">
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Linha do tempo</p>
                  <span className="inline-flex items-center rounded-full bg-slate-900 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-white">
                    Histórico
                  </span>
                </div>
                <div className="flex gap-2">
                  {MONTHS.map((month) => (
                    <Button
                      key={month}
                      variant={month === selectedMonth ? "default" : "outline"}
                      size="sm"
                      onClick={() => setSelectedMonth(month)}
                      className={clsx("flex-1", month === selectedMonth ? "bg-emerald-600 hover:bg-emerald-700" : "text-slate-600")}
                    >
                      {month}
                    </Button>
                  ))}
                </div>
                <p className="text-xs text-slate-500">Os resultados utilizam o mês destacado como referência padrão.</p>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-6">
            <Card className="border-slate-200 bg-white/95">
              <CardContent className="space-y-4">
                <div className="flex items-center gap-2 text-sm font-medium text-slate-600">
                  <Sparkles className="h-4 w-4 text-emerald-500" />
                  Interações recentes
                </div>
                <div className="space-y-3">
                  {messages.length === 0 && (
                    <p className="text-sm text-slate-500">
                      Inicie uma conversa selecionando um exemplo ou digitando sua pergunta sobre metas, performance e mix de produtos.
                    </p>
                  )}
                  {messages.map((message, index) => (
                    <div
                      key={index}
                      className={clsx(
                        "rounded-2xl border px-4 py-3 text-sm",
                        message.role === "user"
                          ? "border-emerald-100 bg-emerald-50 text-emerald-900"
                          : "border-slate-200 bg-slate-50 text-slate-700"
                      )}
                    >
                      <p className="font-medium">{message.role === "user" ? "Você" : "DIPA"}</p>
                      <p>{message.text}</p>
                    </div>
                  ))}
                  {busy && (
                    <div className="flex items-center gap-2 text-sm text-slate-500">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Processando...
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {activeResult ? (
              <>
                <KPIGrid items={activeResult.kpis} />
                <ResultChart result={activeResult.chart} />
                <ResultTable result={activeResult} />
              </>
            ) : (
              <Card className="border-dashed border-emerald-200 bg-emerald-50/50">
                <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
                  <Sparkles className="h-10 w-10 text-emerald-500" />
                  <h2 className="text-lg font-semibold text-emerald-900">Aguardando primeira consulta</h2>
                  <p className="max-w-md text-sm text-emerald-800">
                    Peça um comparativo de metas, explore mix de produtos ou simule cenários de performance para ver KPIs, tabela e gráficos.
                  </p>
                  <Button onClick={() => ask(EXAMPLES[0])} className="mt-2">
                    <ArrowRight className="mr-2 h-4 w-4" />
                    Executar exemplo inicial
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
