# Guia de Deploy - DIPAM COPILOT™

Este guia descreve como fazer deploy do backend no Google Cloud e do frontend no Vercel.

## 📋 Pré-requisitos

1. **Google Cloud Platform**:
   - Conta ativa no GCP
   - Projeto criado: `trivihair`
   - Google Cloud SDK instalado (`gcloud`)
   - Docker instalado (opcional, para build local)

2. **Vercel**:
   - Conta ativa no Vercel
   - Vercel CLI instalado (opcional)

---

## 🚀 Deploy do Backend no Google Cloud

### Opção 1: Cloud Run (Recomendado)

Cloud Run é a forma mais simples e moderna de fazer deploy de containers no Google Cloud.

#### 1. Configurar projeto

```bash
# Login no Google Cloud
gcloud auth login

# Configurar projeto
gcloud config set project trivihair

# Habilitar APIs necessárias
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable sqladmin.googleapis.com  # Se usar Cloud SQL
```

#### 2. Criar Cloud SQL (PostgreSQL) - Opcional mas Recomendado

```bash
# Criar instância Cloud SQL
gcloud sql instances create dipam-postgres \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1

# Criar banco de dados
gcloud sql databases create dipam_dw --instance=dipam-postgres

# Criar usuário
gcloud sql users create dipam_user \
  --instance=dipam-postgres \
  --password=SUA_SENHA_AQUI

# Obter IP da instância (para conexão via IP)
gcloud sql instances describe dipam-postgres --format="value(ipAddresses[0].ipAddress)"
```

#### 3. Configurar Secret Manager (Recomendado)

```bash
# Criar secrets
echo -n "dipam_user" | gcloud secrets create postgres-user --data-file=-
echo -n "SUA_SENHA_AQUI" | gcloud secrets create postgres-password --data-file=-
echo -n "dipam_dw" | gcloud secrets create postgres-db --data-file=-
echo -n "SUA_OPENAI_API_KEY" | gcloud secrets create openai-api-key --data-file=-

# Dar permissão ao Cloud Run service account
PROJECT_NUMBER=$(gcloud projects describe trivihair --format="value(projectNumber)")
gcloud secrets add-iam-policy-binding postgres-user \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
gcloud secrets add-iam-policy-binding postgres-password \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
gcloud secrets add-iam-policy-binding postgres-db \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
gcloud secrets add-iam-policy-binding openai-api-key \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

#### 4. Build e Deploy

**Método 1: Build local e push manual**

```bash
# Build da imagem
docker build -t gcr.io/trivihair/dipam-ai-backend:latest .

# Autenticar Docker no GCR
gcloud auth configure-docker

# Push da imagem
docker push gcr.io/trivihair/dipam-ai-backend:latest

# Deploy no Cloud Run
gcloud run deploy dipam-ai-backend \
  --image gcr.io/trivihair/dipam-ai-backend:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 2Gi \
  --cpu 1 \
  --timeout 300s \
  --max-instances 10 \
  --min-instances 0 \
  --set-env-vars PORT=8080,DB_TYPE=postgresql,POSTGRES_HOST=IP_DO_CLOUD_SQL,POSTGRES_PORT=5432 \
  --set-secrets POSTGRES_USER=postgres-user:latest,POSTGRES_PASSWORD=postgres-password:latest,POSTGRES_DB=postgres-db:latest,OPENAI_API_KEY=openai-api-key:latest
```

**Método 2: CI/CD com Cloud Build (Recomendado)**

```bash
# Configurar triggers do Cloud Build
# Edite cloudbuild.yaml com seus valores antes de executar

# Deploy via Cloud Build
gcloud builds submit --config cloudbuild.yaml

# Ou configure um trigger no console do GCP para build automático a cada push
```

#### 5. Obter URL do serviço

```bash
gcloud run services describe dipam-ai-backend \
  --platform managed \
  --region us-central1 \
  --format="value(status.url)"
```

Exemplo: `https://dipam-ai-backend-xxxxx-uc.a.run.app`

### Opção 2: App Engine

Se preferir usar App Engine (mais antigo, mas ainda suportado):

```bash
# Deploy
gcloud app deploy app.yaml

# Obter URL
gcloud app browse
```

---

## 🌐 Deploy do Frontend no Vercel

### 1. Preparar variáveis de ambiente

Crie um arquivo `.env.production` na raiz do projeto (não commitar):

```env
NEXT_PUBLIC_API_URL=https://dipam-ai-backend-xxxxx-uc.a.run.app
```

### 2. Deploy via Vercel Dashboard

1. Acesse [vercel.com](https://vercel.com)
2. Clique em "New Project"
3. Importe o repositório Git
4. Configure:
   - **Framework Preset**: Next.js
   - **Root Directory**: `./` (raiz)
   - **Build Command**: `npm run build`
   - **Output Directory**: `.next`
5. Adicione variável de ambiente:
   - **Key**: `NEXT_PUBLIC_API_URL`
   - **Value**: URL do seu backend Cloud Run (ex: `https://dipam-ai-backend-xxxxx-uc.a.run.app`)
6. Clique em "Deploy"

### 3. Deploy via CLI

```bash
# Instalar Vercel CLI
npm i -g vercel

# Login
vercel login

# Deploy de produção
vercel --prod

# Adicionar variável de ambiente
vercel env add NEXT_PUBLIC_API_URL production
# Digite a URL do backend quando solicitado
```

### 4. Atualizar API URL no código (se necessário)

Se o frontend usa uma variável hardcoded, atualize `lib/dipamApi.ts`:

```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
```

---

## ✅ Verificação

### Backend

```bash
# Testar health endpoint
curl https://dipam-ai-backend-xxxxx-uc.a.run.app/health

# Testar API
curl -X POST https://dipam-ai-backend-xxxxx-uc.a.run.app/ask \
  -H "Content-Type: application/json" \
  -d '{"pergunta": "teste", "usuarioId": "test", "papel": "diretor"}'
```

### Frontend

1. Acesse a URL fornecida pelo Vercel
2. Faça uma pergunta de teste
3. Verifique se está chamando o backend corretamente

---

## 🔧 Troubleshooting

### Backend não inicia

- Verifique logs: `gcloud run services logs read dipam-ai-backend --region us-central1`
- Verifique variáveis de ambiente no console do Cloud Run
- Verifique permissões do Secret Manager

### Frontend não conecta ao backend

- Verifique `NEXT_PUBLIC_API_URL` no Vercel
- Verifique CORS no backend (já configurado para `allow_origins=["*"]`)
- Verifique se o backend está acessível publicamente

### Erro de conexão com banco

- Verifique IP do Cloud SQL no Cloud Run
- Verifique se o Cloud SQL permite conexões do Cloud Run
- Se usar socket Unix, verifique se adicionou `--add-cloudsql-instances`

---

## 📚 Referências

- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Vercel Documentation](https://vercel.com/docs)
- [Cloud SQL for PostgreSQL](https://cloud.google.com/sql/docs/postgres)


