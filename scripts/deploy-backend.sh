#!/bin/bash
# Script para deploy do backend no Google Cloud Run

set -e

PROJECT_ID="trivihair"
SERVICE_NAME="dipam-ai-backend"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "🚀 Deploy do backend DIPAM COPILOT™ no Google Cloud Run"
echo "=================================================="
echo ""

# Verificar se gcloud está instalado
if ! command -v gcloud &> /dev/null; then
    echo "❌ Erro: gcloud CLI não está instalado"
    echo "   Instale em: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Verificar se está logado
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "⚠️  Não está logado no gcloud. Fazendo login..."
    gcloud auth login
fi

# Configurar projeto
echo "📋 Configurando projeto: ${PROJECT_ID}"
gcloud config set project ${PROJECT_ID}

# Habilitar APIs necessárias
echo "🔧 Habilitando APIs necessárias..."
gcloud services enable cloudbuild.googleapis.com run.googleapis.com sqladmin.googleapis.com secretmanager.googleapis.com

# Build da imagem
echo "🏗️  Construindo imagem Docker..."
docker build -t ${IMAGE_NAME}:latest .

# Autenticar Docker no GCR
echo "🔐 Autenticando Docker no Google Container Registry..."
gcloud auth configure-docker

# Push da imagem
echo "📤 Enviando imagem para Container Registry..."
docker push ${IMAGE_NAME}:latest

# Deploy no Cloud Run
echo "🚀 Fazendo deploy no Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME}:latest \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --port 8080 \
  --memory 2Gi \
  --cpu 1 \
  --timeout 300s \
  --max-instances 10 \
  --min-instances 0 \
  --set-env-vars PORT=8080,DB_TYPE=postgresql \
  --set-secrets POSTGRES_USER=postgres-user:latest,POSTGRES_PASSWORD=postgres-password:latest,POSTGRES_DB=postgres-db:latest,OPENAI_API_KEY=openai-api-key:latest \
  --quiet

# Obter URL do serviço
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
  --platform managed \
  --region ${REGION} \
  --format="value(status.url)")

echo ""
echo "✅ Deploy concluído com sucesso!"
echo "=================================================="
echo "🌐 URL do serviço: ${SERVICE_URL}"
echo "📖 Documentação: ${SERVICE_URL}/docs"
echo "❤️  Health check: ${SERVICE_URL}/health"
echo ""
echo "⚠️  IMPORTANTE: Configure as seguintes variáveis de ambiente no Cloud Run:"
echo "   - POSTGRES_HOST (IP do Cloud SQL ou socket Unix)"
echo "   - POSTGRES_PORT"
echo ""
echo "   E certifique-se de que os secrets existem:"
echo "   - postgres-user"
echo "   - postgres-password"
echo "   - postgres-db"
echo "   - openai-api-key"
echo ""

