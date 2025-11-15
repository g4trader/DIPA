# Árvore de Diretórios do Projeto Dipam AI

```
DIPA/
│
├── src/                          # Código fonte principal
│   ├── __init__.py
│   ├── config.py                 # Configurações centralizadas
│   ├── db_init.py                # Script de inicialização do banco
│   │
│   ├── agent/                    # Módulo do agente de IA comercial
│   │   ├── __init__.py
│   │   ├── intent.py             # Detecção de intenções
│   │   ├── queries.py            # Queries de dados
│   │   └── service.py            # Serviço principal do agente
│   │
│   ├── api/                      # API FastAPI
│   │   ├── main.py               # Aplicação FastAPI
│   │   └── schemas.py            # Schemas Pydantic
│   │
│   ├── data/                     # Módulo de dados (legado)
│   │   ├── __init__.py
│   │   ├── cleaning.py
│   │   └── ingestion.py
│   │
│   ├── dw/                       # Data Warehouse
│   │   ├── __init__.py
│   │   ├── connection.py         # Conexão com banco
│   │   ├── models.py             # Modelos SQLAlchemy
│   │   └── etl.py                # Scripts ETL
│   │
│   ├── features/                 # Feature engineering (módulos separados)
│   │   ├── __init__.py
│   │   ├── churn_features.py
│   │   └── meta_features.py
│   │
│   ├── features.py               # Feature engineering (módulo principal)
│   ├── ingestion.py              # Pipeline de ingestão de CSVs
│   ├── load_to_db.py             # Carregamento de dados no banco
│   ├── llm_integration.py        # Integração com LLM
│   ├── models_ml.py              # Modelos de ML
│   │
│   ├── ml/                       # Módulos de ML (separados)
│   │   ├── __init__.py
│   │   ├── churn_model.py
│   │   └── meta_model.py
│   │
│   ├── run_api.py                # Script CLI para rodar API
│   ├── run_build_features.py     # Script CLI para construir features
│   ├── run_ingestion.py          # Script CLI para ingestão de dados
│   └── run_train_models.py       # Script CLI para treinar modelos
│
├── data_raw/                     # Dados brutos (CSVs originais)
│   ├── *.csv                     # Arquivos CSV de entrada
│   └── README.md                 # Documentação dos dados
│
├── data_processed/               # Dados processados (criado automaticamente)
│   ├── features_vendedor.csv     # Features de vendedor/mês
│   └── features_cliente.csv      # Features de cliente/mês
│
├── models/                       # Modelos treinados (criado automaticamente)
│   └── artefacts/                # Artefatos dos modelos
│       ├── meta_model_*.joblib           # Modelos de bater meta
│       ├── churn_model_*.joblib          # Modelos de churn
│       ├── meta_model_metadata_*.json    # Metadados de meta
│       └── churn_model_metadata_*.json   # Metadados de churn
│
├── logs/                         # Logs da aplicação (criado automaticamente)
│
├── notebooks/                    # Notebooks Jupyter
│   ├── 01_train_models.ipynb     # Treinamento de modelos
│   └── demo_dipam_ai.ipynb       # Notebook de demonstração
│
├── tests/                        # Testes automatizados
│   ├── __init__.py
│   ├── test_api.py               # Testes da API
│   ├── test_full_pipeline.py     # Teste end-to-end do pipeline
│   ├── test_health.py            # Testes de health check
│   ├── test_ingestion.py         # Testes de ingestão
│   ├── test_models.py            # Testes de modelos ML
│   └── test_transformations.py   # Testes de transformações/features
│
├── scripts/                      # Scripts auxiliares
│   ├── __init__.py
│   ├── build_features.py
│   ├── debug_ingestion.py        # Script de debug para validar ingestão
│   ├── debug_scan_data_raw.py    # Script de debug para escanear arquivos CSV
│   ├── init_db.py
│   ├── run_etl.py
│   ├── test_connection.py
│   └── train_models.py
│
├── config/                       # Configurações (legado)
│   ├── __init__.py
│   ├── env.example
│   └── settings.py
│
├── db/                           # Módulo de banco (legado)
│   ├── __init__.py
│   ├── connection.py
│   └── models/
│
├── ml/                           # Módulo ML (legado)
│   ├── __init__.py
│   ├── evaluation/
│   ├── features/
│   └── models/
│
├── data/                         # Módulo de dados (legado)
│   ├── __init__.py
│   ├── cleaning/
│   ├── etl/
│   └── ingestion/
│
├── migrations/                   # Migrações Alembic
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│
├── docker-compose.yml            # Docker Compose (Postgres)
├── Dockerfile                    # Dockerfile da aplicação
├── requirements.txt              # Dependências Python
├── pytest.ini                    # Configuração do pytest
├── run_tests.py                  # Script para rodar testes
├── make_env.py                   # Script de setup do ambiente
│
├── README.md                     # Documentação principal
├── API_README.md                 # Documentação da API
├── ARCHITECTURE.md               # Documentação de arquitetura
├── STRUCTURE.md                  # Documentação de estrutura
├── MODELS.md                     # Documentação de modelos
├── QUICKSTART.md                 # Guia rápido de início
│
└── [Frontend Next.js]            # Frontend (se aplicável)
    ├── app/
    ├── components/
    ├── styles/
    └── package.json
```

## Resumo dos Diretórios Principais

### `src/`
Código fonte principal do projeto:
- **agent/**: Módulo do agente de IA comercial (detecção de intenções, queries, serviço)
- **api/**: API FastAPI (endpoints, schemas)
- **dw/**: Data Warehouse (conexão, modelos SQLAlchemy, ETL)
- **features/**: Feature engineering (features de churn e meta)
- **ml/**: Modelos de ML (churn e meta)
- **Scripts CLI**: `run_ingestion.py`, `run_build_features.py`, `run_train_models.py`, `run_api.py`

### `data_raw/`
Arquivos CSV brutos para ingestão:
- CSVs de clientes, vendas, metas (vendedor e departamento)

### `data_processed/`
Dados processados e features:
- `features_vendedor.csv`: Features de vendedor/mês para ML
- `features_cliente.csv`: Features de cliente/mês para ML

### `models/artefacts/`
Modelos treinados e metadados:
- Modelos `.joblib` (meta e churn)
- Metadados `.json` com métricas e versões

### `notebooks/`
Notebooks Jupyter para análise e demonstração:
- `01_train_models.ipynb`: Treinamento de modelos
- `demo_dipam_ai.ipynb`: Notebook de demonstração para clientes

### `tests/`
Testes automatizados:
- `test_api.py`: Testes da API FastAPI
- `test_ingestion.py`: Testes de ingestão
- `test_transformations.py`: Testes de features
- `test_models.py`: Testes de modelos ML
- `test_full_pipeline.py`: Teste end-to-end completo

