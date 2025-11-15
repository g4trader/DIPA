# Dockerfile para deploy no Cloud Run
# Este Dockerfile cria uma imagem Docker para a aplicação Dipam AI

FROM python:3.11-slim

# Define diretório de trabalho
WORKDIR /app

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copia arquivos de dependências
COPY requirements.txt .

# Instala dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia código da aplicação
COPY . .

# Expõe porta (Cloud Run usa a variável PORT)
ENV PORT=8080
EXPOSE 8080

# Comando para executar a aplicação
# Cloud Run espera que a aplicação escute na porta definida por PORT
# Usa src.api.main:app pois o app FastAPI está em src/api/main.py
CMD exec uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8080}



