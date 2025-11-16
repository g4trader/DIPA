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

# Cria diretório para banco SQLite ANTES de copiar código
RUN mkdir -p /app/data

# Copia código da aplicação (MAS NÃO copia data/ para evitar sobrescrever)
COPY . .

# IMPORTANTE: Baixa arquivo SQLite do Cloud Storage DEPOIS de copiar código
# NOTA: O arquivo tem ~1.8GB e está no Cloud Storage porque não cabe no git
# Durante o build do Cloud Build, o gcloud CLI já está autenticado
# Esta etapa deve ser executada DEPOIS de COPY para garantir que o diretório existe
RUN export PATH=$PATH:/root/google-cloud-sdk/bin && \
    echo "📥 Verificando banco SQLite..." && \
    if command -v gsutil &> /dev/null; then \
        echo "📥 Baixando banco SQLite do Cloud Storage..." && \
        gsutil -m cp gs://trivihair-dipam-data/dipam_dw.db /app/data/dipam_dw.db && \
        chmod 644 /app/data/dipam_dw.db && \
        echo "✅ Arquivo SQLite baixado com sucesso do Cloud Storage" && \
        ls -lh /app/data/dipam_dw.db && \
        echo "✅ Verificando se arquivo tem conteúdo..." && \
        sqlite3 /app/data/dipam_dw.db "SELECT COUNT(*) FROM metas_vendedor LIMIT 1;" 2>&1 || echo "⚠️  Não foi possível verificar tabelas (pode ser normal se sqlite3 não estiver instalado)"; \
    elif [ -f data/dipam_dw.db ]; then \
        echo "📋 Usando arquivo SQLite local (fallback)..." && \
        cp data/dipam_dw.db /app/data/dipam_dw.db && \
        chmod 644 /app/data/dipam_dw.db && \
        echo "✅ Arquivo SQLite copiado do repositório" && \
        ls -lh /app/data/dipam_dw.db; \
    else \
        echo "⚠️  ATENÇÃO: Arquivo SQLite não encontrado!" && \
        echo "   Tente fazer upload para Cloud Storage: gsutil cp data/dipam_dw.db gs://trivihair-dipam-data/dipam_dw.db"; \
        exit 1; \
    fi

# Verificação final: confirma que o arquivo existe e tem tamanho > 0
RUN if [ -f /app/data/dipam_dw.db ]; then \
        FILE_SIZE=$(stat -f%z /app/data/dipam_dw.db 2>/dev/null || stat -c%s /app/data/dipam_dw.db 2>/dev/null || echo "0"); \
        echo "✅ Verificação final: Arquivo SQLite existe com tamanho ${FILE_SIZE} bytes"; \
        if [ "$FILE_SIZE" -lt 1000 ]; then \
            echo "❌ ERRO: Arquivo SQLite muito pequeno (${FILE_SIZE} bytes) - provavelmente vazio!"; \
            exit 1; \
        fi; \
    else \
        echo "❌ ERRO: Arquivo SQLite não existe em /app/data/dipam_dw.db"; \
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
# IMPORTANTE: FastAPI é ASGI, não WSGI, então precisa usar uvicorn.workers.UvicornWorker
# main:app refere-se ao arquivo main.py na raiz que expõe app de src.api.main
CMD ["gunicorn", "-b", "0.0.0.0:8080", "--workers", "1", "--worker-class", "uvicorn.workers.UvicornWorker", "--timeout", "300", "--log-level", "info", "main:app"]



