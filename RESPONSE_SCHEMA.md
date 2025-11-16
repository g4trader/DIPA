# Schema de Resposta Estruturada - DIPAM COPILOT™

Este documento descreve o schema JSON usado para respostas estruturadas do DIPAM COPILOT™ no formato de dashboard.

## Visão Geral

As respostas do Copilot podem ser retornadas em dois formatos:

1. **Resposta Estruturada (Dashboard)** - `structured` (NOVO - prioridade)
   - Formato JSON com dados organizados em cards visuais
   - Renderizado pelo componente `ResponseDashboard.tsx`

2. **Resposta Textual (Fallback)** - `respostaMarkdown` (DEPRECATED)
   - Formato Markdown/texto simples
   - Mantido para compatibilidade

## Schema: CopilotStructuredResponse

```typescript
interface CopilotStructuredResponse {
  /** Resumo executivo em texto (2-4 parágrafos) */
  resumoExecutivo?: string;
  
  /** KPIs do mês/período */
  kpis?: KpiItem[];
  
  /** Ranking de vendedores */
  rankingVendedores?: RankingVendedorItem[];
  
  /** Clientes críticos/problemáticos */
  clientesCriticos?: ClienteCriticoItem[];
  
  /** Insights e recomendações (lista de strings) */
  insightsRecomendacoes?: string[];
  
  /** JSON técnico completo (opcional, para debug) */
  jsonTecnico?: any;
}
```

## Tipos de Dados

### KpiItem

```typescript
type KpiItem = {
  /** Label do KPI (ex.: "Meta Total") */
  label: string;
  
  /** Valor do KPI (pode ser número ou string formatada) */
  value: string | number;
  
  /** Variação percentual (opcional) - ex.: "+5.2%" ou "-10.5%" */
  variation?: string;
  
  /** Cor do valor - "positive" (verde), "negative" (vermelho), "neutral" (cinza) */
  color?: "positive" | "negative" | "neutral";
  
  /** Ícone opcional (emoji ou nome de ícone) */
  icon?: string;
};
```

**Exemplo:**
```json
{
  "label": "Meta Total",
  "value": 1250000,
  "variation": "+5.2%",
  "color": "positive",
  "icon": "🎯"
}
```

### RankingVendedorItem

```typescript
type RankingVendedorItem = {
  /** Nome do vendedor */
  vendedor: string;
  
  /** Meta do vendedor (R$) */
  meta: number;
  
  /** Realizado do vendedor (R$) */
  realizado: number;
  
  /** Atingimento percentual */
  atingimento: number;
  
  /** Gap (realizado - meta, pode ser negativo) */
  gap: number;
  
  /** Supervisor (opcional) */
  supervisor?: string;
  
  /** Rank no ranking */
  rank?: number;
};
```

**Exemplo:**
```json
{
  "vendedor": "ROTA 77",
  "meta": 50000,
  "realizado": 45000,
  "atingimento": 90.0,
  "gap": -5000,
  "supervisor": "João Silva",
  "rank": 1
}
```

### ClienteCriticoItem

```typescript
type ClienteCriticoItem = {
  /** Nome do cliente */
  cliente: string;
  
  /** Faturamento no mês (R$) */
  faturamento: number;
  
  /** Quantidade de pedidos */
  pedidos: number;
  
  /** Insight sobre o cliente (opcional) */
  insight?: string;
  
  /** Vendedor responsável (opcional) */
  vendedor?: string;
  
  /** Variação percentual vs média (opcional) */
  variacao?: number;
};
```

**Exemplo:**
```json
{
  "cliente": "Cliente XYZ Ltda",
  "faturamento": 15000,
  "pedidos": 3,
  "variacao": -25.5,
  "vendedor": "ROTA 77",
  "insight": "Queda de 25.5% vs média dos últimos 3 meses"
}
```

## Exemplo Completo

```json
{
  "resumoExecutivo": "No mês de agosto de 2025, a meta total foi de R$ 1.250.000,00, enquanto o realizado foi de R$ 1.180.000,00, resultando em um gap de R$ 70.000,00 (94,4% de atingimento). Os principais fatores que impactaram negativamente foram...",
  
  "kpis": [
    {
      "label": "Meta Total",
      "value": 1250000,
      "color": "neutral",
      "icon": "🎯"
    },
    {
      "label": "Realizado Total",
      "value": 1180000,
      "variation": "-5.6%",
      "color": "negative",
      "icon": "💰"
    },
    {
      "label": "Atingimento Médio",
      "value": "94.4%",
      "color": "negative",
      "icon": "📊"
    },
    {
      "label": "Vendedores que Bateram",
      "value": 12,
      "color": "positive",
      "icon": "✅"
    }
  ],
  
  "rankingVendedores": [
    {
      "vendedor": "ROTA 77",
      "meta": 50000,
      "realizado": 45000,
      "atingimento": 90.0,
      "gap": -5000,
      "supervisor": "João Silva",
      "rank": 1
    }
  ],
  
  "clientesCriticos": [
    {
      "cliente": "Cliente XYZ Ltda",
      "faturamento": 15000,
      "pedidos": 3,
      "variacao": -25.5,
      "vendedor": "ROTA 77",
      "insight": "Queda de 25.5% vs média dos últimos 3 meses"
    }
  ],
  
  "insightsRecomendacoes": [
    "Priorizar coaching imediato para: ROTA 77, ROTA 75, ROTA 80",
    "Implementar plano de ação para 15 clientes críticos identificados",
    "Recuperar gap de R$ 70.000,00 através de ações direcionadas"
  ],
  
  "jsonTecnico": {
    "contexto_keys": ["kpis", "pioresVendedores", "clientesCriticos"],
    "tem_serie": true,
    "tem_detalhe": true,
    "qtd_piores_vendedores": 10,
    "qtd_clientes_criticos": 15,
    "mes_ano": "2025-08"
  }
}
```

## Fluxo de Geração

1. **Backend (`src/agent/service.py`)**
   - Chama `gerar_resposta_estruturada_consulta_meta()` quando há dados
   - Retorna JSON estruturado + texto complementar
   - Adiciona `structured` ao contexto

2. **Mapper (`src/api/copilot_mapper.py`)**
   - Detecta `structured` no resultado do agente
   - Passa diretamente para o payload
   - Se não houver, tenta construir automaticamente a partir de dados antigos

3. **Frontend (`components/CopilotAnswerCard.tsx`)**
   - Verifica se `payload.structured` existe
   - Se sim, renderiza `ResponseDashboard`
   - Se não, usa fallback (compatibilidade)

## Regras de Validação

1. **Resumo Executivo**: Sempre preenchido quando há dados
2. **KPIs**: Obrigatório quando há `kpis` no contexto
3. **Ranking**: Obrigatório quando há `pioresVendedores` no contexto (top 10)
4. **Clientes Críticos**: Obrigatório quando há `clientesCriticos` no contexto (top 15)
5. **Insights**: Sempre preenchido com 3-5 ações práticas específicas

## Compatibilidade

O sistema mantém compatibilidade retroativa:

- Se o backend retornar apenas texto markdown → mapper tenta construir formato estruturado
- Se o frontend receber apenas dados antigos → usa fallback de renderização
- Campos antigos (`kpis`, `topVendedores`, `clientesProblema`) são mapeados automaticamente para `structured`

## Geração Automática

Quando o LLM não retorna JSON válido, o sistema usa `_gerar_json_fallback()` que:

1. Extrai dados do contexto
2. Gera JSON estruturado automaticamente
3. Calcula KPIs, ranking e insights
4. Preenche todos os campos obrigatórios

Isso garante que sempre haverá uma resposta estruturada quando houver dados disponíveis.
