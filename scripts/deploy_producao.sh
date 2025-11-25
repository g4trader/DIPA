#!/bin/bash
#
# Script de Deploy em Produção - DIPAM AI Backend
#
# Este script faz build e deploy do backend para Cloud Run em produção.
# 
# Uso:
#   ./scripts/deploy_producao.sh [TAG]
#
# Exemplo:
#   ./scripts/deploy_producao.sh v-prod-perf-cors-timeout
#
# Se TAG não for fornecida, usa: v-prod-perf-cors-timeout
#
# Requisitos:
#   - gcloud CLI instalado e autenticado
#   - Permissões para Cloud Build e Cloud Run
#   - Projeto GCP: trivihair
#

set -e  # Para em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configurações
PROJECT_ID="trivihair"
SERVICE_NAME="dipam-ai-backend"
REGION="us-central1"
DEFAULT_TAG="v-prod-perf-cors-timeout"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Tag da imagem (usa argumento ou padrão)
TAG="${1:-${DEFAULT_TAG}}"
FULL_IMAGE="${IMAGE_NAME}:${TAG}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deploy em Produção - DIPAM AI Backend${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Projeto: ${PROJECT_ID}"
echo "Serviço: ${SERVICE_NAME}"
echo "Região: ${REGION}"
echo "Imagem: ${FULL_IMAGE}"
echo ""

# Verifica se gcloud está instalado
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ Erro: gcloud CLI não está instalado${NC}"
    exit 1
fi

# Verifica se está autenticado
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${RED}❌ Erro: gcloud não está autenticado${NC}"
    echo "Execute: gcloud auth login"
    exit 1
fi

# Confirma deploy
echo -e "${YELLOW}⚠️  ATENÇÃO: Você está prestes a fazer deploy em PRODUÇÃO${NC}"
echo -e "${YELLOW}   Serviço: ${SERVICE_NAME}${NC}"
echo -e "${YELLOW}   Imagem: ${FULL_IMAGE}${NC}"
echo ""

# Permite confirmação automática via variável de ambiente
if [[ "${AUTO_CONFIRM_DEPLOY}" == "true" ]]; then
    echo -e "${GREEN}✅ Confirmação automática ativada (AUTO_CONFIRM_DEPLOY=true)${NC}"
    REPLY="s"
else
    read -p "Continuar? (s/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        echo "Deploy cancelado."
        exit 0
    fi
fi

# ============================================
# ETAPA 1: Build da Imagem Docker
# ============================================
echo ""
echo -e "${GREEN}[1/3] Build da imagem Docker...${NC}"
echo "Comando: gcloud builds submit --tag ${FULL_IMAGE} --timeout=20m"
echo ""

if gcloud builds submit --tag "${FULL_IMAGE}" --timeout=20m --project="${PROJECT_ID}"; then
    echo -e "${GREEN}✅ Build concluído com sucesso${NC}"
else
    echo -e "${RED}❌ Erro no build${NC}"
    exit 1
fi

# ============================================
# ETAPA 2: Deploy no Cloud Run
# ============================================
echo ""
echo -e "${GREEN}[2/3] Deploy no Cloud Run...${NC}"
echo "Comando: gcloud run deploy ${SERVICE_NAME} --image ${FULL_IMAGE} ..."
echo ""

DEPLOY_CMD="gcloud run deploy ${SERVICE_NAME} \
  --image ${FULL_IMAGE} \
  --region ${REGION} \
  --platform managed \
  --allow-unauthenticated \
  --min-instances 1 \
  --max-instances 3 \
  --memory 4Gi \
  --cpu 2 \
  --timeout=300 \
  --port 8080 \
  --project=${PROJECT_ID}"

if eval "${DEPLOY_CMD}"; then
    echo -e "${GREEN}✅ Deploy concluído com sucesso${NC}"
else
    echo -e "${RED}❌ Erro no deploy${NC}"
    exit 1
fi

# ============================================
# ETAPA 3: Validação Pós-Deploy
# ============================================
echo ""
echo -e "${GREEN}[3/3] Validação pós-deploy...${NC}"

SERVICE_URL="https://${SERVICE_NAME}-642830139828.${REGION}.run.app"

# Health check
echo "Testando /health..."
if curl -s -f "${SERVICE_URL}/health" > /dev/null; then
    echo -e "${GREEN}✅ Health check passou${NC}"
else
    echo -e "${YELLOW}⚠️  Health check falhou (pode ser normal se serviço ainda estiver iniciando)${NC}"
fi

# CORS check
echo "Testando CORS (OPTIONS)..."
CORS_RESPONSE=$(curl -s -i -X OPTIONS "${SERVICE_URL}/ask" \
  -H "Origin: https://dipam.smartiasolutions.com.br" \
  -H "Access-Control-Request-Method: POST" 2>&1)

if echo "${CORS_RESPONSE}" | grep -q "access-control-allow-origin"; then
    echo -e "${GREEN}✅ CORS funcionando${NC}"
else
    echo -e "${YELLOW}⚠️  CORS não detectado (pode ser normal)${NC}"
fi

# ============================================
# Resumo Final
# ============================================
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deploy Concluído${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "URL do serviço: ${SERVICE_URL}"
echo "Tag da imagem: ${TAG}"
echo ""
echo "Próximos passos:"
echo "  1. Verificar logs: gcloud run services logs read ${SERVICE_NAME} --region ${REGION} --limit 100"
echo "  2. Testar Q1: curl -X POST ${SERVICE_URL}/ask -H 'Content-Type: application/json' -d '{\"pergunta\": \"Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?\", \"papel\": \"diretor\"}'"
echo "  3. Verificar frontend: https://dipam.smartiasolutions.com.br"
echo ""
echo -e "${GREEN}✅ Deploy finalizado com sucesso!${NC}"

