# Correção do Problema 503 no Endpoint /ask

## Data: 2025-11-16

## Problema Identificado

O endpoint `/ask` estava sempre retornando **503 (Service Unavailable)** em produção, mesmo após o servidor subir corretamente. O problema estava relacionado ao **AgentService não ficar "ready"** corretamente.

### Sintomas
- `/health` retornava `200 OK` com `agent_service: "available"`
- `/ask` retornava `503` com mensagem "Os modelos de ML ainda estão carregando"
- CORS estava funcionando corretamente
- Backend subia sem erros

## Causa Raiz

1. **Falta de verificação de readiness**: O `AgentService` não tinha um método explícito para verificar se estava pronto
2. **Falta de lazy loading**: Se o agent falhasse no startup, nunca tentava carregar novamente
3. **Logs insuficientes**: Difícil diagnosticar por que o agent não ficava pronto
4. **Modelos ML opcionais**: O agent deveria funcionar mesmo sem modelos ML, mas não estava claro

## Correções Implementadas

### 1. AgentService com Readiness Check (`src/agent/service.py`)

**Adicionado:**
- `is_ready()`: Verifica se o agent está pronto para processar perguntas
- `get_last_error()`: Retorna o último erro ocorrido durante inicialização
- `ensure_ready()`: Tenta garantir que o agent está pronto (lazy loading/retry)
- Flags internas: `_ready`, `_loading`, `_last_error`

**Melhorias:**
- Logs detalhados durante carregamento de modelos ML
- Modelos ML são opcionais - agent funciona mesmo sem eles
- Tratamento de erros mais robusto

### 2. Endpoint /ask com Lazy Loading (`src/api/main.py`)

**Antes:**
```python
if not app.state.agent_service_available:
    return 503
```

**Depois:**
```python
agent_service = get_agent_service()
if agent_service is None:
    return 503

if not agent_service.is_ready():
    if not agent_service.ensure_ready():
        return 503  # Com detalhes do erro
```

**Benefícios:**
- Tenta carregar o agent on-demand se não estiver pronto
- Retorna mensagens de erro mais detalhadas
- Não fica eternamente em 503 sem explicação

### 3. Endpoint /health/agent (`src/api/main.py`)

**Novo endpoint** para diagnóstico:
```bash
GET /health/agent
```

**Resposta:**
```json
{
  "status": "ready" | "not_ready" | "error",
  "ready": true | false,
  "last_error": "string ou null",
  "timestamp": "ISO 8601"
}
```

**Status codes:**
- `200`: Agent está pronto
- `503`: Agent não está pronto (mas servidor está rodando)
- `500`: Erro ao verificar status

### 4. Melhorias no Startup (`src/api/main.py`)

**Thread de carregamento assíncrono:**
- Aguarda até 60 segundos para o agent ficar pronto
- Logs a cada 5 segundos durante espera
- Marca como disponível mesmo se não ficar totalmente pronto (pode funcionar parcialmente)

### 5. Thread-Safe Singleton (`src/agent/service.py`)

**Melhorias em `get_agent_service()`:**
- Thread-safe com lock
- Double-check pattern
- Tratamento de erros mais robusto
- Não retorna `None` a menos que seja erro crítico

## Testes

### Teste Local (Produção-like)

```bash
export ENVIRONMENT=production
export DB_TYPE=sqlite
export SQLITE_PATH="data/dipam_dw.db"
export OPENAI_API_KEY="..."

python -m src.api.main
```

### Verificação em Produção

```bash
# Health geral
curl https://dipam-ai-backend-6arhlm3mha-uc.a.run.app/health

# Health do agent
curl https://dipam-ai-backend-6arhlm3mha-uc.a.run.app/health/agent

# Teste de pergunta
curl -X POST https://dipam-ai-backend-6arhlm3mha-uc.a.run.app/ask \
  -H "Origin: https://dipam.smartiasolutions.com.br" \
  -H "Content-Type: application/json" \
  -d '{"pergunta": "qual a meta de outubro 2025", "papel": "diretor"}'
```

## Resultados Esperados

1. **`/health/agent` retorna `200`** quando o agent está pronto
2. **`/ask` retorna `200`** com resposta do agent quando pronto
3. **Logs claros** indicando o status do agent durante startup
4. **Lazy loading** funciona se o agent não ficar pronto no startup
5. **Mensagens de erro detalhadas** quando o agent não está pronto

## Próximos Passos

1. Monitorar logs em produção para verificar se o agent fica pronto corretamente
2. Verificar se modelos ML estão sendo carregados (ou se são opcionais)
3. Ajustar timeout de carregamento se necessário
4. Documentar comportamento esperado do agent em produção

## Arquivos Modificados

- `src/agent/service.py`: Readiness check, lazy loading, logs detalhados
- `src/api/main.py`: Endpoint `/health/agent`, lazy loading no `/ask`, melhorias no startup
- `scripts/test_cloud_like_env.py`: Testes de readiness do agent

## Commits

- `f08ced8`: fix: implementar lazy loading e readiness check para AgentService
- `7291e61`: feat: adicionar endpoint /health/agent e melhorar testes

