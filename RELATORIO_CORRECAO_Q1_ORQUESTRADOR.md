# RELATÓRIO DE CORREÇÃO - Q1 Orquestrador (1234 → 932)

## Data: 2025-11-21

---

## 1. CAUSA RAIZ IDENTIFICADA

### ⚠️ STATUS: **EM INVESTIGAÇÃO**

**Problema confirmado:**
- Query Q1 direta (`/diagnostico/q1_contagem`): retorna **932 clientes** ✅
- Query Q1 via orquestrador (`/diagnostico/q1_orquestrador`): retorna **1234 clientes** ❌
- API completa (`/ask`): retorna **1234 clientes** ❌

**Hipóteses testadas e descartadas:**
1. ✅ Cache antigo: Invalidado, problema persiste
2. ✅ Banco diferente: Fingerprint similar, não é o problema
3. ✅ Query Q1 direta: Funciona corretamente (932 clientes)
4. ✅ Normalização alterando cardinalidade: Correção implementada, problema persiste
5. ✅ Cache sendo usado: Bypass implementado, problema persiste

**Hipótese ativa:**
- Pode haver uma versão antiga da query sendo executada em produção
- Pode haver alguma lógica que está expandindo os dados após a normalização
- Pode haver diferença nos parâmetros passados para a query

---

## 2. CORREÇÕES IMPLEMENTADAS

### Arquivos Alterados:

1. **src/agent/orquestrador_dw.py**
   - Normalização específica para Q1: não altera cardinalidade
   - Validação defensiva: remove duplicatas se detectadas
   - Logs detalhados em cada etapa do fluxo
   - Bypass de cache para Q1
   - Validação final: garante que cardinalidade não mudou

2. **src/core/cache_layer.py**
   - Suporte a `bypass_cache=True` no decorator `query_cache`
   - Permite ignorar cache quando necessário

3. **src/agent/handler_dw_refatorado.py**
   - Logs detalhados para rastrear payload final

4. **src/api/main.py**
   - Endpoint `/diagnostico/q1_orquestrador` melhorado
   - Comparação com endpoint direto
   - Informações de cache

5. **src/dw/queries.py**
   - Logs detalhados na query Q1
   - Verificação de duplicatas finais

---

## 3. VALORES ATUAIS EM PRODUÇÃO

### Endpoint Direto (`/diagnostico/q1_contagem`):
- `total_clientes_q1`: **932** ✅

### Endpoint Via Orquestrador (`/diagnostico/q1_orquestrador`):
- `total_direto`: **932** ✅
- `total_orquestrador`: **1234** ❌
- `clientes_unicos`: **1234** ❌
- `consistente`: **False** ❌

### API Completa (`/ask`):
- `metrics.total_clientes`: **1234** ❌
- `tabela_principal.linhas.length`: **1234** ❌

---

## 4. PRÓXIMOS PASSOS CRÍTICOS

### 1. Verificar Logs do Cloud Run:
- Após fazer uma chamada à API `/ask`, verificar logs do Cloud Run
- Procurar por logs `[Q1_ORQ]` para ver o fluxo completo
- Identificar exatamente onde o 1234 está sendo gerado

### 2. Verificar se há versão antiga da query:
- Verificar se há alguma função antiga sendo chamada
- Verificar se há algum alias ou wrapper que está usando versão antiga
- Verificar se há algum import incorreto

### 3. Verificar parâmetros passados:
- Comparar parâmetros entre chamada direta vs via orquestrador
- Verificar se `data_referencia` está sendo passado corretamente
- Verificar se `filtros_behavior` está afetando o resultado

### 4. Testar localmente:
- Executar `/diagnostico/q1_orquestrador` localmente
- Verificar se retorna 932 ou 1234
- Se retornar 932 localmente, o problema é específico de produção

---

## 5. COMANDOS ÚTEIS PARA DIAGNÓSTICO

### Verificar logs do Cloud Run:
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dipam-ai-backend AND textPayload=~'Q1_ORQ'" --limit 50 --format json
```

### Testar endpoints:
```bash
# Endpoint direto
curl "https://dipam-ai-backend-642830139828.us-central1.run.app/diagnostico/q1_contagem?dias=60&bypass_cache=true"

# Endpoint via orquestrador
curl "https://dipam-ai-backend-642830139828.us-central1.run.app/diagnostico/q1_orquestrador?dias=60"

# API completa
curl -X POST "https://dipam-ai-backend-642830139828.us-central1.run.app/ask" \
  -H "Content-Type: application/json" \
  -d '{"pergunta": "Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?"}'
```

---

## 6. CONCLUSÃO

✅ **Correções implementadas:**
- Normalização específica para Q1
- Bypass de cache para Q1
- Validação defensiva de duplicatas
- Logs detalhados em cada etapa

❌ **Problema persiste:**
- Orquestrador ainda retorna 1234 em vez de 932
- Necessário investigar logs do Cloud Run para identificar origem exata

📋 **Próximo passo crítico:**
- Verificar logs do Cloud Run após chamada à API `/ask`
- Identificar exatamente onde o 1234 está sendo gerado
- Corrigir a origem do problema

---

**Gerado em:** 2025-11-21T20:45:00
**Commits:** 6f2e434, 021992e, d3d3a2b
**Backend Image:** gcr.io/trivihair/dipam-ai-backend:v-q1-logs-detalhados

