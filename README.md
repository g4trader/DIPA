# Dipam AI - Analytics e Machine Learning

Sistema de analytics e machine learning para dados comerciais da empresa DIPAM, focado em análise de vendas, metas e risco de churn de clientes.

## 🎯 Objetivo

Este repositório contém um pipeline completo de dados e modelos de ML para:

1. **Ingestão de dados**: Carregamento e processamento de CSVs brutos (clientes, vendas, metas, supervisores)
2. **Padronização e limpeza**: Normalização de datas, valores monetários (R$), números com vírgula
3. **Data Warehouse**: Armazenamento estruturado em PostgreSQL (via Docker) ou SQLite
4. **Feature Engineering**: Criação de features para modelos de ML
5. **Modelos de ML**:
   - **Probabilidade de bater meta**: Previsão de probabilidade de um vendedor bater a meta em um determinado mês
   - **Risco de churn**: Previsão de risco de churn de clientes

## 📁 Estrutura do Projeto

```
dipam-ai/
├── src/                    # Código fonte Python
│   ├── config.py          # Configurações centralizadas
│   ├── data/              # Processamento de dados
│   │   ├── ingestion.py   # Carregamento de CSVs
│   │   └── cleaning.py    # Limpeza e padronização
│   ├── dw/                # Data Warehouse
│   │   ├── connection.py  # Conexão com banco
│   │   ├── models.py      # Modelos SQLAlchemy
│   │   └── etl.py         # Pipeline ETL
│   ├── features/          # Feature Engineering
│   │   ├── meta_features.py    # Features para modelo de meta
│   │   └── churn_features.py   # Features para modelo de churn
│   └── ml/                # Machine Learning
│       ├── meta_model.py       # Modelo de probabilidade de bater meta
│       └── churn_model.py      # Modelo de risco de churn
├── data_raw/              # Dados brutos (CSVs originais)
├── data_processed/        # Dados processados
├── data_warehouse/        # Scripts SQL e migrations
├── models/                # Modelos treinados (salvos)
├── notebooks/             # Jupyter notebooks para análise
├── features/              # Features exportadas
├── scripts/               # Scripts utilitários
│   ├── init_db.py        # Inicializa banco de dados
│   ├── run_etl.py        # Executa pipeline ETL
│   └── train_models.py   # Treina modelos de ML
├── tests/                 # Testes
├── docker-compose.yml     # Docker Compose para PostgreSQL
├── make_env.py           # Script de setup do ambiente
├── requirements.txt      # Dependências Python
└── README.md             # Este arquivo
```

## 🚀 Instalação e Setup

### Pré-requisitos

- Python 3.11+
- Docker e Docker Compose (para PostgreSQL)
- Git

### Setup Automático

Execute o script de setup:

```bash
python make_env.py
```

Este script irá:
1. Criar ambiente virtual
2. Instalar dependências
3. Criar diretórios necessários
4. Criar arquivo `.env` com configurações
5. Iniciar Docker Compose (opcional)
6. Inicializar banco de dados (opcional)

### Setup Manual

1. **Criar ambiente virtual**:
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate  # Linux/Mac
   # ou
   venv\Scripts\activate  # Windows
   ```

2. **Instalar dependências**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurar variáveis de ambiente**:
   ```bash
   cp .env.example .env
   # Edite .env com suas configurações
   ```

4. **Iniciar Docker Compose** (para PostgreSQL):
   ```bash
   docker compose up -d
   ```

5. **Inicializar banco de dados**:
   ```bash
   python scripts/init_db.py
   ```

## 🔄 Fluxo de Dados

### 1. Ingestão (Ingestion)

Dados brutos em CSV são carregados através do módulo `src/data/ingestion.py`:

```python
from src.data.ingestion import load_csv

df = load_csv("data_raw/clientes.csv")
```

### 2. Limpeza e Padronização (Cleaning)

Dados são limpos e padronizados através do módulo `src/data/cleaning.py`:

```python
from src.data.cleaning import (
    clean_data,
    standardize_dates,
    standardize_currency,
    normalize_strings
)

# Limpa dados
df = clean_data(df, remove_duplicates=True)

# Padroniza datas
df = standardize_dates(df, ["data_cadastro"])

# Padroniza valores monetários
df = standardize_currency(df, ["valor"])

# Normaliza strings
df = normalize_strings(df, columns=["nome", "cidade"])
```

### 3. Data Warehouse (ETL)

Dados processados são carregados no data warehouse através do módulo `src/dw/etl.py`:

```python
from src.dw.etl import load_clientes, load_vendas

# Carrega clientes
load_clientes(df_clientes)

# Carrega vendas
load_vendas(df_vendas)
```

### 4. Feature Engineering

Features são criadas para modelos de ML:

```python
from src.features.meta_features import create_meta_features
from src.features.churn_features import create_churn_features

# Features para modelo de meta
df_meta = create_meta_features(ano=2024, mes=12)

# Features para modelo de churn
df_churn = create_churn_features()
```

### 5. Machine Learning

Modelos são treinados e usados para fazer predições:

```python
from src.ml.meta_model import MetaModel
from src.ml.churn_model import ChurnModel

# Treina modelo de meta
meta_model = MetaModel()
metrics = meta_model.train_from_datawarehouse(
    start_ano=2024,
    start_mes=1,
    end_ano=2024,
    end_mes=12
)
meta_model.save()

# Treina modelo de churn
churn_model = ChurnModel()
metrics = churn_model.train_from_datawarehouse()
churn_model.save()

# Faz predições
probabilidades = meta_model.predict(df_features)
riscos = churn_model.predict(df_features)
```

## 📊 Modelos de ML

### 1. Probabilidade de Bater Meta

**Objetivo**: Prever a probabilidade de um vendedor bater a meta em um determinado mês.

**Features**:
- Percentual de meta atingida nos últimos meses
- Média móvel dos últimos 3 meses
- Desvio padrão dos últimos 3 meses
- Total de vendas no mês
- Número de vendas no mês
- Features temporais (mês, estação)

**Algoritmo**: Random Forest ou Gradient Boosting

**Métricas**: Accuracy, Precision, Recall, F1-Score, ROC-AUC

### 2. Risco de Churn

**Objetivo**: Prever o risco de churn de clientes.

**Features**:
- Total de vendas nos últimos 90 dias
- Número de vendas nos últimos 90 dias
- Dias desde última venda
- Total de vendas histórico
- Média de vendas por mês
- Recência, Frequência, Valor (RFV)
- Tendência de vendas

**Algoritmo**: Random Forest ou Gradient Boosting

**Métricas**: Accuracy, Precision, Recall, F1-Score, ROC-AUC

**Score de Risco**:
- **Baixo**: Probabilidade < 30%
- **Médio**: Probabilidade entre 30% e 70%
- **Alto**: Probabilidade > 70%

## 🔧 Uso

### Executar Pipeline ETL

```bash
python scripts/run_etl.py
```

Este script:
1. Carrega dados brutos de `data_raw/`
2. Limpa e padroniza dados
3. Carrega dados no data warehouse

### Treinar Modelos

```bash
python scripts/train_models.py
```

Este script:
1. Cria features a partir do data warehouse
2. Treina modelos de ML
3. Avalia modelos
4. Salva modelos treinados em `models/`

### Usar Modelos

```python
from src.ml.meta_model import MetaModel
from src.ml.churn_model import ChurnModel

# Carrega modelo
meta_model = MetaModel()
meta_model.load()

# Faz predições
probabilidades = meta_model.predict(df_features)

# Carrega modelo de churn
churn_model = ChurnModel()
churn_model.load()

# Faz predições
riscos = churn_model.predict(df_features)
scores = [churn_model.predict_risk_score(p) for p in riscos]
```

## 📝 Configuração

### Arquivo `.env`

```env
# Ambiente
ENVIRONMENT=development
DEBUG=True
LOG_LEVEL=INFO

# Banco de dados
DB_TYPE=postgresql
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=dipam_user
POSTGRES_PASSWORD=dipam_password
POSTGRES_DB=dipam_dw

# SQLite (alternativa)
# DB_TYPE=sqlite
# SQLITE_PATH=data/dipam_dw.db

# ML
ML_RANDOM_SEED=42
ML_TEST_SIZE=0.2
ML_CV_FOLDS=5
```

### Docker Compose

O arquivo `docker-compose.yml` configura um container PostgreSQL:

```yaml
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: dipam_user
      POSTGRES_PASSWORD: dipam_password
      POSTGRES_DB: dipam_dw
    ports:
      - "5432:5432"
```

## 🧪 Testes

```bash
pytest tests/
```

## 📚 Notebooks

Jupyter notebooks estão disponíveis em `notebooks/` para análise exploratória de dados.

## 🔍 Arquitetura

### Fluxo de Dados

```
CSV Brutos → Ingestão → Limpeza → ETL → Data Warehouse → Features → ML → Predições
```

### Componentes

1. **Ingestão**: Carrega dados de CSVs
2. **Limpeza**: Padroniza e limpa dados
3. **ETL**: Carrega dados no data warehouse
4. **Features**: Cria features para ML
5. **ML**: Treina e usa modelos de ML
6. **Predições**: Gera predições e scores

## 🚀 Próximos Passos

1. Integração com API/Backend
2. Integração com agente de GenAI
3. Deploy de modelos em produção
4. Monitoramento de modelos
5. Retreinamento automático
6. Dashboards e visualizações

## 📞 Contato

Para dúvidas ou problemas, entre em contato com a equipe de desenvolvimento.

## 📄 Licença

Proprietário - Dipam
