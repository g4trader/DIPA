# 📚 DOCUMENTAÇÃO COMPLETA - DIPAM COPILOT

**Versão:** 1.0.0  
**Data:** Novembro 2025  
**Status:** Em Produção

---

## 📋 ÍNDICE

1. [Visão Geral do Projeto](#1-visão-geral-do-projeto)
2. [Arquitetura do Sistema](#2-arquitetura-do-sistema)
3. [Tecnologias Utilizadas](#3-tecnologias-utilizadas)
4. [Estrutura de Pastas](#4-estrutura-de-pastas)
5. [Banco de Dados](#5-banco-de-dados)
6. [Backend (FastAPI)](#6-backend-fastapi)
7. [Frontend (Next.js)](#7-frontend-nextjs)
8. [Machine Learning / IA](#8-machine-learning--ia)
9. [APIs e Endpoints](#9-apis-e-endpoints)
10. [Scripts e Automações](#10-scripts-e-automações)
11. [Deploy e Infraestrutura](#11-deploy-e-infraestrutura)
12. [Problemas Resolvidos](#12-problemas-resolvidos)
13. [Como Rodar Localmente](#13-como-rodar-localmente)
14. [Próximos Passos](#14-próximos-passos)

---

## 1. VISÃO GERAL DO PROJETO

### 1.1. O que é o DIPAM COPILOT?

O **DIPAM COPILOT** é um assistente de IA conversacional focado em dados comerciais da DIPAM. Ele permite que diretores, supervisores e vendedores façam perguntas em linguagem natural sobre:

- Metas e realizados de vendas
- Performance de vendedores
- Clientes em risco de churn
- Oportunidades de crescimento
- Análises de produtos
- Alertas e recomendações

### 1.2. Principais Funcionalidades

1. **Análise de Metas e Realizados**
   - KPIs mensais (meta total, realizado total, atingimento médio)
   - Ranking de vendedores
   - Análise de gaps e oportunidades

2. **Insights Preditivos (ML)**
   - Previsão de churn de clientes
   - Risco de não bater meta (vendedores)
   - Oportunidades de crescimento

3. **Interface Conversacional**
   - Chat estilo GenAI
   - Respostas estruturadas com dashboards
   - Visualização de dados em cards e tabelas

4. **Dados Limpos e Consistentes**
   - Remoção automática de totalizadores
   - Normalização de textos
   - Validação de integridade

---

## 2. ARQUITETURA DO SISTEMA

### 2.1. Diagrama de Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (Vercel)                        │
│  Next.js + React + TypeScript + Tailwind CSS                │
│  https://dipam.smartiasolutions.com.br                      │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS (CORS)
                       │
┌──────────────────────▼──────────────────────────────────────┐
│              BACKEND (Google Cloud Run)                       │
│  FastAPI + Python + SQLAlchemy                                │
│  https://dipam-ai-backend-642830139828.us-central1.run.app   │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼──────┐ ┌────▼────┐ ┌───────▼──────┐
│  SQLite DB   │ │ OpenAI  │ │  ML Models   │
│  (dipam_dw)  │ │   API    │ │  (embeddings)│
└──────────────┘ └──────────┘ └──────────────┘
```

### 2.2. Componentes Principais

1. **Frontend (Next.js)**
   - Interface de chat
   - Visualização de dashboards
   - Componentes React reutilizáveis

2. **Backend (FastAPI)**
   - API REST (`/ask`, `/health`, etc.)
   - AgentService (processamento de perguntas)
   - Integração com LLM (OpenAI)
   - Integração com ML (embeddings, previsões)

3. **Banco de Dados (SQLite)**
   - Tabelas de vendas, metas, clientes, vendedores
   - Tabelas analytics (agregações pré-calculadas)
   - Tabela de interações (log de conversas)

4. **Machine Learning**
   - Embeddings de vendedores, clientes, produtos
   - Índices vetoriais (FAISS)
   - Modelos preditivos (churn, risco de meta)

---

## 3. TECNOLOGIAS UTILIZADAS

### 3.1. Backend

- **Python 3.12+**
- **FastAPI**: Framework web assíncrono
- **SQLAlchemy**: ORM para banco de dados
- **Pydantic**: Validação de dados
- **OpenAI API**: Integração com GPT-4o-mini
- **scikit-learn**: Modelos de ML
- **joblib**: Persistência de modelos
- **FAISS**: Índices vetoriais (opcional)
- **NumPy/Pandas**: Processamento de dados

### 3.2. Frontend

- **Next.js 14+**: Framework React
- **TypeScript**: Tipagem estática
- **Tailwind CSS**: Estilização
- **Lucide React**: Ícones
- **clsx**: Classes condicionais

### 3.3. Infraestrutura

- **Google Cloud Run**: Backend (container)
- **Vercel**: Frontend (deploy automático)
- **SQLite**: Banco de dados (POC)
- **GitHub**: Controle de versão

---

## 4. ESTRUTURA DE PASTAS

```
DIPA/
├── src/                          # Código fonte backend
│   ├── api/                      # API FastAPI
│   │   └── main.py              # Endpoints principais
│   ├── agent/                    # Lógica do agente
│   │   ├── service.py           # AgentService (orquestrador)
│   │   ├── intent.py            # Detecção de intenções
│   │   ├── queries.py           # Queries SQL básicas
│   │   ├── queries_analytics.py # Queries de analytics
│   │   ├── queries_metas.py     # Queries de metas (sem totalizadores)
│   │   └── structured_response_builder.py
│   ├── dw/                       # Data Warehouse
│   │   ├── models.py            # Modelos SQLAlchemy
│   │   ├── models_analytics.py  # Modelos analytics
│   │   ├── connection.py        # Conexão com banco
│   │   └── etl.py               # ETL de dados
│   ├── ml/                       # Machine Learning
│   │   ├── predictor.py         # Previsões ML
│   │   ├── training_pipeline.py # Preparação de datasets
│   │   └── model_registry.py    # Registry de modelos
│   ├── llm_integration.py       # Integração com OpenAI
│   └── config.py                 # Configurações
│
├── components/                    # Componentes React (frontend)
│   ├── CopilotAnswerCard.tsx    # Card principal de resposta
│   ├── ResponseDashboard.tsx    # Dashboard de KPIs e tabelas
│   ├── DipaPanel.tsx            # Painel principal de chat
│   └── ui/                       # Componentes UI reutilizáveis
│
├── lib/                          # Bibliotecas frontend
│   └── dipamApi.ts              # Cliente HTTP para API
│
├── types/                        # TypeScript types
│   └── agent.ts                 # Tipos de resposta estruturada
│
├── scripts/                      # Scripts utilitários
│   ├── limpar_dados_globais.py  # Limpeza de dados
│   ├── treinar_ml.py            # Treinamento de embeddings
│   ├── auditar_banco_completo.py # Auditoria do banco
│   ├── run_analytics_job.py    # Recalcular analytics
│   └── deploy-backend.sh       # Script de deploy
│
├── tests/                        # Testes automatizados
│   ├── test_integridade_ml.py  # Testes de integridade
│   ├── test_metas_vendedor_totais.py
│   └── test_kpis_agosto_2025.py
│
├── data/                        # Dados locais
│   └── dipam_dw.db             # Banco SQLite
│
├── ml_cache/                    # Cache de ML (gerado)
│   ├── embeddings_*.npy        # Embeddings
│   ├── index_*.faiss           # Índices vetoriais
│   └── manifest.json           # Metadados
│
├── models/                      # Modelos ML treinados
│   └── *.joblib                # Modelos scikit-learn
│
├── requirements.txt             # Dependências Python
├── package.json                 # Dependências Node.js
├── Dockerfile                   # Container do backend
├── cloudbuild.yaml              # CI/CD Cloud Build
└── README_DEPLOY.md             # Documentação de deploy
```

---

## 5. BANCO DE DADOS

### 5.1. Tabelas Principais

#### Tabelas de Dados Originais

- **`vendas`**: Vendas individuais
  - Campos: `id`, `data_venda`, `vendedor_id`, `cliente_id`, `produto_id`, `valor`, `quantidade`, etc.
  
- **`metas_vendedor`**: Metas mensais por vendedor
  - Campos: `id`, `vendedor_id`, `vendedor_nome`, `mes_ano`, `valor_meta`, `valor_faturado`, etc.
  - ⚠️ **IMPORTANTE:** Pode conter linha "Totais" que deve ser excluída nas queries

- **`metas_departamento`**: Metas por departamento/supervisor

- **`vendedores`**: Cadastro de vendedores
  - Campos: `id`, `nome`, `codigo`, `rota_rca`, `supervisor_id`

- **`clientes`**: Cadastro de clientes
  - Campos: `id`, `nome`, `fantasia`, `cidade_cliente`, `segmento_venda`

- **`supervisores`**: Cadastro de supervisores

#### Tabelas Analytics (Pré-calculadas)

- **`analytics_vendedor_mes`**: Agregações mensais por vendedor
  - Campos: `mes_ano`, `vendedor_id`, `vendedor_nome`, `meta_total`, `realizado_total`, `atingimento_pct`, `gap_valor`, `meta_risk_score`, etc.

- **`analytics_cliente_mes`**: Agregações mensais por cliente
  - Campos: `mes_ano`, `cliente_id`, `faturamento_12m`, `churn_score`, `churn_flag`, etc.

- **`analytics_produto_mes`**: Agregações mensais por produto

- **`analytics_alertas`**: Alertas gerados automaticamente

#### Tabelas de Log e ML

- **`interacoes_agent`**: Log de todas as perguntas/respostas
  - Campos: `id`, `timestamp`, `papel`, `pergunta`, `resposta`, `intent`, `confianca`, etc.

- **`data_clean_log`**: Log de limpezas de dados
  - Campos: `id`, `tabela`, `id_removido`, `motivo`, `timestamp`

### 5.2. Problema dos Totalizadores

**Problema identificado:**
- Linha "Totais" na tabela `metas_vendedor` estava dobrando os valores de KPIs
- Meta total aparecia como ~R$ 35,66M em vez de ~R$ 17,83M

**Solução implementada:**
- Todas as queries agora excluem totalizadores:
  ```sql
  WHERE LOWER(vendedor_nome) NOT LIKE '%total%'
    AND vendedor_nome != 'Totais'
    AND vendedor_id IS NOT NULL
  ```
- Função centralizada: `get_metas_realizado_por_mes()` em `src/agent/queries_analytics.py`

### 5.3. Valores Esperados (Agosto/2025)

- **Meta total:** R$ 17.833.053,45
- **Realizado total:** R$ 17.254.142,15
- **Atingimento médio:** 96,75%
- **Total de vendedores:** 63 (sem totalizador)

---

## 6. BACKEND (FASTAPI)

### 6.1. Estrutura do AgentService

O `AgentService` (`src/agent/service.py`) é o orquestrador principal:

1. **Recebe pergunta** do usuário
2. **Detecta intenção** (`consulta_meta`, `consulta_vendedores_performance`, etc.)
3. **Extrai entidades** (mês, vendedor, cliente, etc.)
4. **Busca dados** no banco (analytics ou queries diretas)
5. **Chama ML** (se necessário: churn, risco de meta, oportunidades)
6. **Gera resposta** com LLM (OpenAI)
7. **Estrutura resposta** em formato JSON padronizado
8. **Registra interação** em `interacoes_agent`

### 6.2. Intenções Suportadas

- **`consulta_meta`**: Perguntas sobre metas e realizados
- **`consulta_vendedores_performance`**: Performance de vendedores
- **`consulta_clientes_churn`**: Clientes em risco de churn
- **`consulta_produtos`**: Análise de produtos
- **`outros`**: Fallback para perguntas genéricas

### 6.3. Formato de Resposta Estruturada

```typescript
interface CopilotStructuredResponse {
  resumo_executivo: string;           // Resumo textual gerado pelo LLM
  secoes?: SecaoResposta[];           // Seções de texto organizadas
  tabelas?: DetalheTabela[];         // Tabelas de dados (vendedores, clientes, etc.)
  insights_preditivos?: InsightsPreditivos;  // Previsões ML
  contexto_debug?: any;               // Dados técnicos (debug)
}
```

### 6.4. Principais Funções

#### Queries de Analytics

- **`get_metas_realizado_por_mes()`** (`src/agent/queries_analytics.py`)
  - FONTE ÚNICA DE VERDADE para KPIs mensais
  - Exclui totalizadores automaticamente
  - Retorna: `meta_total`, `realizado_total`, `atingimento_medio`, `linhas_detalhadas`

- **`get_piores_vendedores_por_gap()`** (`src/agent/queries_analytics.py`)
  - Ranking de vendedores com maior gap negativo
  - Exclui totalizadores

#### Queries Diretas (metas_vendedor)

- **`get_metas_realizado_por_mes_direto()`** (`src/agent/queries_metas.py`)
  - Calcula KPIs diretamente de `metas_vendedor`
  - Exclui totalizadores
  - Usado como validação/fallback

---

## 7. FRONTEND (NEXT.JS)

### 7.1. Componentes Principais

#### `DipaPanel.tsx`
- Painel principal de chat
- Gerencia histórico de mensagens
- Campo de input fixo no rodapé
- Scroll automático para última mensagem

#### `CopilotAnswerCard.tsx`
- Card de resposta do COPILOT
- Renderiza `ResponseDashboard` quando há `structured` response
- Fallback para formato antigo (compatibilidade)

#### `ResponseDashboard.tsx`
- Dashboard completo de KPIs e dados
- **KPIs no topo:** 4 cards principais (meta, realizado, riscos)
- **Resumo executivo:** Texto destacado
- **Insights preditivos:** Cards com badge "IA Preditiva"
- **Tabelas:** Rankings com progress bars, badges de risco, collapse/expand

### 7.2. Tipos TypeScript

```typescript
// types/agent.ts
interface CopilotStructuredResponse {
  resumo_executivo: string;
  secoes?: SecaoResposta[];
  tabelas?: DetalheTabela[];
  insights_preditivos?: InsightsPreditivos;
  contexto_debug?: any;
}

interface InsightsPreditivos {
  churn?: {
    total_clientes_risco_alto: number;
    top_clientes: any[];
  };
  meta_risk?: {
    vendedores_risco_alto: number;
    detalhes: any[];
  };
  oportunidades?: {
    total_clientes_potencial: number;
    top_clientes: any[];
  };
}
```

### 7.3. Cliente API

**`lib/dipamApi.ts`**

```typescript
export async function askDipamAgent(params: AskParams): Promise<AskResponse>

interface AskParams {
  pergunta: string;
  usuarioId?: string;
  papel?: "diretor" | "supervisor" | "vendedor";
}

interface AskResponse {
  question: string;
  intent: string;
  confidence: number;
  resumoExecutivo?: string;
  structured?: CopilotStructuredResponse;
}
```

**URL Base:** Lê de `NEXT_PUBLIC_API_BASE_URL` (variável de ambiente)

---

## 8. MACHINE LEARNING / IA

### 8.1. Embeddings

**Script:** `scripts/treinar_ml.py`

Gera embeddings para:
- **Vendedores:** Nome + código + rota
- **Clientes:** Nome + fantasia + cidade + segmento
- **Produtos:** Descrição + código + departamento

**Modelo:** OpenAI `text-embedding-3-small` (1536 dimensões)

**Armazenamento:**
- `ml_cache/embeddings_*.npy` (arrays NumPy)
- `ml_cache/ids_*.json` (IDs correspondentes)
- `ml_cache/index_*.faiss` (índices vetoriais FAISS)

**Manifest:** `ml_cache/manifest.json`
```json
{
  "timestamp": "2025-11-16T...",
  "schema_version": "1.0.0",
  "embedding_model": "text-embedding-3-small",
  "registros": { ... },
  "data_fingerprint": "..."
}
```

### 8.2. Modelos Preditivos

**Scripts:** `scripts/train_ml_models.py`

Modelos treinados:
1. **Churn de Clientes** (LogisticRegression/GradientBoosting)
2. **Risco de Meta** (LogisticRegression/RandomForest)
3. **Oportunidades** (RandomForest/GradientBoosting)

**Armazenamento:**
- `models/*.joblib` (modelos treinados)
- `models/registry.json` (metadados)

**Uso:** `src/ml/predictor.py`
- Lazy loading de modelos
- Cache em memória
- Funções: `prever_churn_clientes()`, `prever_risco_meta_vendedores()`, `sugerir_oportunidades()`

---

## 9. APIs E ENDPOINTS

### 9.1. POST /ask

**Endpoint principal** para fazer perguntas ao COPILOT.

**Request:**
```json
{
  "pergunta": "qual a meta de vendas do mês de agosto 2025?",
  "papel": "diretor",
  "usuarioId": "opcional"
}
```

**Response:**
```json
{
  "question": "...",
  "intent": "consulta_meta",
  "confidence": 0.7,
  "resumoExecutivo": "...",
  "structured": {
    "resumo_executivo": "...",
    "secoes": [...],
    "tabelas": [...],
    "insights_preditivos": {...}
  }
}
```

### 9.2. GET /health

Health check geral.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "...",
  "environment": "production",
  "database": "sqlite",
  "components": {
    "database": "available",
    "openai": "available",
    "agent_service": "available"
  }
}
```

### 9.3. GET /health/db

Health check do banco de dados.

### 9.4. GET /health/openai

Health check da conexão OpenAI.

### 9.5. GET /ml/status

Status dos modelos ML treinados.

**Response:**
```json
{
  "status": "ok",
  "modelos": {
    "churn": {
      "treinado": true,
      "trained_at": "...",
      "n_samples": 12345
    },
    ...
  }
}
```

### 9.6. POST /feedback

Endpoint para feedback do usuário (futuro).

---

## 10. SCRIPTS E AUTOMAÇÕES

### 10.1. Limpeza de Dados

**Script:** `scripts/limpar_dados_globais.py`

**Funcionalidades:**
- Remove totalizadores de todas as tabelas
- Normaliza campos de texto (strip, remove espaços duplos)
- Converte campos monetários para float
- Verifica datas inválidas
- Cria log em `data_clean_log`

**Uso:**
```bash
DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db python3 scripts/limpar_dados_globais.py
```

### 10.2. Treinamento ML

**Script:** `scripts/treinar_ml.py`

**Funcionalidades:**
- Carrega dados limpos
- Gera embeddings (vendedores, clientes, produtos)
- Cria índices FAISS
- Gera manifest.json

**Uso:**
```bash
OPENAI_API_KEY=sk-... DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db python3 scripts/treinar_ml.py
```

### 10.3. Auditoria do Banco

**Script:** `scripts/auditar_banco_completo.py`

**Funcionalidades:**
- Lista todas as tabelas
- Detecta totalizadores
- Detecta valores absurdos
- Detecta IDs nulos/duplicados
- Gera relatórios JSON e TXT

**Uso:**
```bash
DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db python3 scripts/auditar_banco_completo.py
```

### 10.4. Recalcular Analytics

**Script:** `scripts/run_analytics_job.py`

**Funcionalidades:**
- Recalcula tabelas analytics_*
- Aplica scores (churn, meta_risk, etc.)
- Gera alertas

**Uso:**
```bash
DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db python3 scripts/run_analytics_job.py --mes_ano=2025-08
```

### 10.5. Testes de Deploy

**Script:** `scripts/run_deploy_checks.sh`

Valida:
- Variáveis de ambiente
- Conexão com banco
- Conexão OpenAI
- Serviço do agente

---

## 11. DEPLOY E INFRAESTRUTURA

### 11.1. Backend (Google Cloud Run)

**Projeto:** `trivihair`  
**Serviço:** `dipam-ai-backend`  
**Região:** `us-central1`  
**URL:** `https://dipam-ai-backend-642830139828.us-central1.run.app`

**Configuração:**
- Memória: 4Gi
- CPU: 2
- Min instances: 1 (evita cold start)
- Max instances: 10
- Timeout: 300s
- Port: 8080

**Variáveis de ambiente:**
- `ENVIRONMENT=production`
- `DB_TYPE=sqlite`
- `SQLITE_PATH=/app/data/dipam_dw.db`
- `LOG_LEVEL=INFO`

**Secrets (Secret Manager):**
- `OPENAI_API_KEY`

**Comando de deploy:**
```bash
gcloud run deploy dipam-ai-backend \
  --source=. \
  --region=us-central1 \
  --project=trivihair \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --memory=4Gi \
  --cpu=2 \
  --timeout=300s \
  --max-instances=10 \
  --min-instances=1 \
  --set-env-vars=ENVIRONMENT=production,DB_TYPE=sqlite,SQLITE_PATH=/app/data/dipam_dw.db,LOG_LEVEL=INFO \
  --set-secrets=OPENAI_API_KEY=openai-api-key:latest
```

### 11.2. Frontend (Vercel)

**URL:** `https://dipam.smartiasolutions.com.br`

**Deploy:** Automático via GitHub (push para `main`)

**Variáveis de ambiente necessárias:**
- `NEXT_PUBLIC_API_BASE_URL`: URL do backend
  - Valor: `https://dipam-ai-backend-642830139828.us-central1.run.app`

**Como configurar:**
1. Vercel Dashboard → Projeto DIPAM COPILOT
2. Settings → Environment Variables
3. Adicionar: `NEXT_PUBLIC_API_BASE_URL = https://dipam-ai-backend-642830139828.us-central1.run.app`
4. Fazer novo deploy

### 11.3. CORS

**Origens permitidas:**
- `https://dipam.smartiasolutions.com.br`
- `https://dipam-copilot-frontend-6arhlm3mha-uc.a.run.app`
- `http://localhost:3000` (desenvolvimento)

**Configuração:** `src/api/main.py`
- Middleware CORS do FastAPI
- Handler OPTIONS específico para `/ask`
- Headers sempre adicionados mesmo em erros

---

## 12. PROBLEMAS RESOLVIDOS

### 12.1. Duplicação de KPIs (Totalizadores)

**Problema:** KPIs apareciam duplicados (ex: R$ 35,66M em vez de R$ 17,83M)

**Causa:** Linha "Totais" em `metas_vendedor` sendo somada junto com vendedores individuais

**Solução:**
- Função centralizada `get_metas_realizado_por_mes()` que exclui totalizadores
- Todas as queries agora filtram: `WHERE vendedor_nome != 'Totais' AND LOWER(vendedor_nome) NOT LIKE '%total%'`
- Testes automatizados validam valores corretos

### 12.2. CORS em Cold Start

**Problema:** 503 Service Unavailable durante cold start, sem headers CORS

**Solução:**
- `min-instances=1` para evitar cold start
- Handler OPTIONS específico para `/ask`
- Middleware CORS que adiciona headers mesmo em erros

### 12.3. Memória Insuficiente

**Problema:** Backend crashando com OOM (Out of Memory)

**Solução:**
- Aumentado de 2Gi para 4Gi de memória
- CPU aumentado de 1 para 2

### 12.4. Formato de Resposta Inconsistente

**Problema:** Backend retornando formato antigo (camelCase) em vez de novo (snake_case)

**Solução:**
- Priorização de campo `structured` no `_extrair_dados_estruturados()`
- Preservação explícita do formato novo em `main.py`

---

## 13. COMO RODAR LOCALMENTE

### 13.1. Pré-requisitos

- Python 3.12+
- Node.js 18+
- SQLite (banco incluído em `data/dipam_dw.db`)

### 13.2. Backend

```bash
# 1. Criar venv
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou: .venv\Scripts\activate  # Windows

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Configurar variáveis de ambiente
export DB_TYPE=sqlite
export SQLITE_PATH=data/dipam_dw.db
export OPENAI_API_KEY=sk-...

# 4. Rodar servidor
python -m src.api.main
# ou: uvicorn src.api.main:app --reload --port 8000
```

**Acessar:** `http://localhost:8000`  
**Docs:** `http://localhost:8000/docs`

### 13.3. Frontend

```bash
# 1. Instalar dependências
npm install

# 2. Configurar variável de ambiente
# Criar .env.local:
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# 3. Rodar servidor de desenvolvimento
npm run dev
```

**Acessar:** `http://localhost:3000`

### 13.4. Testes

```bash
# Rodar todos os testes
DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db pytest -v

# Testes específicos
pytest tests/test_integridade_ml.py -v
pytest tests/test_metas_vendedor_totais.py -v
```

---

## 14. PRÓXIMOS PASSOS

### 14.1. Melhorias Planejadas

1. **Migração para PostgreSQL**
   - Atualmente usando SQLite (POC)
   - Migrar para Cloud SQL ou PostgreSQL gerenciado

2. **Melhorias de ML**
   - Treinar modelos com mais dados históricos
   - A/B testing de modelos
   - Métricas de performance (ROC-AUC, precision, recall)

3. **Cache de Respostas**
   - Cache de respostas frequentes
   - Redução de chamadas ao LLM

4. **Analytics Avançados**
   - Dashboards interativos
   - Exportação de relatórios (PDF, Excel)
   - Agendamento de relatórios

### 14.2. Funcionalidades Futuras

1. **Multi-idioma**
   - Suporte a perguntas em inglês/espanhol

2. **Integração com outras fontes**
   - APIs externas
   - Webhooks

3. **Notificações**
   - Alertas por email
   - Notificações push

---

## 15. COMANDOS ÚTEIS

### 15.1. Desenvolvimento

```bash
# Limpar dados
DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db python3 scripts/limpar_dados_globais.py

# Treinar ML
OPENAI_API_KEY=sk-... DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db python3 scripts/treinar_ml.py

# Auditar banco
DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db python3 scripts/auditar_banco_completo.py

# Testar API localmente
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"pergunta": "qual a meta de agosto 2025?", "papel": "diretor"}'
```

### 15.2. Deploy

```bash
# Deploy backend
gcloud run deploy dipam-ai-backend --source=. --region=us-central1 --project=trivihair ...

# Ver logs
gcloud logs read --project=trivihair --service=dipam-ai-backend --region=us-central1 --limit=50

# Verificar status
gcloud run services describe dipam-ai-backend --region=us-central1 --project=trivihair
```

### 15.3. Testes

```bash
# Health checks
curl https://dipam-ai-backend-642830139828.us-central1.run.app/health
curl https://dipam-ai-backend-642830139828.us-central1.run.app/health/db
curl https://dipam-ai-backend-642830139828.us-central1.run.app/health/openai

# Teste CORS
curl -X OPTIONS https://dipam-ai-backend-642830139828.us-central1.run.app/ask \
  -H "Origin: https://dipam.smartiasolutions.com.br" \
  -H "Access-Control-Request-Method: POST"
```

---

## 16. CONTATOS E REFERÊNCIAS

### 16.1. Documentação Adicional

- `README_DEPLOY.md`: Guia completo de deploy
- `PIPELINE_DEPLOY_RESUMO_FINAL.md`: Resumo do último pipeline
- `README_FRONTEND.md`: Documentação do frontend
- `DEPLOY_ENV_VARS.md`: Variáveis de ambiente

### 16.2. URLs de Produção

- **Backend:** https://dipam-ai-backend-642830139828.us-central1.run.app
- **Frontend:** https://dipam.smartiasolutions.com.br
- **API Docs:** https://dipam-ai-backend-642830139828.us-central1.run.app/docs

### 16.3. Repositório

- **GitHub:** https://github.com/g4trader/DIPA
- **Branch principal:** `main`

---

## 17. NOTAS IMPORTANTES

### 17.1. Valores Críticos

**Agosto/2025 (valores corretos SEM totalizador):**
- Meta total: **R$ 17.833.053,45**
- Realizado total: **R$ 17.254.142,15**
- Atingimento médio: **96,75%**

**⚠️ NUNCA usar valores duplicados (~R$ 35,66M)**

### 17.2. Regras de Negócio

1. **Sempre excluir totalizadores** nas queries de agregação
2. **Usar função centralizada** `get_metas_realizado_por_mes()` para KPIs
3. **Validar valores** com testes automatizados
4. **Logar auditoria** com prefixo `[AUDIT_KPIS]`

### 17.3. Convenções de Código

- **Backend:** snake_case (Python)
- **Frontend:** camelCase (TypeScript/JavaScript)
- **Banco:** snake_case (SQL)
- **APIs:** snake_case no backend, camelCase no frontend (conversão automática)

---

**Fim da Documentação**

