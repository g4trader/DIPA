# Mapeamento de Performance - Q1 (Clientes sem Compra)

## Objetivo
Identificar gargalos de performance na consulta Q1 para otimização.

## Métricas Observadas em Produção (DevTools)

### Requisições HTTP
- **Total de requests**: 12
- **Transfer size**: 718 kB
- **Resource size**: 1.6 MB
- **DOMContentLoaded**: ~900 ms
- **Load**: ~958 ms
- **Finish**: ~32 s ⚠️

### Análise
O tempo de "Finish" de 32 segundos indica que há requisições longas mantendo a aba ativa. Provavelmente:
- A requisição `/ask` está demorando ~25-30 segundos
- Possíveis chamadas adicionais a `/metrics` ou outras rotas auxiliares

## Fluxo Atual da Q1

### 1. Endpoint `/ask` (FastAPI)
- **Arquivo**: `src/api/main.py:1359`
- **Fluxo**:
  1. Recebe pergunta do usuário
  2. Chama `processar_pergunta_com_dw()`
  3. Retorna `AskResponse`

### 2. Handler Refatorado
- **Arquivo**: `src/agent/handler_dw_refatorado.py:39`
- **Fluxo sequencial**:
  1. **LLM IntentSpec** (~2-3s): `gerar_intent_spec_via_llm()`
  2. **DW Query** (~5-8s): `executar_intent_spec()` → `get_clientes_sem_compra_ha_dias()`
  3. **Pós-processador** (~1-2s): `processar_resposta()`
  4. **LLM Resposta Executiva** (~8-15s): `gerar_resposta_executiva_com_dados_dw()` → GROQ

### 3. Query DW (Q1)
- **Arquivo**: `src/dw/queries.py:80`
- **Função**: `get_clientes_sem_compra_ha_dias()`
- **Decorators**:
  - `@performance_guard(timeout_seconds=12.0)`
  - `@query_cache(ttl_seconds=300, query_id="Q1")`
  - `@profile_query("Q1")`
- **Tempo estimado**: 5-8 segundos

### 4. LLM Resposta Executiva
- **Arquivo**: `src/llm_integration_intent.py:334`
- **Função**: `gerar_resposta_executiva_com_dados_dw()`
- **Chamada GROQ**: ~8-15 segundos
- **Payload enviado**: Dados condensados (top 20 registros + estatísticas)

## Gargalos Identificados

### 1. Execução Sequencial
- **Problema**: DW e LLM executam sequencialmente
- **Impacto**: Tempo total = DW (5-8s) + LLM (8-15s) = 13-23s
- **Oportunidade**: Paralelizar quando possível

### 2. Payload Grande para LLM
- **Problema**: Envia tabela completa de clientes para GROQ
- **Impacto**: Aumenta tempo de resposta do GROQ
- **Oportunidade**: Enviar apenas resumo estatístico (já parcialmente implementado)

### 3. Falta de Cache Eficiente
- **Problema**: Cache existe mas pode não estar sendo usado efetivamente
- **Impacto**: Recalcula Q1 mesmo quando dados não mudaram
- **Oportunidade**: Cache mais agressivo para Q1 (10-30 min TTL)

### 4. Frontend Bloqueante
- **Problema**: Frontend espera resposta completa antes de renderizar
- **Impacto**: Usuário vê tela vazia por 30+ segundos
- **Oportunidade**: Renderização progressiva (Big Number → Resumo → Tabela)

## Próximos Passos

1. ✅ Instrumentar logs de performance por etapa
2. ⏳ Paralelizar DW + LLM (quando possível)
3. ⏳ Otimizar payload para LLM (apenas estatísticas)
4. ⏳ Implementar cache mais agressivo
5. ⏳ Renderização progressiva no frontend

