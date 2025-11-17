# Camada DW de Causas - DIPAM COPILOT™

## Visão Geral

O módulo `src/dw/causas.py` fornece funções de alto nível para análise de causas quando a meta não foi batida. Todas as funções consultam exclusivamente o DW (SQLite hoje, PostgreSQL no futuro).

## Funções Disponíveis

### 1. `get_metas_realizado_por_mes(session, periodo_inicio, periodo_fim)`

Retorna meta e realizado agregados por mês no período especificado.

**Parâmetros:**
- `session`: Sessão SQLAlchemy
- `periodo_inicio`: Mês inicial no formato "YYYY-MM" (ex.: "2024-11")
- `periodo_fim`: Mês final no formato "YYYY-MM" (ex.: "2025-10")

**Retorno:**
- Lista de `MetaRealizadoMes`, uma entrada por mês, ordenada por mês

**Exemplo:**
```python
from src.dw.causas import get_metas_realizado_por_mes

metas_mes = get_metas_realizado_por_mes(session, "2025-08", "2025-08")
for meta in metas_mes:
    print(f"{meta.mes}: Meta={meta.meta_total}, Realizado={meta.realizado_total}, Gap={meta.gap_total}")
```

### 2. `get_piores_vendedores_no_mes(session, ano_mes, limite=10)`

Retorna lista de piores vendedores no mês, ordenados por menor atingimento / maior gap.

**Parâmetros:**
- `session`: Sessão SQLAlchemy
- `ano_mes`: Mês/ano no formato "YYYY-MM" (ex.: "2025-08")
- `limite`: Número máximo de vendedores a retornar (padrão: 10)

**Retorno:**
- Lista de `VendedorCausa` ordenada por menor atingimento primeiro

**Exemplo:**
```python
from src.dw.causas import get_piores_vendedores_no_mes

vendedores = get_piores_vendedores_no_mes(session, "2025-08", limite=10)
for v in vendedores:
    print(f"{v.vendedor_nome}: Atingimento={v.atingimento_vendedor}%, Gap={v.gap_vendedor}")
```

### 3. `get_rotas_com_maior_gap_no_mes(session, ano_mes, limite=10)`

Retorna rotas com maior gap no mês, ordenadas por maior gap.

**Parâmetros:**
- `session`: Sessão SQLAlchemy
- `ano_mes`: Mês/ano no formato "YYYY-MM" (ex.: "2025-08")
- `limite`: Número máximo de rotas a retornar (padrão: 10)

**Retorno:**
- Lista de `RotaCausa` ordenada por maior gap primeiro

**Exemplo:**
```python
from src.dw.causas import get_rotas_com_maior_gap_no_mes

rotas = get_rotas_com_maior_gap_no_mes(session, "2025-08", limite=10)
for r in rotas:
    print(f"{r.rota_nome}: Gap={r.gap_rota}, % do gap total={r.percent_gap_do_total}%")
```

### 4. `get_clientes_com_queda_no_mes(session, ano_mes, limite=20)`

Retorna clientes com queda de compra no mês, comparando com mês anterior.

**Parâmetros:**
- `session`: Sessão SQLAlchemy
- `ano_mes`: Mês/ano no formato "YYYY-MM" (ex.: "2025-08")
- `limite`: Número máximo de clientes a retornar (padrão: 20)

**Retorno:**
- Lista de `ClienteQueda` ordenada por maior queda primeiro (mais negativo)

**Exemplo:**
```python
from src.dw.causas import get_clientes_com_queda_no_mes

clientes = get_clientes_com_queda_no_mes(session, "2025-08", limite=20)
for c in clientes:
    print(f"{c.cliente_nome}: Variação={c.variacao_pct}%")
```

### 5. `get_skus_com_queda_no_mes(session, ano_mes, limite=20)`

Retorna SKUs com queda de vendas no mês, comparando com mês anterior.

**Parâmetros:**
- `session`: Sessão SQLAlchemy
- `ano_mes`: Mês/ano no formato "YYYY-MM" (ex.: "2025-08")
- `limite`: Número máximo de SKUs a retornar (padrão: 20)

**Retorno:**
- Lista de `SKUQueda` ordenada por maior queda primeiro (mais negativo)

**Exemplo:**
```python
from src.dw.causas import get_skus_com_queda_no_mes

skus = get_skus_com_queda_no_mes(session, "2025-08", limite=20)
for s in skus:
    print(f"{s.sku_nome}: Variação={s.variacao_pct}%")
```

## Dataclasses de Retorno

### `MetaRealizadoMes`
- `mes`: str (YYYY-MM)
- `meta_total`: float
- `realizado_total`: float
- `gap_total`: float
- `atingimento_medio`: float (percentual)

### `VendedorCausa`
- `vendedor_id`: int
- `vendedor_nome`: str
- `supervisor_id`: Optional[int]
- `supervisor_nome`: Optional[str]
- `rota_id`: Optional[int]
- `rota_nome`: Optional[str]
- `meta_vendedor_mes`: float
- `realizado_vendedor_mes`: float
- `gap_vendedor`: float
- `atingimento_vendedor`: float (percentual)

### `RotaCausa`
- `rota_id`: Optional[int]
- `rota_nome`: str
- `supervisor_id`: Optional[int]
- `supervisor_nome`: Optional[str]
- `meta_rota_mes`: float
- `realizado_rota_mes`: float
- `gap_rota`: float
- `percent_gap_do_total`: float (percentual)

### `ClienteQueda`
- `cliente_id`: int
- `cliente_nome`: str
- `faturamento_mes_atual`: float
- `faturamento_mes_anterior`: float
- `variacao_abs`: float
- `variacao_pct`: float (percentual)

### `SKUQueda`
- `sku_id`: Optional[str]
- `sku_nome`: Optional[str]
- `faturamento_mes_atual`: float
- `faturamento_mes_anterior`: float
- `variacao_abs`: float
- `variacao_pct`: float (percentual)

## Arquitetura

- **Nunca acessa banco fora da camada DW**: Todas as funções usam `connection.py` e `models.py`
- **Retorna dataclasses tipadas**: Garante type safety
- **Logs legíveis**: Todas as funções logam operações importantes
- **Compatível com SQLite e PostgreSQL**: Usa SQLAlchemy para abstração

## Notas Importantes

1. **Filtragem de Totais**: As funções automaticamente excluem linhas com "Totais" ou "total" no nome do vendedor
2. **Ordenação**: Todas as funções retornam dados ordenados (piores primeiro para gaps, maiores quedas primeiro)
3. **Limites**: Todas as funções aplicam limites para evitar retornar listas muito grandes
4. **Comparação Mensal**: Funções de queda comparam com o mês anterior automaticamente

