# Correção do Standalone Output no Frontend - DIPAM COPILOT™

**Data/Hora**: 2025-11-16 11:40:00 -03  
**Commit**: `7578960` - "fix: corrigir Dockerfile.frontend para usar standalone output corretamente"  
**Problema**: Frontend tentando chamar `http://localhost:8000/ask` em vez do backend no Cloud Run

## 🔴 Problema Identificado

### Sintomas:
1. Frontend tentando chamar `http://localhost:8000/ask` (fallback)
2. Variável `NEXT_PUBLIC_API_BASE_URL` não está embutida no código JavaScript
3. Warning: `"next start" does not work with "output: standalone" configuration`

### Causa Raiz:
1. **Variável NEXT_PUBLIC_* não embutida**: Variáveis `NEXT_PUBLIC_*` precisam estar disponíveis durante o BUILD, não apenas no runtime
2. **Standalone output não usado**: Dockerfile estava tentando usar `npm run start` em vez de `node server.js`
3. **Estrutura do standalone**: O standalone output do Next.js cria `server.js` na raiz, não em `.next/standalone/server.js`

## ✅ Correções Aplicadas

### 1. Dockerfile.frontend - Build Args

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

### 2. Dockerfile.frontend - Standalone Output

**Ajustado para usar standalone output corretamente**:

```dockerfile
# Com output: 'standalone', Next.js cria servidor otimizado em .next/standalone
# Copia standalone output (mais otimizado - inclui apenas dependências necessárias)
# O standalone output já inclui todos os arquivos necessários, incluindo public/ se existir
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# IMPORTANTE: Quando standalone está ativo, NÃO use "next start" (não funciona)
# O standalone output já inclui um servidor Node.js otimizado em server.js
CMD ["node", "server.js"]
```

### 3. cloudbuild.frontend.yaml - Build Args

**Adicionado --build-arg durante o build**:

```yaml
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-f'
      - 'Dockerfile.frontend'
      - '--build-arg'
      - 'NEXT_PUBLIC_API_BASE_URL=https://dipam-ai-backend-6arhlm3mha-uc.a.run.app'
      ...
```

## 📊 Como Funciona

1. **Durante o build**:
   - `ARG NEXT_PUBLIC_API_BASE_URL` recebe valor via `--build-arg` no cloudbuild.yaml
   - `ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}` disponibiliza durante build
   - `npm run build` embute a variável no código JavaScript
   - `output: 'standalone'` cria servidor otimizado em `.next/standalone/`

2. **No runtime**:
   - Standalone output copiado para `/app`
   - `server.js` está na raiz (criado pelo standalone output)
   - `CMD ["node", "server.js"]` executa servidor standalone
   - Variável já está embutida no código (não precisa env var de runtime)

## 🧪 Validação

### 1. Verificar Build Logs

```bash
# Ver logs do último build
gcloud builds list --limit=1 --format='value(id)' | xargs -I {} gcloud builds log {} | grep "NEXT_PUBLIC_API_BASE_URL"
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
# Buscar por dipam-ai-backend (deve encontrar)
curl -s https://dipam-copilot-frontend-6arhlm3mha-uc.a.run.app/_next/static/chunks/page-*.js | grep -o "dipam-ai-backend" | head -3

# Buscar por localhost:8000 (NÃO deve encontrar)
curl -s https://dipam-copilot-frontend-6arhlm3mha-uc.a.run.app/_next/static/chunks/page-*.js | grep -o "localhost:8000"
```

**Esperado**: Deve encontrar `dipam-ai-backend`, não deve encontrar `localhost:8000`

## ⚠️ Notas Importantes

1. **Variáveis NEXT_PUBLIC_* são estáticas**: Elas são embutidas no código durante o build e não podem ser alteradas no runtime sem rebuild.

2. **Standalone output**: O Next.js com `output: 'standalone'` cria um servidor otimizado em `.next/standalone/` que deve ser copiado para a raiz e executado com `node server.js`.

3. **Se precisar mudar a URL do backend**:
   - Atualizar `--build-arg` no `cloudbuild.frontend.yaml`
   - Atualizar `ARG` no `Dockerfile.frontend`
   - Fazer novo build e deploy

## 🔧 Comandos Úteis

### Rebuild e Redeploy

```bash
# Rebuild com nova URL do backend (se necessário)
gcloud builds submit --config=cloudbuild.frontend.yaml \
  --substitutions=COMMIT_SHA=$(git rev-parse --short HEAD)
```

### Atualizar Imagem do Serviço

```bash
# Atualizar serviço para usar nova imagem
gcloud run services update dipam-copilot-frontend \
  --region=us-central1 \
  --image=gcr.io/trivihair/dipam-copilot-frontend:LATEST_IMAGE_TAG
```

## ✅ Checklist de Validação

- [x] `ARG NEXT_PUBLIC_API_BASE_URL` adicionado no Dockerfile.frontend
- [x] `ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}` no stage builder
- [x] `--build-arg` passado no cloudbuild.frontend.yaml
- [x] `CMD ["node", "server.js"]` usando standalone output
- [x] Removido `COPY public/` (standalone já inclui se existir)
- [ ] **Testar no navegador**: Verificar que não há mais erro de CORS com localhost
- [ ] **Verificar Network**: Confirmar que requisições vão para o Cloud Run backend

---

**Última atualização**: 2025-11-16 11:40:00 -03  
**Status**: ✅ **Correção Aplicada - Aguardando Teste no Navegador**

