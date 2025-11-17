# Detector Inteligente de Causas - DIPAM COPILOT™

## Visão Geral

O módulo `src/agent/causas_detector.py` detecta as causas mais relevantes para explicar por que um mês não bateu meta, consumindo dados do `dw/causas.py` e aplicando regras de negócio.

## Função Principal

### `detectar_causas_para_mes(session, ano_mes, ...)`

Detecta causas mais relevantes para explicar o gap do mês.

**Parâmetros:**
- `session`: Sessão SQLAlchemy
- `ano_mes`: Mês/ano no formato "YYYY-MM" (ex.: "2025-08")
- `gap_vendedor_minimo`: Gap mínimo em R$ para considerar vendedor crítico (padrão: 10000.0)
- `percent_gap_rota_minimo`: Percentual mínimo do gap total para considerar rota crítica (padrão: 20.0)
- `percent_queda_cliente_minimo`: Queda percentual mínima para considerar cliente crítico (padrão: 25.0)
- `percent_queda_sku_minimo`: Queda percentual mínima para considerar SKU crítico (padrão: 30.0)
- `atingimento_vendedor_critico`: Atingimento mínimo para considerar vendedor crítico (padrão: 85.0)

**Retorno:**
```python
{
    "gap_total": float,
    "atingimento_medio": float,
    "causas": {
        "rotas": List[Dict],
        "vendedores": List[Dict],
        "clientes": List[Dict],
        "skus": List[Dict]
    },
    "resumo_causas": List[str]
}
```

**Exemplo:**
```python
from src.agent.causas_detector import detectar_causas_para_mes

causas = detectar_causas_para_mes(session, "2025-08")
print(f"Gap total: R$ {causas['gap_total']:,.2f}")
print(f"Atingimento: {causas['atingimento_medio']:.2f}%")
print(f"Rotas críticas: {len(causas['causas']['rotas'])}")
print(f"Vendedores críticos: {len(causas['causas']['vendedores'])}")
```

## Regras de Negócio

### Causas Críticas

1. **Rotas**: Rota com gap >= `percent_gap_rota_minimo%` do gap_total_mes
2. **Vendedores**: Vendedor com atingimento < `atingimento_vendedor_critico%` E gap > `gap_vendedor_minimo`
3. **Clientes**: Cliente com queda > `percent_queda_cliente_minimo%`
4. **SKUs**: SKU com queda > `percent_queda_sku_minimo%`

### Comportamento

- **Se gap_total <= 0**: Não há causas negativas → retorna vazio com mensagem
- **Se não há dados**: Retorna estrutura vazia
- **Resumo de causas**: Gera resumo em linguagem natural baseado nas causas críticas detectadas

## Integração

O `causas_detector` é chamado automaticamente pelo `orquestrador_dw.py` quando:
- `intent_spec.tipo == "meta"` ou `"analise_meta_detalhada"`
- `atingimento_medio < 100%` ou `realizado_total < meta_total`

## Estrutura de Retorno

### `causas["rotas"]`
Lista de rotas críticas, cada uma com:
- `rota_id`, `rota_nome`
- `supervisor_id`, `supervisor_nome`
- `meta_rota_mes`, `realizado_rota_mes`
- `gap_rota`, `percent_gap_do_total`

### `causas["vendedores"]`
Lista de vendedores críticos, cada um com:
- `vendedor_id`, `vendedor_nome`
- `supervisor_id`, `supervisor_nome`
- `rota_id`, `rota_nome`
- `meta_vendedor_mes`, `realizado_vendedor_mes`
- `gap_vendedor`, `atingimento_vendedor`

### `causas["clientes"]`
Lista de clientes críticos, cada um com:
- `cliente_id`, `cliente_nome`
- `faturamento_mes_atual`, `faturamento_mes_anterior`
- `variacao_abs`, `variacao_pct`

### `causas["skus"]`
Lista de SKUs críticos, cada um com:
- `sku_id`, `sku_nome`
- `faturamento_mes_atual`, `faturamento_mes_anterior`
- `variacao_abs`, `variacao_pct`

### `resumo_causas`
Lista de strings em linguagem natural descrevendo as causas principais.

