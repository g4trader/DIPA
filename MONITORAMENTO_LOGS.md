# Monitoramento de Logs - DIPAM AI Backend

**Data:** 2025-11-25  
**Ambiente:** Cloud Run (Produção)

## Logs de Performance `[PERF_STEP]`

Todos os logs de performance seguem o padrão:
```
[PERF_STEP] <ETAPA> - query_id=<ID>, status=<STATUS>, duration=<MS>ms, ...
```

### Etapas Monitoradas

1. **GROQ Intent (Primeira chamada LLM):**
   - `[PERF_STEP] START_GROQ_INTENT - query_id=Q1`
   - `[PERF_STEP] END_GROQ_INTENT - query_id=Q1, duration=<MS>ms`

2. **DW Query:**
   - `[PERF_STEP] START_DW_QUERY - query_id=Q1, dias=<N>, data_referencia=<DATE>`
   - `[PERF_STEP] END_DW_QUERY - query_id=Q1, status=<ok|timeout|error>, duration=<MS>ms, records=<N>`

3. **Post Processor:**
   - `[PERF_STEP] START_POST_PROCESSOR - query_id=Q1`
   - `[PERF_STEP] END_POST_PROCESSOR - query_id=Q1, duration=<MS>ms`

4. **GROQ Executive (Segunda chamada LLM):**
   - `[PERF_STEP] START_GROQ_EXECUTIVE - query_id=Q1`
   - `[PERF_STEP] END_GROQ_EXECUTIVE - query_id=Q1, duration=<MS>ms`

5. **Assembly:**
   - `[PERF_STEP] START_ASSEMBLY - query_id=Q1`
   - `[PERF_STEP] END_ASSEMBLY - query_id=Q1, duration=<MS>ms`

6. **Response Mapping:**
   - `[PERF_STEP] START_MAP_RESPONSE`
   - `[PERF_STEP] END_MAP_RESPONSE - duration=<MS>ms`

7. **Response Creation:**
   - `[PERF_STEP] START_CREATE_RESPONSE`
   - `[PERF_STEP] END_CREATE_RESPONSE - duration=<MS>ms`

8. **Serialization:**
   - `[PERF_STEP] START_SERIALIZE_RESPONSE`
   - `[PERF_STEP] END_SERIALIZE_RESPONSE - duration=<MS>ms`
   - `[PERF_STEP] RETURNING_RESPONSE - total_duration=<MS>ms`

## Consultas Úteis no Cloud Logging

### 1. Filtrar Logs de Performance

**Todos os logs [PERF_STEP]:**
```
resource.type="cloud_run_revision"
resource.labels.service_name="dipam-ai-backend"
textPayload=~"\[PERF_STEP\]"
```

**Apenas END_DW_QUERY:**
```
resource.type="cloud_run_revision"
resource.labels.service_name="dipam-ai-backend"
textPayload=~"\[PERF_STEP\] END_DW_QUERY"
```

**Apenas timeouts:**
```
resource.type="cloud_run_revision"
resource.labels.service_name="dipam-ai-backend"
textPayload=~"\[PERF_STEP\] END_DW_QUERY.*status=timeout"
```

### 2. Identificar Frequência de DW_TIMEOUT

**Contar timeouts nas últimas 24h:**
```
resource.type="cloud_run_revision"
resource.labels.service_name="dipam-ai-backend"
textPayload=~"\[PERF_STEP\] END_DW_QUERY.*status=timeout"
timestamp>="2025-11-25T00:00:00Z"
```

**Ver detalhes de timeouts:**
```
resource.type="cloud_run_revision"
resource.labels.service_name="dipam-ai-backend"
textPayload=~"\[PERF_STEP\] END_DW_QUERY.*status=timeout"
```

### 3. Distribuição de Tempos de Query Q1

**Todas as queries Q1 (sucesso):**
```
resource.type="cloud_run_revision"
resource.labels.service_name="dipam-ai-backend"
textPayload=~"\[PERF_STEP\] END_DW_QUERY.*query_id=Q1.*status=ok"
```

**Extrair duration_ms:**
Os logs incluem `duration=<MS>ms` que pode ser extraído para análise.

### 4. Verificar Ausência de END_DW_QUERY

**START sem END correspondente (últimas 10 min):**
```
resource.type="cloud_run_revision"
resource.labels.service_name="dipam-ai-backend"
textPayload=~"\[PERF_STEP\] START_DW_QUERY"
timestamp>="2025-11-25T20:00:00Z"
```

**⚠️ Se houver START sem END, pode indicar:**
- Query travando antes do timeout
- Erro não capturado
- Timeout intermediário (Google Frontend)

## Alertas Recomendados

### Alerta 1: Ausência de END_DW_QUERY

**Condição:**
- START_DW_QUERY sem END_DW_QUERY correspondente em 10 minutos

**Query:**
```
resource.type="cloud_run_revision"
resource.labels.service_name="dipam-ai-backend"
textPayload=~"\[PERF_STEP\] START_DW_QUERY"
```

**Ação:**
- Notificar time de engenharia
- Verificar logs completos da requisição

### Alerta 2: Taxa Alta de Timeout

**Condição:**
- Mais de 5% das queries Q1 retornando timeout nas últimas 24h

**Query:**
```
resource.type="cloud_run_revision"
resource.labels.service_name="dipam-ai-backend"
textPayload=~"\[PERF_STEP\] END_DW_QUERY.*status=timeout"
```

**Ação:**
- Investigar performance da query
- Considerar otimização ou aumento de timeout

### Alerta 3: Tempo Médio de Query > 15s

**Condição:**
- Tempo médio de END_DW_QUERY > 15000ms nas últimas 24h

**Ação:**
- Revisar índices do banco
- Considerar otimização da query

## Comandos Úteis via gcloud

### Ver logs recentes de performance

```bash
gcloud run services logs read dipam-ai-backend \
  --region us-central1 \
  --limit 500 \
  --format="value(timestamp,textPayload)" | \
  grep -E "\[PERF_STEP\]"
```

### Ver apenas END_DW_QUERY

```bash
gcloud run services logs read dipam-ai-backend \
  --region us-central1 \
  --limit 1000 \
  --format="value(timestamp,textPayload)" | \
  grep "\[PERF_STEP\] END_DW_QUERY"
```

### Ver timeouts

```bash
gcloud run services logs read dipam-ai-backend \
  --region us-central1 \
  --limit 1000 \
  --format="value(timestamp,textPayload)" | \
  grep "status=timeout"
```

### Ver logs de uma requisição específica (últimas 2h)

```bash
gcloud run services logs read dipam-ai-backend \
  --region us-central1 \
  --limit 2000 \
  --format="value(timestamp,textPayload)" | \
  grep -A 20 "\[PERF_ASK\] Iniciando"
```

## Métricas a Monitorar

1. **Taxa de Sucesso de Queries Q1:**
   - `status=ok` / total de queries Q1
   - Meta: > 95%

2. **Tempo Médio de Resposta Q1:**
   - Média de `duration_ms` de `END_DW_QUERY` com `status=ok`
   - Meta: < 10000ms (10s)

3. **Taxa de Timeout:**
   - `status=timeout` / total de queries Q1
   - Meta: < 5%

4. **Tempo Total de /ask:**
   - `[PERF_ASK] Processamento completo: <MS>ms`
   - Meta: < 21000ms (21s) sem cache, < 100ms com cache

## Dashboard Recomendado

Criar dashboard no Cloud Monitoring com:

1. **Gráfico de Tempo de Query Q1:**
   - Linha do tempo mostrando `duration_ms` ao longo do dia
   - Separar por `status` (ok, timeout, error)

2. **Taxa de Sucesso:**
   - Gauge mostrando % de `status=ok`

3. **Distribuição de Tempos:**
   - Histograma de `duration_ms`

4. **Alertas Ativos:**
   - Lista de alertas disparados nas últimas 24h

---

**Status:** 📊 **DOCUMENTAÇÃO COMPLETA - PRONTO PARA CONFIGURAR ALERTAS**

