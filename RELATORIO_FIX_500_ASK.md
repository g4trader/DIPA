# Relatório de Correção - Erro 500 no /ask

**Data:** 2025-11-25  
**Revisão Corrigida:** `acbb9d7`  
**Status:** ✅ **CORRIGIDO E VALIDADO**

## 📋 Resumo Executivo

O erro 500 no endpoint `/ask` foi causado por **erros de indentação** no arquivo `src/llm_integration_intent.py`, introduzidos durante a padronização dos logs `[PERF_STEP]`. O problema foi identificado, corrigido e o tratamento de erros foi melhorado para garantir que o frontend sempre receba JSON estruturado.

## 🔍 Causa Raiz

### Problema Principal

**Tipo:** `IndentationError: unexpected indent`  
**Arquivo:** `src/llm_integration_intent.py`  
**Linhas:** 486, 510, 524, 554

### Detalhes Técnicos

Durante a padronização dos logs `[PERF_STEP]`, algumas linhas receberam indentação extra (8 espaços em vez de 8 espaços corretos), causando erro de sintaxe Python que impedia a importação do módulo.

**Stacktrace:**
```
IndentationError: unexpected indent (llm_integration_intent.py, line 486)
  File "/app/src/api/main.py", line 1438, in ask_question
    from src.agent.handler_dw_refatorado import processar_pergunta_com_dw
  File "/app/src/agent/handler_dw_refatorado.py", line 35, in <module>
    from src.llm_integration_intent import (
  File "/app/src/llm_integration_intent.py", line 486
    logger.info(f"[PERF_STEP] LLM_START - query_id=Q1")
IndentationError: unexpected indent
```

## 🔧 Correções Aplicadas

### 1. Correção de Indentação

**Arquivo:** `src/llm_integration_intent.py`

Corrigidas 4 linhas com indentação incorreta:

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
- ✅ Linha 486: `LLM_START`
- ✅ Linha 510: `LLM_END`
- ✅ Linha 524: `ASSEMBLY_START`
- ✅ Linha 554: `ASSEMBLY_END`

### 2. Melhoria no Tratamento de Erros

**Arquivo:** `src/api/main.py`

Melhorado o handler de exceções no endpoint `/ask`:

**Antes:**
```python
except Exception as e:
    logger.error(f"❌ Erro ao processar pergunta: {str(e)}")
    logger.error(traceback.format_exc())
    # Usava HTTPException que podia não passar pelo CORS corretamente
    raise HTTPException(...)
```

**Depois:**
```python
except Exception as e:
    import traceback
    error_traceback = traceback.format_exc()
    logger.error(f"[ASK_ERROR_FATAL] ❌ Erro ao processar pergunta: {str(e)}")
    logger.error(f"[ASK_ERROR_FATAL] Traceback completo:\n{error_traceback}")
    
    # Retorna JSON estruturado com erro amigável
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=500,
        content={
            "status": "erro_interno",
            "mensagem": "Ocorreu um erro ao processar sua pergunta. Por favor, tente novamente.",
            "erro_tecnico": str(e) if os.getenv("ENVIRONMENT") == "development" else None,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )
```

**Benefícios:**
- ✅ Sempre retorna JSON estruturado (não HTML de erro)
- ✅ Headers CORS garantidos (JSONResponse passa pelo CORSMiddleware)
- ✅ Logging estruturado com tag `[ASK_ERROR_FATAL]`
- ✅ Mensagem amigável para o usuário
- ✅ Detalhes técnicos apenas em desenvolvimento

### 3. Correções Adicionais

- ✅ Corrigido erro de sintaxe (vírgula faltando) na linha 1619
- ✅ Removido `raise error_response` desnecessário após `return JSONResponse`

## ✅ Validação

### Validação de Sintaxe

```bash
python3 -m py_compile src/llm_integration_intent.py src/api/main.py
# ✅ Sem erros
```

### Validação de Importação

```python
# Teste de importação
from src.llm_integration_intent import gerar_resposta_executiva_com_dados_dw
from src.agent.handler_dw_refatorado import processar_pergunta_com_dw
# ✅ Importações bem-sucedidas
```

### Commits Realizados

1. `27eef8f` - fix: corrigir erros de indentação em llm_integration_intent.py e melhorar tratamento de erros no /ask
2. `acbb9d7` - fix: corrigir erro de sintaxe (vírgula faltando) em main.py
3. `[próximo]` - fix: remover raise desnecessário após JSONResponse

## 🚀 Próximos Passos

### Deploy em Produção

```bash
# Build e deploy
./scripts/deploy_producao.sh v-prod-fix-500
```

### Validação Pós-Deploy

1. **Teste direto na API:**
   ```bash
   curl -X POST "https://dipam-ai-backend-642830139828.us-central1.run.app/ask" \
     -H "Content-Type: application/json" \
     -H "Origin: https://dipam.smartiasolutions.com.br" \
     -d '{"pergunta": "Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?", "papel": "diretor"}'
   ```

2. **Teste no frontend:**
   - Acessar: https://dipam.smartiasolutions.com.br
   - Fazer pergunta Q1
   - Verificar:
     - ✅ Não há erro 500 no console
     - ✅ Resposta JSON é recebida corretamente
     - ✅ Em caso de erro, mensagem amigável é exibida

3. **Verificar logs:**
   ```bash
   gcloud run services logs read dipam-ai-backend \
     --region us-central1 \
     --limit 100 \
     --format="value(timestamp,textPayload)" | \
     grep -E "\[ASK_ERROR_FATAL\]|ERROR|500"
   ```
   - ✅ Não deve aparecer `[ASK_ERROR_FATAL]`
   - ✅ Não deve aparecer `IndentationError`
   - ✅ Workers não devem reiniciar

## 📊 Evidências de Correção

### Antes da Correção

- ❌ HTTP 500 Internal Server Error
- ❌ `IndentationError: unexpected indent`
- ❌ Módulo `llm_integration_intent.py` não pode ser importado
- ❌ Workers reiniciam continuamente
- ❌ Frontend recebe erro genérico

### Depois da Correção

- ✅ Sintaxe Python válida
- ✅ Módulos importam corretamente
- ✅ Endpoint `/ask` retorna JSON estruturado
- ✅ Tratamento de erros robusto
- ✅ Logging estruturado para debugging
- ✅ Mensagens amigáveis para o usuário

## 🎯 Critérios de Aceitação

- [x] Erro de indentação corrigido
- [x] Sintaxe Python válida
- [x] Tratamento de erros melhorado
- [x] JSON estruturado sempre retornado
- [x] Headers CORS garantidos
- [x] Logging estruturado implementado
- [ ] Deploy em produção (próximo passo)
- [ ] Validação em produção (próximo passo)

## 📝 Lições Aprendidas

1. **Validação pré-commit:** Sempre validar sintaxe Python antes de commit
2. **Testes de importação:** Testar importação de módulos após mudanças
3. **Tratamento de erros:** Sempre retornar JSON estruturado, nunca deixar exceções subirem cruas
4. **Logging estruturado:** Usar tags consistentes (`[ASK_ERROR_FATAL]`) para facilitar debugging

---

**Status:** ✅ **CORRIGIDO - PRONTO PARA DEPLOY**

**Próximo passo:** Executar `./scripts/deploy_producao.sh v-prod-fix-500`

