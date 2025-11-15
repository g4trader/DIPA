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

# Instala gsutil para baixar arquivo do Cloud Storage
RUN apt-get update && apt-get install -y \
    curl \
    python3 \
    && curl https://sdk.cloud.google.com | bash \
    && export PATH=$PATH:/root/google-cloud-sdk/bin \
    && gcloud components install gsutil -q || true \
    && rm -rf /var/lib/apt/lists/*

# Cria diretório para banco SQLite
RUN mkdir -p /app/data

# Copia código da aplicação
COPY . .

# Baixa arquivo SQLite do Cloud Storage durante o build
# NOTA: O arquivo tem ~1.8GB e está no Cloud Storage porque não cabe no git
# Durante o build do Cloud Build, o gcloud CLI já está autenticado
RUN export PATH=$PATH:/root/google-cloud-sdk/bin && \
    if command -v gsutil &> /dev/null; then \
        echo "📥 Baixando banco SQLite do Cloud Storage..." && \
        gsutil cp gs://trivihair-dipam-data/dipam_dw.db /app/data/dipam_dw.db && \
        chmod 644 /app/data/dipam_dw.db && \
        echo "✅ Arquivo SQLite baixado com sucesso do Cloud Storage"; \
    elif [ -f data/dipam_dw.db ]; then \
        echo "📋 Usando arquivo SQLite local (fallback)..." && \
        cp data/dipam_dw.db /app/data/dipam_dw.db && \
        chmod 644 /app/data/dipam_dw.db && \
        echo "✅ Arquivo SQLite copiado do repositório"; \
    else \
        echo "⚠️  ATENÇÃO: Arquivo SQLite não encontrado!" && \
        echo "   Tente fazer upload para Cloud Storage: gsutil cp data/dipam_dw.db gs://trivihair-dipam-data/dipam_dw.db"; \
        exit 1; \
    fi

# Variáveis de ambiente padrão para SQLite em produção
# Pode ser sobrescrito via variáveis de ambiente do Cloud Run
ENV DB_TYPE=sqlite
ENV SQLITE_PATH=/app/data/dipam_dw.db
ENV PORT=8080

EXPOSE 8080

# Comando para executar a aplicação
# Cloud Run espera que a aplicação escute na porta definida por PORT
# Usa src.api.main:app pois o app FastAPI está em src/api/main.py
CMD exec uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8080}



