"use server";

import { ParsedQuery, TParsedQuery } from "./schema";

const functions = [
  {
    name: "parse_sales_query",
    description: "Mapeia pergunta em linguagem natural para filtros do data mart de vendas Dipam.",
    parameters: {
      type: "object",
      properties: {
        intent: {
          type: "string",
          enum: [
            "target_vs_actual",
            "seller_performance",
            "mix_products",
            "promotion_mix",
            "top_products",
            "avg_ticket",
            "sales_overview"
          ]
        },
        month: { type: "string", description: "YYYY-MM (2025-07|08|09|10|11)" },
        region: { type: "string" },
        brand: { type: "string" },
        sellerId: { type: "string" },
        promoOnly: { type: "boolean" }
      },
      required: ["intent"]
    }
  }
];

type OpenAIChatCompletion = {
  choices: Array<{
    message?: {
      tool_calls?: Array<{
        function?: {
          name?: string;
          arguments?: string;
        };
      }>;
    };
  }>;
};

const DEFAULT_BASE_URL = "https://api.openai.com/v1";
const DEFAULT_MODEL = "gpt-4o-mini";
const baseUrl = (process.env.OPENAI_BASE_URL || DEFAULT_BASE_URL).replace(/\/$/, "");
const OPENAI_URL = `${baseUrl}/chat/completions`;
const MODEL = process.env.OPENAI_MODEL || DEFAULT_MODEL;
const JSON_HEADERS = { "Content-Type": "application/json" };

function jsonResponse<T>(status: number, payload: T) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: JSON_HEADERS
  });
}

export async function POST(req: Request) {
  let body: unknown;

  try {
    body = await req.json();
  } catch {
    return jsonResponse(400, { ok: false, error: "Invalid JSON body." });
  }

  if (!body || typeof body !== "object" || typeof (body as { question?: unknown }).question !== "string") {
    return jsonResponse(400, { ok: false, error: "Body must include a question string." });
  }

  const { question } = body as { question: string };

  // Detecta qual provedor usar (prioridade: Grok > OpenAI)
  const grokApiKey = process.env.GROK_API_KEY;
  const openaiApiKey = process.env.OPENAI_API_KEY;
  
  let apiKey: string;
  let apiUrl: string;
  let model: string;
  let provider: string;
  
  if (grokApiKey) {
    apiKey = grokApiKey;
    apiUrl = GROK_URL;
    model = GROK_MODEL;
    provider = "Grok";
  } else if (openaiApiKey) {
    apiKey = openaiApiKey;
    apiUrl = OPENAI_URL;
    model = OPENAI_MODEL;
    provider = "OpenAI";
  } else {
    return jsonResponse(500, { ok: false, error: "LLM API key is not configured. Set GROK_API_KEY or OPENAI_API_KEY." });
  }

  const tools = functions.map((fn) => ({ type: "function", function: fn }));

  const response = await fetch(apiUrl, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      model: model,
      messages: [
        {
          role: "system",
          content:
            "Você é um parser especializado do assistente DIPA. Extraia intent e filtros estruturados para consultas de vendas. Retorne apenas argumentos compatíveis com o schema."
        },
        {
          role: "user",
          content: question
        }
      ],
      tools,
      tool_choice: { type: "function", function: { name: "parse_sales_query" } }
    })
  });

  if (!response.ok) {
    return jsonResponse(502, { ok: false, error: "Failed to contact the LLM provider." });
  }

  const completion = (await response.json()) as OpenAIChatCompletion;
  const toolCall = completion.choices?.[0]?.message?.tool_calls?.find(
    (call) => call.function?.name === "parse_sales_query"
  );

  if (!toolCall?.function?.arguments) {
    return jsonResponse(502, { ok: false, error: "LLM did not return function arguments." });
  }

  let args: unknown;
  try {
    args = JSON.parse(toolCall.function.arguments);
  } catch {
    return jsonResponse(502, { ok: false, error: "Invalid JSON from LLM function call." });
  }

  const parsedArgs = ParsedQuery.safeParse(args);
  if (!parsedArgs.success) {
    return jsonResponse(400, { ok: false, error: parsedArgs.error.flatten() });
  }

  return jsonResponse(200, { ok: true, data: parsedArgs.data });
}
