# Deploy do Frontend Next.js no Cloud Run - DIPAM COPILOT™

**Data/Hora**: 2025-11-16 11:07:00 -03  
**Commit**: `6db926f` - "feat: adicionar Dockerfile e Cloud Build para deploy do frontend no Cloud Run"  
**Serviço Cloud Run**: `dipam-copilot-frontend`  
**URL**: `https://dipam-copilot-frontend-6arhlm3mha-uc.a.run.app`

## ✅ Deploy Realizado

### Arquivos Criados

1. **Dockerfile.frontend**
   - Multi-stage build otimizado para Next.js
   - Usa `node:20-alpine` como base
   - Build otimizado com cache de dependências
   - Imagem final mínima para produção

2. **cloudbuild.frontend.yaml**
   - Configuração de Cloud Build para build e deploy automático
   - Build da imagem Docker
   - Push para Container Registry
   - Deploy automático no Cloud Run

3. **.dockerignore.frontend**
   - Ignora arquivos do backend Python durante build
   - Reduz tamanho do contexto de build
   - Otimiza tempo de build

### Configurações Ajustadas

1. **next.config.mjs**
   - Habilitado `output: 'standalone'` para otimização
   - Configuração de variáveis de ambiente públicas

2. **package.json**
   - Script `start` ajustado para usar `PORT` do Cloud Run
   - Configurado para escutar em `0.0.0.0` (necessário para Cloud Run)

## 📋 Configuração do Serviço

### Cloud Run Settings

- **Região**: `us-central1`
- **Plataforma**: `managed`
- **Porta**: `8080`
- **Memória**: `1Gi`
- **CPU**: `1`
- **Timeout**: `300s` (5 minutos)
- **Max Instances**: `10`
- **Min Instances**: `0` (serverless, escala para zero)

### Variáveis de Ambiente

```
NEXT_PUBLIC_API_BASE_URL=https://dipam-ai-backend-6arhlm3mha-uc.a.run.app
NODE_ENV=production
```

**⚠️ IMPORTANTE**: A URL do backend está configurada para `https://dipam-ai-backend-6arhlm3mha-uc.a.run.app`  
**Verificar**: Se esta é a URL correta do backend em produção.

## 🔧 Comandos de Deploy

### Deploy Manual via Cloud Build

```bash
# Build e deploy automático
gcloud builds submit --config=cloudbuild.frontend.yaml --substitutions=COMMIT_SHA=$(git rev-parse --short HEAD)
```

### Deploy Direto (alternativa)

```bash
gcloud run deploy dipam-copilot-frontend \
  --source . \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --memory=1Gi \
  --cpu=1 \
  --timeout=300s \
  --max-instances=10 \
  --min-instances=0 \
  --set-env-vars="NEXT_PUBLIC_API_BASE_URL=https://dipam-ai-backend-6arhlm3mha-uc.a.run.app,NODE_ENV=production"
```

**⚠️ NOTA**: Para deploy direto via `--source`, é necessário usar um Dockerfile específico. Atualmente, o deploy usa `Dockerfile.frontend` via Cloud Build.

### Permitir Acesso Público (se necessário)

```bash
gcloud run services add-iam-policy-binding dipam-copilot-frontend \
  --region=us-central1 \
  --member="allUsers" \
  --role="roles/run.invoker"
```

## 🧪 Testes Pós-Deploy

### 1. Verificar Health Check

```bash
curl -I https://dipam-copilot-frontend-6arhlm3mha-uc.a.run.app
```

**Esperado**: `HTTP/2 200`

### 2. Verificar HTML

```bash
curl https://dipam-copilot-frontend-6arhlm3mha-uc.a.run.app | head -50
```

**Esperado**: HTML do Next.js com React

### 3. Verificar Logs

```bash
gcloud run services logs read dipam-copilot-frontend --region=us-central1 --limit=50
```

**Esperado**: Logs do Next.js mostrando servidor iniciado

### 4. Testar no Navegador

1. Abrir `https://dipam-copilot-frontend-6arhlm3mha-uc.a.run.app`
2. Verificar se a aplicação carrega
3. Abrir DevTools → Console → verificar erros
4. Testar uma pergunta ao agente
5. Verificar se a API do backend é chamada corretamente

## 🔗 URLs de Produção

**Frontend**: `https://dipam-copilot-frontend-6arhlm3mha-uc.a.run.app`  
**Backend**: `https://dipam-ai-backend-6arhlm3mha-uc.a.run.app`

## ⚠️ Próximos Passos

1. **Verificar URL do Backend**: Confirmar se `NEXT_PUBLIC_API_BASE_URL` está correto
2. **Configurar Domínio Customizado** (opcional): Configurar `dipam.smartiasolutions.com.br` para apontar para o Cloud Run
3. **Monitorar Performance**: Verificar logs e métricas no Cloud Console
4. **Configurar CDN** (opcional): Para melhor performance global

## 📝 Notas

- O frontend está configurado para usar o modo `standalone` do Next.js, que cria um servidor Node.js otimizado
- A aplicação escuta na porta `8080` (padrão do Cloud Run via env var `PORT`)
- O acesso é público (não autenticado) via `--allow-unauthenticated`

---

**Última atualização**: 2025-11-16 11:07:00 -03  
**Status**: ✅ **Deploy Concluído**

