# Estrutura do Projeto Dipam AI

Este documento descreve a estrutura do projeto e como cada módulo se relaciona.

## 📁 Estrutura de Diretórios

```
dipam-ai/
├── api/                    # API FastAPI
│   ├── main.py            # Aplicação principal FastAPI
│   ├── routes/            # Rotas da API organizadas por funcionalidade
│   └── services/          # Lógica de negócio (separada das rotas)
│
├── config/                # Configurações
│   ├── settings.py        # Configurações centralizadas (Pydantic Settings)
│   └── env.example        # Exemplo de variáveis de ambiente
│
├── data/                  # Processamento de dados
│   ├── ingestion/         # Scripts de ingestão de dados (CSV, Excel, APIs)
│   ├── cleaning/          # Funções de limpeza e normalização
│   └── etl/               # Pipelines ETL completos
│
├── db/                    # Database
│   ├── connection.py      # Conexão com banco (BigQuery/PostgreSQL)
│   ├── bigquery_client.py # Cliente BigQuery para operações diretas
│   └── models/            # Modelos SQLAlchemy
│
├── ml/                    # Machine Learning
│   ├── features/          # Feature engineering
│   ├── models/            # Modelos treinados e funções de treinamento
│   └── evaluation/        # Avaliação de modelos
│
├── tests/                 # Testes
│   └── test_health.py     # Testes básicos
│
├── requirements.txt       # Dependências Python
├── Dockerfile            # Docker para Cloud Run
├── setup.sh              # Script de setup do ambiente
└── README.md             # Documentação principal
```

## 🔧 Componentes Principais

### API (api/)

A API FastAPI é o ponto de entrada principal da aplicação. Ela:
- Expõe endpoints REST
- Inicializa conexões com banco de dados
- Organiza rotas por funcionalidade
- Separa lógica de negócio em serviços

**Principais arquivos:**
- `api/main.py`: Aplicação FastAPI principal com eventos de startup/shutdown
- `api/routes/`: Rotas organizadas por funcionalidade
- `api/services/`: Lógica de negócio reutilizável

### Configuração (config/)

Centraliza todas as configurações usando Pydantic Settings:
- Lê variáveis de ambiente
- Fornece valores padrão
- Valida configurações
- Suporta diferentes ambientes (dev, staging, prod)

**Principais arquivos:**
- `config/settings.py`: Configurações centralizadas
- `config/env.example`: Exemplo de variáveis de ambiente

### Database (db/)

Gerencia conexões com banco de dados:
- Suporta BigQuery e PostgreSQL
- Usa SQLAlchemy para ORM
- Fornece cliente direto para BigQuery quando necessário
- Define modelos de dados

**Principais arquivos:**
- `db/connection.py`: Conexão SQLAlchemy unificada
- `db/bigquery_client.py`: Cliente BigQuery para operações diretas
- `db/models/`: Modelos SQLAlchemy

### Data Processing (data/)

Processa e transforma dados:
- **Ingestion**: Carrega dados de diversas fontes
- **Cleaning**: Limpa e normaliza dados
- **ETL**: Pipelines completos de ETL

**Principais arquivos:**
- `data/ingestion/csv_loader.py`: Carregador de CSV
- `data/cleaning/cleaners.py`: Funções de limpeza
- `data/etl/example_etl.py`: Exemplo de pipeline ETL

### Machine Learning (ml/)

Modelos e features de ML:
- **Features**: Feature engineering
- **Models**: Modelos treinados e funções de treinamento
- **Evaluation**: Avaliação de modelos

## 🔄 Fluxo de Dados

1. **Ingestão**: Dados são carregados de CSV/Excel/APIs
2. **Limpeza**: Dados são limpos e normalizados
3. **ETL**: Dados são transformados e carregados no data warehouse
4. **Feature Engineering**: Features são criadas para ML
5. **Modelagem**: Modelos são treinados e avaliados
6. **API**: Modelos são expostos via API

## 🚀 Deploy

O projeto está preparado para deploy no Google Cloud Run:

1. **Dockerfile**: Cria imagem Docker da aplicação
2. **Cloud Run**: Deploy automático via Dockerfile
3. **Variáveis de Ambiente**: Configuradas no Cloud Run

## 📝 Próximos Passos

1. Criar modelos SQLAlchemy específicos para o domínio
2. Implementar rotas de API para funcionalidades específicas
3. Desenvolver pipelines ETL para dados reais
4. Treinar modelos de ML conforme necessário
5. Configurar testes automatizados
6. Configurar CI/CD para deploy

## 🔍 Notas Importantes

### BigQuery vs PostgreSQL

- **BigQuery**: Usado como data warehouse principal. Para operações complexas, use `db/bigquery_client.py` diretamente.
- **PostgreSQL**: Alternativa para desenvolvimento local ou quando necessário um banco relacional tradicional.

### SQLAlchemy com BigQuery

O SQLAlchemy pode ser usado com BigQuery através de drivers como `sqlalchemy-bigquery` ou `pybigquery`, mas para operações mais complexas (queries complexas, jobs de carga), é recomendado usar `google-cloud-bigquery` diretamente.

### Configuração

Sempre configure as variáveis de ambiente antes de executar a aplicação. Use `config/env.example` como referência.





