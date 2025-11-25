# Análise de Raiz - Timeout Q1 em Produção

**Data:** 2025-11-25  
**Revisão:** dipam-ai-backend-00145-twd  
**Status:** 🔍 **ANALISADO**

## 🔍 Problema Identificado

### Sintomas

1. **Chamada ao `/ask` demora ~44s e retorna 503 Service Unavailable**
2. **Erro CORS no navegador:** "No 'Access-Control-Allow-Origin' header is present"
3. **Workers sendo mortos:** `Worker (pid:X) was sent SIGABRT!` a cada ~5 minutos

### Análise dos Logs

**Logs capturados:**
```
2025-11-25 23:15:10 INFO:src.agent.handler_dw_refatorado:[PERF_STEP] START_GROQ_INTENT - query_id=Q1
2025-11-25 23:15:10 INFO:src.api.groq_client:[PERF_STEP] GROQ_CALL_END - 0.47s
2025-11-25 23:15:10 INFO:src.agent.handler_dw_refatorado:[PERF_STEP] END_GROQ_INTENT - query_id=Q1, duration=479.00ms
2025-11-25 23:15:10 INFO:src.agent.handler_dw_refatorado:[PERF_STEP] START_DW_QUERY - query_id=Q1
2025-11-25 23:15:10 INFO:src.dw.query_executor:[PERF_STEP] START_DW_QUERY - query_id=Q1, dias=60, data_referencia=2025-11-30
2025-11-25 23:20:19 [2025-11-25 23:20:19 +0000] [1] [ERROR] Worker (pid:2) was sent SIGABRT!
```

### Ponto Exato do Problema

**Onde o fluxo desaparece:**
- ✅ `START_GROQ_INTENT` → aparece
- ✅ `END_GROQ_INTENT` → aparece (479ms)
- ✅ `START_DW_QUERY` → aparece
- ❌ `END_DW_QUERY` → **NUNCA aparece**

**Conclusão:**
A query DW está travando e nunca completa. O timeout de 20s configurado no `query_executor.py` não está sendo respeitado ou a query está demorando mais que isso.

### Causa Raiz

1. **Query DW muito lenta:** A query `get_clientes_sem_compra_ha_dias` está demorando > 20s e possivelmente > 5 minutos
2. **Timeout de infra:** Cloud Run/Gunicorn mata o worker após ~5 minutos (timeout configurado)
3. **503 sem CORS:** Quando a infra mata o worker, não há resposta da aplicação, então não há headers CORS
4. **Sem tratamento de timeout:** A aplicação não detecta o timeout antes da infra matar

### Evidências

- **Nenhum `END_DW_QUERY` nos logs:** A query nunca completa
- **Workers mortos a cada 5 minutos:** Timeout de infra sendo atingido
- **503 sem CORS:** Resposta vem da infra, não da aplicação
- **Nenhum `[ASK_ERROR_FATAL]`:** A aplicação não está tratando o timeout

## 🎯 Solução Proposta

1. **Timeout interno de aplicação:** Limitar todo o fluxo `/ask` a 18-20s
2. **Detectar timeout antes da infra:** Retornar erro estruturado com CORS
3. **Garantir CORS em todas as respostas:** Incluindo timeouts e erros
4. **Melhorar tratamento de timeout DW:** Garantir que o timeout de 20s seja respeitado

---

**Status:** ✅ **ANÁLISE COMPLETA - PRONTO PARA IMPLEMENTAÇÃO**

