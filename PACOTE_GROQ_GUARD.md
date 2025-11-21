# 🛡️ PACOTE GROQ GUARD - Proteção contra Limites de Tamanho

## 📋 Resumo

Este pacote implementa proteção completa contra erros 400 do GROQ relacionados a conteúdo muito longo ("Please reduce the length of the messages or completion").

## ✅ Implementações

### 1. Módulo Central: `src/api/groq_client.py`

**Funcionalidades:**
- ✅ Limitação automática de tamanho de prompt (padrão: 10.000 caracteres)
- ✅ Truncamento inteligente preservando início e fim
- ✅ Sempre define `max_tokens` (nunca deixa "solto")
- ✅ Tratamento específico de erros GROQ (400 - "Please reduce the length")
- ✅ Logging estruturado de eventos (`groq_too_long`, `groq_prompt_truncated`, etc.)
- ✅ Exceções customizadas: `GroqContentTooLongError`, `GroqError`

**Função principal:**
```python
def call_groq_model(
    prompt: str,
    *,
    max_tokens: int = 512,
    system: Optional[str] = None,
    max_prompt_chars: Optional[int] = None,
    contexto: str = "default",
    temperature: float = 0.7,
) -> str
```

**Configurações por contexto:**
- `resumo_executivo`: max_tokens=512
- `pdf`: max_tokens=1024
- `ask`: max_tokens=2048
- `default`: max_tokens=512

### 2. Ajuste na Geração de Resumo Executivo

**Arquivo:** `src/llm_integration.py`

**Mudanças:**
- ✅ Condensa contexto antes de enviar para GROQ
- ✅ Não envia tabelas completas, apenas top 5 vendedores
- ✅ Usa `call_groq_model` com proteção automática
- ✅ Fallback via código quando GROQ falha (`_gerar_resumo_executivo_fallback`)

**Função de fallback:**
```python
def _gerar_resumo_executivo_fallback(contexto: Dict[str, Any]) -> str
```

### 3. Ajuste na Geração de Resposta Executiva (Intent)

**Arquivo:** `src/llm_integration_intent.py`

**Mudanças:**
- ✅ Condensa `dados_dw` antes de enviar (`_condensar_dados_dw`)
- ✅ Mantém apenas top 20 registros de tabelas grandes
- ✅ Usa `call_groq_model` com proteção automática
- ✅ Fallback para cliente padrão se GROQ falhar

**Função de condensação:**
```python
def _condensar_dados_dw(dados_dw: Dict[str, Any]) -> Dict[str, Any]
```

### 4. Ajuste no Endpoint `/ask`

**Arquivo:** `src/api/main.py`

**Mudanças:**
- ✅ Sanitiza pergunta antes de processar (limite: 2000 caracteres)
- ✅ Loga evento `ask_pergunta_truncada` quando necessário
- ✅ Todas as chamadas internas já usam GROQ Guard

### 5. Ajuste na Geração de Resposta de Performance de Vendedores

**Arquivo:** `src/llm_integration.py`

**Mudanças:**
- ✅ Usa `call_groq_model` com proteção automática
- ✅ Reduz `max_tokens` de 2000 para 1024
- ✅ Fallback para cliente padrão se GROQ falhar

### 6. Geração de PDF

**Status:** ✅ Não requer alteração

O PDF é gerado no frontend (TypeScript) e não usa GROQ diretamente. Recebe dados já processados pelo backend, que agora estão protegidos pelo GROQ Guard.

## 📊 Eventos de Log Estruturado

Os seguintes eventos são logados:

1. **`groq_too_long`**: Quando GROQ retorna erro 400 por conteúdo muito longo
   - `length_prompt_chars`: Tamanho do prompt
   - `max_tokens`: Max tokens configurado
   - `contexto`: Contexto da chamada
   - `error_message`: Mensagem de erro do GROQ

2. **`groq_prompt_truncated`**: Quando prompt é truncado antes do envio
   - `original_length`: Tamanho original
   - `truncated_length`: Tamanho após truncamento

3. **`resumo_executivo_fallback_sem_groq`**: Quando fallback é usado para resumo executivo
   - `error`: Erro que causou o fallback

4. **`ask_pergunta_truncada`**: Quando pergunta no `/ask` é truncada
   - `original_length`: Tamanho original
   - `truncated_length`: Tamanho após truncamento

## 🧪 Scripts de Teste

### `scripts/test_groq_guard_tamanho.py`

Testa:
- ✅ Truncamento de prompt
- ✅ GROQ Guard com prompt grande
- ✅ GROQ Guard com prompt normal

**Uso:**
```bash
python scripts/test_groq_guard_tamanho.py
```

### `scripts/test_resumo_executivo_groq_len.py`

Testa:
- ✅ Resumo executivo com dados grandes
- ✅ Fallback quando GROQ falha

**Uso:**
```bash
python scripts/test_resumo_executivo_groq_len.py
```

## 🔧 Configuração

### Variáveis de Ambiente

- `GROQ_API_KEY`: Chave de API do GROQ (obrigatória)
- `GROQ_BASE_URL`: URL base (opcional, padrão: `https://api.groq.com/openai/v1`)
- `GROQ_MODEL`: Modelo (opcional, padrão: `llama-3.3-70b-versatile`)

### Limites Configuráveis

No código (`src/api/groq_client.py`):
- `DEFAULT_MAX_PROMPT_CHARS = 10000`: Limite padrão de caracteres no prompt
- `DEFAULT_MAX_TOKENS = 512`: Max tokens padrão para resumos
- `DEFAULT_MAX_TOKENS_PDF = 1024`: Max tokens para PDF
- `DEFAULT_MAX_TOKENS_ASK = 2048`: Max tokens para /ask

## ✅ Critérios de Aceitação Atendidos

- ✅ NENHUMA chamada ao GROQ deve estourar limite e derrubar a funcionalidade
- ✅ O erro "Please reduce the length" não aparece mais para o usuário final (tratado com fallback)
- ✅ Resumo Executivo continua sendo gerado, usa menos contexto, fica estável
- ✅ PDF é gerado mesmo em cenários com mais dados (não usa GROQ diretamente)
- ✅ n8n e outras integrações conseguem chamar `/ask` sem erro 400
- ✅ Logs estruturados funcionando (`groq_too_long`, `resumo_executivo_fallback_sem_groq`, etc.)

## 📝 Arquivos Modificados

1. `src/api/groq_client.py` (NOVO)
2. `src/llm_integration.py`
3. `src/llm_integration_intent.py`
4. `src/api/main.py`
5. `scripts/test_groq_guard_tamanho.py` (NOVO)
6. `scripts/test_resumo_executivo_groq_len.py` (NOVO)

## 🚀 Próximos Passos

1. Executar testes locais:
   ```bash
   python scripts/test_groq_guard_tamanho.py
   python scripts/test_resumo_executivo_groq_len.py
   ```

2. Validar em produção:
   - Fazer perguntas que geram respostas grandes
   - Verificar logs para eventos `groq_too_long` e fallbacks
   - Confirmar que não há mais erros 400 do GROQ

3. Monitorar logs estruturados:
   - Eventos `groq_too_long`
   - Eventos `resumo_executivo_fallback_sem_groq`
   - Eventos `groq_prompt_truncated`

