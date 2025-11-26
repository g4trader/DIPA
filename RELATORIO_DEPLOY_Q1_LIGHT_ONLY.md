# Relatório de Deploy - Q1 Light Only em Produção

**Data:** 2025-11-26 01:32:56 UTC  
**Tag da Imagem:** `gcr.io/trivihair/dipam-ai-backend:v-prod-q1-light-only`  
**Revision Cloud Run:** `dipam-ai-backend-00147-gm6`  
**URL do Serviço:** `https://dipam-ai-backend-642830139828.us-central1.run.app`  
**Status:** ✅ **DEPLOY CONCLUÍDO - MODO LIGHT ATIVO**

## 📋 Resumo Executivo

O deploy da versão `v-prod-q1-light-only` foi concluído com sucesso. A imagem foi construída e publicada no Cloud Run com a variável de ambiente `Q1_EXECUTION_MODE=light` configurada. A Q1 agora executa sempre em modo light, usando a query `get_clientes_sem_compra_ha_dias_light()` diretamente, sem tentar a query completa.

## 🔧 Informações do Deploy

### Build
- **Build ID:** `bf7a311c-c313-4be8-929f-0f5c709b8945`
- **Duração:** 8m15s
- **Status:** SUCCESS
- **Digest:** `sha256:e9db6390dafb765a332dadd9c05f856abe04c937d58dfe3bfabb4726dfad8621`

### Deploy Cloud Run
- **Revision:** `dipam-ai-backend-00147-gm6`
- **Região:** `us-central1`
- **Status:** Deployed and serving 100% of traffic
- **Health Check:** ✅ Passou
- **CORS Check:** ✅ Funcionando
- **Variável de Ambiente:** `Q1_EXECUTION_MODE=light` ✅ Configurada

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

- **Status HTTP:** `200 OK` ✅
- **Tempo de Resposta:** ~29 segundos
- **CORS:** ✅ Headers presentes
- **Problema Identificado:** Resposta retornou sem dados (`tem_dados: false`)

### Análise da Resposta

**JSON retornado:**
```json
{
  "intent": "clientes_sem_compra",
  "confidence": 0.3,
  "resumoExecutivo": "Não encontrei dados no data warehouse DIPAM para o período/filtro solicitado...",
  "tem_dados": false,
  "tabela_principal": [],
  "total_clientes_unicos": null
}
```

**Observações:**
- ✅ HTTP 200 (não houve timeout)
- ✅ CORS funcionando
- ❌ Query light não retornou dados
- ❌ `tem_dados: false`
- ❌ `tabela_principal` vazia

**Possíveis causas:**
1. A query light pode estar retornando lista vazia por algum filtro incorreto
2. O período de referência pode estar incorreto (2025-11-01 a 2025-11-30)
3. Pode haver um problema na função `get_clientes_sem_compra_ha_dias_light()`

## 📊 Validações

| Validação | Esperado | Resultado | Status |
|-----------|----------|-----------|--------|
| Deploy concluído | Sim | ✅ Sim | ✅ |
| Health check | 200 OK | ✅ 200 OK | ✅ |
| CORS funcionando | Sim | ✅ Sim | ✅ |
| Q1 retorna em ≤ 10s | Sim | ⚠️ 29s (ainda lento) | ⚠️ |
| Status HTTP 200 | Sim | ✅ 200 OK | ✅ |
| Status "partial" | Sim | ❌ Não retornou | ❌ |
| total_estimado = 932 | Sim | ❌ Não retornou | ❌ |
| Tabela com registros | ≥ 50 | ❌ Vazia | ❌ |
| Q1_EXECUTION_MODE=light | Sim | ✅ Configurado | ✅ |

## 🔍 Análise de Problema

### Causa Raiz Identificada

A query light não está retornando dados. Possíveis causas:

1. **Período de referência incorreto:**
   - A query está usando `data_referencia=2025-11-30` (futuro)
   - Pode estar filtrando incorretamente os clientes

2. **Query light pode ter bug:**
   - A função `get_clientes_sem_compra_ha_dias_light()` pode não estar funcionando corretamente
   - Pode estar faltando algum filtro ou condição

3. **Logs não mostram execução:**
   - Não aparecem logs `[PERF_Q1] DW_MODE=LIGHT` nos logs recentes
   - Pode indicar que a query light não foi executada

### Próximos Passos Recomendados

1. **Verificar logs completos:**
   - Buscar logs de `[Q1_ORQ]` e `[PERF_Q1]` para confirmar execução
   - Verificar se há erros na execução da query light

2. **Testar query light localmente:**
   - Executar `get_clientes_sem_compra_ha_dias_light()` localmente
   - Verificar se retorna dados com os mesmos parâmetros

3. **Ajustar data_referencia:**
   - Usar data atual (hoje) em vez de data futura
   - Verificar se o período está correto

4. **Adicionar mais logs:**
   - Logar parâmetros da query light antes da execução
   - Logar resultado da query light após execução

## 📝 Logs Relevantes

### Logs de Performance

**Nota:** Logs `[PERF_Q1] DW_MODE=LIGHT` não aparecem nos logs recentes, indicando que a query light pode não ter sido executada ou não retornou dados.

## ✅ Conclusão

**Status do Deploy:** ✅ **CONCLUÍDO COM SUCESSO**

**Status Funcional:** ⚠️ **QUERY LIGHT NÃO RETORNA DADOS**

**Recomendação Imediata:**
- Investigar por que a query light não retorna dados
- Verificar logs completos de execução
- Testar query light localmente com os mesmos parâmetros
- Ajustar data_referencia se necessário

**Para Demo:**
- O sistema está respondendo sem timeout (HTTP 200)
- Mas não está retornando dados úteis
- É necessário corrigir a query light antes da demo

---

**Próxima Ação:** Investigar por que `get_clientes_sem_compra_ha_dias_light()` não retorna dados e corrigir a query ou os parâmetros.

