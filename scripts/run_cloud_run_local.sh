#!/usr/bin/env bash
# Script para simular ambiente Cloud Run localmente
# 
# Uso:
#   ./scripts/run_cloud_run_local.sh
#
# Este script configura variáveis de ambiente como no Cloud Run e inicia o servidor.
# Se o servidor subir em http://localhost:8080/health, então o problema provavelmente
# é apenas configuração no Cloud Run (não código).

set -e  # Para em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Simulando ambiente Cloud Run localmente${NC}"
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

# Configura variáveis de ambiente como no Cloud Run
echo -e "${GREEN}🔧 Configurando variáveis de ambiente (Cloud Run mode)...${NC}"

export PORT=8080
export ENVIRONMENT=production
export DB_TYPE=sqlite
export SQLITE_PATH="data/dipam_dw.db"

# Carrega OPENAI_API_KEY do .env se existir (mas não hardcode aqui)
if [ -f ".env" ]; then
    echo -e "${GREEN}📝 Carregando OPENAI_API_KEY do .env...${NC}"
    export $(grep -v '^#' .env | grep OPENAI_API_KEY | xargs)
fi

# Verifica se OPENAI_API_KEY está configurada
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${YELLOW}⚠️  OPENAI_API_KEY não configurada${NC}"
    echo -e "${YELLOW}   O servidor subirá, mas funcionalidades de LLM não estarão disponíveis${NC}"
    echo -e "${YELLOW}   Configure: export OPENAI_API_KEY='sk-...'${NC}"
    echo ""
fi

# Verifica se arquivo SQLite existe
if [ ! -f "$SQLITE_PATH" ]; then
    echo -e "${RED}❌ Arquivo SQLite não encontrado: ${SQLITE_PATH}${NC}"
    echo -e "${YELLOW}   O servidor subirá, mas consultas ao banco podem falhar${NC}"
    echo ""
fi

echo -e "${GREEN}✅ Variáveis configuradas:${NC}"
echo "   PORT=$PORT"
echo "   ENVIRONMENT=$ENVIRONMENT"
echo "   DB_TYPE=$DB_TYPE"
echo "   SQLITE_PATH=$SQLITE_PATH"
echo "   OPENAI_API_KEY=${OPENAI_API_KEY:+configurada (oculta)}"
echo ""

# Inicia servidor
echo -e "${GREEN}🚀 Iniciando servidor FastAPI...${NC}"
echo -e "${GREEN}   URL: http://localhost:${PORT}${NC}"
echo -e "${GREEN}   Health: http://localhost:${PORT}/health${NC}"
echo ""
echo -e "${YELLOW}💡 Para testar após iniciar:${NC}"
echo -e "   curl http://localhost:${PORT}/health"
echo -e "   curl http://localhost:${PORT}/health/db"
echo -e "   curl http://localhost:${PORT}/health/openai"
echo ""
echo -e "${YELLOW}💡 Pressione Ctrl+C para parar o servidor${NC}"
echo ""

# Executa o servidor
python -m src.api.main

