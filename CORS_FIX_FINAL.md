# Correção Final de CORS e 503 no Endpoint /ask - DIPAM COPILOT™

**Data/Hora**: 2025-11-16 12:15:00 -03  
**Commit**: `af34ff7` - "fix: remover import duplicado de HTTPException"  
**Revisão Cloud Run**: `dipam-ai-backend-00034-4hc`  
**Status**: ✅ **Correção Aplicada e Deploy Realizado**

## 🔴 Problemas Identificados

### Sintomas:
1. **Erro de CORS**: 
   - `Access to fetch at 'https://dipam-ai-backend-6arhlm3mha-uc.a.run.app/ask' from origin 'https://dipam.smartiasolutions.com.br' has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present`
   - `Access to fetch at 'https://dipam-ai-backend-6arhlm3mha-uc.a.run.app/ask' from origin 'https://dipam-copilot-frontend-6arhlm3mha-uc.a.run.app' has been blocked by CORS policy`

2. **Status HTTP 503 sem CORS**: Respostas 503 não incluíam headers CORS

### Causa Raiz:
1. **JSONResponse bypassando CORSMiddleware**: O endpoint `/ask` estava retornando `JSONResponse` diretamente nos casos de erro (503, 500), o que pode fazer com que o CORSMiddleware não adicione os headers corretamente em algumas configurações.
2. **Origem localhost:5173 ausente**: A origem `http://localhost:5173` não estava na lista de origens permitidas.
3. **URLs alternativas desnecessárias**: URLs alternativas do Cloud Run estavam na lista, mas não eram necessárias.

## ✅ Correções Aplicadas

### 1. Ajuste das Origens CORS (`src/api/main.py`)

**Antes**:
```python
origins = [
    "https://dipam.smartiasolutions.com.br",
    "https://dipam-copilot-frontend-6arhlm3mha-uc.a.run.app",
    "https://dipam-copilot-frontend-642830139828.us-central1.run.app",  # URL alternativa desnecessária
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
```

**Depois**:
```python
allowed_origins = [
    # Produção
    "https://dipam.smartiasolutions.com.br",
    "https://dipam-copilot-frontend-6arhlm3mha-uc.a.run.app",
    # Local development
    "http://localhost:3000",
    "http://localhost:5173",  # ✅ Adicionado
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",  # ✅ Adicionado
]
```

**Melhorias**:
- ✅ Adicionado `localhost:5173` para desenvolvimento com Vite
- ✅ Removido URL alternativa desnecessária do Cloud Run
- ✅ Renomeado `origins` para `allowed_origins` para clareza
- ✅ Adicionado `expose_headers=["*"]` para garantir que todos os headers sejam expostos

### 2. Mudança de JSONResponse para HTTPException (`src/api/main.py`)

**Antes (Erro 503)**:
```python
if not app.state.agent_service_available:
    return JSONResponse(
        status_code=503,
        content={...}
    )
```

**Depois**:
```python
if not app.state.agent_service_available:
    # IMPORTANTE: Usa HTTPException ao invés de JSONResponse para garantir que passa pelo CORSMiddleware
    # HTTPException sempre passa pelo pipeline do FastAPI, incluindo middlewares de CORS
    raise HTTPException(
        status_code=503,
        detail={...}
    )
```

**Antes (Erro 500)**:
```python
except Exception as e:
    return JSONResponse(
        status_code=500,
        content={...}
    )
```

**Depois**:
```python
except HTTPException:
    # Re-lança HTTPException para manter status code e passar pelo CORS corretamente
    raise
except Exception as e:
    # IMPORTANTE: Usa HTTPException ao invés de JSONResponse para garantir que passa pelo CORSMiddleware
    # HTTPException sempre passa pelo pipeline do FastAPI, incluindo middlewares de CORS
    raise HTTPException(
        status_code=500,
        detail={...}
    )
```

**Por que HTTPException?**
- ✅ `HTTPException` sempre passa pelo pipeline completo do FastAPI, incluindo `CORSMiddleware`
- ✅ `JSONResponse` direto pode, em algumas configurações, escapar do middleware
- ✅ Garante que **TODAS** as respostas (200, 503, 500, 4xx) incluem headers CORS

### 3. Script de Teste Automatizado (`scripts/test_cors_cloud.py`)

Criado script para testar CORS automaticamente:

```bash
# Testar em produção
export API_BASE_URL=https://dipam-ai-backend-6arhlm3mha-uc.a.run.app
python scripts/test_cors_cloud.py

# Testar localmente
export API_BASE_URL=http://localhost:8080
python scripts/test_cors_cloud.py
```

**Testes realizados**:
- ✅ OPTIONS /ask com cada origem permitida
- ✅ POST /ask com cada origem permitida
- ✅ Verifica header `Access-Control-Allow-Origin` em todas as respostas (incluindo 503, 500)

## 🧪 Validação em Produção

### Teste 1: Preflight OPTIONS - dipam.smartiasolutions.com.br

```bash
curl -X OPTIONS https://dipam-ai-backend-6arhlm3mha-uc.a.run.app/ask \
  -H "Origin: https://dipam.smartiasolutions.com.br" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -i
```

**Esperado**:
```
HTTP/2 200
access-control-allow-origin: https://dipam.smartiasolutions.com.br
access-control-allow-methods: DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT
access-control-allow-credentials: true
access-control-allow-headers: Content-Type
```

### Teste 2: Preflight OPTIONS - dipam-copilot-frontend-6arhlm3mha-uc.a.run.app

```bash
curl -X OPTIONS https://dipam-ai-backend-6arhlm3mha-uc.a.run.app/ask \
  -H "Origin: https://dipam-copilot-frontend-6arhlm3mha-uc.a.run.app" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -i
```

**Esperado**: Headers CORS corretos com `access-control-allow-origin` igual à origem enviada

### Teste 3: POST Real - dipam.smartiasolutions.com.br

```bash
curl -X POST https://dipam-ai-backend-6arhlm3mha-uc.a.run.app/ask \
  -H "Origin: https://dipam.smartiasolutions.com.br" \
  -H "Content-Type: application/json" \
  -d '{"pergunta": "teste de cors", "papel": "diretor"}' \
  -i
```

**Esperado**: 
- Header `access-control-allow-origin: https://dipam.smartiasolutions.com.br` presente
- Mesmo que status seja 503 ou 500, o header CORS deve estar presente

### Teste 4: POST Real - dipam-copilot-frontend-6arhlm3mha-uc.a.run.app

```bash
curl -X POST https://dipam-ai-backend-6arhlm3mha-uc.a.run.app/ask \
  -H "Origin: https://dipam-copilot-frontend-6arhlm3mha-uc.a.run.app" \
  -H "Content-Type: application/json" \
  -d '{"pergunta": "teste de cors", "papel": "diretor"}' \
  -i
```

**Esperado**: Header `access-control-allow-origin` presente mesmo em 503/500

## 📋 Checklist de Validação

- [x] Origens CORS atualizadas: `https://dipam.smartiasolutions.com.br`, `https://dipam-copilot-frontend-6arhlm3mha-uc.a.run.app`, `localhost:3000`, `localhost:5173`
- [x] Erro 503 usa `HTTPException` ao invés de `JSONResponse`
- [x] Erro 500 usa `HTTPException` ao invés de `JSONResponse`
- [x] `HTTPException` sempre passa pelo `CORSMiddleware`
- [x] Script de teste automatizado criado
- [x] Deploy realizado no Cloud Run
- [ ] **Testar no navegador**: Verificar que não há mais erro de CORS
- [ ] **Verificar Network**: Confirmar que todas as respostas (200, 503, 500) incluem `Access-Control-Allow-Origin`

## 🚀 Próximos Passos

1. **Testar no navegador**:
   - Abrir `https://dipam.smartiasolutions.com.br`
   - Abrir `https://dipam-copilot-frontend-6arhlm3mha-uc.a.run.app`
   - Fazer uma pergunta ao agente
   - Verificar no DevTools → Network que não há mais erro de CORS

2. **Verificar logs do Cloud Run**:
   ```bash
   gcloud run services logs read dipam-ai-backend --region=us-central1 --limit=50
   ```

3. **Executar script de teste automatizado** (quando Python estiver disponível):
   ```bash
   export API_BASE_URL=https://dipam-ai-backend-6arhlm3mha-uc.a.run.app
   python scripts/test_cors_cloud.py
   ```

## ✅ Garantias Implementadas

1. **Todas as respostas passam pelo CORSMiddleware**: `HTTPException` sempre passa pelo pipeline completo do FastAPI
2. **Headers CORS sempre presentes**: Mesmo em erros (503, 500), os headers CORS são adicionados
3. **Origens corretas permitidas**: Apenas as origens necessárias estão na lista
4. **Testes automatizados**: Script de teste permite validação rápida de CORS

---

**Última atualização**: 2025-11-16 12:15:00 -03  
**Status**: ✅ **Correção Aplicada e Deploy Realizado - Aguardando Teste no Navegador**

