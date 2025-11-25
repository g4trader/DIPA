# Checklist de Deploy em Produção - CORS + Timeout Query DW

**Data:** 2025-11-25  
**Versão:** v-prod-perf-cors-timeout  
**Branch:** main

## 1. Pré-Deploy ✅

- [x] Código validado e testado localmente
- [x] CORS testado via curl (OPTIONS e POST)
- [x] Timeout implementado e testado
- [x] Logging completo implementado
- [x] Commits pushados para `main`

## 2. Build e Deploy (Automático)

### Opção Recomendada: Script de Deploy

Use o script automatizado que faz build e deploy em um único comando:

```bash
./scripts/deploy_producao.sh [TAG]
```

**Exemplo:**
```bash
# Usa tag padrão: v-prod-perf-cors-timeout
./scripts/deploy_producao.sh

# Ou especifica tag customizada
./scripts/deploy_producao.sh v-prod-perf-cors-timeout-v2
```

**O que o script faz:**
1. ✅ Verifica se gcloud está instalado e autenticado
2. ✅ Solicita confirmação antes de fazer deploy
3. ✅ Faz build da imagem Docker
4. ✅ Faz deploy no Cloud Run
5. ✅ Valida pós-deploy (health check, CORS)

**Verificações:**
- [ ] Script executado com sucesso
- [ ] Build completa sem erros
- [ ] Deploy concluído sem erros
- [ ] Health check passou
- [ ] CORS funcionando

### Opção Manual: Comandos Individuais

Se preferir executar manualmente:

**Build:**
```bash
gcloud builds submit --tag gcr.io/trivihair/dipam-ai-backend:v-prod-perf-cors-timeout \
  --timeout=20m
```

**Deploy:**
```bash
gcloud run deploy dipam-ai-backend \
  --image gcr.io/trivihair/dipam-ai-backend:v-prod-perf-cors-timeout \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --min-instances 1 \
  --max-instances 3 \
  --memory 4Gi \
  --cpu 2 \
  --timeout=300 \
  --port 8080
```

**Parâmetros importantes:**
- `--timeout=300`: Timeout do Cloud Run (300s) - internamente cortamos em 20s na DW
- `--memory 4Gi`: Memória suficiente para queries pesadas
- `--cpu 2`: CPU suficiente para processamento
- `--min-instances 1`: Evita cold start

**Verificações:**
- [ ] Deploy completa sem erros
- [ ] Nova revisão criada
- [ ] 100% do tráfego roteado para nova revisão

## 4. Verificação Pós-Deploy (Backend)

### 4.1. Health Check

```bash
curl -i "https://dipam-ai-backend-642830139828.us-central1.run.app/health"
```

**Esperado:**
- Status: `200 OK`
- JSON com `"status": "healthy"`

### 4.2. Teste CORS (OPTIONS)

```bash
curl -i -X OPTIONS "https://dipam-ai-backend-642830139828.us-central1.run.app/ask" \
  -H "Origin: https://dipam.smartiasolutions.com.br" \
  -H "Access-Control-Request-Method: POST"
```

**Esperado:**
- Status: `200 OK`
- `Access-Control-Allow-Origin: https://dipam.smartiasolutions.com.br`
- `Access-Control-Allow-Methods: POST, OPTIONS, GET`
- `Access-Control-Allow-Credentials: true`

### 4.3. Teste CORS (POST)

```bash
curl -i -X POST "https://dipam-ai-backend-642830139828.us-central1.run.app/ask" \
  -H "Origin: https://dipam.smartiasolutions.com.br" \
  -H "Content-Type: application/json" \
  -d '{"pergunta": "teste", "papel": "diretor"}'
```

**Esperado:**
- Status: `200 OK` ou `4xx/5xx` (com CORS)
- `Access-Control-Allow-Origin: https://dipam.smartiasolutions.com.br` presente

### 4.4. Teste Q1 (Timeout)

```bash
curl -X POST "https://dipam-ai-backend-642830139828.us-central1.run.app/ask" \
  -H "Content-Type: application/json" \
  -d '{"pergunta": "Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?", "papel": "diretor"}' \
  -w "\nHTTP: %{http_code}\nTime: %{time_total}s\n"
```

**Esperado:**
- Resposta em < 21s (com cache) ou < 20s (sem cache, com timeout)
- Se timeout: JSON com `erro_dw.error_type: "DW_TIMEOUT"`

## 5. Verificação de Logs

### 5.1. Logs de CORS

```bash
gcloud run services logs read dipam-ai-backend \
  --region us-central1 \
  --limit 100 \
  --format="value(timestamp,textPayload)" | \
  grep -E "\[PERF_STEP\] CORS|CORS OPTIONS"
```

**Esperado:**
- Logs `[PERF_STEP] CORS origin=https://dipam.smartiasolutions.com.br`
- Logs de OPTIONS funcionando

### 5.2. Logs de DW Query

```bash
gcloud run services logs read dipam-ai-backend \
  --region us-central1 \
  --limit 200 \
  --format="value(timestamp,textPayload)" | \
  grep -E "\[PERF_STEP\] (START_DW_QUERY|END_DW_QUERY)"
```

**Esperado:**
- Sempre pares de `START_DW_QUERY` e `END_DW_QUERY`
- `END_DW_QUERY` com `status=ok`, `status=timeout`, ou `status=error`
- `duration_ms` sempre presente

## 6. Teste no Frontend

### 6.1. Acessar Frontend

URL: `https://dipam.smartiasolutions.com.br`

### 6.2. Teste 1: Pergunta Simples (sem DW)

**Pergunta:** "Qual é o total de vendas?"

**Esperado:**
- ✅ Resposta normal
- ✅ Sem erro de CORS
- ✅ Resposta rápida

### 6.3. Teste 2: Pergunta Q1 (com período longo)

**Pergunta:** "Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?"

**Esperado:**
- ✅ Resposta rápida (< 21s com cache) OU
- ✅ Erro de timeout estruturado com mensagem clara para o usuário
- ✅ Frontend mostra mensagem amigável (não erro técnico)

### 6.4. Teste 3: Verificar Console do Navegador

**Verificações:**
- [ ] Sem erros de CORS
- [ ] Sem erros de rede
- [ ] Mensagens de erro (se houver) são amigáveis

## 7. Monitoramento Pós-Deploy

### 7.1. Alertas Recomendados

**Cloud Logging Alert:**
- Condição: Ausência de `END_DW_QUERY` em 10 minutos
- Ação: Notificar time de engenharia

**Métrica:**
- Distribuição de `duration_ms` das queries Q1
- Ajustar timeout se necessário (20s pode virar 15s ou 30s)

### 7.2. Métricas a Monitorar

- Taxa de sucesso de queries Q1
- Tempo médio de resposta Q1
- Taxa de timeout Q1
- Erros de CORS
- Erros de timeout

## 8. Rollback (se necessário)

### Comando de Rollback

```bash
# Listar revisões
gcloud run revisions list --service dipam-ai-backend --region us-central1

# Fazer rollback para revisão anterior
gcloud run services update-traffic dipam-ai-backend \
  --region us-central1 \
  --to-revisions REVISION_NAME=100
```

## 9. Checklist Final

- [ ] Build da imagem concluído
- [ ] Deploy no Cloud Run concluído
- [ ] Health check passando
- [ ] CORS funcionando (OPTIONS e POST)
- [ ] Q1 respondendo ou retornando timeout estruturado
- [ ] Logs `[PERF_STEP] END_DW_QUERY` aparecendo
- [ ] Frontend funcionando sem erros de CORS
- [ ] Frontend tratando timeout com mensagem amigável
- [ ] Monitoramento configurado

## 10. Próximos Passos (Pós-Deploy)

1. **Monitorar métricas por 24-48h**
2. **Ajustar timeout se necessário** (baseado em métricas reais)
3. **Otimizar query Q1** se continuar demorando > 20s
4. **Implementar cache mais agressivo** se necessário
5. **Iniciar POC de execução assíncrona** se timeout for frequente

---

**Status:** 🔜 **PRONTO PARA DEPLOY**

