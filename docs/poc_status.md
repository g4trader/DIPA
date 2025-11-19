# Status das 13 Perguntas da POC - DIPAM COPILOT™

## Resumo Executivo

- **Q1**: ✅ OK (clientes_sem_compra)
- **Q2**: ⚠️  Funcional mas com riscos (queda_faturamento)
- **Q3-Q13**: ❌ Requerem diagnóstico e correções

## Diagnóstico Detalhado

### Q1: Clientes sem compra há 60 dias
- **Intent esperado**: `clientes_sem_compra`
- **Status**: ✅ OK
- **Query DW**: `get_clientes_sem_compra_ha_dias` ✅
- **Narrativa**: `_format_clientes_sem_compra` ✅
- **Observações**: Funcionando corretamente

### Q2: Queda de faturamento 2025 x 2024
- **Intent esperado**: `queda_faturamento`
- **Status**: ⚠️  Funcional mas com riscos
- **Query DW**: `get_clientes_queda_faturamento_ano_contra_ano` ✅
- **Narrativa**: `_format_queda_faturamento` ✅
- **Observações**: Funciona mas pode melhorar estrutura

### Q3: Indústria com mais vendedores fora de meta (Outubro/25)
- **Intent esperado**: `meta_departamento`
- **Status**: ❓ Requer diagnóstico
- **Query DW**: `get_industrias_com_mais_vendedores_fora_meta` ✅
- **Narrativa**: `_format_meta_departamento` ✅
- **Observações**: Verificar se query está retornando dados corretos

### Q4: Rotas com melhor/pior desempenho em positivação Mars
- **Intent esperado**: `positivacao`
- **Status**: ❓ Requer diagnóstico
- **Query DW**: `get_rotas_positivacao_industria` ✅
- **Narrativa**: `_format_positivacao` ✅
- **Observações**: Verificar se dimensão "rota" está sendo detectada corretamente

### Q5: Itens com média mensal < 10 caixas
- **Intent esperado**: `vendas_baixas`
- **Status**: ❓ Requer diagnóstico
- **Query DW**: `get_itens_baixa_media_mensal` ✅
- **Narrativa**: `_format_vendas_baixas` ✅
- **Observações**: Verificar mapeamento de intent (pode estar como "mix" ao invés de "vendas_baixas")

### Q6: Clientes sem recompra de Snickers Duplo Chocolate
- **Intent esperado**: `recompra`
- **Status**: ❓ Requer diagnóstico
- **Query DW**: `get_clientes_sem_recompra_sku` ✅
- **Narrativa**: `_format_recompra` ✅
- **Observações**: Verificar se SKU está sendo extraído corretamente do IntentSpec

### Q7: Clientes equipe conveniência sem Red Bull Zero (Outubro)
- **Intent esperado**: `clientes_sem_item`
- **Status**: ❓ Requer diagnóstico
- **Query DW**: `get_clientes_segmento_sem_sku_no_periodo` ✅
- **Narrativa**: `_format_clientes_sem_item` ✅
- **Observações**: Verificar se segmento "conveniência" e SKU estão sendo detectados

### Q8: Clientes com 1 unidade AB Brasil (Outubro)
- **Intent esperado**: `clientes_sem_item`
- **Status**: ❓ Requer diagnóstico
- **Query DW**: `get_clientes_uma_unidade_industria_mes` ✅
- **Narrativa**: `_format_clientes_sem_item` ou genérica ⚠️
- **Observações**: Pode precisar de narrativa específica

### Q9-Q11: Positivação P12 (Snickers, M&Ms Choco, M&Ms Tubo)
- **Intent esperado**: `positivacao`
- **Status**: ❓ Requer diagnóstico
- **Query DW**: `get_clientes_sem_sku_no_periodo` ✅
- **Narrativa**: `_format_positivacao` ✅
- **Observações**: Verificar se período P12 está sendo mapeado corretamente

### Q12: Clientes com mix mínimo Nissin (Outubro)
- **Intent esperado**: `mix_nissin`
- **Status**: ❓ Requer diagnóstico
- **Query DW**: `get_clientes_mix_minimo_nissin_mes` ✅
- **Narrativa**: `_format_mix_nissin` ✅
- **Observações**: Verificar se lógica de mix mínimo está correta

### Q13: Rotas com pior desempenho mix mínimo Nissin (Outubro)
- **Intent esperado**: `mix_nissin`
- **Status**: ❓ Requer diagnóstico
- **Query DW**: `get_rotas_desempenho_mix_minimo_nissin_mes` ✅
- **Narrativa**: `_format_mix_nissin` ou genérica ⚠️
- **Observações**: Verificar se dimensão "rota" está sendo detectada

## Problemas Identificados

1. **Tratamento de Erro**: Verificar se todas as queries têm try/except adequado
2. **Mapeamento de Intent**: Algumas perguntas podem estar caindo em intents genéricas
3. **Narrativas Genéricas**: Q8 e Q13 podem precisar de narrativas específicas
4. **Rotas no TOP 10**: Problema conhecido - rotas aparecem como "—"

## Próximos Passos

1. ✅ Criar documento de status (este arquivo)
2. ⏳ Rodar diagnóstico completo com CLI de aceitação
3. ⏳ Corrigir tratamento de erro em todas as queries
4. ⏳ Adicionar narrativas específicas onde necessário
5. ⏳ Corrigir problema de rotas no TOP 10
6. ⏳ Validar todas as 13 perguntas

