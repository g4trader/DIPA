# Resumo - Fase 2: ML Baseline (Heurísticas/Estatística)

## Data: 2025-11-16

## Objetivo

Criar uma camada de "ML baseline" usando heurísticas e estatística para calcular scores de churn, risco de meta e queda de produtos, sem usar bibliotecas pesadas de ML (adequado para Cloud Run).

## Arquivos Criados

### 1. Módulo de Features (`src/ml/features.py`)

Funções para calcular features temporárias a partir das tabelas analytics:

- **`calcular_faturamento_historico_cliente()`**: Série histórica de faturamento para um cliente
- **`calcular_variacao_faturamento_cliente()`**: Variação de faturamento vs média dos últimos 3 meses
- **`calcular_variacao_faturamento_produto()`**: Variação de faturamento do produto vs média 3m
- **`calcular_trend_atingimento_vendedor()`**: Tendência de atingimento do vendedor (melhorando/piorando/estável)

**Características:**
- Usa tabelas `analytics_*` como fonte primária (eficiente)
- Só cai em dados brutos se realmente necessário
- Compatível com SQLite e PostgreSQL

### 2. Módulo de Scoring (`src/ml/scoring.py`)

Funções puramente em Python (sem sklearn) para calcular scores:

#### Churn Score (0-100)
- **`calcular_churn_score()`**: Calcula score baseado em:
  - Faturamento atual vs média 3m
  - Dias desde última compra
  - Variação percentual
  - Regras: cliente sem compra + histórico alto = score alto (80-100)
  
- **`classificar_churn_flag()`**: Retorna `True` se score >= 60

#### Meta Risk Score (0-100)
- **`calcular_meta_risk_score()`**: Calcula score baseado em:
  - Atingimento percentual (< 70% = alto risco)
  - Gap valor (quanto mais negativo, maior risco)
  - Tendência (piorando aumenta risco)
  
- **`classificar_meta_risk_flag()`**: Retorna `True` se score >= 60

#### Queda Score (0-100)
- **`calcular_queda_score()`**: Calcula score baseado em:
  - Variação percentual vs média 3m
  - Queda > 50% = score 90
  - Queda 30-50% = score 65-80
  
- **`classificar_queda_flag()`**: Retorna `True` se score >= 60

### 3. Script de Teste (`scripts/test_ml_baseline.py`)

Script completo para validar o pipeline:

- Executa `run_all_analytics()` completo
- Imprime top 10 clientes com maior `churn_score`
- Imprime top 10 vendedores com maior `meta_risk_score`
- Imprime top 10 produtos com maior `queda_score`
- Imprime total de alertas por `tipo_alerta` e nível
- Resumo de flags (quantos clientes/vendedores/produtos em risco)

**Uso:**
```bash
DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db python -m scripts.test_ml_baseline --mes-ano 2025-08
```

## Arquivos Modificados

### 1. `src/dw/models_analytics.py`

#### AnalyticsClienteMes
- ✅ `churn_score`: `Numeric(5, 2)` (0-100) - default 0.0
- ✅ `churn_flag`: `Boolean` - default False
- ✅ `faturamento_media_3m`: `Numeric(15, 2)` - nullable
- ✅ `variacao_pct_vs_3m`: `Numeric(5, 2)` - nullable

#### AnalyticsVendedorMes
- ✅ `meta_risk_score`: `Numeric(5, 2)` (0-100) - default 0.0
- ✅ `meta_risk_flag`: `Boolean` - default False

#### AnalyticsProdutoMes
- ✅ `variacao_pct_vs_3m`: `Numeric(5, 2)` - nullable
- ✅ `queda_score`: `Numeric(5, 2)` (0-100) - default 0.0
- ✅ `queda_flag`: `Boolean` - default False

### 2. `scripts/build_analytics.py`

#### Novas Funções Adicionadas

1. **`aplicar_scores_clientes()`**:
   - Percorre `analytics_cliente_mes` do mês
   - Calcula features via `calcular_variacao_faturamento_cliente()`
   - Calcula `churn_score` via `calcular_churn_score()`
   - Atualiza `churn_score`, `churn_flag`, `faturamento_media_3m`, `variacao_pct_vs_3m`

2. **`aplicar_scores_vendedores()`**:
   - Percorre `analytics_vendedor_mes` do mês
   - Calcula trend via `calcular_trend_atingimento_vendedor()`
   - Calcula `meta_risk_score` via `calcular_meta_risk_score()`
   - Atualiza `meta_risk_score` e `meta_risk_flag`

3. **`aplicar_scores_produtos()`**:
   - Percorre `analytics_produto_mes` do mês
   - Calcula features via `calcular_variacao_faturamento_produto()`
   - Calcula `queda_score` via `calcular_queda_score()`
   - Atualiza `queda_score`, `queda_flag`, `variacao_pct_vs_3m`

#### Função `build_analytics_alertas()` Atualizada

Agora usa os **scores e flags** em vez de regras hardcoded:

1. **Alertas de Vendedor**:
   - Busca `analytics_vendedor_mes` onde `meta_risk_flag == True`
   - Ordena por `meta_risk_score` desc
   - Nível baseado no score: >= 80 = alto, >= 60 = médio, < 60 = baixo
   - Inclui `meta_risk_score` no `detalhes_json`

2. **Alertas de Cliente**:
   - Busca `analytics_cliente_mes` onde `churn_flag == True`
   - Ordena por `churn_score` desc
   - Nível baseado no score
   - Inclui `churn_score`, `variacao_pct_vs_3m`, `dias_desde_ultima_compra` no `detalhes_json`

3. **Alertas de Produto**:
   - Busca `analytics_produto_mes` onde `queda_flag == True`
   - Ordena por `queda_score` desc
   - Nível baseado no score
   - Inclui `queda_score`, `variacao_pct_vs_3m` no `detalhes_json`

#### Função `run_all_analytics()` Atualizada

Nova ordem de execução:

1. `build_analytics_vendedor_mes()`
2. `build_analytics_cliente_mes()`
3. `build_analytics_produto_mes()`
4. **`aplicar_scores_clientes()`** ← NOVO
5. **`aplicar_scores_vendedores()`** ← NOVO
6. **`aplicar_scores_produtos()`** ← NOVO
7. `build_analytics_alertas()` (agora usa os scores)

## Lógica de Scores

### Churn Score (Cliente)

```
Score = 0.0

# Critério 1: Cliente não comprou no mês atual
Se faturamento_atual == 0 e faturamento_media_3m > 0:
    Se dias_sem_comprar > 60: +50
    Se dias_sem_comprar > 30: +30
    Se faturamento_media_3m > 10000: +20 (cliente grande)

# Critério 2: Queda de faturamento
Se variacao_pct < -50%: +40
Se variacao_pct < -30%: +25
Se variacao_pct < -20%: +15

# Critério 3: Dias sem comprar
Se dias > 90: +30
Se dias > 60: +20

Score final: min(100, max(0, score))
Flag: score >= 60
```

### Meta Risk Score (Vendedor)

```
Score = 0.0

# Critério 1: Atingimento
Se atingimento < 70%: +50
Se atingimento < 80%: +35
Se atingimento < 90%: +20
Se atingimento < 95%: +10

# Critério 2: Gap valor
Se gap < -50000: +30
Se gap < -20000: +20
Se gap < -10000: +15
Se gap < -5000: +10
Se gap < -1000: +5

# Critério 3: Tendência
Se tendencia == "piorando": +15
Se tendencia == "melhorando": -10

Score final: min(100, max(0, score))
Flag: score >= 60
```

### Queda Score (Produto)

```
Score = 0.0

# Baseado em variação percentual
Se variacao_pct < -50%: score = 90
Se variacao_pct < -40%: score = 80
Se variacao_pct < -30%: score = 65
Se variacao_pct < -20%: score = 50
Se variacao_pct < -10%: score = 30
Caso contrário: score = 10

Score final: min(100, max(0, score))
Flag: score >= 60
```

## Características Técnicas

### Performance

- **Código leve**: Sem sklearn, numpy pesado ou outras libs ML
- **Queries eficientes**: Usa tabelas `analytics_*` como fonte primária
- **Processamento em lote**: Aplica scores para todos os registros de uma vez
- **Compatível com Cloud Run**: Não trava o container

### Tratamento de Erros

- Logs detalhados em cada etapa
- Tratamento gracioso: se um cliente/vendedor/produto falhar, continua com os outros
- Rollback automático em caso de erro crítico

### Dados Reais

- **Nada de mock**: Tudo baseado em dados reais do banco
- **Features calculadas dinamicamente**: Média 3m, variação, tendências
- **Scores baseados em regras de negócio**: Heurísticas claras e explicáveis

## Testes

Para testar a implementação:

```bash
# 1. Executar build completo (inclui scores)
DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db python -m scripts.build_analytics --mes-ano 2025-08

# 2. Testar e validar ML baseline
DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db python -m scripts.test_ml_baseline --mes-ano 2025-08
```

## Resultados Esperados

Após executar `test_ml_baseline.py`, você deve ver:

1. **Top 10 Clientes com Churn Score**:
   - Clientes com score mais alto (maior risco)
   - Flags marcadas corretamente
   - Features (faturamento, variação, dias) preenchidas

2. **Top 10 Vendedores com Meta Risk Score**:
   - Vendedores com score mais alto (maior risco)
   - Flags marcadas corretamente
   - Atingimento e gap preenchidos

3. **Top 10 Produtos com Queda Score**:
   - Produtos com score mais alto (maior queda)
   - Flags marcadas corretamente
   - Variação percentual preenchida

4. **Alertas por Tipo**:
   - `vendedor_meta_em_risco`: Alertas de vendedores
   - `cliente_churn_alto`: Alertas de clientes
   - `produto_queda_forte`: Alertas de produtos
   - Distribuição por nível (alto/médio/baixo)

5. **Resumo de Flags**:
   - Total de clientes em risco de churn
   - Total de vendedores em risco de meta
   - Total de produtos em queda

## Próximos Passos (Fase 3 - ML Avançado - Opcional)

1. Substituir heurísticas por modelos ML treinados (Random Forest, XGBoost)
2. Adicionar features mais complexas (sazonalidade, correlações)
3. Calibrar thresholds de flags baseado em histórico
4. Adicionar métricas de precisão/recall dos scores

## Observações

- Os scores são **heurísticos** (não modelos ML treinados)
- As regras são **explicáveis** e **ajustáveis**
- O código é **leve** e adequado para Cloud Run
- Tudo é baseado em **dados reais** do banco
- Os alertas são gerados **automaticamente** baseados nos scores

