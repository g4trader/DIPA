# Guia Rápido - Dipam AI

Este guia ajuda você a começar rapidamente com o projeto Dipam AI.

## 🚀 Início Rápido

### 1. Setup do Ambiente

```bash
# Opção 1: Usar o script de setup
./setup.sh

# Opção 2: Setup manual
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
cp config/env.example .env
```

### 2. Configurar Variáveis de Ambiente

Edite o arquivo `.env` com suas credenciais:

```bash
# Para BigQuery
DATABASE_TYPE=bigquery
BIGQUERY_PROJECT_ID=seu-project-id
BIGQUERY_DATASET=seu-dataset
BIGQUERY_CREDENTIALS_PATH=caminho/para/credenciais.json

# Ou para PostgreSQL
DATABASE_TYPE=postgresql
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=seu_usuario
POSTGRES_PASSWORD=sua_senha
POSTGRES_DB=dipam_ai
```

### 3. Testar Conexão com Banco de Dados

```bash
python scripts/test_connection.py
```

### 4. Executar a API

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Acessar a API

- API: http://localhost:8000
- Health Check: http://localhost:8000/health
- Documentação: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📝 Próximos Passos

### Criar um Modelo SQLAlchemy

1. Crie um novo arquivo em `db/models/` (ex: `db/models/vendas.py`)
2. Defina o modelo herdando de `Base`:

```python
from sqlalchemy import Column, Integer, String, DateTime
from db.connection import Base

class Venda(Base):
    __tablename__ = "vendas"
    
    id = Column(Integer, primary_key=True, index=True)
    produto = Column(String(255), nullable=False)
    valor = Column(Integer, nullable=False)
    # ... outros campos
```

3. Importe o modelo em `db/models/__init__.py`

### Criar uma Rota

1. Crie um arquivo em `api/routes/` (ex: `api/routes/vendas.py`)
2. Defina as rotas:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.connection import get_db
from db.models.vendas import Venda

router = APIRouter()

@router.get("/vendas")
def get_vendas(db: Session = Depends(get_db)):
    return db.query(Venda).all()
```

3. Registre a rota em `api/routes/__init__.py`
4. Inclua o router em `api/main.py`

### Criar um Pipeline ETL

1. Use o exemplo em `data/etl/example_etl.py` como referência
2. Adapte para suas necessidades:

```python
from data.etl.example_etl import run_etl_pipeline

run_etl_pipeline("data/raw/meu_arquivo.csv", "minha_tabela")
```

### Executar Testes

```bash
pytest tests/
```

## 🔍 Comandos Úteis

```bash
# Executar API
uvicorn api.main:app --reload

# Executar testes
pytest tests/

# Testar conexão
python scripts/test_connection.py

# Executar ETL
python data/etl/example_etl.py
```

## 📚 Documentação Adicional

- `README.md`: Documentação principal
- `STRUCTURE.md`: Estrutura detalhada do projeto
- `api/main.py`: Aplicação FastAPI principal
- `config/settings.py`: Configurações da aplicação

## 🐛 Troubleshooting

### Erro ao conectar com BigQuery

- Verifique se as credenciais estão configuradas corretamente
- Verifique se o arquivo de credenciais existe e está acessível
- Verifique se o projeto e dataset estão configurados

### Erro ao conectar com PostgreSQL

- Verifique se o PostgreSQL está rodando
- Verifique se as credenciais estão corretas
- Verifique se o banco de dados existe

### Erro ao executar a API

- Verifique se todas as dependências estão instaladas
- Verifique se as variáveis de ambiente estão configuradas
- Verifique os logs para mais detalhes

## 📞 Suporte

Para dúvidas ou problemas, entre em contato com a equipe de desenvolvimento.




