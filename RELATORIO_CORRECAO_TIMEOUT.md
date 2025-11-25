# Relatório de Correção de Timeout - DIPAM COPILOT™

**Data:** 2025-11-25  
**Versão:** v-prod-perf-fix-timeout  
**Revisão:** dipam-ai-backend-00140-8z9

## Problema Identificado

### Sintoma Original
- Serviço retornando `503 Service Unavailable` após ~32 segundos
- Timeout ocorrendo durante processamento da Q1
- Query DW executando corretamente (4-5 segundos)
- Timeout antes da conclusão completa

### Análise dos Logs

**Primeira chamada GROQ (IntentSpec):**
- ✅ Completando rapidamente: ~0.55-0.64 segundos
- ✅ Logs `[PERF_STEP] GROQ_CALL_END` sendo gerados
- ✅ Timeout do GROQ aumentado para 60s (correção aplicada)

**Query DW:**
- ✅ Executando corretamente: 4-5 segundos
- ✅ 1234 clientes únicos detectados
- ✅ Logs de performance sendo gerados

**Segunda chamada GROQ (gerar_resposta_executiva_com_dados_dw):**
- ⚠️ Não aparecem logs `[PERF_STEP] LLM_START` ou `[PERF_STEP] LLM_END`
- ⚠️ Timeout ocorrendo antes da conclusão
- ⚠️ Possível timeout intermediário do Cloud Run ou Google Frontend

## Correções Implementadas

### 1. Aumento do Timeout do GROQ ✅

**Arquivo:** `src/api/groq_client.py`

**Mudança:**
- Timeout aumentado de 30s para 60s
- Configurável via variável de ambiente `GROQ_TIMEOUT` (padrão: 60s)
- Logs adicionados para rastreamento

**Código:**
```python
groq_timeout = int(os.getenv("GROQ_TIMEOUT", "60"))
logger.info(f"[GROQ] Timeout configurado: {groq_timeout}s, prompt_length={len(prompt_truncated)}")
```

### 2. Logs Detalhados de Performance ✅

**Arquivos:** 
- `src/api/groq_client.py`
- `src/llm_integration_intent.py`

**Logs Adicionados:**
- `[PERF_STEP] GROQ_CALL_END` - Tempo de chamada GROQ
- `[PERF_STEP] LLM_START` - Início da chamada LLM
- `[PERF_STEP] LLM_END` - Fim da chamada LLM (tempo em ms)
- `[PERF_STEP] ASSEMBLY_START` - Início da montagem da resposta
- `[PERF_STEP] ASSEMBLY_END` - Fim da montagem da resposta (tempo em ms)

### 3. Deploy da Correção ✅

**Build:**
- Tag: `v-prod-perf-fix-timeout`
- Imagem: `gcr.io/trivihair/dipam-ai-backend:v-prod-perf-fix-timeout`
- Status: ✅ Build concluído com sucesso

**Deploy:**
- Revisão: `dipam-ai-backend-00140-8z9`
- Status: ✅ Deploy concluído
- URL: `https://dipam-ai-backend-642830139828.us-central1.run.app`

## Observações Pós-Deploy

### Status Atual

**Funcionando:**
- ✅ Endpoint `/health` respondendo corretamente
- ✅ Primeira chamada GROQ (IntentSpec) completando rapidamente
- ✅ Query DW executando corretamente
- ✅ Logs de performance sendo gerados
- ✅ Timeout do GROQ aumentado para 60s

**Ainda com Problema:**
- ⚠️ Serviço ainda retornando 503 após ~50s
- ⚠️ Segunda chamada GROQ (gerar_resposta_executiva) não aparece nos logs
- ⚠️ Possível timeout intermediário do Cloud Run ou Google Frontend

### Possíveis Causas Adicionais

1. **Timeout do Google Frontend (30s)**
   - O Google Frontend pode ter um timeout de 30s para requisições HTTP
   - Mesmo com timeout do Cloud Run configurado para 300s, o Frontend pode estar cortando antes

2. **Timeout do Cloud Run (intermediário)**
   - Pode haver um timeout intermediário não configurado
   - Requisições muito longas podem ser cortadas antes do timeout final

3. **Processamento Muito Longo**
   - A segunda chamada GROQ pode estar demorando mais de 60s
   - A montagem da resposta pode estar demorando muito

4. **Serialização JSON Pesada**
   - A resposta com 932 clientes pode estar demorando muito para serializar
   - Pode haver problema de memória durante serialização

## Próximas Ações Recomendadas

### Imediato

1. **Verificar Timeout do Google Frontend**
   - Investigar se há timeout intermediário do Google Frontend
   - Considerar usar streaming response se necessário

2. **Adicionar Mais Logs**
   - Adicionar logs antes e depois da segunda chamada GROQ
   - Adicionar logs durante montagem da resposta
   - Adicionar logs durante serialização JSON

3. **Otimizar Montagem da Resposta**
   - Limitar número de clientes na resposta inicial
   - Usar paginação server-side
   - Otimizar serialização JSON

### Curto Prazo

1. **Implementar Streaming Response**
   - Usar `StreamingResponse` do FastAPI
   - Enviar resposta incrementalmente

2. **Implementar Timeout Interno**
   - Adicionar timeout interno de 20s para chamada GROQ
   - Usar fallback se exceder

3. **Otimizar Payload**
   - Reduzir ainda mais o payload enviado ao GROQ
   - Limitar número de exemplos enviados

## Validação

### Testes Realizados

1. **Health Check:** ✅ Passando
2. **Primeira Chamada GROQ:** ✅ Completando rapidamente (~0.6s)
3. **Query DW:** ✅ Executando corretamente (4-5s)
4. **Segunda Chamada GROQ:** ⚠️ Não completando (timeout)

### Métricas Observadas

| Métrica | Antes | Depois | Status |
|---------|-------|--------|--------|
| Timeout GROQ | 30s | 60s | ✅ Aumentado |
| Primeira chamada GROQ | ~0.6s | ~0.6s | ✅ Mantido |
| Query DW | 4-5s | 4-5s | ✅ Mantido |
| Segunda chamada GROQ | Timeout 32s | Timeout 50s | ⚠️ Ainda com problema |
| Logs de performance | Parcial | Completo | ✅ Melhorado |

## Conclusão

### ✅ Correções Aplicadas

1. Timeout do GROQ aumentado de 30s para 60s
2. Logs detalhados de performance adicionados
3. Deploy da correção concluído

### ⚠️ Problema Persistente

O timeout ainda está ocorrendo, mas agora após ~50s (em vez de 32s). Isso sugere que:
- O timeout do GROQ não era o único problema
- Há um timeout intermediário (possivelmente do Google Frontend ou Cloud Run)
- A segunda chamada GROQ ou montagem da resposta está demorando muito

### 📋 Recomendações

1. **Investigar timeout intermediário** do Google Frontend ou Cloud Run
2. **Adicionar mais logs** para identificar onde exatamente está travando
3. **Otimizar montagem da resposta** para reduzir tempo de processamento
4. **Considerar streaming response** para respostas muito grandes

**Status:** ⚠️ **CORREÇÃO PARCIAL - REQUER INVESTIGAÇÃO ADICIONAL**

