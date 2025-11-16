#!/bin/bash
# Script auxiliar para executar checks de deploy
# 
# Uso:
#   ./scripts/run_deploy_checks.sh
#   ou
#   ENVIRONMENT=production OPENAI_API_KEY=... ./scripts/run_deploy_checks.sh

set -e  # Para em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 DIPAM COPILOT™ - Checks de Deploy${NC}"
echo ""

# Verifica se estamos no diretório raiz do projeto
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ Erro: Execute este script a partir do diretório raiz do projeto${NC}"
    exit 1
fi

# Verifica se venv existe
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️  venv não encontrado. Criando...${NC}"
    python3 -m venv venv
fi

# Ativa venv
echo -e "${GREEN}📦 Ativando ambiente virtual...${NC}"
source venv/bin/activate

# Instala dependências se necessário
if ! python -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Dependências não instaladas. Instalando...${NC}"
    pip install -q -r requirements.txt
fi

# Carrega variáveis de ambiente do .env se existir
if [ -f ".env" ]; then
    echo -e "${GREEN}📝 Carregando variáveis de .env...${NC}"
    export $(cat .env | grep -v '^#' | xargs)
fi

# Valida variáveis críticas
echo -e "${GREEN}🔍 Validando variáveis de ambiente...${NC}"

MISSING_VARS=()

if [ -z "$OPENAI_API_KEY" ]; then
    MISSING_VARS+=("OPENAI_API_KEY")
fi

if [ -z "$DB_TYPE" ]; then
    DB_TYPE="sqlite"  # Default
    echo -e "${YELLOW}⚠️  DB_TYPE não definido, usando padrão: sqlite${NC}"
fi

if [ "$DB_TYPE" = "sqlite" ] && [ -z "$SQLITE_PATH" ]; then
    SQLITE_PATH="data/dipam_dw.db"  # Default
    echo -e "${YELLOW}⚠️  SQLITE_PATH não definido, usando padrão: data/dipam_dw.db${NC}"
fi

if [ -z "$ENVIRONMENT" ]; then
    ENVIRONMENT="production"  # Default para testes
    echo -e "${YELLOW}⚠️  ENVIRONMENT não definido, usando padrão: production${NC}"
fi

# Exporta variáveis para o script Python
export OPENAI_API_KEY
export DB_TYPE
export SQLITE_PATH
export ENVIRONMENT

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo -e "${RED}❌ Variáveis obrigatórias não encontradas:${NC}"
    for var in "${MISSING_VARS[@]}"; do
        echo -e "   - ${var}"
    done
    echo ""
    echo -e "${YELLOW}💡 Dica: Configure as variáveis ou crie um arquivo .env${NC}"
    exit 1
fi

# Verifica se arquivo SQLite existe (se DB_TYPE=sqlite)
if [ "$DB_TYPE" = "sqlite" ] && [ ! -f "$SQLITE_PATH" ]; then
    echo -e "${RED}❌ Arquivo SQLite não encontrado: ${SQLITE_PATH}${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Variáveis de ambiente validadas${NC}"
echo ""

# Executa script de teste
echo -e "${GREEN}🧪 Executando testes de ambiente de produção...${NC}"
echo ""

python scripts/test_cloud_like_env.py

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ Todos os checks passaram! Ambiente pronto para deploy.${NC}"
else
    echo -e "${RED}❌ Alguns checks falharam. Corrija os problemas antes do deploy.${NC}"
fi

exit $EXIT_CODE

