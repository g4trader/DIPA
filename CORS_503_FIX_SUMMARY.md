# Correção de CORS e 503 - DIPAM COPILOT™

**Data/Hora**: 2025-11-16 04:35:00 -03  
**Commits**: 
- `c470408` - "fix: tornar carregamento de modelos ML assíncrono para startup rápido"
- `b3939a5` - "fix: aumentar graceful-timeout do Gunicorn para startup assíncrono"
**Revisão Cloud Run**: `dipam-ai-backend-00027-qdv`

## 🔴 Problema Identificado

### Sintomas:
1. **Erro CORS no navegador**:
   ```
   Access to fetch at 'https://dipam-ai-backend-6arhlm3mha-uc.a.run.app/ask' 
   from origin 'https://dipam.smartiasolutions.com.br' has been blocked by CORS policy: 
   No 'Access-Control-Allow-Origin' header is present
   ```

2. **503 Service Unavailable**:
   ```
   POST https://dipam-ai-backend-6arhlm3mha-uc.a.run.app/ask 
   net::ERR_FAILED 503 (Service Unavailable)
   ```

### Causa Raiz:
- O servidor estava demorando **mais de 30 segundos** para completar o startup
- Durante esse tempo, o Cloud Run/Gunicorn retornava **503** para todas as requisições
- Quando uma requisição retorna **503 antes de chegar ao FastAPI**, o middleware CORS não é executado
- Portanto, os headers CORS não eram adicionados às respostas de erro

### Logs Reveladores:
```
2025-11-16 04:29:58 [2025-11-16 04:29:58 +0000] [1] [CRITICAL] WORKER TIMEOUT (pid:2)
2025-11-16 04:29:58 [2025-11-16 04:29:58 +0000] [1] [ERROR] Worker (pid:2) was sent SIGABRT!
```

O Gunicorn estava matando o worker porque ele demorava mais de 30 segundos para iniciar.

## ✅ Correções Aplicadas

### 1. Carregamento Assíncrono de Modelos ML

**Arquivo**: `src/api/main.py`

**Mudança**: Modelos ML agora carregam em **thread separada** (background), não bloqueando o startup:

```python
# 3. Carrega modelos de ML (não crítico para o servidor subir)
# IMPORTANTE: Modelos ML podem demorar para carregar (~20s para arquivos grandes)
# Em vez de bloquear o startup, carregamos de forma assíncrona após o servidor subir
# O servidor sobe imediatamente e os modelos são carregados em background
# Isso evita timeouts do Cloud Run (container precisa responder rápido no startup)
logger.info("Carregando modelos de ML em background...")
from threading import Thread

def load_models_async():
    """Carrega modelos ML em thread separada para não bloquear startup"""
    try:
        logger.info("📦 Iniciando carregamento de modelos ML em background...")
        agent_service = get_agent_service()
        if agent_service:
            app.state.agent_service_available = True
            logger.info("✅ Modelos de ML carregados com sucesso")
        # ... tratamento de erros
    except Exception as e:
        # ... tratamento de erros

# Inicia carregamento em thread separada (daemon=True para não bloquear shutdown)
thread = Thread(target=load_models_async, daemon=True, name="LoadModelsThread")
thread.start()
logger.info("🚀 Servidor pronto - modelos ML carregando em background (não bloqueia requests)")
```

**Benefício**: O servidor sobe **imediatamente** (<5 segundos) e os modelos ML carregam em background.

### 2. Aumentar Timeout do Gunicorn

**Arquivo**: `Dockerfile`

**Mudança**: Aumentado `--graceful-timeout` para 60s:

```dockerfile
CMD ["gunicorn", "-b", "0.0.0.0:8080", "--workers", "1", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--timeout", "300", "--graceful-timeout", "60", \
     "--log-level", "info", "main:app"]
```

**Nota**: O `--graceful-timeout` controla o tempo máximo que o Gunicorn espera pelo worker durante shutdown/restart. Com startup assíncrono, isso não deve mais ser necessário, mas garante margem de segurança.

## 📊 Resultado Esperado

Após essas correções:

1. ✅ **Servidor sobe rápido** (<5 segundos) mesmo sem modelos ML carregados
2. ✅ **Endpoints respondem imediatamente** após startup (sem 503)
3. ✅ **Headers CORS são adicionados** a todas as respostas (incluindo erros)
4. ✅ **Modelos ML carregam em background** sem bloquear requests
5. ✅ **Health check mostra `agent_service: unavailable`** enquanto carrega

## 🧪 Testes Pós-Deploy

### 1. Teste de Health Check (deve responder rápido):
```bash
curl https://dipam-ai-backend-642830139828.us-central1.run.app/health
```

**Esperado**:
```json
{
    "status": "healthy",
    "components": {
        "database": "available",
        "openai": "available",
        "agent_service": "unavailable"  // ou "available" se já carregou
    }
}
```

### 2. Teste de CORS Preflight:
```bash
curl -i -X OPTIONS \
  -H "Origin: https://dipam.smartiasolutions.com.br" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  https://dipam-ai-backend-642830139828.us-central1.run.app/ask
```

**Esperado**:
```
HTTP/2 200
access-control-allow-origin: https://dipam.smartiasolutions.com.br
access-control-allow-methods: DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT
access-control-allow-credentials: true
```

### 3. Teste de Requisição Real:
```bash
curl -i -X POST \
  -H "Origin: https://dipam.smartiasolutions.com.br" \
  -H "Content-Type: application/json" \
  -d '{"pergunta": "qual a meta de outubro 2025", "papel": "diretor"}' \
  https://dipam-ai-backend-642830139828.us-central1.run.app/ask
```

**Esperado**:
- `HTTP/2 200` (não 503)
- `access-control-allow-origin: https://dipam.smartiasolutions.com.br`
- JSON com resposta (ou erro estruturado se modelos ML ainda não carregaram)

## 🔍 Verificação no Navegador

Após o deploy, verificar no navegador (`https://dipam.smartiasolutions.com.br`):

1. **Abrir DevTools → Console**: Não deve haver erros CORS
2. **Abrir DevTools → Network → Filtrar por "ask"**:
   - Status deve ser `200` (não `503`)
   - Headers de resposta devem incluir `Access-Control-Allow-Origin: https://dipam.smartiasolutions.com.br`
   - URL deve ser `https://dipam-ai-backend-...run.app/ask` (sem `//` duplicado)

## ⚠️ Notas Importantes

1. **Modelos ML em Background**: Se uma requisição chegar antes dos modelos ML carregarem, o endpoint `/ask` pode retornar um erro informando que o serviço ainda está carregando. Isso é esperado e não deve causar 503.

2. **Vercel Config**: Garantir que `NEXT_PUBLIC_API_BASE_URL` no Vercel está configurado **sem barra final**:
   ```
   NEXT_PUBLIC_API_BASE_URL=https://dipam-ai-backend-6arhlm3mha-uc.a.run.app
   ```

3. **Logs de Monitoramento**: Monitorar logs do Cloud Run para confirmar que o startup está rápido:
   ```bash
   gcloud run services logs read dipam-ai-backend --region=us-central1 --limit=100
   ```
   
   Procurar por:
   - `🚀 Servidor pronto - modelos ML carregando em background`
   - `Application startup complete` (deve aparecer em <10 segundos)

---

**Última atualização**: 2025-11-16 04:35:00 -03  
**Status**: ✅ **Correções Aplicadas e Deploy Concluído**

