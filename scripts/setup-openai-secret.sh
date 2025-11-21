#!/bin/bash

# Script para configurar o secret OPENAI_API_KEY no Google Cloud Secret Manager
# e atualizar o Cloud Run para usar esse secret

set -e

PROJECT_ID="trivihair"
REGION="us-central1"
SERVICE_NAME="dipam-ai-backend"
SECRET_NAME="openai-api-key"
SERVICE_ACCOUNT="642830139828-compute@developer.gserviceaccount.com"

echo "🔐 Configuração do OPENAI_API_KEY no Cloud Run"
echo "=============================================="
echo ""

# Verificar se a chave foi fornecida
if [ -z "$1" ]; then
    echo "❌ ERRO: Chave da API OpenAI não fornecida!"
    echo ""
    echo "📋 USO:"
    echo "  ./scripts/setup-openai-secret.sh YOUR_OPENAI_API_KEY"
    echo ""
    echo "💡 EXEMPLO:"
    echo "  ./scripts/setup-openai-secret.sh sk-proj-..."
    echo ""
    exit 1
fi

OPENAI_API_KEY="$1"

# Verificar formato comum da chave (OpenAI usa sk-, Grok usa gsk_)
if [[ ! "$OPENAI_API_KEY" =~ ^(sk-|gsk_|xai-) ]]; then
    echo "⚠️  AVISO: A chave da API costuma começar com 'sk-' (OpenAI) ou 'gsk_'/'xai-' (Grok)."
    echo "   Você tem certeza de que a chave está correta? (s/N)"
    read -r CONFIRM
    if [[ ! "$CONFIRM" =~ ^[Ss]$ ]]; then
        echo "❌ Operação cancelada."
        exit 1
    fi
fi

echo "📋 Configuração:"
echo "   Projeto: $PROJECT_ID"
echo "   Região: $REGION"
echo "   Serviço: $SERVICE_NAME"
echo "   Secret: $SECRET_NAME"
echo ""

# 1. Criar o secret (ou atualizar se já existir)
echo "🔐 1/3 Criando/atualizando secret no Secret Manager..."
if gcloud secrets describe "$SECRET_NAME" --project="$PROJECT_ID" &>/dev/null; then
    echo "   Secret já existe. Atualizando..."
    echo -n "$OPENAI_API_KEY" | gcloud secrets versions add "$SECRET_NAME" \
        --project="$PROJECT_ID" \
        --data-file=-
    echo "   ✅ Secret atualizado!"
else
    echo "   Criando novo secret..."
    echo -n "$OPENAI_API_KEY" | gcloud secrets create "$SECRET_NAME" \
        --project="$PROJECT_ID" \
        --data-file=-
    echo "   ✅ Secret criado!"
fi

echo ""

# 2. Conceder permissão ao service account do Cloud Run
echo "🔑 2/3 Concedendo permissão ao Cloud Run service account..."
gcloud secrets add-iam-policy-binding "$SECRET_NAME" \
    --project="$PROJECT_ID" \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor" \
    --quiet

echo "   ✅ Permissão concedida!"
echo ""

# 3. Atualizar o Cloud Run para usar o secret
echo "🚀 3/3 Atualizando Cloud Run para usar o secret..."
gcloud run services update "$SERVICE_NAME" \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --update-secrets "OPENAI_API_KEY=$SECRET_NAME:latest" \
    --quiet

echo "   ✅ Cloud Run atualizado!"
echo ""

echo "=============================================="
echo "✅✅✅ CONFIGURAÇÃO CONCLUÍDA!"
echo "=============================================="
echo ""
echo "📋 Próximos passos:"
echo "   1. Aguarde alguns segundos para o Cloud Run reiniciar"
echo "   2. Teste a API novamente"
echo "   3. A mensagem 'Dados processados via template' deve desaparecer"
echo "   4. A confiança deve aumentar (de 30% para ~90%)"
echo ""
echo "🧪 Teste rápido:"
echo "   curl -X POST https://dipam-ai-backend-642830139828.us-central1.run.app/ask \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"pergunta\":\"qual a meta de vendas do mês de outubro 2025\",\"usuario_id\":\"test\",\"papel\":\"diretor\"}'"
echo ""



