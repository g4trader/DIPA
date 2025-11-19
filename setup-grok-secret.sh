#!/bin/bash
PROJECT_ID="642830139828"
SERVICE_NAME="dipam-ai-backend"
REGION="us-central1"
SECRET_NAME="grok-api-key"
GROK_KEY="SUA_CHAVE_GROK_AQUI"
SERVICE_ACCOUNT="${PROJECT_ID}-compute@developer.gserviceaccount.com"

echo "🔧 Configurando Grok Secret no Cloud Run..."
echo ""

# 1. Criar secret (se não existir)
if ! gcloud secrets describe $SECRET_NAME --project=$PROJECT_ID &>/dev/null; then
  echo "📦 Criando secret '$SECRET_NAME'..."
  echo -n "$GROK_KEY" | \
    gcloud secrets create $SECRET_NAME \
      --data-file=- \
      --project=$PROJECT_ID \
      --replication-policy="automatic"
  echo "✅ Secret criado!"
else
  echo "📦 Secret já existe, atualizando versão..."
  echo -n "$GROK_KEY" | \
    gcloud secrets versions add $SECRET_NAME \
      --data-file=- \
      --project=$PROJECT_ID
  echo "✅ Secret atualizado!"
fi

# 2. Conceder permissão
echo ""
echo "🔐 Concedendo permissão à service account..."
gcloud secrets add-iam-policy-binding $SECRET_NAME \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor" \
  --project=$PROJECT_ID
echo "✅ Permissão concedida!"

# 3. Atualizar Cloud Run
echo ""
echo "🚀 Atualizando Cloud Run service..."
gcloud run services update $SERVICE_NAME \
  --set-secrets="GROK_API_KEY=${SECRET_NAME}:latest" \
  --region=$REGION \
  --project=$PROJECT_ID

echo ""
echo "✅ Configuração concluída!"
echo ""
echo "📋 Verificar configuração:"
echo "   gcloud run services describe $SERVICE_NAME --region=$REGION --project=$PROJECT_ID --format='value(spec.template.spec.containers[0].env)'"
