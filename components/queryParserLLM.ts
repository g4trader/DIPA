
export type ParsedQuery = { intent: string; month?: string; region?: string; brand?: string; sellerId?: string; promoOnly?: boolean; metrics?: string[] };
// Substitua por Function Calling/OpenAI/Claude/Mistral. Aqui devolvemos um mock coerente.
export async function parseWithLLM(userText: string): Promise<ParsedQuery> {
  const s = userText.toLowerCase();
  const month = /2025-(09|10|11)/.exec(s)?.[0];
  const promoOnly = /(promo|promoção|oferta|desconto)/.test(s);
  if (/meta|target/.test(s)) return { intent: "target_vs_actual", month, promoOnly };
  if (/vendedor|representante/.test(s)) return { intent: "seller_performance", month, promoOnly };
  if (/mix|participação|share/.test(s)) return { intent: "mix_products", month, promoOnly };
  if (/top|mais vendido|ranking/.test(s)) return { intent: "top_products", month, promoOnly };
  if (/ticket médio|ticket medio/.test(s)) return { intent: "avg_ticket", month, promoOnly };
  return { intent: "sales_overview", month, promoOnly };
}
