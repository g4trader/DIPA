# Testes de Aceitação - 40 Perguntas do DIPAM COPILOT™

Este documento lista as 40 perguntas de teste de aceitação organizadas por tema, com o que é esperado em cada resposta.

## Estrutura de Resposta Esperada

Todas as respostas devem seguir o formato:

```json
{
  "resumo_executivo": "texto objetivo explicando o que aconteceu, sem florear",
  "periodo_analisado": {
    "inicio": "YYYY-MM-DD",
    "fim": "YYYY-MM-DD"
  },
  "tabela_principal": [
    {
      "colunas": ["Coluna1", "Coluna2", ...],
      "linhas": [
        ["Valor1", "Valor2", ...],
        ...
      ]
    }
  ],
  "insights": [
    "Insight acionável 1 (específico, com números reais)",
    "Insight acionável 2 (específico, com números reais)",
    "Insight acionável 3 (específico, com números reais)"
  ]
}
```

---

## 3.1. Metas por Período (7 testes)

### Teste 3.1.1
**Pergunta:** "Liste as metas por mês de todo o período que você tem."

**Intent esperado:**
- `tipo`: "meta"
- `dimensao_principal`: "mes"

**Resposta esperada:**
- Tabela com 1 linha por mês
- Resumo fala de melhor e pior mês
- Insights citam meses críticos

---

### Teste 3.1.2
**Pergunta:** "Qual a meta total e o realizado total de agosto de 2025?"

**Intent esperado:**
- `tipo`: "meta"
- `periodo_inicio`: "2025-08-01"
- `dimensao_principal`: "nenhuma"

**Resposta esperada:**
- 1 linha agregada (meta, realizado, % atingimento)
- Resumo menciona gap ou superação

---

### Teste 3.1.3
**Pergunta:** "Como foi a evolução da meta realizada de novembro/2024 até outubro/2025?"

**Intent esperado:**
- `tipo`: "meta"
- `dimensao_principal`: "mes"
- `periodo_inicio`: "2024-11-01"
- `periodo_fim`: "2025-10-31"

**Resposta esperada:**
- Linhas mensais com meta x realizado
- Insights destacam tendência (alta/queda)

---

### Teste 3.1.4
**Pergunta:** "Qual foi o mês com pior atingimento de meta no período disponível?"

**Resposta esperada:**
- Resumo aponta mês específico
- Tabela traz meses ordenados

---

### Teste 3.1.5
**Pergunta:** "Em quais meses o atingimento ficou abaixo de 95%?"

**Resposta esperada:**
- Só meses críticos
- Insights sugerem acompanhamento

---

### Teste 3.1.6
**Pergunta:** "Quantos vendedores bateram a meta em agosto de 2025?"

**Intent esperado:**
- `tipo`: "meta"
- `dimensao_principal`: "vendedor"
- `periodo_inicio`: "2025-08-01"

**Resposta esperada:**
- Tabela de vendedores com meta x realizado
- Resumo cita contagem

---

### Teste 3.1.7
**Pergunta:** "Quero a soma das metas do período inteiro, independente de mês."

**Resposta esperada:**
- 1 linha com meta_total geral
- `periodo_analisado` deve cobrir todo o intervalo disponível

---

## 3.2. Ranking de Vendedores e Supervisores (8 testes)

### Teste 3.2.1
**Pergunta:** "Quais são os 5 vendedores com maior risco de não bater a meta em agosto de 2025?"

**Intent esperado:**
- `tipo`: "ranking_vendedores"
- `dimensao_principal`: "vendedor"
- `periodo_inicio`: "2025-08-01"
- `filtros.top_n`: 5

**Resposta esperada:**
- Tabela com vendedor, supervisor, meta, realizado, %
- Insights reforçam quem precisa de coaching

---

### Teste 3.2.2
**Pergunta:** "Quais são os 5 vendedores com melhor performance no período de junho a agosto de 2025?"

**Intent esperado:**
- `tipo`: "ranking_vendedores"
- `dimensao_principal`: "vendedor"
- `periodo_inicio`: "2025-06-01"
- `periodo_fim`: "2025-08-31"
- `filtros.top_n`: 5

**Resposta esperada:**
- Ranking positivo

---

### Teste 3.2.3
**Pergunta:** "Qual supervisor ficou mais distante da meta em agosto de 2025?"

**Intent esperado:**
- `tipo`: "meta"
- `dimensao_principal`: "supervisor"
- `periodo_inicio`: "2025-08-01"

**Resposta esperada:**
- Tabela de supervisores
- Resumo aponta o pior e o melhor

---

### Teste 3.2.4
**Pergunta:** "Traga o ranking completo de vendedores por atingimento de meta em agosto de 2025."

**Resposta esperada:**
- Ranking total
- Insights falam de cauda longa de baixo desempenho

---

### Teste 3.2.5
**Pergunta:** "Qual é o percentual médio de atingimento da equipe em agosto de 2025?"

**Resposta esperada:**
- 1 valor
- Resumo explica se está aceitável/acima/abaixo

---

### Teste 3.2.6
**Pergunta:** "Mostre a lista de vendedores que estão abaixo de 80% da meta em agosto de 2025."

**Resposta esperada:**
- Apenas vendedores críticos

---

### Teste 3.2.7
**Pergunta:** "Comparar a performance dos supervisores da região Norte e Sul em agosto de 2025."

**Resposta esperada:**
- Tabela mostrando regiões
- Resumo compara

---

### Teste 3.2.8
**Pergunta:** "Quais vendedores melhoraram mais o atingimento entre julho e agosto de 2025?"

**Resposta esperada:**
- Tabela com delta
- Insights destacam evolução

---

## 3.3. Clientes Críticos, Churn e Recuperação (10 testes)

### Teste 3.3.1
**Pergunta:** "Liste os clientes críticos (60 dias sem compra) por supervisor."

**Intent esperado:**
- `tipo`: "clientes_criticos"
- `dimensao_principal`: "cliente"

**Resposta esperada:**
- Tabela com cliente, supervisor, dias_sem_compra
- Insights sugerem planos de ação

---

### Teste 3.3.2
**Pergunta:** "Quais clientes deixaram de comprar há mais de 90 dias (churn) em agosto de 2025?"

**Resposta esperada:**
- Lista de churn
- Resumo cita impacto de faturamento

---

### Teste 3.3.3
**Pergunta:** "Quais são os 10 clientes com maior queda de faturamento vs média dos 3 meses anteriores?"

**Resposta esperada:**
- Tabela com cliente, variação % e R$
- Insights focam nos mais relevantes

---

### Teste 3.3.4
**Pergunta:** "Mostre os clientes que voltaram a comprar após estarem críticos nos últimos 3 meses."

**Resposta esperada:**
- Tabela de clientes recuperados
- Insights sobre boa atuação comercial

---

### Teste 3.3.5
**Pergunta:** "Quais clientes críticos estão concentrados na ROTA 75 VD?"

**Resposta esperada:**
- Lista segmentada

---

### Teste 3.3.6
**Pergunta:** "Quais são os clientes da marca Nissin com risco de churn em agosto de 2025?"

**Resposta esperada:**
- Tabela detalhando frequência e valor

---

### Teste 3.3.7
**Pergunta:** "Mostre o impacto financeiro estimado se recuperarmos apenas 50% dos clientes críticos atuais."

**Resposta esperada:**
- Campo numérico de potencial
- Insights com recomendação prática

---

### Teste 3.3.8
**Pergunta:** "Liste clientes com queda acima de 50% em relação à média dos últimos 6 meses."

**Resposta esperada:**
- Lista de outliers
- Insights de priorização

---

### Teste 3.3.9
**Pergunta:** "Quais clientes críticos pertencem ao supervisor X?"

**Resposta esperada:**
- Lista filtrada

---

### Teste 3.3.10
**Pergunta:** "Quais clientes passaram de churn para ativos em outubro de 2025?"

**Resposta esperada:**
- Clientes reativados
- Insights valorizam ação

---

## 3.4. Produtos, Marcas, Categorias (7 testes)

### Teste 3.4.1
**Pergunta:** "Quais são os produtos com maior queda de vendas em agosto de 2025 vs julho de 2025?"

**Resposta esperada:**
- Lista ordenada por variação negativa

---

### Teste 3.4.2
**Pergunta:** "Mostre as 5 marcas com melhor crescimento no trimestre de jun–ago/2025."

**Resposta esperada:**
- Ranking de crescimento

---

### Teste 3.4.3
**Pergunta:** "Qual é a participação de Nissin no faturamento total de agosto de 2025?"

**Resposta esperada:**
- % de share + valor em R$

---

### Teste 3.4.4
**Pergunta:** "Quais categorias puxaram o resultado positivo em outubro de 2025?"

**Resposta esperada:**
- Top categorias com crescimento
- Insights

---

### Teste 3.4.5
**Pergunta:** "Liste os SKUs com ticket médio mais alto no período de maio a julho de 2025."

**Resposta esperada:**
- Ranking

---

### Teste 3.4.6
**Pergunta:** "Quais produtos tiveram ruptura de compras (ficaram 2 meses sem ser vendidos) e depois voltaram?"

**Resposta esperada:**
- Lista de SKUs com períodos de ruptura e retomada

---

### Teste 3.4.7
**Pergunta:** "Quais produtos são mais sensíveis à sazonalidade entre novembro e fevereiro?"

**Resposta esperada:**
- Identificação de padrões de pico/queda

---

## 3.5. Consultas Executivas Complexas (8 testes)

### Teste 3.5.1
**Pergunta:** "Sou o Diretor e quero entender detalhadamente por que não batemos a meta em agosto de 2025. Quero explicação por vendedor, por produto e por cliente."

**Intent esperado:**
- `tipo`: "analise_meta_detalhada"
- `dimensao_principal`: "vendedor"
- `periodo_inicio`: "2025-08-01"

**Resposta esperada:**
- Resumo forte
- Tabela principal (ex: por vendedor)
- Insights com produtos/clientes chave

---

### Teste 3.5.2
**Pergunta:** "Quais regiões venderam abaixo do esperado em agosto de 2025 e qual foi o impacto financeiro?"

**Resposta esperada:**
- Tabela + impacto total

---

### Teste 3.5.3
**Pergunta:** "Qual rota tem mais clientes positivados em produtos Nissin no mês de agosto de 2025?"

**Resposta esperada:**
- Rota top
- Resumo claro

---

### Teste 3.5.4
**Pergunta:** "Quais vendedores têm carteira mais concentrada em poucos clientes (risco de concentração)?"

**Resposta esperada:**
- Ranking

---

### Teste 3.5.5
**Pergunta:** "Se mantivermos o ritmo médio diário de agosto de 2025, qual a projeção de fechamento do mês?"

**Resposta esperada:**
- Projeção em R$ e %
- Insights explicam risco

---

### Teste 3.5.6
**Pergunta:** "Mostre a relação entre visitas (pedidos) e faturamento por vendedor em agosto de 2025."

**Resposta esperada:**
- Tabela + insight de produtividade

---

### Teste 3.5.7
**Pergunta:** "Quais supervisores têm maior número de clientes críticos na carteira?"

**Resposta esperada:**
- Ranking

---

### Teste 3.5.8
**Pergunta:** "Mostre um resumo executivo geral do período nov/2024 a out/2025: melhores meses, piores meses, marcas que cresceram e principais riscos."

**Resposta esperada:**
- Resumo bem completo
- Tabela de meses e/ou marcas
- Vários insights

---

## Como Executar os Testes

```bash
# Executar todos os testes de aceitação
pytest tests/test_aceitacao_40_perguntas.py -v

# Executar um teste específico
pytest tests/test_aceitacao_40_perguntas.py::test_aceitacao_01_liste_metas_por_mes_periodo_completo -v

# Executar testes por tema (usando marcadores)
pytest -m aceitacao tests/ -v

# Executar apenas testes de metas
pytest tests/test_aceitacao_40_perguntas.py -k "test_aceitacao_0[1-7]" -v
```

## Validações Automáticas

Cada teste valida:

1. **Estrutura da resposta:**
   - `resumo_executivo` (string, mínimo 10 caracteres)
   - `periodo_analisado` (dict com `inicio` e `fim`)
   - `tabela_principal` (list)
   - `insights` (list, não vazio)

2. **IntentSpec esperado:**
   - `tipo` correto
   - `dimensao_principal` correta
   - Período correto (quando especificado)

3. **Conteúdo da resposta:**
   - Tabela presente (quando esperado)
   - Insights presentes
   - Palavras-chave no resumo executivo

