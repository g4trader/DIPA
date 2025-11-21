# RESUMO DE CORREÇÃO - Q1 Orquestrador (1234 → 932)

## Data: 2025-11-21

---

## 1. CAUSA RAIZ (HIPÓTESE)

### ⚠️ STATUS: **EM INVESTIGAÇÃO ATIVA**

**Problema confirmado:**
- Query Q1 direta: **932 clientes** ✅
- Query Q1 via orquestrador: **1234 clientes** ❌
- API `/ask`: **1234 clientes** ❌

**Hipótese mais provável:**
O orquestrador pode estar usando uma versão antiga da query ou há alguma lógica que está expandindo os dados após a normalização. Os logs detalhados adicionados devem ajudar a identificar a origem exata.

---

## 2. ARQUIVOS ALTERADOS

1. **src/agent/orquestrador_dw.py**
   - Normalização específica para Q1 (não altera cardinalidade)
   - Validação defensiva (remove duplicatas se detectadas)
   - Logs detalhados em cada etapa
   - Bypass de cache para Q1
   - Validação final robusta

2. **src/core/cache_layer.py**
   - Suporte a `bypass_cache=True`

3. **src/agent/handler_dw_refatorado.py**
   - Logs para rastrear payload final

4. **src/api/main.py**
   - Endpoint `/diagnostico/q1_orquestrador` melhorado

5. **src/dw/queries.py**
   - Logs detalhados na query Q1

---

## 3. PRÓXIMOS PASSOS

**CRÍTICO:** Verificar logs do Cloud Run após chamada à API `/ask`:
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dipam-ai-backend AND textPayload=~'Q1_ORQ'" --limit 100 --format json
```

Os logs devem mostrar:
- `[Q1_ORQ] Resultado DW bruto - registros: X`
- `[Q1_ORQ] Resultado após normalização - registros: Y`
- `[Q1_ORQ] Payload final enviado ao LLM - registros: Z`

Isso identificará exatamente onde o 1234 está sendo gerado.

---

**Commit:** afc7087
**Backend Image:** gcr.io/trivihair/dipam-ai-backend:v-q1-fix-final

