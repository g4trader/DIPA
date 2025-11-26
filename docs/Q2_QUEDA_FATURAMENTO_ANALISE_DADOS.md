# Análise de Dados - Q2: Queda de Faturamento (Set/25 x Out/25)

## Resumo Executivo

**Data da análise:** 2025-11-26  
**Períodos analisados:**
- Setembro 2025: 2025-09-01 a 2025-09-30
- Outubro 2025: 2025-10-01 a 2025-10-31

## Estatísticas Gerais

### Volume de Dados

- **Total de clientes ativos com faturamento em set/25:** 4.061 clientes
- **Total de clientes com queda de faturamento (set → out/25):** 2.326 clientes
- **Taxa de queda:** 57,3% dos clientes que compraram em setembro tiveram queda em outubro

### Conclusão Inicial

✅ **Os dados suportam bem a análise Q2.**  
Há um volume significativo de clientes (2.326) com queda de faturamento, representando mais da metade dos clientes que compraram em setembro.

## Top 10 Clientes por Queda Absoluta (R$)

| # | Cliente ID | Nome | Queda Absoluta | Queda % |
|---|------------|------|----------------|---------|
| 1 | 3318 | ATACADAO DISTR COM IND LTDA LJ2 | R$ 843.012,12 | 22,90% |
| 2 | 2366 | VIEZZER & CIA LTDA | R$ 528.601,29 | 73,13% |
| 3 | 462 | SDB COMERCIO DE ALIMENTOS LTDA | R$ 441.436,41 | 87,58% |
| 4 | 3378 | PEDRALLI & PEDRALLI SUPERMERCADO LTDA | R$ 342.961,95 | 59,77% |
| 5 | 1476 | NW DISTRIBUIDORA DE BEBIDAS LTDA EPP | R$ 340.144,74 | 100,00% |
| 6 | 573 | SDB COMERCIO DE ALIMENTOS LTDA | R$ 309.213,12 | 67,89% |
| 7 | 5468 | SDB COMERCIO DE ALIMENTOS LTDA | R$ 299.800,80 | 98,27% |
| 8 | 3381 | SDB COMERCIO DE ALIMENTOS LTDA | R$ 261.725,97 | 65,99% |
| 9 | 561 | MERCADO J. DE CONTO LTDA | R$ 235.762,14 | 91,25% |
| 10 | 5582 | SUPERMERCADO DO PAULINHO LTDA S T | R$ 208.736,97 | 71,12% |

**Observações:**
- Maior queda absoluta: R$ 843.012,12 (ATACADAO DISTR COM IND LTDA LJ2)
- Vários clientes da rede SDB COMERCIO DE ALIMENTOS LTDA aparecem no top 10
- Quedas percentuais variam de 22,90% a 100% (cliente que parou de comprar)

## Top 10 Clientes por Queda Percentual

**Filtro aplicado:** Faturamento em set/25 >= R$ 200,00 (para evitar % absurdos)

| # | Cliente ID | Nome | Set/25 | Out/25 | Queda % |
|---|------------|------|--------|--------|---------|
| 1 | 1088 | FRANCIELI FERNANDA SINGESKI | R$ 910,32 | R$ 0,00 | 100,00% |
| 2 | 1193 | CAMILA PALINSKI | R$ 326,16 | R$ 0,00 | 100,00% |
| 3 | 2657 | EVERTON CARLOS PERES | R$ 549,18 | R$ 0,00 | 100,00% |
| 4 | 2942 | RPJ INDUSTRIA E COMERCIO DE ALIMENTOS LT | R$ 1.401,24 | R$ 0,00 | 100,00% |
| 5 | 3098 | MARISA RODRIGUES | R$ 339,39 | R$ 0,00 | 100,00% |
| 6 | 3456 | LUIS CLAUDIOMIR DE AVILA & CIA LTDA EPP | R$ 5.557,62 | R$ 0,00 | 100,00% |
| 7 | 3554 | INES CAUMO | R$ 2.189,64 | R$ 0,00 | 100,00% |
| 8 | 3785 | EVERTON SCARTEZZINI ABEG | R$ 690,54 | R$ 0,00 | 100,00% |
| 9 | 5056 | MERCADO SCHUMACHER LTDA | R$ 1.715,55 | R$ 0,00 | 100,00% |
| 10 | 5391 | MERCADO E ACOUGUE VEIGA LTDA | R$ 488,91 | R$ 0,00 | 100,00% |

**Observações:**
- Muitos clientes com 100% de queda (pararam de comprar completamente)
- Alguns clientes com faturamento significativo em setembro (ex.: R$ 5.557,62) pararam completamente em outubro

## Análise de Distribuição

### Rotas Mais Afetadas (Top 5 Clientes)

- **ROTA 113:** 2 clientes
- **ROTA 21:** 1 cliente
- **ROTA 04:** 1 cliente
- **ROTA 06:** 1 cliente

**Conclusão:** A queda está distribuída entre várias rotas, não há concentração extrema em uma única rota/vendedor.

## Limitações Identificadas

1. **Clientes com 100% de queda:** Muitos clientes pararam completamente de comprar. Isso pode indicar:
   - Mudança de fornecedor
   - Fechamento temporário/permanente
   - Sazonalidade específica

2. **Faturamento negativo em outubro:** Alguns cálculos mostram valores negativos, o que pode indicar:
   - Devoluções/estornos
   - Ajustes contábeis
   - Necessidade de revisar a lógica de cálculo

3. **Concentração em redes:** Vários clientes da mesma rede (SDB COMERCIO DE ALIMENTOS LTDA) aparecem no top 10, o que pode indicar:
   - Mudança de estratégia da rede
   - Negociação centralizada
   - Oportunidade de ação comercial coordenada

## Recomendações para Implementação

1. **Filtros mínimos sugeridos:**
   - `min_faturamento_mes_anterior: 500.0` (evita casos muito pequenos)
   - `min_queda_percentual: 10.0` (foca em quedas relevantes)

2. **Ordenação:**
   - Priorizar queda absoluta (R$) para impacto financeiro
   - Usar queda percentual como desempate

3. **Agrupamento por rede:**
   - Considerar agrupar clientes da mesma rede para análise executiva
   - Identificar padrões de queda por rede/segmento

## Conclusão

✅ **A pergunta "Quais os clientes com maior queda de faturamento de setembro 2025 x outubro 2025?" é bem respondida pelos dados.**

- Volume significativo de casos (2.326 clientes)
- Distribuição entre várias rotas
- Quedas relevantes tanto em valor absoluto quanto percentual
- Dados suficientes para análise executiva e plano de ação

**Próximos passos:**
1. Implementar query DW genérica
2. Criar fluxo de orquestração
3. Integrar com LLM para resposta executiva

