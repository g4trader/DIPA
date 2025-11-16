#!/usr/bin/env bash
# Script para simular ambiente Cloud Run localmente com Gunicorn
# 
# Uso:
#   ./scripts/run_cloudrun_style_local.sh
#
# Este script configura variáveis de ambiente como no Cloud Run e inicia o servidor
# usando Gunicorn, exatamente como o Cloud Run buildpack faz.
# 
# Para tornar executável: chmod +x scripts/run_cloudrun_style_local.sh
#
# IMPORTANTE: Este script usa gunicorn -b 0.0.0.0:8080 main:app
# O Cloud Run buildpack espera encontrar main:app na raiz do projeto.

set -e  # Para em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Simulando ambiente Cloud Run localmente (com Gunicorn)${NC}"
echo ""

# Verifica se estamos no diretório raiz do projeto
if [ ! -f "main.py" ]; then
    echo -e "${RED}❌ Erro: main.py não encontrado na raiz. Execute este script a partir do diretório raiz do projeto${NC}"
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

# Verifica se gunicorn está instalado
if ! python -c "import gunicorn" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Gunicorn não instalado. Instalando...${NC}"
    pip install -q gunicorn
fi

# Configura variáveis de ambiente como no Cloud Run
echo -e "${GREEN}🔧 Configurando variáveis de ambiente (Cloud Run mode)...${NC}"

export PORT=8080
export ENVIRONMENT=production

# Banco em modo Cloud Run-like
export DB_TYPE=sqlite
export SQLITE_PATH="data/dipam_dw.db"  # Caminho relativo - será criado se necessário

# NÃO colocar chave real aqui, apenas placeholder/comment
# export OPENAI_API_KEY="SUA_CHAVE_DE_TESTE"
# Carrega OPENAI_API_KEY do .env se existir (mas não hardcode aqui)
if [ -f ".env" ]; then
    echo -e "${GREEN}📝 Carregando OPENAI_API_KEY do .env...${NC}"
    export $(grep -v '^#' .env | grep OPENAI_API_KEY | xargs)
fi

echo -e "${GREEN}✅ Variáveis configuradas:${NC}"
echo "   PORT=$PORT"
echo "   ENVIRONMENT=$ENVIRONMENT"
echo "   DB_TYPE=$DB_TYPE"
echo "   SQLITE_PATH=$SQLITE_PATH"
echo "   OPENAI_API_KEY=${OPENAI_API_KEY:+configurada (oculta)}"
echo ""

echo -e "${GREEN}🚀 Iniciando servidor FastAPI com Gunicorn...${NC}"
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

# Executa o servidor com Gunicorn (como o Cloud Run buildpack faz)
# main:app é o módulo main.py na raiz, exportando app
gunicorn -b 0.0.0.0:${PORT} main:app --workers 1 --timeout 300 --log-level info

