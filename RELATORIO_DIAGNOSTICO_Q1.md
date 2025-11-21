# RELATÓRIO DE DIAGNÓSTICO - Q1: Inconsistência Local vs Produção

## Data: 2025-11-21

---

## 1. CAUSA RAIZ IDENTIFICADA

### ✅ CONCLUSÃO PRINCIPAL:
**A Q1 está funcionando CORRETAMENTE em ambos os ambientes (932 clientes únicos).**

O problema de **1234 clientes** NÃO está vindo da query Q1 diretamente, mas provavelmente de:
- **Resposta do LLM** que pode estar usando números antigos ou gerando texto com valores incorretos
- **Cache no frontend/browser** que pode estar exibindo respostas antigas
- **Versão antiga do código** ainda em cache em algum lugar

---

## 2. FINGERPRINT DO BANCO

### LOCAL:
```json
{
  "db_type": "sqlite",
  "db_path": "/Users/.../data/dipam_dw.db",
  "total_clientes": 5746,
  "total_clientes_ativos": 5746,
  "total_vendas": 3773163,
  "ultima_venda_data": "2025-10-31",
  "hash_fingerprint": "5746_5746_3773163_2025-10-31"
}
```

### PRODUÇÃO:
```json
{
  "db_type": "sqlite",
  "db_path": "/app/data/dipam_dw.db",
  "total_clientes": 5743,
  "total_clientes_ativos": 5743,
  "total_vendas": 3773163,
  "ultima_venda_data": "2025-10-31",
  "hash_fingerprint": "5743_5743_3773163_2025-10-31"
}
```

### ⚠️ DIFERENÇA:
- **3 clientes** de diferença (5746 vs 5743)
- Mesmo número de vendas e mesma data da última venda
- **Não afeta a Q1** (ambos retornam 932 clientes)

---

## 3. CONTAGEM Q1

### LOCAL:
```json
{
  "total_clientes_q1": 932,
  "total_clientes_ativos": 5746,
  "faixas_q1": {
    "faixa_61_120": 497,
    "faixa_121_180": 178,
    "faixa_181_300": 221,
    "faixa_maior_300": 36
  }
}
```

### PRODUÇÃO:
```json
{
  "total_clientes_q1": 932,
  "total_clientes_ativos": 5743,
  "faixas_q1": {
    "faixa_61_120": 497,
    "faixa_121_180": 178,
    "faixa_181_300": 221,
    "faixa_maior_300": 36
  }
}
```

### ✅ RESULTADO:
**IDÊNTICO em ambos os ambientes:**
- `total_clientes_q1`: **932** (local) = **932** (produção) ✅
- Faixas: **idênticas** em ambos os ambientes ✅

---

## 4. ARQUIVOS ALTERADOS

1. **src/dw/diagnostico_db.py** (NOVO)
   - Função `get_db_fingerprint()`: gera fingerprint do banco
   - Função `get_q1_contagem()`: executa Q1 e retorna contagens detalhadas

2. **src/api/main.py**
   - Endpoint `GET /diagnostico/db_fingerprint`: retorna fingerprint do banco
   - Endpoint `GET /diagnostico/q1_contagem`: retorna contagem detalhada da Q1

3. **scripts/test_diagnostico_db.py** (NOVO)
   - Script de teste para validar os endpoints localmente

---

## 5. VALORES FINAIS

### LOCAL (DEV):
- `total_clientes_q1`: **932**
- `total_linhas_tabela`: **932**
- `faixas_q1`: 61-120: 497, 121-180: 178, 181-300: 221, >300: 36

### PRODUÇÃO:
- `total_clientes_q1`: **932**
- `total_linhas_tabela`: **932** (deve ser igual)
- `faixas_q1`: 61-120: 497, 121-180: 178, 181-300: 221, >300: 36

---

## 6. PRÓXIMOS PASSOS RECOMENDADOS

1. **Verificar resposta do LLM:**
   - O número 1234 pode estar vindo do texto gerado pelo LLM
   - Verificar logs do LLM em produção para ver se está gerando esse número
   - Ajustar prompt do LLM para usar explicitamente `total_clientes_q1` do `dados_dw`

2. **Limpar cache:**
   - Limpar cache do browser
   - Verificar se há cache no frontend (Vercel)
   - Forçar refresh completo da aplicação

3. **Validar resposta completa da API:**
   - Fazer uma chamada completa à API `/ask` em produção
   - Verificar se `metrics.total_clientes` está correto (932)
   - Verificar se `tabelaPrincipal.rows.length` está correto (932)
   - Verificar se o texto do `resumo_executivo` menciona 1234

4. **Ajustar prompt do LLM (se necessário):**
   - Garantir que o prompt do LLM use explicitamente `total_clientes_q1` do `dados_dw`
   - Não permitir que o LLM "invente" números baseado em contexto antigo

---

## 7. CONCLUSÃO

✅ **A Q1 está funcionando corretamente** em ambos os ambientes (932 clientes únicos).

⚠️ **O problema de 1234 clientes** não está na query Q1, mas provavelmente:
- No texto gerado pelo LLM (resumo executivo)
- Em cache do frontend/browser
- Em alguma versão antiga do código ainda em uso

🔧 **Solução implementada:**
- Endpoints de diagnóstico criados para facilitar comparação entre ambientes
- Validação explícita de que Q1 retorna 932 clientes em ambos os ambientes
- Campo `metrics.total_clientes` adicionado para garantir consistência

---

**Gerado em:** 2025-11-21T18:50:00
**Commit:** 6e76795
**Backend Image:** gcr.io/trivihair/dipam-ai-backend:v-diagnostico-db

