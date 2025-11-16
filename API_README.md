# API do Agente Comercial - Dipam AI

API FastAPI para o agente de IA comercial que permite interação em linguagem natural com os dados da empresa.

## 🚀 Características

- **Endpoint `/ask`**: Pergunte ao agente em linguagem natural
- **Endpoint `/preview/vendedor/{vendedor}/{mes_ano}`**: Dados numéricos de vendedor/mês
- **Endpoint `/health`**: Health check da API
- **Integração com LLM**: Respostas em linguagem natural (stub pronto para OpenAI)
- **Integração com ML**: Usa modelos treinados para predições
- **Queries SQLAlchemy**: Busca dados do banco de forma eficiente

## 📦 Pré-requisitos

- Python 3.11+
- Banco de dados configurado (PostgreSQL ou SQLite)
- Modelos de ML treinados (opcional, mas recomendado)

## 🔧 Instalação

### 1. Instalar dependências

```bash
pip install -r requirements.txt
```

### 2. Configurar variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
# Database
DB_TYPE=postgresql
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=dipam_user
POSTGRES_PASSWORD=dipam_password
POSTGRES_DB=dipam_dw

# API
API_AGENT_PORT=8000
API_AGENT_HOST=0.0.0.0

# Environment
ENVIRONMENT=development
DEBUG=True
LOG_LEVEL=INFO
```

### 3. Inicializar banco de dados

```bash
python src/db_init.py
```

### 4. Carregar dados (opcional)

```bash
python src/run_ingestion.py
```

### 5. Treinar modelos (opcional)

```bash
python scripts/train_models.py
```

## 🚀 Executar API Localmente

### Opção 1: Diretamente com Python

```bash
python src/api/main.py
```

### Opção 2: Com uvicorn

```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Opção 3: Com variável de ambiente

```bash
PORT=8000 uvicorn src.api.main:app --reload
```

A API estará disponível em: `http://localhost:8000`

## 📚 Endpoints

### 1. GET `/health`

Health check da API.

**Resposta:**
```json
{
  "status": "healthy",
  "timestamp": "2024-12-01T10:00:00",
  "environment": "development",
  "version": "1.0.0",
  "database": "postgresql"
}
```

### 2. POST `/ask`

Pergunte ao agente em linguagem natural.

**Request:**
```json
{
  "pergunta": "Por que o vendedor ROTA 77 não bateu a meta em dezembro?",
  "usuario_id": "user123",
  "papel": "supervisor"
}
```

**Resposta:**
```json
{
  "resposta": "## Análise de Meta - ROTA 77 (2024-12)\n\n**Situação Atual:**\n- Meta: R$ 100,000.00\n- Realizado: R$ 85,000.00\n- Percentual Atingido: 85.0%\n- Gap: R$ 15,000.00\n\n**Análise:**\nO vendedor não atingiu a meta, ficando 15.0% abaixo do esperado...",
  "intent": "meta_vendedor",
  "contexto": {
    "vendedor": "ROTA 77",
    "mes_ano": "2024-12",
    "meta_valor": 100000.0,
    "realizado_valor": 85000.0,
    "perc_atingido": 85.0
  },
  "confianca": 0.8,
  "timestamp": "2024-12-01T10:00:00"
}
```

**Exemplos de perguntas:**
- "Por que a equipe do Supervisor X não bateu a meta em janeiro?"
- "Quais clientes da rota 12 estão em maior risco de churn este mês?"
- "Analise as vendas do vendedor ROTA 77 em dezembro"
- "Ranking dos vendedores por meta atingida em novembro"

### 3. GET `/preview/vendedor/{vendedor}/{mes_ano}`

Retorna dados numéricos de um vendedor/mês sem processamento pelo LLM.

**Exemplo:**
```
GET /preview/vendedor/ROTA%2077/2024-12
```

**Resposta:**
```json
{
  "vendedor": "ROTA 77",
  "mes_ano": "2024-12",
  "dados": {
    "vendedor": "ROTA 77",
    "vendedor_codigo": "ROTA 77",
    "supervisor": "Supervisor X",
    "mes_ano": "2024-12",
    "meta_valor": 100000.0,
    "realizado_valor": 85000.0,
    "gap_valor": -15000.0,
    "perc_atingido": 85.0,
    "meta_volume": 1000,
    "realizado_volume": 850,
    "perc_atingido_volume": 85.0,
    "total_vendas": 85000.0,
    "qtd_clientes": 50,
    "ticket_medio": 1700.0
  },
  "timestamp": "2024-12-01T10:00:00"
}
```

## 🔍 Documentação Interativa

A API expõe documentação interativa usando Swagger UI:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🏗️ Arquitetura

### Pipeline do Endpoint `/ask`

```
Pergunta do Usuário
    ↓
Detecção de Intenção (intent.py)
    ↓
Queries no Banco (queries.py)
    ↓
Enriquecimento com ML (service.py)
    ↓
Geração de Resposta (llm_integration.py)
    ↓
Resposta em Linguagem Natural
```

### Componentes

1. **`src/api/main.py`**: API FastAPI com endpoints
2. **`src/agent/intent.py`**: Detecção de intenções
3. **`src/agent/queries.py`**: Queries SQLAlchemy
4. **`src/agent/service.py`**: Orquestração do agente
5. **`src/llm_integration.py`**: Integração com LLM (stub)

## 🔧 Integração com LLM Real

Para integrar com OpenAI (ou outro LLM), edite `src/llm_integration.py`:

```python
def call_llm(contexto, pergunta, temperatura=0.7, max_tokens=1000):
    import openai
    
    prompt = format_prompt(contexto, pergunta)
    
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Você é um assistente comercial..."},
            {"role": "user", "content": prompt}
        ],
        temperature=temperatura,
        max_tokens=max_tokens
    )
    
    return response.choices[0].message.content
```

Configure a API key no `.env`:
```env
OPENAI_API_KEY=sk-...
```

## 🐳 Deploy no Cloud Run

A API está preparada para deploy no Google Cloud Run. O Dockerfile e configurações já estão criados.

1. Build da imagem:
```bash
docker build -t dipam-ai-agent .
```

2. Teste local:
```bash
docker run -p 8000:8000 dipam-ai-agent
```

3. Deploy no Cloud Run:
```bash
gcloud run deploy dipam-ai-agent \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

## 📝 Exemplos de Uso

### cURL

```bash
# Health check
curl http://localhost:8000/health

# Pergunta ao agente
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "pergunta": "Por que o vendedor ROTA 77 não bateu a meta em dezembro?",
    "papel": "supervisor"
  }'

# Preview de vendedor
curl http://localhost:8000/preview/vendedor/ROTA%2077/2024-12
```

### Python

```python
import requests

# Pergunta ao agente
response = requests.post(
    "http://localhost:8000/ask",
    json={
        "pergunta": "Quais clientes da rota 12 estão em maior risco de churn?",
        "papel": "supervisor"
    }
)

result = response.json()
print(result["resposta"])
```

## 🐛 Troubleshooting

### Erro ao conectar com banco de dados

- Verifique se o PostgreSQL está rodando (se usar Docker: `docker compose up -d`)
- Verifique as credenciais no arquivo `.env`
- Execute `python src/db_init.py` para inicializar o banco

### Modelos de ML não encontrados

- Execute `python scripts/train_models.py` para treinar os modelos
- Os modelos são opcionais, a API funciona sem eles

### Erro ao iniciar a API

- Verifique se a porta 8000 está disponível
- Verifique se todas as dependências estão instaladas
- Veja os logs para mais detalhes

## 🔐 Segurança

Em produção:
- Configure autenticação/autorização
- Use HTTPS
- Limite origens CORS
- Valide inputs
- Rate limiting

## 📞 Suporte

Para dúvidas ou problemas, entre em contato com a equipe de desenvolvimento.




