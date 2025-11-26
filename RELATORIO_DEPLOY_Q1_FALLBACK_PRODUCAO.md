# Relatório de Deploy - Q1 Fallback em Produção

**Data:** 2025-11-26 01:03:51 UTC  
**Tag da Imagem:** `gcr.io/trivihair/dipam-ai-backend:v-prod-q1-fallback`  
**Revision Cloud Run:** `dipam-ai-backend-00146-jt6`  
**URL do Serviço:** `https://dipam-ai-backend-642830139828.us-central1.run.app`  
**Status:** ⚠️ **DEPLOY CONCLUÍDO - FALLBACK NÃO ATIVADO**

## 📋 Resumo Executivo

O deploy da versão `v-prod-q1-fallback` foi concluído com sucesso. A imagem foi construída e publicada no Cloud Run. No entanto, durante o smoke test, a query Q1 ainda está travando antes do fallback ser ativado, resultando em timeout de infra (503) após ~40 segundos.

## 🔧 Informações do Deploy

### Build
- **Build ID:** `3ab13b0a-497b-4058-81e9-fa7d0c0f3b07`
- **Duração:** 8m17s
- **Status:** SUCCESS
- **Digest:** `sha256:d809c7954b37dc0fbc79c160a292ffac59ff34a471c00fbe0b46dcf9c12bbbc4`

### Deploy Cloud Run
- **Revision:** `dipam-ai-backend-00146-jt6`
- **Região:** `us-central1`
- **Status:** Deployed and serving 100% of traffic
- **Health Check:** ✅ Passou
- **CORS Check:** ✅ Funcionando

## 🧪 Smoke Test da Q1

### Teste Executado

```bash
curl -i -X POST "https://dipam-ai-backend-642830139828.us-central1.run.app/ask" \
  -H "Content-Type: application/json" \
  -H "Origin: https://dipam.smartiasolutions.com.br" \
  -d '{
    "pergunta": "Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?",
    "papel": "diretor"
  }'
```

### Resultado

- **Status HTTP:** `503 Service Unavailable`
- **Tempo de Resposta:** ~40 segundos
- **Erro:** Timeout de infra (Google Frontend), não timeout controlado da aplicação

### Análise

**Logs capturados:**
```
2025-11-26 01:17:46 INFO:src.api.main:[PERF_ASK] Iniciando processamento de pergunta (timeout: 18s)
2025-11-26 01:17:47 INFO:src.agent.handler_dw_refatorado:[PERF_STEP] START_GROQ_INTENT - query_id=Q1
2025-11-26 01:17:47 INFO:src.api.groq_client:[PERF_STEP] GROQ_CALL_END - 0.49s
2025-11-26 01:17:47 INFO:src.agent.handler_dw_refatorado:[PERF_STEP] END_GROQ_INTENT - query_id=Q1, duration=493.00ms
2025-11-26 01:17:47 INFO:src.agent.handler_dw_refatorado:[PERF_STEP] START_DW_QUERY - query_id=Q1
2025-11-26 01:17:47 INFO:src.dw.query_executor:[PERF_STEP] START_DW_QUERY - query_id=Q1, dias=60, data_referencia=2025-11-30
```

**Observações:**
- ✅ `START_DW_QUERY` aparece
- ❌ `END_DW_QUERY` **NÃO aparece**
- ❌ `[PERF_Q1] FallbackParcial` **NÃO aparece**
- ❌ `DW_MODE: LIGHT` **NÃO aparece**

**Conclusão:**
A query DW está travando de forma que o `ThreadPoolExecutor` não consegue cancelar ou o timeout de 8s não está sendo respeitado. O processo é morto pela infra antes do fallback ser ativado.

## 📊 Validações

| Validação | Esperado | Resultado | Status |
|-----------|----------|-----------|--------|
| Deploy concluído | Sim | ✅ Sim | ✅ |
| Health check | 200 OK | ✅ 200 OK | ✅ |
| CORS funcionando | Sim | ✅ Sim | ✅ |
| Q1 retorna em ≤ 10s | Sim | ❌ 503 após ~40s | ❌ |
| Status "ok" ou "partial" | Sim | ❌ 503 (timeout infra) | ❌ |
| Fallback ativado | Quando > 8s | ❌ Não ativado | ❌ |
| Logs [PERF_Q1] FallbackParcial | Presentes | ❌ Não aparecem | ❌ |
| Tabela com registros | ≥ 50 | ❌ N/A (timeout) | ❌ |

## 🔍 Análise de Problema

### Causa Raiz Identificada

O fallback não está sendo ativado porque:

1. **ThreadPoolExecutor não cancela queries SQLite bloqueadas:**
   - O `future.cancel()` não interrompe queries SQLite em execução
   - A query continua rodando mesmo após o timeout de 8s
   - O processo é morto pela infra após ~40s

2. **Timeout de 8s pode ser muito curto:**
   - A query pode estar demorando entre 8-18s
   - O fallback deveria ativar, mas não está sendo detectado

3. **Possível problema com sessão SQLAlchemy em thread:**
   - Sessões SQLAlchemy podem não ser thread-safe
   - A query pode estar travando a sessão principal

### Próximos Passos Recomendados

1. **Reduzir timeout de fallback para 5s:**
   - Ativar fallback mais cedo para garantir resposta em ≤ 10s

2. **Implementar timeout no nível SQL:**
   - Usar `PRAGMA busy_timeout` no SQLite
   - Configurar `statement_timeout` no PostgreSQL

3. **Melhorar cancelamento de query:**
   - Usar `signal.SIGALRM` para forçar interrupção
   - Implementar timeout no nível do driver SQLAlchemy

4. **Adicionar mais logs:**
   - Logar tentativa de cancelamento
   - Logar quando fallback é ativado (mesmo que falhe)

## 📝 Logs Relevantes

### Logs de Performance

```
[PERF_ASK] Iniciando processamento de pergunta (timeout: 18s)
[PERF_STEP] START_GROQ_INTENT - query_id=Q1
[PERF_STEP] GROQ_CALL_END - 0.49s
[PERF_STEP] END_GROQ_INTENT - query_id=Q1, duration=493.00ms
[PERF_STEP] START_DW_QUERY - query_id=Q1, dias=60, data_referencia=2025-11-30
```

**Nota:** Não há logs de `END_DW_QUERY`, `FallbackParcial` ou `DW_MODE: LIGHT`.

### Logs de Erro

Nenhum erro estruturado foi encontrado nos logs. O timeout ocorre na camada de infra (Google Frontend), não na aplicação.

## ✅ Conclusão

**Status do Deploy:** ✅ **CONCLUÍDO COM SUCESSO**

**Status Funcional:** ⚠️ **FALLBACK NÃO ESTÁ SENDO ATIVADO**

**Recomendação Imediata:**
- Investigar por que o `ThreadPoolExecutor` não está cancelando a query
- Reduzir timeout de fallback para 5s
- Implementar timeout no nível SQL (PRAGMA/statement_timeout)
- Adicionar mais logs para debugging

**Para Demo:**
- O sistema ainda não está pronto para apresentação executiva
- A query Q1 continua travando e retornando 503
- É necessário corrigir o mecanismo de fallback antes da demo

---

**Próxima Ação:** Investigar e corrigir o mecanismo de cancelamento de query no `query_executor.py`.

