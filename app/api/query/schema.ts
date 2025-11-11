import { z } from "zod";

export const ParsedQuery = z.object({
  intent: z.enum([
    "target_vs_actual",
    "seller_performance",
    "mix_products",
    "promotion_mix",
    "top_products",
    "avg_ticket",
    "sales_overview"
  ]),
  month: z.string().regex(/^2025-(07|08|09|10|11)$/).optional(),
  region: z.string().optional(),
  brand: z.string().optional(),
  sellerId: z.string().optional(),
  promoOnly: z.boolean().optional()
});

export type TParsedQuery = z.infer<typeof ParsedQuery>;

