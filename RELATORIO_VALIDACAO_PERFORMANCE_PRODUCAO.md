# Relatório de Validação de Performance - Produção

**Data:** 2025-11-25  
**Ambiente:** Produção (Cloud Run)  
**Versão:** v-prod-perf

## Status da Validação

### ⚠️ Problema Identificado: Timeout de 32s

O serviço está retornando `503 Service Unavailable` após aproximadamente 32 segundos de processamento. Isso impede a validação completa de performance e cache.

**Observações:**
- Query DW está executando (1234 clientes únicos detectados)
- Logs `[PERF_ASK]` sendo gerados
- Timeout ocorre antes da conclusão (possivelmente durante LLM ou montagem da resposta)

**Tempos observados:**
- Timeout: ~32-36 segundos
- Query DW: Executando (4-5 segundos baseado nos logs)
- LLM: Não completou (timeout antes)

**Recomendação:** Investigar e corrigir timeout antes de validar performance completa.

## Validações Realizadas

### 1. Script de Teste de Performance

**Script criado:** `scripts/test_api_ask_q1_perf.py`

**Funcionalidades:**
- Executa duas chamadas consecutivas à Q1
- Mede tempo de resposta
- Valida headers de compressão
- Verifica cache hit na segunda chamada
- Gera relatório JSON com resultados

**Status:** ✅ Script criado e pronto para uso

### 2. Headers de Compressão

**Validação pendente:** Requer resposta HTTP 200 para verificar headers

**Headers esperados:**
- `Content-Encoding: gzip`
- `Cache-Control: public, max-age=600` (se aplicável)
- `X-Cache-Hit: true` (na segunda chamada, se implementado)

**Status:** ⏳ Aguardando estabilização do serviço

### 3. Logs de Performance

Logs `[PERF_ASK]` sendo gerados:
```
[PERF_ASK] Iniciando processamento de pergunta
```

**Logs esperados (quando serviço estabilizar):**
- `[PERF_Q1] INTENT_SPEC took X.XX ms`
- `[PERF_Q1] DW_QUERY took X.XX ms`
- `[PERF_Q1] POST_PROCESSOR took X.XX ms`
- `[PERF_Q1] LLM_RESPONSE took X.XX ms`
- `[PERF_Q1] TOTAL_HANDLER took X.XX ms`
- `[PERF_Q1] ✅ Retornando resposta do cache` (na segunda chamada)

**Status:** ✅ Logs instrumentados, aguardando execução completa

## Métricas Esperadas

### Primeira Chamada (sem cache)

| Métrica | Meta | Status |
|---------|------|--------|
| Tempo total | 12-21s | ⏳ Pendente |
| DW Query | 5-8s | ⏳ Pendente |
| LLM Resposta | 4-8s | ⏳ Pendente |
| Payload comprimido | ~150-250 KB | ⏳ Pendente |
| Gzip ativo | Sim | ⏳ Pendente |

### Segunda Chamada (cache hit)

| Métrica | Meta | Status |
|---------|------|--------|
| Tempo total | < 100ms | ⏳ Pendente |
| Cache hit | true | ⏳ Pendente |
| Log cache | `[PERF_Q1] ✅ Retornando resposta do cache` | ⏳ Pendente |

## Validações Pendentes

### 1. Teste de Latência Real

**Comando:**
```bash
python3 scripts/test_api_ask_q1_perf.py --prod
```

**Validações:**
- [ ] Primeira chamada: 12-21s
- [ ] Segunda chamada: < 100ms
- [ ] Gzip ativo em ambas
- [ ] Cache hit na segunda

**Status:** ⏳ Aguardando estabilização do serviço

### 2. Validação de Headers

**Comando:**
```bash
curl -I -X POST "https://dipam-ai-backend-642830139828.us-central1.run.app/ask" \
  -H "Content-Type: application/json" \
  -H "Accept-Encoding: gzip" \
  -d '{"pergunta": "Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?", "papel": "diretor"}'
```

**Status:** ⏳ Aguardando estabilização do serviço

### 3. Monitoramento de Logs

**Comando:**
```bash
gcloud run services logs read dipam-ai-backend \
  --region us-central1 \
  --limit 200 \
  --format="value(textPayload)" | \
  grep -E "\[PERF_Q1\]|Cache"
```

**Status:** ⏳ Aguardando execução completa de requisições

## Observações Técnicas

### Timeout de 32s Observado

Algumas requisições podem estar atingindo timeout antes de completar. Com o timeout configurado para 300s no Cloud Run, isso deve ser resolvido após estabilização.

### Reinicializações Frequentes

O serviço está reiniciando frequentemente, possivelmente devido a:
- Timeout durante processamento
- Cold start do Cloud Run
- Recursos insuficientes

**Recomendação:** Monitorar métricas do Cloud Run e considerar:
- Aumentar `min-instances` para 2
- Aumentar `memory` se necessário
- Verificar se há memory leaks ou queries muito lentas

## Próximos Passos

1. **Aguardar estabilização** (10-15 minutos após último deploy)
2. **Executar teste de performance:**
   ```bash
   python3 scripts/test_api_ask_q1_perf.py --prod
   ```
3. **Validar headers de compressão**
4. **Monitorar logs** para métricas `[PERF_Q1]` completas
5. **Verificar cache hit** na segunda chamada

## Conclusão

✅ **Scripts de validação criados**  
✅ **Logs de performance instrumentados**  
⏳ **Validações de performance pendentes** (aguardando estabilização)

**Status Geral:** ⚠️ **AGUARDANDO ESTABILIZAÇÃO PARA VALIDAÇÃO COMPLETA**

**Recomendação:** Executar validações novamente após 10-15 minutos de estabilização do serviço.

