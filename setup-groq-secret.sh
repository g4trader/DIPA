#!/bin/bash
# Script para configurar o secret GROQ_API_KEY no Google Cloud Secret Manager
# e atualizar o Cloud Run service para usar o secret

set -e

PROJECT_ID=$(gcloud projects describe 642830139828 --format="value(projectId)")
SECRET_NAME="groq-api-key"
SERVICE_NAME="dipam-ai-backend"
REGION="us-central1"
SERVICE_ACCOUNT="642830139828-compute@developer.gserviceaccount.com"

echo "🔑 Configurando secret GROQ_API_KEY no Secret Manager..."
echo ""

# Aceita a chave como argumento ou variável de ambiente
if [ -n "$1" ]; then
    GROQ_KEY="$1"
elif [ -n "$GROQ_API_KEY" ]; then
    GROQ_KEY="$GROQ_API_KEY"
else
    echo "⚠️  Chave não fornecida!"
    echo ""
    echo "Uso:"
    echo "  $0 <GROQ_API_KEY>"
    echo "  ou"
    echo "  GROQ_API_KEY=<sua-chave> $0"
    echo ""
    echo "Você pode obter sua chave em: https://console.groq.com/"
    exit 1
fi

# Verifica se o secret já existe
if gcloud secrets describe "$SECRET_NAME" --project="$PROJECT_ID" &>/dev/null; then
    echo "⚠️  Secret '$SECRET_NAME' já existe. Atualizando versão..."
    echo -n "$GROQ_KEY" | gcloud secrets versions add "$SECRET_NAME" --project="$PROJECT_ID" --data-file=-
    echo "✅ Versão do secret atualizada!"
else
    echo "📝 Criando novo secret '$SECRET_NAME'..."
    echo -n "$GROQ_KEY" | gcloud secrets create "$SECRET_NAME" \
        --project="$PROJECT_ID" \
        --data-file=- \
        --replication-policy="automatic"
    echo "✅ Secret criado com sucesso!"
fi

echo ""
echo "🔐 Concedendo permissão ao Cloud Run service account..."
gcloud secrets add-iam-policy-binding "$SECRET_NAME" \
    --project="$PROJECT_ID" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor" \
    --condition=None

echo "✅ Permissão concedida!"
echo ""
echo "🚀 Atualizando Cloud Run service para usar o secret..."
gcloud run services update "$SERVICE_NAME" \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --update-secrets="GROQ_API_KEY=${SECRET_NAME}:latest" \
    --platform=managed

echo ""
echo "✅ Configuração concluída!"
echo ""
echo "📋 Fazendo deploy final com o secret configurado..."
gcloud run deploy "$SERVICE_NAME" \
    --source . \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --platform=managed \
    --allow-unauthenticated \
    --set-secrets="GROQ_API_KEY=${SECRET_NAME}:latest" \
    --memory=4Gi \
    --cpu=2 \
    --timeout=300s \
    --max-instances=10 \
    --min-instances=1

echo ""
echo "🎉 Deploy concluído com Groq configurado!"
