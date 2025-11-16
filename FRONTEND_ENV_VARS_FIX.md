# Correção de Variáveis de Ambiente NEXT_PUBLIC_ no Frontend - DIPAM COPILOT™

**Data/Hora**: 2025-11-16 11:30:00 -03  
**Commit**: `63cddae` - "fix: passar NEXT_PUBLIC_API_BASE_URL como build arg no Dockerfile"  
**Problema**: Frontend tentando chamar `http://localhost:8000/ask` em vez do backend no Cloud Run

## 🔴 Problema Identificado

### Sintoma:
```
Access to fetch at 'http://localhost:8000/ask' from origin 'https://dipam-copilot-frontend-6arhlm3mha-uc.a.run.app' 
has been blocked by CORS policy: Response to preflight request doesn't pass access control check: 
No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

### Causa Raiz:
Variáveis `NEXT_PUBLIC_*` no Next.js **precisam estar disponíveis durante o BUILD**, não apenas no runtime.

O Next.js **embute essas variáveis no código JavaScript durante o build**. Se a variável não estiver definida durante o build, o código usará o fallback (`http://localhost:8000`).

## ✅ Correção Aplicada

### 1. Dockerfile.frontend

**Adicionado ARG e ENV no stage builder**:

```dockerfile
# IMPORTANTE: Variáveis NEXT_PUBLIC_* precisam estar disponíveis durante o BUILD
# Essas variáveis são embutidas no código JavaScript durante o build
# Se não estiverem definidas aqui, o código usará o fallback (localhost)
ARG NEXT_PUBLIC_API_BASE_URL=https://dipam-ai-backend-6arhlm3mha-uc.a.run.app
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}

# Faz o build da aplicação
RUN npm run build
```

### 2. cloudbuild.frontend.yaml

**Adicionado --build-arg durante o build**:

```yaml
  # Build da imagem Docker do frontend
  # IMPORTANTE: Passa NEXT_PUBLIC_API_BASE_URL como build arg para que seja embutida no build
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-f'
      - 'Dockerfile.frontend'
      - '--build-arg'
      - 'NEXT_PUBLIC_API_BASE_URL=https://dipam-ai-backend-6arhlm3mha-uc.a.run.app'
      - '-t'
      - 'gcr.io/$PROJECT_ID/dipam-copilot-frontend:$COMMIT_SHA'
      ...
```

**Removido das env vars de runtime** (já não é necessário, pois está embutida no build):

```yaml
      - '--set-env-vars'
      - 'NODE_ENV=production'  # NEXT_PUBLIC_API_BASE_URL removido (já embutida no build)
```

## 📊 Como Funciona

1. **Durante o build** (Dockerfile):
   - `ARG NEXT_PUBLIC_API_BASE_URL` recebe o valor via `--build-arg`
   - `ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}` disponibiliza durante o build
   - `npm run build` embute a variável no código JavaScript

2. **Resultado**:
   - O código JavaScript gerado contém a URL correta: `https://dipam-ai-backend-6arhlm3mha-uc.a.run.app`
   - Não precisa mais da variável no runtime

3. **No runtime** (Cloud Run):
   - A variável já está embutida no código
   - Não precisa estar nas env vars de runtime

## 🧪 Validação

### 1. Verificar Build Logs

```bash
gcloud builds log <BUILD_ID> | grep "NEXT_PUBLIC_API_BASE_URL"
```

**Esperado**: Variável definida durante o build

### 2. Testar no Navegador

1. Abrir `https://dipam-copilot-frontend-6arhlm3mha-uc.a.run.app`
2. Abrir DevTools → Network
3. Fazer uma pergunta ao agente
4. Verificar requisições para `/ask`
5. **Esperado**: URL deve ser `https://dipam-ai-backend-6arhlm3mha-uc.a.run.app/ask` (não `localhost:8000`)

### 3. Verificar JavaScript Gerado

```bash
# Buscar por localhost:8000 (não deve encontrar)
curl -s https://dipam-copilot-frontend-6arhlm3mha-uc.a.run.app/_next/static/chunks/page-*.js | grep -o "localhost:8000"

# Buscar por dipam-ai-backend (deve encontrar)
curl -s https://dipam-copilot-frontend-6arhlm3mha-uc.a.run.app/_next/static/chunks/page-*.js | grep -o "dipam-ai-backend"
```

## ⚠️ Notas Importantes

1. **Variáveis NEXT_PUBLIC_* são estáticas**: Elas são embutidas no código durante o build e não podem ser alteradas no runtime sem rebuild.

2. **Se precisar mudar a URL do backend**:
   - Atualizar `--build-arg` no `cloudbuild.frontend.yaml`
   - Atualizar `ARG` no `Dockerfile.frontend`
   - Fazer novo build e deploy

3. **Para diferentes ambientes** (dev, staging, prod):
   - Use diferentes valores no `--build-arg` durante o build
   - Ou use diferentes `cloudbuild.*.yaml` para cada ambiente

## 🔧 Comandos Úteis

### Rebuild e Redeploy

```bash
# Rebuild com nova URL do backend
gcloud builds submit --config=cloudbuild.frontend.yaml \
  --substitutions=COMMIT_SHA=$(git rev-parse --short HEAD)

# Ou atualizar a URL diretamente no cloudbuild.frontend.yaml e rebuild
```

### Verificar URL Atual no Build

```bash
# Ver logs do último build
gcloud builds list --limit=1 --format='value(id)' | xargs -I {} gcloud builds log {} | grep "NEXT_PUBLIC_API_BASE_URL"
```

## ✅ Checklist de Validação

- [x] `ARG NEXT_PUBLIC_API_BASE_URL` adicionado no Dockerfile.frontend
- [x] `ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}` no stage builder
- [x] `--build-arg` passado no cloudbuild.frontend.yaml
- [x] Removido `NEXT_PUBLIC_API_BASE_URL` das env vars de runtime
- [ ] **Testar no navegador**: Verificar que não há mais erro de CORS com localhost
- [ ] **Verificar Network**: Confirmar que requisições vão para o Cloud Run backend

---

**Última atualização**: 2025-11-16 11:30:00 -03  
**Status**: ✅ **Correção Aplicada - Aguardando Teste no Navegador**

