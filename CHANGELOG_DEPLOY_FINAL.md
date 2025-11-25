# Changelog - Deploy Final CORS + Timeout Query DW

**Data:** 2025-11-25  
**Versão:** v-prod-perf-cors-timeout  
**Commit:** `1d49269` (após correções)

## Resumo das Mudanças

Este changelog documenta todas as alterações realizadas para correção de CORS e implementação de timeout na query DW, incluindo padronização de logs, criação de scripts de deploy e documentação completa.

---

## 📁 Arquivos Criados

### Scripts
- **`scripts/deploy_producao.sh`**
  - Script automatizado para build e deploy em produção
  - Validações pré-deploy (gcloud instalado, autenticado)
  - Confirmação manual antes de deploy
  - Validação pós-deploy (health check, CORS)
  - Uso: `./scripts/deploy_producao.sh [TAG]`

### Documentação
- **`DEPLOY_CICD.md`**
  - Documentação para implementação futura de CI/CD
  - Opções: GitHub Actions ou Cloud Build Triggers
  - Estrutura de workflow recomendada
  - Configuração de aprovação manual

- **`MONITORAMENTO_LOGS.md`**
  - Guia completo de monitoramento de logs
  - Consultas úteis no Cloud Logging
  - Alertas recomendados
  - Comandos gcloud para análise de logs
  - Métricas a monitorar

- **`TRATAMENTO_ERRO_TIMEOUT_FRONTEND.md`**
  - Documentação do tratamento de erro no frontend
  - Fluxo completo de erro (backend → frontend → UI)
  - Exemplos de mensagens exibidas ao usuário

- **`RELATORIO_CORRECAO_CORS_TIMEOUT.md`**
  - Relatório completo das correções implementadas
  - Validação de CORS e timeout
  - Preparação para execução assíncrona

- **`VALIDACAO_TECNICA_FINAL.md`**
  - Validação técnica completa antes do deploy
  - Testes de CORS e timeout
  - Checklist de pré-deploy

- **`CHECKLIST_DEPLOY_PRODUCAO.md`** (atualizado)
  - Checklist completo de deploy
  - Referência ao script `deploy_producao.sh`
  - Comandos manuais como alternativa

---

## 🔧 Arquivos Modificados

### Backend (Python)

#### 1. `src/api/main.py`
**Mudanças:**
- ✅ CORS melhorado: Headers explícitos adicionados (`Access-Control-Allow-Methods`, `Access-Control-Allow-Headers`)
- ✅ Log de origem CORS: `[PERF_STEP] CORS origin={origin}`
- ✅ Logs `[PERF_STEP]` padronizados:
  - `START_MAP_RESPONSE` → `END_MAP_RESPONSE - duration=<MS>ms`
  - `START_CREATE_RESPONSE` → `END_CREATE_RESPONSE - duration=<MS>ms`
  - `START_SERIALIZE_RESPONSE` → `END_SERIALIZE_RESPONSE - duration=<MS>ms`
  - `RETURNING_RESPONSE - total_duration=<MS>ms`
- ✅ Endpoint `/health` agora inclui `commit` hash (quando disponível)

#### 2. `src/dw/query_executor.py` (NOVO)
**Criado:**
- ✅ Função `run_dw_query_q1()` que encapsula execução da query Q1
- ✅ Timeout de 20s configurado
- ✅ Logging completo `[PERF_STEP] START_DW_QUERY` e `END_DW_QUERY`
- ✅ Tratamento de erros estruturado (timeout, error)
- ✅ Retorno consistente com `status`, `data`, `error`, `duration_ms`
- ✅ Preparado para futura execução assíncrona (comentário `FUTURO:`)

#### 3. `src/agent/orquestrador_dw.py`
**Mudanças:**
- ✅ Q1 usa `run_dw_query_q1()` quando `intent_spec.tipo == "clientes_sem_compra"`
- ✅ Tratamento de timeout retorna erro estruturado para frontend
- ✅ Tratamento de erro retorna erro estruturado para frontend
- ✅ Comentário `FUTURO:` indica onde será trocado por job assíncrono
- ✅ Log simplificado (removido kwargs completo do log)

#### 4. `src/agent/handler_dw_refatorado.py`
**Mudanças:**
- ✅ Logs `[PERF_STEP]` padronizados com `query_id=Q1` e `duration=<MS>ms`:
  - `START_GROQ_INTENT - query_id=Q1`
  - `END_GROQ_INTENT - query_id=Q1, duration=<MS>ms`
  - `START_DW_QUERY - query_id=Q1`
  - `END_DW_QUERY - query_id=Q1, status=<ok|error>, duration=<MS>ms`
  - `START_POST_PROCESSOR - query_id=Q1`
  - `END_POST_PROCESSOR - query_id=Q1, duration=<MS>ms`
  - `START_GROQ_EXECUTIVE - query_id=Q1`
  - `END_GROQ_EXECUTIVE - query_id=Q1, duration=<MS>ms`
  - `START_ASSEMBLY - query_id=Q1`
  - `END_ASSEMBLY - query_id=Q1, duration=<MS>ms`
- ✅ Garantia de `END_DW_QUERY` sempre logado (mesmo em erro)

#### 5. `src/llm_integration_intent.py`
**Mudanças:**
- ✅ Logs `[PERF_STEP]` padronizados:
  - `LLM_START - query_id=Q1`
  - `LLM_END - query_id=Q1, duration=<MS>ms`
  - `ASSEMBLY_START - query_id=Q1`
  - `ASSEMBLY_END - query_id=Q1, duration=<MS>ms`

#### 6. `src/dw/queries.py`
**Mudanças:**
- ✅ Timeout `performance_guard` aumentado de 12s para 20s na função Q1

### Frontend (TypeScript/React)

#### 7. `lib/dipamApi.ts`
**Mudanças:**
- ✅ Classe `DipamApiError` estendida com campos `tipo` e `hint`
- ✅ Detecção de erro de timeout DW (`erro_dw.error_type === "DW_TIMEOUT"`)
- ✅ Criação de erro customizado com `tipo: "timeout_dw"` e mensagem amigável
- ✅ Detecção de outros erros internos (`status === "erro_interno"`)

#### 8. `components/DipaPanel.tsx`
**Mudanças:**
- ✅ Tratamento específico para `error.tipo === "timeout_dw"`
- ✅ Emoji diferenciado: ⏱️ para timeout, ❌ para outros erros
- ✅ Mensagem amigável exibida ao usuário (não erro técnico)

---

## 📊 Padronização de Logs

### Formato Padrão `[PERF_STEP]`

Todos os logs seguem o formato:
```
[PERF_STEP] <ETAPA> - query_id=<ID>, status=<STATUS>, duration=<MS>ms, ...
```

**Campos sempre presentes:**
- `query_id`: Identificador da query (ex.: "Q1")
- `status`: Status da operação (ok, timeout, error)
- `duration`: Duração em milissegundos (sempre presente, mesmo em timeout)

**Exemplos:**
```
[PERF_STEP] START_DW_QUERY - query_id=Q1, dias=60, data_referencia=2025-11-30
[PERF_STEP] END_DW_QUERY - query_id=Q1, status=ok, duration=4500.23ms, records=932
[PERF_STEP] END_DW_QUERY - query_id=Q1, status=timeout, duration=20000.00ms
[PERF_STEP] END_DW_QUERY - query_id=Q1, status=error, duration=1234.56ms, error=...
```

---

## 🚀 Como Fazer Deploy em Produção

### Opção 1: Script Automatizado (Recomendado)

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

### Opção 2: Comandos Manuais

**Build:**
```bash
gcloud builds submit --tag gcr.io/trivihair/dipam-ai-backend:v-prod-perf-cors-timeout --timeout=20m
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

---

## ✅ Validações Implementadas

### CORS
- ✅ Headers CORS presentes em todas as respostas (200, 4xx, 5xx, 503)
- ✅ Preflight OPTIONS funcionando
- ✅ Log de origem para debug

### Timeout Query DW
- ✅ Timeout de 20s configurado
- ✅ Logging completo (START/END sempre presente)
- ✅ Erro estruturado retornado ao frontend
- ✅ `duration_ms` sempre registrado (mesmo em timeout)

### Frontend
- ✅ Tratamento de erro de timeout com mensagem amigável
- ✅ Diferenciação visual (⏱️ vs ❌)
- ✅ Sugestão de ação para o usuário

---

## 📋 Checklist de Deploy

Seguir `CHECKLIST_DEPLOY_PRODUCAO.md` para:
- [ ] Build da imagem
- [ ] Deploy no Cloud Run
- [ ] Health check
- [ ] Teste CORS (OPTIONS e POST)
- [ ] Teste Q1 (timeout ou resposta rápida)
- [ ] Verificação de logs `[PERF_STEP] END_DW_QUERY`
- [ ] Teste no frontend

---

## 🔍 Monitoramento

### Consultas Úteis

**Ver logs de performance:**
```bash
gcloud run services logs read dipam-ai-backend \
  --region us-central1 \
  --limit 500 \
  --format="value(timestamp,textPayload)" | \
  grep -E "\[PERF_STEP\]"
```

**Ver apenas END_DW_QUERY:**
```bash
gcloud run services logs read dipam-ai-backend \
  --region us-central1 \
  --limit 1000 \
  --format="value(timestamp,textPayload)" | \
  grep "\[PERF_STEP\] END_DW_QUERY"
```

**Ver timeouts:**
```bash
gcloud run services logs read dipam-ai-backend \
  --region us-central1 \
  --limit 1000 \
  --format="value(timestamp,textPayload)" | \
  grep "status=timeout"
```

Ver `MONITORAMENTO_LOGS.md` para mais detalhes.

---

## 🎯 Próximos Passos (Pós-Deploy)

1. **Monitorar métricas por 24-48h:**
   - Taxa de sucesso de queries Q1
   - Tempo médio de resposta
   - Taxa de timeout

2. **Ajustar timeout se necessário:**
   - Baseado em métricas reais
   - 20s pode virar 15s ou 30s

3. **Otimizar query Q1 se necessário:**
   - Revisar índices
   - Avaliar materialização

4. **Implementar CI/CD:**
   - Seguir `DEPLOY_CICD.md`
   - Configurar GitHub Actions ou Cloud Build

---

## 📝 Resumo Executivo

### Correções Implementadas
- ✅ **CORS:** Headers presentes em todas as respostas, validado via curl
- ✅ **Timeout:** 20s com logging completo e erro estruturado
- ✅ **Frontend:** Tratamento de erro com mensagem amigável
- ✅ **Logs:** Padronizados com formato consistente
- ✅ **Deploy:** Script automatizado criado
- ✅ **Documentação:** Completa e atualizada

### Arquivos Criados
- `scripts/deploy_producao.sh`
- `DEPLOY_CICD.md`
- `MONITORAMENTO_LOGS.md`
- `TRATAMENTO_ERRO_TIMEOUT_FRONTEND.md`
- `RELATORIO_CORRECAO_CORS_TIMEOUT.md`
- `VALIDACAO_TECNICA_FINAL.md`
- `CHANGELOG_DEPLOY_FINAL.md` (este arquivo)

### Arquivos Modificados
- `src/api/main.py`
- `src/dw/query_executor.py` (novo)
- `src/agent/orquestrador_dw.py`
- `src/agent/handler_dw_refatorado.py`
- `src/llm_integration_intent.py`
- `src/dw/queries.py`
- `lib/dipamApi.ts`
- `components/DipaPanel.tsx`
- `CHECKLIST_DEPLOY_PRODUCAO.md`

---

**Status:** ✅ **PRONTO PARA DEPLOY EM PRODUÇÃO**

**Comando de deploy:**
```bash
./scripts/deploy_producao.sh
```

