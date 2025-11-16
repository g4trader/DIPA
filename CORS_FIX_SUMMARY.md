# Correções de CORS e URL - DIPAM COPILOT™

**Data/Hora**: 2025-11-16 04:00:00 -03  
**Commit**: `8fbbe10` - "fix: corrigir CORS e normalizar URL da API"  
**Revisão Cloud Run**: `dipam-ai-backend-00025-hp4`

## ✅ Correções Aplicadas

### 1. Backend - CORS Configurado Corretamente

**Arquivo**: `src/api/main.py`

**Mudanças**:
- ✅ Removido `allow_origins=["*"]` por segurança
- ✅ Configurado explicitamente para permitir:
  - `https://dipam.smartiasolutions.com.br`
  - `https://www.dipam.smartiasolutions.com.br`
  - `http://localhost:3000` (desenvolvimento)
  - `http://127.0.0.1:3000` (desenvolvimento)
  - Localhost ports em desenvolvimento (8000, 8080)

**Código**:
```python
origins = [
    "https://dipam.smartiasolutions.com.br",
    "https://www.dipam.smartiasolutions.com.br",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

if config.environment == "development":
    origins.extend([
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 2. Frontend - URL Normalizada

**Arquivo**: `lib/dipamApi.ts`

**Mudanças**:
- ✅ Função `buildUrl()` para normalizar URLs
- ✅ Remove barras no final do `baseUrl` automaticamente
- ✅ Evita URLs duplicadas (ex: `...run.app//ask`)
- ✅ Mensagens de erro mostram URL final usada

**Código**:
```typescript
// Remove barra extra no final, se houver
export const DIPAM_API_BASE_URL = rawBaseUrl.replace(/\/+$/, "");

function buildUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${DIPAM_API_BASE_URL}${normalizedPath}`;
}

// Uso:
const url = buildUrl("/ask");
const response = await fetch(url, { ... });
```

### 3. Documentação Atualizada

**Arquivo**: `README_DEPLOY.md`

**Mudanças**:
- ✅ Instruções de `NEXT_PUBLIC_API_BASE_URL` sem barra final
- ✅ Seção de teste CORS com curl adicionada
- ✅ Troubleshooting de CORS melhorado

## 🧪 Testes de CORS

### Teste de Preflight OPTIONS

```bash
curl -i -X OPTIONS \
  -H "Origin: https://dipam.smartiasolutions.com.br" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  https://dipam-ai-backend-642830139828.us-central1.run.app/ask
```

**Esperado**:
- `Access-Control-Allow-Origin: https://dipam.smartiasolutions.com.br`
- `Access-Control-Allow-Methods: POST, GET, OPTIONS, ...`
- `Access-Control-Allow-Headers: Content-Type, ...`
- `HTTP/1.1 200 OK`

### Teste de Requisição Real POST

```bash
curl -i -X POST \
  -H "Origin: https://dipam.smartiasolutions.com.br" \
  -H "Content-Type: application/json" \
  -d '{"pergunta": "qual a meta de outubro 2025", "papel": "diretor"}' \
  https://dipam-ai-backend-642830139828.us-central1.run.app/ask
```

**Esperado**:
- `Access-Control-Allow-Origin: https://dipam.smartiasolutions.com.br`
- `HTTP/1.1 200 OK`
- JSON com resposta da API

## 🔗 URLs

**Backend (Cloud Run)**: `https://dipam-ai-backend-642830139828.us-central1.run.app`  
**Frontend (Vercel)**: `https://dipam.smartiasolutions.com.br`

## 📋 Checklist Pós-Deploy

- [x] Backend deployado com CORS configurado
- [ ] **Verificar no Vercel**: `NEXT_PUBLIC_API_BASE_URL` sem barra final
- [ ] **Testar CORS**: Executar curl de preflight OPTIONS
- [ ] **Testar no navegador**: 
  - Abrir `https://dipam.smartiasolutions.com.br`
  - Abrir DevTools → Network
  - Filtrar por "ask"
  - Verificar:
    - Status 200/201
    - Headers incluem `Access-Control-Allow-Origin: https://dipam.smartiasolutions.com.br`
    - URL sem barras duplicadas (ex: `...run.app/ask` não `...run.app//ask`)

## 📝 Próximos Passos

1. **No Vercel**:
   - Verificar se `NEXT_PUBLIC_API_BASE_URL` está configurada **sem barra final**
   - Valor: `https://dipam-ai-backend-6arhlm3mha-uc.a.run.app` (ou a URL atual do serviço)

2. **Testar no navegador**:
   - Recarregar `https://dipam.smartiasolutions.com.br`
   - Abrir DevTools → Console → verificar se não há erros CORS
   - Abrir DevTools → Network → filtrar por "ask" → verificar headers de resposta

3. **Se ainda houver erro CORS**:
   - Verificar logs do Cloud Run: `gcloud run services logs read dipam-ai-backend --region=us-central1`
   - Verificar se o domínio está correto em `src/api/main.py`
   - Testar preflight OPTIONS com curl

---

**Última atualização**: 2025-11-16 04:00:00 -03  
**Status**: ✅ **Correções Aplicadas e Deploy Concluído**

