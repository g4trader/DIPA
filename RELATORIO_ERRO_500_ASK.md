# Relatório de Investigação - Erro 500 no /ask

**Data:** 2025-11-25  
**Revisão Deployada:** dipam-ai-backend-00144-7cn  
**Status:** ✅ CORRIGIDO

## 🔍 Causa Raiz Identificada

### Erro Principal

**Tipo:** `IndentationError: unexpected indent`  
**Arquivo:** `src/llm_integration_intent.py`  
**Linhas afetadas:** 486, 510, 524, 554

### Stacktrace Completo

```
2025-11-25 22:06:00 ERROR:src.api.main:❌ Erro ao processar pergunta: unexpected indent (llm_integration_intent.py, line 486)
2025-11-25 22:06:00 ERROR:src.api.main:Traceback (most recent call last):
  File "/app/src/api/main.py", line 1438, in ask_question
    from src.agent.handler_dw_refatorado import processar_pergunta_com_dw
  File "/app/src/agent/handler_dw_refatorado.py", line 35, in <module>
    from src.llm_integration_intent import (
  File "/app/src/llm_integration_intent.py", line 486
    logger.info(f"[PERF_STEP] LLM_START - query_id=Q1")
IndentationError: unexpected indent
```

### Análise

O erro ocorreu durante a padronização dos logs `[PERF_STEP]`. Durante as edições, algumas linhas de log receberam indentação extra (8 espaços em vez de 8 espaços corretos), causando erro de sintaxe Python.

**Linhas com problema:**
1. Linha 486: `logger.info(f"[PERF_STEP] LLM_START - query_id=Q1")` - indentação extra
2. Linha 510: `logger.info(f"[PERF_STEP] LLM_END - query_id=Q1, duration={llm_duration:.2f}ms")` - indentação extra
3. Linha 524: `logger.info(f"[PERF_STEP] ASSEMBLY_START - query_id=Q1")` - indentação extra
4. Linha 554: `logger.info(f"[PERF_STEP] ASSEMBLY_END - query_id=Q1, duration={assembly_duration:.2f}ms")` - indentação extra

### Impacto

- **Endpoint afetado:** `/ask`
- **Tipo de pergunta:** Todas (Q1, Q2, etc.)
- **Sintoma:** HTTP 500 Internal Server Error
- **Causa:** Módulo `llm_integration_intent.py` não pode ser importado devido a erro de sintaxe
- **Efeito cascata:** Worker do Gunicorn reinicia continuamente ao tentar processar requisições

## 🔧 Correções Aplicadas

### 1. Correção de Indentação

**Arquivo:** `src/llm_integration_intent.py`

Corrigidas todas as linhas com indentação incorreta:

```python
# ANTES (ERRADO):
    try:
        llm_start_time = time.perf_counter()
            logger.info(f"[PERF_STEP] LLM_START - query_id=Q1")  # ❌ Indentação extra

# DEPOIS (CORRETO):
    try:
        llm_start_time = time.perf_counter()
        logger.info(f"[PERF_STEP] LLM_START - query_id=Q1")  # ✅ Indentação correta
```

**Linhas corrigidas:**
- Linha 486: `LLM_START`
- Linha 510: `LLM_END`
- Linha 524: `ASSEMBLY_START`
- Linha 554: `ASSEMBLY_END`

### 2. Melhoria no Tratamento de Erros

**Arquivo:** `src/api/main.py`

Melhorado o handler de exceções no endpoint `/ask` para:

1. **Sempre retornar JSON estruturado:**
   ```python
   return JSONResponse(
       status_code=500,
       content={
           "status": "erro_interno",
           "mensagem": "Ocorreu um erro ao processar sua pergunta. Por favor, tente novamente.",
           "erro_tecnico": str(e) if os.getenv("ENVIRONMENT") == "development" else None
       }
   )
   ```

2. **Logging estruturado:**
   ```python
   logger.error(f"[ASK_ERROR_FATAL] ❌ Erro ao processar pergunta: {str(e)}")
   logger.error(f"[ASK_ERROR_FATAL] Traceback completo:\n{error_traceback}")
   ```

3. **Garantir headers CORS:**
   - `JSONResponse` passa automaticamente pelo `CORSMiddleware`
   - Headers CORS são adicionados mesmo em respostas de erro

### 3. Validação de Sintaxe

Adicionada validação pré-commit:
```bash
python3 -m py_compile src/llm_integration_intent.py src/api/main.py
```

## ✅ Validação

### Teste Local

```bash
# Compilação Python
python3 -m py_compile src/llm_integration_intent.py src/api/main.py
# ✅ Sem erros
```

### Teste de Importação

```python
# Teste de importação do módulo
from src.llm_integration_intent import gerar_resposta_executiva_com_dados_dw
# ✅ Importação bem-sucedida
```

## 📋 Checklist de Correção

- [x] Identificar causa raiz (IndentationError)
- [x] Corrigir todas as linhas com indentação incorreta
- [x] Melhorar tratamento de erros no `/ask`
- [x] Validar sintaxe Python
- [x] Validar importação de módulos
- [x] Documentar correções

## 🚀 Próximos Passos

1. **Deploy da correção:**
   ```bash
   ./scripts/deploy_producao.sh v-prod-fix-500
   ```

2. **Validação em produção:**
   - Testar endpoint `/ask` com Q1
   - Verificar logs para confirmar ausência de erros
   - Validar que frontend recebe JSON estruturado

3. **Monitoramento:**
   - Verificar logs `[ASK_ERROR_FATAL]` (não deve aparecer)
   - Confirmar que workers não reiniciam mais

---

**Status:** ✅ **CORRIGIDO - PRONTO PARA DEPLOY**

