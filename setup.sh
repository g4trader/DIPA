#!/bin/bash
# Script de setup do projeto Dipam AI
# Este script configura o ambiente de desenvolvimento

set -e

echo "🚀 Configurando ambiente Dipam AI..."

# Verifica Python 3.11
if ! command -v python3.11 &> /dev/null; then
    echo "❌ Python 3.11 não encontrado. Por favor, instale Python 3.11."
    exit 1
fi

echo "✅ Python 3.11 encontrado"

# Cria ambiente virtual
if [ ! -d "venv" ]; then
    echo "📦 Criando ambiente virtual..."
    python3.11 -m venv venv
else
    echo "✅ Ambiente virtual já existe"
fi

# Ativa ambiente virtual
echo "🔌 Ativando ambiente virtual..."
source venv/bin/activate

# Atualiza pip
echo "📥 Atualizando pip..."
pip install --upgrade pip

# Instala dependências
echo "📚 Instalando dependências..."
pip install -r requirements.txt

# Cria diretórios necessários
echo "📁 Criando diretórios..."
mkdir -p data/raw
mkdir -p data/processed
mkdir -p ml/models
mkdir -p ml/features
mkdir -p logs

# Copia arquivo de exemplo de configuração
if [ ! -f ".env" ]; then
    echo "⚙️  Criando arquivo .env..."
    if [ -f "config/env.example" ]; then
        cp config/env.example .env
        echo "✅ Arquivo .env criado. Por favor, configure as variáveis de ambiente."
    else
        echo "⚠️  Arquivo config/env.example não encontrado"
    fi
else
    echo "✅ Arquivo .env já existe"
fi

echo ""
echo "✅ Setup concluído!"
echo ""
echo "Próximos passos:"
echo "1. Configure o arquivo .env com suas credenciais"
echo "2. Execute: source venv/bin/activate"
echo "3. Execute: uvicorn api.main:app --reload"
echo "4. Acesse: http://localhost:8000/docs"



