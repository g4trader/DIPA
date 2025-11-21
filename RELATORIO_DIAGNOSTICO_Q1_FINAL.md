# RELATÓRIO FINAL DE DIAGNÓSTICO - Q1: Inconsistência Local vs Produção

## Data: 2025-11-21

---

## 1. CAUSA RAIZ IDENTIFICADA

### ✅ CONCLUSÃO PRINCIPAL:
**O problema está no ORQUESTRADOR, não na query Q1 diretamente.**

- **Query Q1 direta** (`/diagnostico/q1_contagem`): retorna **932 clientes** ✅
- **Query Q1 via orquestrador** (`/diagnostico/q1_orquestrador`): retorna **1234 clientes** ❌
- **API completa** (`/ask`): retorna **1234 clientes** ❌

---

## 2. FINGERPRINT DO BANCO

### LOCAL:
- `total_clientes`: 5746
- `total_clientes_ativos`: 5746
- `total_vendas`: 3773163
- `ultima_venda_data`: 2025-10-31
- `hash_fingerprint`: `5746_5746_3773163_2025-10-31`

### PRODUÇÃO:
- `total_clientes`: 5743
- `total_clientes_ativos`: 5743
- `total_vendas`: 3773163
- `ultima_venda_data`: 2025-10-31
- `hash_fingerprint`: `5743_5743_3773163_2025-10-31`

### ⚠️ DIFERENÇA:
- **3 clientes** de diferença (5746 vs 5743)
- **Não afeta a Q1** (ambos retornam 932 quando executados diretamente)

---

## 3. CONTAGEM Q1 - COMPARAÇÃO DE ENDPOINTS

### Endpoint Direto (`/diagnostico/q1_contagem`):
```json
{
  "total_clientes_q1": 932,
  "faixas_q1": {
    "faixa_61_120": 497,
    "faixa_121_180": 178,
    "faixa_181_300": 221,
    "faixa_maior_300": 36
  }
}
```

### Endpoint Via Orquestrador (`/diagnostico/q1_orquestrador`):
```json
{
  "total_orquestrador": 1234,
  "clientes_unicos": 1234,
  "duplicatas": false
}
```

### API Completa (`/ask`):
```json
{
  "metrics.total_clientes": 1234,
  "tabela_principal.linhas.length": 1234
}
```

---

## 4. HIPÓTESES TESTADAS

### ✅ Testado e Descartado:
1. **Cache**: Invalidado, problema persiste
2. **Banco diferente**: Fingerprint similar, não é o problema
3. **Query Q1 direta**: Funciona corretamente (932 clientes)

### ⚠️ Hipótese Ativa:
**O orquestrador está chamando a query Q1 com parâmetros diferentes ou há processamento adicional que está adicionando mais registros.**

Possíveis causas:
- `data_referencia` sendo passado de forma diferente
- `filtros_behavior` afetando o resultado
- Normalização de dados duplicando registros
- Cache sendo usado com chave diferente

---

## 5. ARQUIVOS ALTERADOS

1. **src/dw/diagnostico_db.py** (NOVO)
   - `get_db_fingerprint()`: gera fingerprint do banco
   - `get_q1_contagem()`: executa Q1 diretamente

2. **src/api/main.py**
   - `GET /diagnostico/db_fingerprint`: retorna fingerprint do banco
   - `GET /diagnostico/q1_contagem`: retorna contagem detalhada da Q1
   - `GET /diagnostico/q1_orquestrador`: executa Q1 via orquestrador
   - `POST /diagnostico/invalidate_cache`: invalida cache manualmente

3. **src/agent/orquestrador_dw.py**
   - Logs detalhados para Q1 (antes e depois da normalização)
   - Verificação de duplicatas

4. **src/dw/queries.py**
   - Logs detalhados na query Q1
   - Verificação de duplicatas finais

5. **scripts/test_diagnostico_db.py** (NOVO)
   - Script de teste para validar endpoints localmente

---

## 6. VALORES FINAIS

### LOCAL (DEV):
- `total_clientes_q1` (direto): **932** ✅
- `total_clientes_q1` (via orquestrador): **A testar localmente**

### PRODUÇÃO:
- `total_clientes_q1` (direto): **932** ✅
- `total_clientes_q1` (via orquestrador): **1234** ❌
- `total_clientes_q1` (via `/ask`): **1234** ❌

---

## 7. PRÓXIMOS PASSOS RECOMENDADOS

1. **Verificar logs do Cloud Run:**
   - Após fazer uma chamada à API `/ask`, verificar logs do Cloud Run
   - Procurar por logs `[get_clientes_sem_compra_ha_dias]` e `[orquestrador_dw]`
   - Identificar onde o 1234 está sendo gerado

2. **Comparar parâmetros:**
   - Verificar se `data_referencia` está sendo passado corretamente
   - Verificar se `filtros_behavior` está afetando o resultado
   - Comparar parâmetros entre chamada direta vs via orquestrador

3. **Testar localmente:**
   - Executar `/diagnostico/q1_orquestrador` localmente
   - Verificar se retorna 932 ou 1234
   - Se retornar 932 localmente, o problema é específico de produção

4. **Verificar normalização:**
   - Verificar se `_normalizar_resultado_dw` está duplicando registros
   - Verificar se há processamento adicional no orquestrador

---

## 8. CONCLUSÃO

✅ **A query Q1 está funcionando corretamente** quando executada diretamente (932 clientes).

❌ **O problema está no orquestrador** que está retornando 1234 clientes quando executa a Q1.

🔧 **Solução implementada:**
- Endpoints de diagnóstico criados para facilitar comparação
- Logs detalhados adicionados para rastrear origem do problema
- Validação explícita de duplicatas em cada etapa

📋 **Próximo passo crítico:**
- Verificar logs do Cloud Run após chamada à API `/ask`
- Identificar exatamente onde o 1234 está sendo gerado
- Corrigir o problema no orquestrador ou na normalização

---

**Gerado em:** 2025-11-21T19:25:00
**Commits:** 6e76795, c10e9e9, 972a362, 7752d5a, bf1c936
**Backend Image:** gcr.io/trivihair/dipam-ai-backend:v-diagnostico-logs-q1

