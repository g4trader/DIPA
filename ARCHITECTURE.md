# Arquitetura do Projeto Dipam AI

Este documento descreve a arquitetura e o fluxo de dados do projeto.

## 🏗️ Arquitetura Geral

```
┌─────────────┐
│  CSV Brutos │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Ingestão   │ ◄─── src/data/ingestion.py
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Limpeza   │ ◄─── src/data/cleaning.py
└──────┬──────┘
       │
       ▼
┌─────────────┐
│     ETL     │ ◄─── src/dw/etl.py
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Data        │
│ Warehouse   │ ◄─── BigQuery/PostgreSQL/SQLite
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Features   │ ◄─── src/features/
└──────┬──────┘
       │
       ▼
┌─────────────┐
│     ML      │ ◄─── src/ml/
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Predições   │
└─────────────┘
```

## 📊 Fluxo de Dados

### 1. Ingestão (Ingestion)

**Módulo**: `src/data/ingestion.py`

**Responsabilidade**:
- Carregar dados de arquivos CSV
- Validar dados
- Tratar diferentes encodings

**Funções principais**:
- `load_csv()`: Carrega CSV em DataFrame
- `validate_data()`: Valida dados conforme regras
- `load_multiple_csvs()`: Carrega múltiplos CSVs

### 2. Limpeza e Padronização (Cleaning)

**Módulo**: `src/data/cleaning.py`

**Responsabilidade**:
- Limpar dados (remover duplicatas, tratar valores faltantes)
- Padronizar datas (formatos brasileiros)
- Padronizar valores monetários (R$ 1.234,56)
- Padronizar números com vírgula
- Normalizar strings

**Funções principais**:
- `clean_data()`: Limpa dados gerais
- `standardize_dates()`: Padroniza datas
- `standardize_currency()`: Padroniza valores monetários
- `standardize_numbers()`: Padroniza números
- `normalize_strings()`: Normaliza strings

### 3. ETL (Extract, Transform, Load)

**Módulo**: `src/dw/etl.py`

**Responsabilidade**:
- Carregar dados processados no data warehouse
- Mapear dados para modelos SQLAlchemy
- Atualizar cálculos derivados

**Funções principais**:
- `load_data_to_dw()`: Carrega dados no banco
- `load_clientes()`: Carrega clientes
- `load_vendedores()`: Carrega vendedores
- `load_vendas()`: Carrega vendas
- `load_metas_vendedor()`: Carrega metas
- `update_percentual_atingido()`: Atualiza percentual de meta

### 4. Data Warehouse

**Módulo**: `src/dw/`

**Responsabilidade**:
- Armazenar dados estruturados
- Fornecer acesso aos dados via SQLAlchemy
- Gerenciar modelos de dados

**Modelos**:
- `Cliente`: Clientes da empresa
- `Vendedor`: Vendedores da empresa
- `Supervisor`: Supervisores/pastas
- `Venda`: Vendas realizadas
- `MetaVendedor`: Metas por vendedor/mês
- `MetaDepartamento`: Metas por departamento/mês
- `MetaPrediction`: Predições de meta
- `ChurnRisk`: Risco de churn

### 5. Feature Engineering

**Módulo**: `src/features/`

**Responsabilidade**:
- Criar features para modelos de ML
- Extrair features históricas
- Calcular features derivadas

**Módulos**:
- `meta_features.py`: Features para modelo de meta
- `churn_features.py`: Features para modelo de churn

### 6. Machine Learning

**Módulo**: `src/ml/`

**Responsabilidade**:
- Treinar modelos de ML
- Fazer predições
- Avaliar modelos
- Salvar/carregar modelos

**Modelos**:
- `MetaModel`: Modelo de probabilidade de bater meta
- `ChurnModel`: Modelo de risco de churn

## 🔄 Pipeline Completo

### Executar Pipeline ETL

```bash
python scripts/run_etl.py
```

**Fluxo**:
1. Carrega CSVs de `data_raw/`
2. Valida dados
3. Limpa e padroniza dados
4. Carrega dados no data warehouse
5. Atualiza cálculos derivados

### Treinar Modelos

```bash
python scripts/train_models.py
```

**Fluxo**:
1. Cria features do data warehouse
2. Prepara dados para treinamento
3. Treina modelos de ML
4. Avalia modelos
5. Salva modelos em `models/`

### Usar Modelos

```python
from src.ml.meta_model import MetaModel
from src.ml.churn_model import ChurnModel

# Carrega modelo
meta_model = MetaModel()
meta_model.load()

# Cria features
from src.features.meta_features import create_meta_features
df_features = create_meta_features(ano=2024, mes=12)

# Faz predições
probabilidades = meta_model.predict(df_features)
```

## 📦 Componentes

### Configuração

**Módulo**: `src/config.py`

**Responsabilidade**:
- Centralizar configurações
- Gerenciar variáveis de ambiente
- Fornecer acesso a configurações

**Classes**:
- `DatabaseConfig`: Configurações de banco de dados
- `PathsConfig`: Configurações de paths
- `MLConfig`: Configurações de ML
- `Config`: Configuração principal

### Data Warehouse

**Módulo**: `src/dw/`

**Responsabilidade**:
- Gerenciar conexão com banco
- Definir modelos de dados
- Executar ETL

**Arquivos**:
- `connection.py`: Conexão com banco
- `models.py`: Modelos SQLAlchemy
- `etl.py`: Pipeline ETL

### Features

**Módulo**: `src/features/`

**Responsabilidade**:
- Criar features para ML
- Extrair features históricas
- Calcular features derivadas

**Arquivos**:
- `meta_features.py`: Features para modelo de meta
- `churn_features.py`: Features para modelo de churn

### ML

**Módulo**: `src/ml/`

**Responsabilidade**:
- Treinar modelos de ML
- Fazer predições
- Avaliar modelos

**Arquivos**:
- `meta_model.py`: Modelo de meta
- `churn_model.py`: Modelo de churn

## 🚀 Próximos Passos

1. **Integração com API/Backend**
   - Criar endpoints para predições
   - Expor modelos via API REST
   - Criar endpoints para features

2. **Integração com GenAI**
   - Criar agentes de GenAI
   - Integrar predições com GenAI
   - Criar prompts para análise

3. **Deploy**
   - Deploy de modelos em produção
   - Monitoramento de modelos
   - Retreinamento automático

4. **Visualização**
   - Dashboards e visualizações
   - Relatórios automáticos
   - Alertas e notificações

## 📝 Notas

- O projeto usa SQLAlchemy para acesso ao banco de dados
- PostgreSQL é recomendado para produção
- SQLite pode ser usado para desenvolvimento
- Modelos são salvos em `models/` usando joblib
- Features são calculadas dinamicamente do data warehouse
- Pipeline ETL é executado via scripts Python





