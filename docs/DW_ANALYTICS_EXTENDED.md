# Data Warehouse - Funções Estendidas de Análise

## Visão Geral

Este documento descreve as funções estendidas de análise do Data Warehouse implementadas para suportar o **TEMPLATE DE RESPOSTA NEGATIVA** do DIPAM COPILOT™.

## Arquivo: `src/dw/analytics_metas_extended.py`

### Funções Implementadas

#### 1. `get_metas_por_mes(session, mes_ano, excluir_totais=True)`

Wrapper para compatibilidade que chama `get_metas_realizado_por_mes` de `queries_analytics.py`.

**Parâmetros:**
- `session`: Sessão SQLAlchemy
- `mes_ano`: Mês/ano no formato "YYYY-MM"
- `excluir_totais`: Se True, exclui linhas de "Totais"

**Retorna:**
- `dict` com `meta_total`, `realizado_total`, `gap_total`, `atingimento_medio`, `total_vendedores`

---

#### 2. `get_gap_por_rota(session, mes_ano, top_n=None, excluir_totais=True)`

Obtém gap agregado por rota (vendedor).

**Parâmetros:**
- `session`: Sessão SQLAlchemy
- `mes_ano`: Mês/ano no formato "YYYY-MM"
- `top_n`: Se fornecido, retorna apenas os top N rotas com maior gap
- `excluir_totais`: Se True, exclui linhas de "Totais"

**Retorna:**
- `List[GapRota]` ordenada por `gap_total` decrescente (maior gap primeiro)

**Dataclass `GapRota`:**
```python
@dataclass
class GapRota:
    rota: str
    vendedor_id: Optional[int]
    vendedor_nome: str
    meta_total: float
    realizado_total: float
    gap_total: float
    atingimento_pct: float
    quantidade_vendedores: int
```

---

#### 3. `get_piores_vendedores(session, mes_ano, limite=10, excluir_totais=True)`

Obtém lista de piores vendedores por gap (maior gap negativo = pior desempenho).

**Parâmetros:**
- `session`: Sessão SQLAlchemy
- `mes_ano`: Mês/ano no formato "YYYY-MM"
- `limite`: Número máximo de vendedores a retornar
- `excluir_totais`: Se True, exclui linhas de "Totais"

**Retorna:**
- `List[VendedorGap]` ordenada por `gap_total` crescente (piores primeiro)

**Dataclass `VendedorGap`:**
```python
@dataclass
class VendedorGap:
    vendedor_id: int
    vendedor_nome: str
    rota: str
    supervisor_id: Optional[int]
    supervisor_nome: Optional[str]
    meta_total: float
    realizado_total: float
    gap_total: float
    atingimento_pct: float
    posicao_ranking: int
```

---

#### 4. `get_clientes_com_queda(session, mes_ano_atual, mes_ano_anterior=None, limite=20, variacao_minima_pct=-10.0)`

Identifica clientes com queda de compra comparando dois períodos.

**Parâmetros:**
- `session`: Sessão SQLAlchemy
- `mes_ano_atual`: Mês atual no formato "YYYY-MM"
- `mes_ano_anterior`: Mês anterior (se None, calcula automaticamente)
- `limite`: Número máximo de clientes a retornar
- `variacao_minima_pct`: Variação percentual mínima para considerar queda (ex.: -10.0 = -10%)

**Retorna:**
- `List[ClienteQueda]` ordenada por maior queda (mais negativo primeiro)

**Dataclass `ClienteQueda`:**
```python
@dataclass
class ClienteQueda:
    cliente_id: int
    cliente_nome: str
    vendedor_id: Optional[int]
    vendedor_nome: Optional[str]
    rota: Optional[str]
    faturamento_atual: float
    faturamento_anterior: float
    variacao_pct: float
    dias_sem_compra: int
    mes_ano_atual: str
    mes_ano_anterior: str
```

---

#### 5. `get_skus_com_quebra(session, mes_ano_atual, mes_ano_anterior=None, limite=20, variacao_minima_pct=-20.0)`

Identifica SKUs com quebra/ruptura comparando dois períodos.

**Parâmetros:**
- `session`: Sessão SQLAlchemy
- `mes_ano_atual`: Mês atual no formato "YYYY-MM"
- `mes_ano_anterior`: Mês anterior (se None, calcula automaticamente)
- `limite`: Número máximo de SKUs a retornar
- `variacao_minima_pct`: Variação percentual mínima para considerar quebra

**Retorna:**
- `List[SKUQuebra]` ordenada por maior queda ou ruptura primeiro

**Dataclass `SKUQuebra`:**
```python
@dataclass
class SKUQuebra:
    codigo_produto: str
    desc_produto: str
    departamento: Optional[str]
    vendas_atual: float
    vendas_anterior: float
    variacao_pct: float
    dias_sem_venda: int
    ruptura: bool  # True se não teve venda no período atual
    mes_ano_atual: str
    mes_ano_anterior: str
```

---

#### 6. `get_tendencias(session, metrica, periodo_inicio, periodo_fim)`

Calcula tendência de uma métrica ao longo de um período.

**Parâmetros:**
- `session`: Sessão SQLAlchemy
- `metrica`: "meta", "vendas", "clientes", "atingimento"
- `periodo_inicio`: Mês inicial "YYYY-MM"
- `periodo_fim`: Mês final "YYYY-MM"

**Retorna:**
- `Tendencia` com análise da métrica

**Dataclass `Tendencia`:**
```python
@dataclass
class Tendencia:
    metrica: str
    periodo_inicio: str
    periodo_fim: str
    valor_inicial: float
    valor_final: float
    variacao_pct: float
    tendencia: str  # "alta", "queda", "estavel"
    media_periodo: float
```

---

## Arquivo: `src/agent/analise_causas.py`

### Funções de Análise

#### 1. `detectar_atingimento_abaixo_meta(dados_dw)`

Detecta se o atingimento está abaixo de 100%.

**Parâmetros:**
- `dados_dw`: Dicionário com dados retornados do DW

**Retorna:**
- `bool`: True se atingimento < 100%, False caso contrário

---

#### 2. `gerar_analise_causas(session, dados_dw, mes_ano, limite_vendedores=10, limite_clientes=20, limite_skus=20)`

Gera análise completa de causas quando meta não foi batida.

**Parâmetros:**
- `session`: Sessão SQLAlchemy
- `dados_dw`: Dados retornados do DW
- `mes_ano`: Mês/ano no formato "YYYY-MM"
- `limite_vendedores`: Limite de vendedores a retornar
- `limite_clientes`: Limite de clientes a retornar
- `limite_skus`: Limite de SKUs a retornar

**Retorna:**
- `dict` com todas as análises estruturadas:
  - `vendedores_pior_desempenho`: Lista de vendedores com maior gap
  - `rotas_maior_gap`: Lista de rotas com maior gap
  - `clientes_reduziram_compra`: Lista de clientes com queda
  - `skus_queda_relevante`: Lista de SKUs com quebra/ruptura
  - `gargalos_rupturas`: Lista de gargalos identificados
  - `checklist_problemas`: Lista estruturada de problemas

---

## Integração no Orquestrador

O `orquestrador_dw.py` foi atualizado para:

1. **Detectar automaticamente** quando `atingimento < 100%`
2. **Gerar análise de causas** automaticamente quando meta não batida
3. **Incluir `analise_causas`** no payload de resposta

### Fluxo:

```
IntentSpec → Executar DW → Normalizar Dados → Detectar Atingimento < 100% → Gerar Análise de Causas → Incluir no Payload
```

---

## Compatibilidade

- ✅ **SQLite** (POC atual)
- ✅ **PostgreSQL** (produção futura)
- ❌ **BigQuery** (não implementado, apenas roadmap)

---

## Logs

Todas as funções geram logs legíveis com prefixo `[analytics_metas_extended]` ou `[analise_causas]` para facilitar auditoria e debug.

---

## Exemplos de Uso

### Exemplo 1: Obter piores vendedores

```python
from src.dw.connection import get_db_session
from src.dw.analytics_metas_extended import get_piores_vendedores

session = get_db_session()
vendedores = get_piores_vendedores(session, "2025-08", limite=10)

for v in vendedores:
    print(f"{v.vendedor_nome}: gap de R$ {v.gap_total:,.2f}")
```

### Exemplo 2: Identificar clientes com queda

```python
from src.dw.analytics_metas_extended import get_clientes_com_queda

clientes = get_clientes_com_queda(session, "2025-08", limite=20)

for c in clientes:
    print(f"{c.cliente_nome}: queda de {c.variacao_pct:.1f}%")
```

### Exemplo 3: Gerar análise completa de causas

```python
from src.agent.analise_causas import gerar_analise_causas

analise = gerar_analise_causas(
    session=session,
    dados_dw={"dados": [...], "meta_total": 1000000, "realizado_total": 950000},
    mes_ano="2025-08"
)

print(f"Vendedores com pior desempenho: {len(analise['vendedores_pior_desempenho'])}")
print(f"Clientes com queda: {len(analise['clientes_reduziram_compra'])}")
print(f"SKUs com quebra: {len(analise['skus_queda_relevante'])}")
```

---

## Notas Técnicas

1. **Performance**: Todas as queries usam índices otimizados do banco
2. **Agregações**: Funções fazem agregações no banco (não em memória)
3. **Tipagem**: Retornam dataclasses tipadas (não dicionários soltos)
4. **Tratamento de Erros**: Logs de erro detalhados, nunca quebra o fluxo principal

---

## Próximos Passos

- [ ] Adicionar testes unitários para cada função
- [ ] Otimizar queries para grandes volumes de dados
- [ ] Adicionar cache para análises frequentes
- [ ] Implementar análises preditivas (ML)

