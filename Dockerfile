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

# Cria diretório para banco SQLite (garante que existe antes de copiar o arquivo)
RUN mkdir -p /app/data

# Copia código da aplicação
COPY . .

# Copia arquivo SQLite do banco de dados populado pelo ETL
# Este arquivo contém os dados de metas e vendas necessários para produção
# IMPORTANTE: O arquivo deve estar commitado no repositório ou ser copiado no build
COPY data/dipam_dw.db /app/data/dipam_dw.db

# Garante permissões corretas para o banco SQLite
RUN chmod 644 /app/data/dipam_dw.db

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



