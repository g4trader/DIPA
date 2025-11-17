# Exemplos de Casos de Uso - DIPAM COPILOT™

Este documento apresenta exemplos práticos de perguntas e como o DIPAM COPILOT™ as processa usando o novo fluxo baseado em IntentSpec e camada DW.

## Arquitetura do Fluxo

```
PERGUNTA DO USUÁRIO
  ↓
LLM gera IntentSpec (JSON)
  ↓
Backend parseia JSON → IntentSpec
  ↓
Executa consulta na camada DW (analytics_metas.py, query_executor.py)
  ↓
LLM recebe dados brutos e gera resposta executiva estruturada
  ↓
RESPOSTA FINAL (resumo_executivo + tabela_principal + insights)
```

## Casos de Uso Obrigatórios

### Caso A: Listar Metas por Mês (Período Completo)

**Pergunta:**
> "Preciso que liste as metas de todo o período que você tem, separe por mês"

**IntentSpec gerado pelo LLM:**
```json
{
  "tipo": "meta",
  "periodo_inicio": "2024-11",
  "periodo_fim": "2025-10",
  "dimensao_principal": "mes",
  "filtros": {},
  "metricas": ["meta_total", "realizado_total", "atingimento_medio", "gap_total"],
  "confianca": 0.9,
  "entidades_extraidas": {
    "n_meses": null,
    "periodo_completo": true
  }
}
```

**Consulta DW executada:**
```python
metas_por_mes = listar_metas_por_mes(
    session,
    periodo_inicio="2024-11",
    periodo_fim="2025-10",
    excluir_totais=True
)
```

**Resposta esperada:**
```json
{
  "resumo_executivo": "No período de novembro/2024 a outubro/2025, a DIPAM apresentou uma evolução mista nas metas. O período iniciou com metas de R$ 1.280.000,00 em novembro/2024, atingindo R$ 1.050.000,00 (82,0% de atingimento). Em agosto/2025, a meta foi de R$ 17.833.054,85, com realizado de R$ 17.254.142,15 (96,75% de atingimento).",
  "periodo_analisado": {
    "inicio": "2024-11-01",
    "fim": "2025-10-31"
  },
  "tabela_principal": [
    {
      "colunas": ["Mês", "Meta Total", "Realizado Total", "Gap", "Atingimento (%)"],
      "linhas": [
        ["2024-11", "R$ 1.280.000,00", "R$ 1.050.000,00", "R$ -230.000,00", "82,0%"],
        ["2024-12", "R$ 1.350.000,00", "R$ 1.200.000,00", "R$ -150.000,00", "88,9%"],
        ...
        ["2025-08", "R$ 17.833.054,85", "R$ 17.254.142,15", "R$ -578.912,70", "96,75%"],
        ...
        ["2025-10", "R$ 1.500.000,00", "R$ 1.400.000,00", "R$ -100.000,00", "93,3%"]
      ]
    }
  ],
  "insights": [
    "Atingimento melhorou de 82,0% em novembro/2024 para 96,75% em agosto/2025, indicando recuperação gradual.",
    "Agosto/2025 apresentou o maior volume de meta (R$ 17,8M) e maior gap absoluto (R$ 578,9K), requerendo atenção especial.",
    "Recomenda-se análise detalhada dos vendedores com maior gap em agosto/2025 para identificar causas raiz."
  ]
}
```

---

### Caso B: Top 5 Vendedores com Maior Risco

**Pergunta:**
> "Quais são os 5 vendedores com maior risco de não bater a meta em agosto de 2025?"

**IntentSpec gerado pelo LLM:**
```json
{
  "tipo": "meta",
  "periodo_inicio": "2025-08",
  "periodo_fim": "2025-08",
  "dimensao_principal": "vendedor",
  "filtros": {
    "mes": "2025-08",
    "top_n": 5,
    "ordenacao": "gap",
    "incluir_ranking": true
  },
  "metricas": ["meta_total", "realizado_total", "atingimento_pct", "gap_valor", "meta_risk_score"],
  "confianca": 0.95,
  "entidades_extraidas": {
    "mes_ano": "2025-08",
    "top_n": 5
  }
}
```

**Consulta DW executada:**
```python
# 1. Busca KPIs do mês
kpis_mes = get_metas_realizado_por_mes(session, "2025-08", excluir_totais=True)

# 2. Busca piores vendedores por gap
piores_vendedores = get_piores_vendedores_por_gap(
    session,
    "2025-08",
    limite=5,
    excluir_totais=True
)
```

**Resposta esperada:**
```json
{
  "resumo_executivo": "Em agosto/2025, identificamos 5 vendedores com maior risco de não bater a meta. O vendedor ROTA 22 apresentou o maior gap (R$ -450.000,00), com atingimento de 72,5% e meta_risk_score de 85,2. Juntos, esses 5 vendedores representam um gap total de R$ -1.200.000,00.",
  "periodo_analisado": {
    "inicio": "2025-08-01",
    "fim": "2025-08-31"
  },
  "tabela_principal": [
    {
      "colunas": ["Posição", "Vendedor", "Meta", "Realizado", "Gap", "Atingimento (%)", "Risco"],
      "linhas": [
        ["1", "ROTA 22", "R$ 1.200.000,00", "R$ 870.000,00", "R$ -330.000,00", "72,5%", "Alto (85,2)"],
        ["2", "ROTA 77", "R$ 980.000,00", "R$ 750.000,00", "R$ -230.000,00", "76,5%", "Alto (82,1)"],
        ["3", "ROTA 94", "R$ 850.000,00", "R$ 680.000,00", "R$ -170.000,00", "80,0%", "Médio (75,3)"],
        ["4", "ROTA 101", "R$ 720.000,00", "R$ 590.000,00", "R$ -130.000,00", "81,9%", "Médio (72,8)"],
        ["5", "ROTA 45", "R$ 650.000,00", "R$ 540.000,00", "R$ -110.000,00", "83,1%", "Médio (70,5)"]
      ]
    }
  ],
  "insights": [
    "ROTA 22 requer intervenção imediata: gap de R$ 330K e risco alto (85,2). Agendar reunião com supervisor para análise detalhada.",
    "ROTA 77 e ROTA 94 também apresentam risco alto/médio. Priorizar acompanhamento semanal dessas rotas.",
    "Os 5 vendedores em risco representam 21% do gap total de agosto/2025. Focar ações de recuperação nesses casos."
  ]
}
```

---

### Caso C: Análise Detalhada Multi-Dimensional

**Pergunta:**
> "Sou o diretor e quero entender por que não batemos a meta em agosto de 2025. Quero explicação por vendedor, por produto e por cliente."

**IntentSpec gerado pelo LLM:**
```json
{
  "tipo": "analise_meta_detalhada",
  "periodo_inicio": "2025-08",
  "periodo_fim": "2025-08",
  "dimensao_principal": "vendedor",
  "filtros": {
    "mes": "2025-08",
    "incluir_produtos": true,
    "incluir_clientes": true,
    "incluir_ranking": true
  },
  "metricas": [
    "meta_total",
    "realizado_total",
    "atingimento_medio",
    "gap_total",
    "faturamento_por_produto",
    "faturamento_por_cliente",
    "churn_score"
  ],
  "confianca": 0.9,
  "entidades_extraidas": {
    "mes_ano": "2025-08",
    "analise_detalhada": true,
    "dimensoes": ["vendedor", "produto", "cliente"]
  }
}
```

**Consulta DW executada:**
```python
# 1. KPIs agregados do mês
kpis_mes = get_metas_realizado_por_mes(session, "2025-08", excluir_totais=True)

# 2. Piores vendedores
piores_vendedores = get_piores_vendedores_por_gap(session, "2025-08", limite=10, excluir_totais=True)

# 3. Vendas por produto (se necessário)
# 4. Clientes críticos (se necessário)
```

**Resposta esperada:**
```json
{
  "resumo_executivo": "Em agosto/2025, a DIPAM não atingiu a meta de R$ 17.833.054,85, realizando R$ 17.254.142,15 (96,75% de atingimento), com gap de R$ -578.912,70. A análise detalhada revela que 10 vendedores concentram 65% do gap total, sendo ROTA 22 o maior responsável (R$ -330.000,00). Em relação a produtos, a categoria 'Biscoito' apresentou queda de 12% vs. média dos últimos 3 meses. Quanto a clientes, identificamos 23 clientes em alto risco de churn, concentrados principalmente nas rotas 22 e 94.",
  "periodo_analisado": {
    "inicio": "2025-08-01",
    "fim": "2025-08-31"
  },
  "tabela_principal": [
    {
      "titulo": "Top 10 Vendedores com Maior Impacto no Gap",
      "colunas": ["Vendedor", "Meta", "Realizado", "Gap", "Atingimento (%)", "% do Gap Total"],
      "linhas": [
        ["ROTA 22", "R$ 1.200.000,00", "R$ 870.000,00", "R$ -330.000,00", "72,5%", "57,0%"],
        ["ROTA 77", "R$ 980.000,00", "R$ 750.000,00", "R$ -230.000,00", "76,5%", "39,7%"],
        ...
      ]
    },
    {
      "titulo": "Produtos com Maior Queda vs. Média 3 Meses",
      "colunas": ["Produto", "Faturamento Ago/2025", "Média 3 Meses", "Variação (%)"],
      "linhas": [
        ["Biscoito Nissin", "R$ 450.000,00", "R$ 511.363,64", "-12,0%"],
        ...
      ]
    },
    {
      "titulo": "Clientes em Alto Risco de Churn",
      "colunas": ["Cliente", "Vendedor", "Churn Score", "Dias sem Compra", "Faturamento 12m"],
      "linhas": [
        ["Supermercado ABC", "ROTA 22", "87,5", "95", "R$ 120.000,00"],
        ...
      ]
    }
  ],
  "insights": [
    "ROTA 22 concentra 57% do gap total (R$ 330K). Investigar causas: perda de clientes, mudança de supervisor, problemas operacionais.",
    "Categoria 'Biscoito' apresentou queda de 12% vs. média 3 meses. Analisar se há mudança de preferência do consumidor ou problemas de estoque.",
    "23 clientes em alto risco de churn concentrados em ROTA 22 e ROTA 94. Implementar plano de recuperação imediata para esses clientes.",
    "Recomenda-se reunião de emergência com supervisores das rotas 22, 77 e 94 para definir plano de ação corretiva para setembro/2025."
  ]
}
```

---

## Regras Anti-Alucinação

### Quando não há dados

**Pergunta:**
> "Quais são as metas de dezembro de 2026?"

**Resposta esperada:**
```json
{
  "resumo_executivo": "Não encontrei dados no data warehouse DIPAM para o período solicitado. Período solicitado: 2026-12 a 2026-12. Verifique se os dados foram carregados para este período.",
  "periodo_analisado": {
    "inicio": "2026-12-01",
    "fim": "2026-12-31"
  },
  "tabela_principal": [],
  "insights": [
    "Verifique se os dados foram carregados no data warehouse DIPAM para o período solicitado.",
    "Tente reformular a pergunta com um período diferente ou filtros mais amplos."
  ]
}
```

### Quando a pergunta é vaga

**Pergunta:**
> "Me mostre as metas"

**Resposta esperada:**
```json
{
  "resumo_executivo": "Sua pergunta é muito genérica. Para fornecer uma resposta precisa, preciso saber: (1) qual período você deseja analisar? (ex.: 'agosto de 2025' ou 'últimos 6 meses'), (2) você quer ver metas por vendedor, por supervisor ou agregadas? (3) há algum filtro específico (ex.: 'apenas ROTA 22')?",
  "periodo_analisado": {
    "inicio": null,
    "fim": null
  },
  "tabela_principal": [],
  "insights": [
    "Reformule sua pergunta especificando: período, dimensão (vendedor/supervisor/mês) e filtros opcionais."
  ]
}
```

---

## Notas Técnicas

- **Fonte de dados:** Todos os dados vêm do **data warehouse DIPAM** (camada DW)
- **BigQuery:** NÃO está implementado (apenas roadmap futuro)
- **Compatibilidade:** SQLite (POC atual) → PostgreSQL (futuro)
- **Nunca inventar dados:** Se um dado não estiver no DW, o COPILOT deve dizer claramente

