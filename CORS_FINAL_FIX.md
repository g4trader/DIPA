# Correção Final de CORS - DIPAM COPILOT™

**Data/Hora**: 2025-11-16 09:00:00 -03  
**Commit**: `fbb5e7a` - "fix: usar JSONResponse em vez de HTTPException para garantir CORS em erros"  
**Revisão Cloud Run**: `dipam-ai-backend-00031-6ck`

## 🔴 Problema Identificado

O erro CORS ainda estava acontecendo porque:

1. **HTTPException não passa pelo middleware CORS** corretamente
2. Quando o worker do Gunicorn morre (SIGABRT), o Google Frontend retorna 503 **sem headers CORS**
3. O navegador bloqueia a requisição porque não há `Access-Control-Allow-Origin`

### Sintoma:
```
Access to fetch at 'https://dipam-ai-backend-6arhlm3mha-uc.a.run.app/ask' 
from origin 'https://dipam.smartiasolutions.com.br' has been blocked by CORS policy: 
No 'Access-Control-Allow-Origin' header is present
```

## ✅ Correção Aplicada

### Mudança em `src/api/main.py`

**Antes** (usando `HTTPException`):
```python
except Exception as e:
    logger.error(f"Erro ao processar pergunta: {str(e)}")
    raise HTTPException(status_code=500, detail=f"Erro ao processar pergunta: {str(e)}")
```

**Depois** (usando `JSONResponse`):
```python
except Exception as e:
    # IMPORTANTE: Captura TODAS as exceções para garantir que sempre retornamos uma resposta com CORS
    # JSONResponse garante que o middleware CORS adicione os headers mesmo em erros
    # Isso evita que o worker morra e o Google Frontend retorne 503 sem headers CORS
    logger.error(f"❌ Erro ao processar pergunta: {str(e)}")
    import traceback
    logger.error(traceback.format_exc())
    
    # Retorna erro estruturado COM headers CORS (via JSONResponse)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Erro interno do servidor",
            "message": "Ocorreu um erro ao processar sua pergunta. Por favor, tente novamente.",
            "detail": str(e) if config.environment == "development" else "Erro interno do servidor",
            "timestamp": datetime.utcnow().isoformat(),
        }
    )
```

### Por que isso funciona?

1. **JSONResponse passa pelo middleware CORS**: Ao retornar `JSONResponse`, o FastAPI garante que o `CORSMiddleware` processa a resposta e adiciona os headers CORS antes de enviar ao cliente.

2. **HTTPException pode não passar pelo middleware**: Quando você `raise HTTPException`, o FastAPI pode processar a exceção de forma diferente, e em alguns casos o middleware CORS não é aplicado corretamente.

3. **Mesmo em erros, temos CORS**: Agora, mesmo quando há um erro 500, o cliente recebe uma resposta com headers CORS, permitindo que o navegador processe a resposta normalmente.

## 📊 Resultado Esperado

Após essa correção:

1. ✅ **Erros retornam com headers CORS**: Mesmo quando há um erro 500, o navegador recebe `Access-Control-Allow-Origin`
2. ✅ **Navegador não bloqueia requisições**: O erro CORS não aparece mais no console
3. ✅ **Mensagens de erro estruturadas**: O frontend pode processar erros de forma adequada
4. ✅ **Logs melhorados**: Traceback completo para debugging

## 🧪 Teste Pós-Deploy

### 1. Teste de Erro (deve retornar CORS):
```bash
curl -i -X POST \
  -H "Origin: https://dipam.smartiasolutions.com.br" \
  -H "Content-Type: application/json" \
  -d '{"pergunta": "qual a meta de outubro 2025", "papel": "diretor"}' \
  https://dipam-ai-backend-6arhlm3mha-uc.a.run.app/ask
```

**Esperado**:
- `HTTP/2 200` ou `HTTP/2 500` (mas **SEMPRE** com headers CORS)
- `access-control-allow-origin: https://dipam.smartiasolutions.com.br`
- JSON com resposta ou erro estruturado

### 2. Verificação no Navegador

Após o deploy, verificar em `https://dipam.smartiasolutions.com.br`:

1. **DevTools → Console**: Não deve haver erros CORS
2. **DevTools → Network → Filtrar por "ask"**:
   - Headers de resposta devem incluir `Access-Control-Allow-Origin`
   - Mesmo se o status for `500` ou `503`, os headers CORS devem estar presentes

## ⚠️ Notas Importantes

1. **Worker ainda pode morrer**: Se o worker do Gunicorn morrer durante o processamento (SIGABRT), o Google Frontend ainda retornará 503 sem headers CORS. Isso é uma limitação do Cloud Run quando o container não responde a tempo.

2. **Timeout do Cloud Run**: O timeout está configurado para 300s (5 minutos). Se uma requisição demorar mais que isso, o Cloud Run retornará 504 sem headers CORS.

3. **Monitoramento**: Monitorar logs do Cloud Run para identificar requisições que demoram muito:
   ```bash
   gcloud run services logs read dipam-ai-backend --region=us-central1 --limit=100
   ```

## 📋 Checklist de Validação

- [x] CORS configurado no backend para `https://dipam.smartiasolutions.com.br`
- [x] URL normalizada no frontend (sem barras duplicadas)
- [x] Startup rápido (<5 segundos)
- [x] Modelos ML carregam em background
- [x] Erros retornam com `JSONResponse` (garante CORS)
- [ ] **Verificar no navegador**: Erro CORS não deve mais aparecer
- [ ] **Testar requisição real**: Deve funcionar normalmente

---

**Última atualização**: 2025-11-16 09:00:00 -03  
**Status**: ✅ **Correção Aplicada e Deploy Concluído**

