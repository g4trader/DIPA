
# DIPA — Dipam Intelligence & Performance Assistant (Mockup Next.js)

Pronto para abrir no **Cursor** e publicar na **Vercel**.

## Rodar local
```bash
npm i
npm run dev
```

> O painel usa um conjunto mínimo de componentes (compatíveis com shadcn) já incluído em `components/ui`.
> Gráficos com `recharts`. Não há dependência externa além das listadas no `package.json`.

## Estrutura
- `app/page.tsx` carrega o painel (`components/DipaPanel.tsx`).
- `components/ui/*` componentes básicos (Card, Button, Input, Tabs, Select, Slider).
- `components/queryParserLLM.ts` stub para parser LLM.
- `styles/globals.css` + Tailwind.

## Próximo passo (LLM parser real)
- Trocar `queryParserLLM.ts` por implementação com **Function Calling** (OpenAI/Claude/Mistral) retornando JSON `{ intent, filters }`.
- Guardrails: listar intents suportadas; validar campos; abortar operações perigosas.
- (Opcional) API route `/api/query` para rodar no **Cloud Run** com streaming.

## Dados
Você pode usar os CSVs mock gerados anteriormente. Coloque-os em uma pasta `data/` na raiz ou sirva via API.
