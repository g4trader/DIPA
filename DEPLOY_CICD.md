# CI/CD - Deploy Automatizado - DIPAM AI Backend

**Data:** 2025-11-25  
**Status:** Documentação preparada para implementação futura

## Visão Geral

Este documento descreve a estrutura recomendada para CI/CD do backend DIPAM AI, incluindo:
- GitHub Actions workflow para build e deploy
- Cloud Build triggers (alternativa)
- Aprovação manual para deploy em produção

## Opções de CI/CD

### Opção 1: GitHub Actions (Recomendado)

**Vantagens:**
- Integração nativa com GitHub
- Fácil de configurar e manter
- Suporta approval manual
- Logs centralizados no GitHub

**Workflow recomendado:** `.github/workflows/deploy-prod.yml`

### Opção 2: Cloud Build Triggers

**Vantagens:**
- Nativo do GCP
- Integração direta com Cloud Run
- Suporta approval via Cloud Build

**Configuração:** Via console GCP ou `gcloud` CLI

## Estrutura Recomendada

### Workflow GitHub Actions

```yaml
name: Deploy to Production

on:
  workflow_dispatch:
    inputs:
      tag:
        description: 'Image tag (default: v-prod-{SHA})'
        required: false
        default: ''
      approve:
        description: 'Approve deployment'
        type: boolean
        default: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      
      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v1
      
      - name: Build Docker image
        run: |
          TAG=${GITHUB_SHA::8}
          if [ -n "${{ inputs.tag }}" ]; then
            TAG="${{ inputs.tag }}"
          fi
          gcloud builds submit --tag gcr.io/trivihair/dipam-ai-backend:$TAG
      
      - name: Save image tag
        run: echo "IMAGE_TAG=$TAG" >> $GITHUB_ENV
  
  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: ${{ inputs.approve == true }}
    steps:
      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      
      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v1
      
      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy dipam-ai-backend \
            --image gcr.io/trivihair/dipam-ai-backend:${{ env.IMAGE_TAG }} \
            --region us-central1 \
            --platform managed \
            --allow-unauthenticated \
            --min-instances 1 \
            --max-instances 3 \
            --memory 4Gi \
            --cpu 2 \
            --timeout=300 \
            --port 8080
```

### Configuração Necessária

1. **Service Account do GCP:**
   - Criar service account com permissões:
     - Cloud Build Editor
     - Cloud Run Admin
     - Service Account User
   - Gerar chave JSON
   - Adicionar como secret no GitHub: `GCP_SA_KEY`

2. **GitHub Secrets:**
   - `GCP_SA_KEY`: Chave JSON do service account

3. **Aprovação Manual:**
   - Usar `workflow_dispatch` com input `approve: boolean`
   - Ou usar GitHub Environments com required reviewers

## Cloud Build Trigger (Alternativa)

### Configuração via gcloud

```bash
# Criar trigger
gcloud builds triggers create github \
  --name="deploy-prod" \
  --repo-name="DIPA" \
  --repo-owner="g4trader" \
  --branch-pattern="^main$" \
  --build-config="cloudbuild.yaml" \
  --require-approval
```

### cloudbuild.yaml

```yaml
steps:
  # Build
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/dipam-ai-backend:$SHORT_SHA', '.']
  
  # Push
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/dipam-ai-backend:$SHORT_SHA']
  
  # Deploy
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'dipam-ai-backend'
      - '--image'
      - 'gcr.io/$PROJECT_ID/dipam-ai-backend:$SHORT_SHA'
      - '--region'
      - 'us-central1'
      - '--platform'
      - 'managed'
      - '--allow-unauthenticated'
      - '--min-instances'
      - '1'
      - '--max-instances'
      - '3'
      - '--memory'
      - '4Gi'
      - '--cpu'
      - '2'
      - '--timeout'
      - '300'
      - '--port'
      - '8080'

options:
  machineType: 'E2_HIGHCPU_8'
  timeout: '20m'
```

## Aprovação Manual

### GitHub Actions

**Opção 1: Input manual**
```yaml
on:
  workflow_dispatch:
    inputs:
      approve:
        type: boolean
        default: false
```

**Opção 2: Environments com reviewers**
```yaml
jobs:
  deploy:
    environment:
      name: production
      # Requer aprovação de reviewers configurados no GitHub
```

### Cloud Build

```bash
# Criar trigger com aprovação obrigatória
gcloud builds triggers create github \
  --require-approval \
  ...
```

## Deploy Manual (Atual)

Atualmente, o deploy é feito manualmente usando:

```bash
./scripts/deploy_producao.sh [TAG]
```

Este script:
- ✅ Faz build da imagem
- ✅ Faz deploy no Cloud Run
- ✅ Valida pós-deploy
- ✅ Solicita confirmação antes de deploy

## Recomendações

1. **Para começar:**
   - Continue usando `scripts/deploy_producao.sh` para deploys manuais
   - Configure CI/CD quando houver necessidade de deploys mais frequentes

2. **Quando implementar CI/CD:**
   - Use GitHub Actions se já usa GitHub
   - Use Cloud Build se preferir solução nativa GCP
   - Sempre exija aprovação manual para produção

3. **Segurança:**
   - Nunca commitar chaves de service account
   - Usar GitHub Secrets ou Secret Manager do GCP
   - Limitar permissões do service account ao mínimo necessário

## Próximos Passos

1. **Criar service account do GCP** (se ainda não existir)
2. **Configurar GitHub Secrets** (se usar GitHub Actions)
3. **Criar workflow/trigger** conforme opção escolhida
4. **Testar em ambiente de staging** antes de produção
5. **Documentar processo** para o time

---

**Status:** 📋 **DOCUMENTAÇÃO PRONTA - AGUARDANDO IMPLEMENTAÇÃO**

