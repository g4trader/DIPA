# DIPAM COPILOT™ - Guia de Deploy

Este documento descreve como fazer deploy do DIPAM COPILOT™ em produção (backend no Google Cloud Run e frontend no Vercel).

## 📋 Índice

1. [Arquitetura](#arquitetura)
2. [Variáveis de Ambiente](#variáveis-de-ambiente)
3. [Backend (Cloud Run)](#backend-cloud-run)
4. [Frontend (Vercel)](#frontend-vercel)
5. [Testes](#testes)
6. [Troubleshooting](#troubleshooting)

## 🏗️ Arquitetura

```
┌─────────────────┐         ┌──────────────────┐
│   Vercel        │         │  Google Cloud Run │
│   (Frontend)    │────────▶│  (Backend API)    │
│   Next.js       │         │  FastAPI          │
└─────────────────┘         └──────────────────┘
                                      │
                                      ▼
                            ┌──────────────────┐
                            │  SQLite Database │
                            │  (Cloud Storage)  │
                            └──────────────────┘
                                      │
                                      ▼
                            ┌──────────────────┐
                            │  OpenAI API      │
                            └──────────────────┘
```

## 🔐 Variáveis de Ambiente

> **📚 Documentação Completa**: Veja [DEPLOY_ENV_VARS.md](./DEPLOY_ENV_VARS.md) para mapeamento detalhado de todas as variáveis.

### Backend (Cloud Run)

#### Obrigatórias

| Variável | Descrição | Exemplo | Onde é Usada |
|----------|-----------|---------|--------------|
| `OPENAI_API_KEY` | Chave de API da OpenAI (obrigatória) | `sk-...` | `src/llm_openai_client.py`, `src/agent/memory.py` |
| `DB_TYPE` | Tipo de banco: `sqlite` ou `postgresql` | `sqlite` | `src/config.py:39` |
| `ENVIRONMENT` | Ambiente: `development`, `staging`, `production` | `production` | `src/config.py:166` |

#### Condicionais (dependem de DB_TYPE)

**Se DB_TYPE=sqlite:**
| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `SQLITE_PATH` | Caminho do arquivo SQLite (relativo ou absoluto) | `data/dipam_dw.db` (recomendado)<br>`/app/data/dipam_dw.db` (absoluto, se necessário) |
| | **Nota**: O diretório será criado automaticamente se não existir |

**Se DB_TYPE=postgresql:**
| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `POSTGRES_HOST` | Host do PostgreSQL | `localhost` ou Cloud SQL socket |
| `POSTGRES_PORT` | Porta do PostgreSQL | `5432` |
| `POSTGRES_USER` | Usuário do PostgreSQL | `dipam_user` |
| `POSTGRES_PASSWORD` | Senha do PostgreSQL | `***` |
| `POSTGRES_DB` | Nome do banco | `dipam_dw` |

#### Opcionais

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `PORT` | Porta do servidor | `8080` |
| `LOG_LEVEL` | Nível de log: `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` |
| `DEBUG` | Modo debug (True/False) | `False` (prod) |
| `OPENAI_BASE_URL` | URL base da API OpenAI | `https://api.openai.com/v1` |
| `OPENAI_MODEL` | Modelo OpenAI a usar | `gpt-4o-mini` |

### Frontend (Vercel)

| Variável | Descrição | Exemplo | Onde é Usada |
|---------|-----------|---------|--------------|
| `NEXT_PUBLIC_API_BASE_URL` | URL base da API do backend | `https://dipam-ai-backend-xxx.run.app` | `lib/dipamApi.ts:16` |

**⚠️ Importante**: URL deve ser completa, sem barra final.

## 🚀 Backend (Cloud Run)

### Pré-requisitos

1. Google Cloud SDK instalado e configurado
2. Projeto Google Cloud criado
3. Cloud Build API habilitada
4. Cloud Run API habilitada
5. Arquivo SQLite (`dipam_dw.db`) no Cloud Storage (ou usar caminho relativo)
6. Arquivo `main.py` na raiz do projeto (expõe `app` para o Cloud Run buildpack)

### Estrutura Necessária

O Cloud Run buildpack (source-based deploy) espera encontrar `main:app` na raiz do projeto:
- ✅ `main.py` na raiz → expõe `app` de `src.api.main`
- ✅ `src/api/main.py` → contém o objeto `app` FastAPI

### Passo 1: Upload do Banco SQLite

```bash
# Upload do banco SQLite para Cloud Storage
gsutil cp data/dipam_dw.db gs://trivihair-dipam-data/dipam_dw.db
```

### Passo 2: Configurar SQLITE_PATH

**Recomendação**: Use caminho relativo `data/dipam_dw.db` em vez de absoluto `/app/data/dipam_dw.db`.

**Por quê?** 
- O código cria o diretório automaticamente se não existir
- Funciona tanto local quanto no Cloud Run
- Evita problemas de permissão

**Se precisar usar caminho absoluto** (ex: `/app/data/dipam_dw.db`):
- O diretório `/app/data/` será criado automaticamente pelo código
- Garante que não falhe por "unable to open database file"

### Passo 3: Configurar Secrets no Secret Manager

```bash
# Criar secret para OPENAI_API_KEY
echo -n "sk-..." | gcloud secrets create openai-api-key --data-file=-

# Criar secret para outros valores sensíveis (se necessário)
echo -n "valor" | gcloud secrets create postgres-password --data-file=-
```

### Passo 4: Deploy via Cloud Build (ou Deploy Direto)

#### Opção A: Deploy Direto (Recomendado - Mais Rápido)

```bash
# Deploy direto usando source (Cloud Run builda automaticamente)
gcloud run deploy dipam-ai-backend \
  --source . \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --memory=4Gi \
  --cpu=2 \
  --timeout=300s \
  --max-instances=10 \
  --min-instances=0 \
  --set-env-vars="ENVIRONMENT=production,DB_TYPE=sqlite,SQLITE_PATH=data/dipam_dw.db,LOG_LEVEL=INFO" \
  --set-secrets="OPENAI_API_KEY=openai-api-key:latest"
```

**Observação**: O Cloud Run espera que o servidor escute na porta definida por `PORT` (8080).
O Dockerfile usa `CMD ["python", "-m", "src.api.main"]` que inicia o uvicorn na porta correta.

#### Opção B: Deploy via Cloud Build

```bash
# Fazer commit das mudanças
git add .
git commit -m "Deploy: preparação para produção"
git push origin main

# Trigger do Cloud Build (se configurado)
# Ou executar manualmente:
gcloud builds submit --config cloudbuild.yaml
```

**Nota**: O `cloudbuild.yaml` pode precisar de ajustes para usar `SHORT_SHA` corretamente.

### Passo 5: Configurar Variáveis de Ambiente no Cloud Run

Após o deploy, configure as variáveis de ambiente:

#### Para SQLite (configuração atual):

```bash
gcloud run services update dipam-ai-backend \
  --region=us-central1 \
  --set-env-vars="ENVIRONMENT=production,DB_TYPE=sqlite,SQLITE_PATH=data/dipam_dw.db,LOG_LEVEL=INFO" \
  --set-secrets="OPENAI_API_KEY=openai-api-key:latest"
```

#### Para PostgreSQL (se migrar no futuro):

```bash
gcloud run services update dipam-ai-backend \
  --region=us-central1 \
  --set-env-vars="ENVIRONMENT=production,DB_TYPE=postgresql,POSTGRES_HOST=/cloudsql/PROJECT:REGION:INSTANCE,POSTGRES_PORT=5432,POSTGRES_DB=dipam_dw" \
  --set-secrets="OPENAI_API_KEY=openai-api-key:latest,POSTGRES_USER=postgres-user:latest,POSTGRES_PASSWORD=postgres-password:latest"
```

**Serviço**: `dipam-ai-backend` (ou nome real do seu serviço)

### Passo 6: Verificar Deploy

```bash
# Obter URL do serviço
SERVICE_URL=$(gcloud run services describe dipam-ai-backend --region=us-central1 --format='value(status.url)')

# Testar health check básico
curl $SERVICE_URL/health
# Resposta esperada: {"status":"healthy","timestamp":"...","environment":"production",...}

# Testar health check do banco
curl $SERVICE_URL/health/db
# Resposta esperada: {"status":"healthy","database":"sqlite","connected":true,"metas_vendedor_count":...}

# Testar health check da OpenAI
curl $SERVICE_URL/health/openai
# Resposta esperada: {"status":"healthy","openai_configured":true,"openai_connected":true,...}
```

**⚠️ Se algum health check falhar**, verifique os logs:
```bash
gcloud run services logs read dipam-ai-backend --region=us-central1 --limit=50
```

### Testar CORS

Após o deploy, teste se o CORS está funcionando corretamente:

```bash
# Testar preflight OPTIONS (simula requisição do navegador)
curl -i -X OPTIONS \
  -H "Origin: https://dipam.smartiasolutions.com.br" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  https://dipam-ai-backend-6arhlm3mha-uc.a.run.app/ask

# Esperado:
# Access-Control-Allow-Origin: https://dipam.smartiasolutions.com.br
# Access-Control-Allow-Methods: POST, GET, OPTIONS, ...
# Access-Control-Allow-Headers: Content-Type, ...
# Status: 200 OK

# Testar requisição real POST
curl -i -X POST \
  -H "Origin: https://dipam.smartiasolutions.com.br" \
  -H "Content-Type: application/json" \
  -d '{"pergunta": "qual a meta de outubro 2025", "papel": "diretor"}' \
  https://dipam-ai-backend-6arhlm3mha-uc.a.run.app/ask

# Esperado:
# Access-Control-Allow-Origin: https://dipam.smartiasolutions.com.br
# Status: 200 OK
# Body: JSON com resposta da API
```

### Passo 7: Testar Endpoint Principal

```bash
# Pergunta 1: Meta de outubro 2025
curl -X POST $SERVICE_URL/ask \
  -H "Content-Type: application/json" \
  -d '{
    "pergunta": "qual a meta de vendas do mês de outubro 2025",
    "papel": "diretor"
  }'

# Pergunta 2: Por que não batemos a meta em agosto 2025
curl -X POST $SERVICE_URL/ask \
  -H "Content-Type: application/json" \
  -d '{
    "pergunta": "Sou o Diretor e preciso saber de forma detalhada porque não batemos a meta no mês de agosto 2025",
    "papel": "diretor"
  }'

# Pergunta 3: Vendedores com impacto negativo
curl -X POST $SERVICE_URL/ask \
  -H "Content-Type: application/json" \
  -d '{
    "pergunta": "quais foram os vendedores que mais geraram impacto negativo no realizado do mês de agosto 2025",
    "papel": "diretor"
  }'
```

**✅ Resposta esperada**: JSON com `intent`, `resumoExecutivo`, `kpis`, `topVendedores`, `payload`, etc.
**❌ Resposta indesejada**: Mensagens genéricas como "não encontrei dados", "erro na API", etc.

## 🎨 Frontend (Vercel)

### Pré-requisitos

1. Conta Vercel
2. Vercel CLI instalado (`npm i -g vercel`)
3. Projeto conectado ao repositório Git

### Passo 1: Configurar Variáveis de Ambiente

No painel da Vercel:

1. Acesse o projeto
2. Vá em **Settings** → **Environment Variables**
3. Adicione:

```
NEXT_PUBLIC_API_BASE_URL=https://dipam-ai-backend-6arhlm3mha-uc.a.run.app
```

**⚠️ IMPORTANTE**: 
- Use a URL completa do Cloud Run **SEM barra final** (ex: `https://dipam-ai-backend-xxx.run.app`)
- O código remove barras no final automaticamente, mas é melhor não ter
- Configure para **Production**, **Preview** e **Development** se necessário
- Após adicionar, faça um novo deploy para aplicar as mudanças

**Onde é usada**: `lib/dipamApi.ts` - A URL é normalizada automaticamente para evitar `//ask`

**CORS no Backend**:
- O backend já está configurado para permitir `https://dipam.smartiasolutions.com.br`
- Verifique se o domínio está correto em `src/api/main.py`

### Passo 2: Deploy

```bash
# Deploy via CLI
vercel --prod

# Ou faça push para a branch main (se configurado auto-deploy)
git push origin main
```

### Passo 3: Verificar Deploy

1. Acesse a URL do projeto na Vercel
2. Teste uma pergunta: "qual a meta de vendas do mês de outubro 2025"
3. Verifique se a resposta vem do backend (não é mock)

## 🧪 Testes

### Simular Ambiente Cloud Run Localmente

Antes de fazer deploy, teste localmente como se fosse Cloud Run:

```bash
# Ativa ambiente virtual
source venv/bin/activate

# Configura variáveis de ambiente (produção)
export ENVIRONMENT=production
export DB_TYPE=sqlite
export SQLITE_PATH="data/dipam_dw.db"  # Caminho relativo - será criado se necessário
export PORT=8080

# Opcional: carrega OPENAI_API_KEY do .env
export $(grep -v '^#' .env | grep OPENAI_API_KEY | xargs)

# Testa com Gunicorn (como o Cloud Run buildpack faz)
gunicorn -b 0.0.0.0:8080 main:app --workers 1 --timeout 300 --log-level info
```

Ou use o script automatizado:

```bash
# Torna executável (primeira vez)
chmod +x scripts/run_cloudrun_style_local.sh

# Executa
./scripts/run_cloudrun_style_local.sh
```

Depois, teste os health endpoints:

```bash
curl http://localhost:8080/health
curl http://localhost:8080/health/db
curl http://localhost:8080/health/openai
```

**⚠️ Se isso funcionar localmente, a chance do deploy no Cloud Run dar certo é muito alta!**

### Testes

### Simular Ambiente Cloud Run Localmente

#### Opção 1: Script de Simulação Cloud Run (Recomendado para Debug de Startup)

```bash
# Simula exatamente o ambiente Cloud Run (PORT=8080, produção, etc.)
./scripts/run_cloud_run_local.sh
```

Este script:
- Configura variáveis de ambiente como no Cloud Run (`PORT=8080`, `ENVIRONMENT=production`)
- Inicia o servidor com `python -m src.api.main`
- Permite testar se o servidor sobe corretamente antes do deploy

**Testar após iniciar**:
```bash
curl http://localhost:8080/health
curl http://localhost:8080/health/db
curl http://localhost:8080/health/openai
```

**Se o servidor subir localmente neste script mas falhar no Cloud Run**, o problema é configuração no Cloud Run (não código).

#### Opção 2: Script de Validação Completa (Recomendado para Validação Pré-Deploy)

```bash
# Ativa venv, valida envs e executa testes automaticamente
./scripts/run_deploy_checks.sh

# Se tudo OK, seguir para o deploy no Cloud Run
```

**O que o script valida**:
1. ✅ Variáveis de ambiente obrigatórias
2. ✅ Conexão com banco de dados
3. ✅ Conexão com OpenAI
4. ✅ Serviço do agente com perguntas críticas
5. ✅ Validação de respostas (não genéricas/fallback)

#### Opção 2: Manual

```bash
# Ativar ambiente virtual
source venv/bin/activate

# Configurar variáveis de ambiente
export OPENAI_API_KEY="sk-..."
export DB_TYPE="sqlite"
export SQLITE_PATH="data/dipam_dw.db"
export ENVIRONMENT="production"

# Executar script de teste
python scripts/test_cloud_like_env.py
```

#### Opção 3: Usando arquivo .env

```bash
# Criar .env com as variáveis
cat > .env << EOF
OPENAI_API_KEY=sk-...
DB_TYPE=sqlite
SQLITE_PATH=data/dipam_dw.db
ENVIRONMENT=production
EOF

# Executar script (ele carrega .env automaticamente)
./scripts/run_deploy_checks.sh
```

#### O que o script testa:

1. ✅ **Variáveis de Ambiente**: Valida todas as env vars obrigatórias
2. ✅ **Conexão com Banco**: Testa conexão e verifica dados para agosto/outubro 2025
3. ✅ **Conexão OpenAI**: Testa chamada mínima à API
4. ✅ **Serviço do Agente**: Testa 3 perguntas críticas:
   - "qual a meta de vendas do mês de outubro 2025"
   - "Sou o Diretor e preciso saber de forma detalhada porque não batemos a meta no mês de agosto 2025"
   - "quais foram os vendedores que mais geraram impacto negativo no realizado do mês de agosto 2025"

Para cada pergunta, o script mostra:
- 🎯 Intent detectado
- 📅 Mês/ano extraído
- 📊 Contagem de registros no banco
- 👥 Vendedores encontrados no contexto
- ✅ Validação de resposta (não genérica/fallback)

### Teste de Health Checks

Após o deploy, substitua `SUA_URL_CLOUD_RUN` pela URL real do serviço:

```bash
# Health básico
curl https://SUA_URL_CLOUD_RUN/health

# Health do banco
curl https://SUA_URL_CLOUD_RUN/health/db

# Health da OpenAI
curl https://SUA_URL_CLOUD_RUN/health/openai
```

**Resposta esperada do `/health`**:
```json
{
  "status": "healthy",
  "environment": "production",
  "database": "sqlite",
  "components": {
    "database": "available",
    "openai": "available",
    "agent_service": "available"
  }
}
```

Se algum componente não estiver disponível, o status será `"degraded"` mas o servidor continua funcionando.

### Teste de Perguntas Críticas

Após o deploy, substitua `SUA_URL_CLOUD_RUN` pela URL real do serviço:

```bash
# Pergunta 1: Meta de outubro 2025
curl -X POST https://SUA_URL_CLOUD_RUN/ask \
  -H "Content-Type: application/json" \
  -d '{"pergunta": "qual a meta de vendas do mês de outubro 2025", "papel": "diretor"}'

# Pergunta 2: Por que não batemos a meta em agosto 2025
curl -X POST https://SUA_URL_CLOUD_RUN/ask \
  -H "Content-Type: application/json" \
  -d '{"pergunta": "Sou o Diretor e preciso saber de forma detalhada porque não batemos a meta no mês de agosto 2025", "papel": "diretor"}'

# Pergunta 3: Vendedores com impacto negativo
curl -X POST https://SUA_URL_CLOUD_RUN/ask \
  -H "Content-Type: application/json" \
  -d '{"pergunta": "quais foram os vendedores que mais geraram impacto negativo no realizado do mês de agosto 2025", "papel": "diretor"}'
```

**Importante**: Não codificar a chave da OpenAI em texto plano. Use Secret Manager do Google Cloud:
1. Criar secret: `echo -n "sk-..." | gcloud secrets create openai-api-key --data-file=-`
2. Referenciar no Cloud Run: `--set-secrets="OPENAI_API_KEY=openai-api-key:latest"`

## 🔍 Troubleshooting

### Problema: "OPENAI_API_KEY não encontrada"

**Solução**:
1. Verifique se o secret foi criado no Secret Manager
2. Verifique se o secret está sendo referenciado corretamente no Cloud Run
3. Verifique os logs: `gcloud run services logs read dipam-ai-backend --region=us-central1`

### Problema: "Arquivo SQLite não encontrado"

**Solução**:
1. Verifique se o arquivo foi enviado para Cloud Storage: `gsutil ls gs://trivihair-dipam-data/`
2. Verifique se o Dockerfile está baixando o arquivo corretamente
3. Verifique os logs do build do Cloud Build

### Problema: Frontend não consegue conectar com backend

**Solução**:
1. Verifique se `NEXT_PUBLIC_API_BASE_URL` está configurada na Vercel
2. Verifique se a URL está correta (sem barra final)
3. Verifique CORS no backend (deve permitir origem da Vercel)
4. Abra o console do navegador e verifique erros de rede

### Problema: Respostas genéricas / "Não encontrei dados"

**Solução**:
1. Verifique se há dados no banco para o período consultado:
   ```sql
   SELECT COUNT(*) FROM metas_vendedor WHERE mes_ano = '2025-08';
   ```
2. Verifique os logs do backend para ver qual SQL foi executado
3. Verifique se a extração de datas está funcionando (logs mostram `mes_ano` extraído)

### Problema: Erro 500 no backend

**Solução**:
1. Verifique os logs: `gcloud run services logs read dipam-ai-backend --region=us-central1 --limit=50`
2. Verifique se todas as variáveis de ambiente estão configuradas
3. Teste localmente com as mesmas variáveis de ambiente

## 📊 Monitoramento

### Logs do Backend

```bash
# Ver logs em tempo real
gcloud run services logs tail dipam-ai-backend --region=us-central1

# Ver últimas 100 linhas
gcloud run services logs read dipam-ai-backend --region=us-central1 --limit=100
```

### Métricas do Cloud Run

1. Acesse o Console do Google Cloud
2. Vá em **Cloud Run** → **dipam-ai-backend**
3. Veja métricas de:
   - Requisições por segundo
   - Latência
   - Taxa de erro
   - Uso de memória/CPU

## ⏰ Jobs Agendados (Analytics + Aprendizado) - FASE 4

O DIPAM COPILOT™ mantém os dados sempre atualizados através de jobs agendados que recalculam analytics e scores automaticamente.

### Objetivo

Manter o sistema sempre atualizado com:
- ✅ Novos meses de dados
- ✅ Ajustes de scores (churn_score, meta_risk_score, queda_score)
- ✅ Novos alertas baseados em analytics
- ✅ Dados prontos para treino futuro de modelos ML

### Script de Recálculo

O script `scripts/run_analytics_job.py` orquestra o recálculo completo:

```bash
# Recalcular apenas o mês corrente (último mês fechado)
DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db python -m scripts.run_analytics_job

# Recalcular um mês específico
DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db python -m scripts.run_analytics_job --mes_ano=2025-08

# Recalcular últimos N meses
DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db python -m scripts.run_analytics_job --ultimos_n_meses=6
```

**O que o script faz**:
1. Determina quais meses processar (baseado em argumentos ou mês anterior)
2. Para cada mês:
   - Recalcula `analytics_vendedor_mes`
   - Recalcula `analytics_cliente_mes`
   - Recalcula `analytics_produto_mes`
   - Aplica scores (churn_score, meta_risk_score, queda_score)
   - Gera `analytics_alertas`
3. Registra logs e estatísticas

### Agendamento em Produção

#### Opção 1: Cloud Scheduler (Recomendado)

Crie um job no Cloud Scheduler que executa o script via Cloud Run Job ou HTTP endpoint:

```bash
# Criar Cloud Run Job (se implementado endpoint /admin/run_analytics_job)
gcloud scheduler jobs create http dipam-analytics-daily \
  --schedule="0 2 * * *" \
  --uri="https://dipam-ai-backend-xxx.run.app/admin/run_analytics_job" \
  --http-method=POST \
  --headers="Content-Type=application/json" \
  --message-body='{"ultimos_n_meses": 6}' \
  --time-zone="America/Sao_Paulo" \
  --region=us-central1
```

**Horário sugerido**: 02:00 AM (madrugada) para processar dados do dia anterior.

#### Opção 2: Cloud Run Job (Execução Direta)

Crie um Cloud Run Job que executa o script diretamente:

```bash
# Criar Cloud Run Job
gcloud run jobs create dipam-analytics-job \
  --image=gcr.io/PROJECT_ID/dipam-analytics:latest \
  --region=us-central1 \
  --set-env-vars="ENVIRONMENT=production,DB_TYPE=sqlite,SQLITE_PATH=data/dipam_dw.db" \
  --set-secrets="OPENAI_API_KEY=openai-api-key:latest" \
  --command="python" \
  --args="-m,scripts.run_analytics_job,--ultimos_n_meses,6" \
  --max-retries=3 \
  --task-timeout=1800

# Agendar execução diária via Cloud Scheduler
gcloud scheduler jobs create http dipam-analytics-daily \
  --schedule="0 2 * * *" \
  --uri="https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/PROJECT_ID/jobs/dipam-analytics-job:run" \
  --http-method=POST \
  --oauth-service-account-email=PROJECT_NUMBER-compute@developer.gserviceaccount.com \
  --time-zone="America/Sao_Paulo" \
  --region=us-central1
```

#### Opção 3: Pipeline Externo (Cron, Airflow, etc.)

Se você usa um orquestrador externo (Airflow, Prefect, etc.), configure um job que executa:

```bash
# Exemplo com cron (não recomendado para Cloud Run, mas útil para VMs)
0 2 * * * cd /path/to/dipa && DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db python -m scripts.run_analytics_job --ultimos_n_meses=6 >> /var/log/dipam-analytics.log 2>&1
```

### Monitoramento

Após configurar o agendamento, monitore os logs:

```bash
# Ver logs do Cloud Run Job
gcloud run jobs executions list --job=dipam-analytics-job --region=us-central1

# Ver logs de uma execução específica
gcloud run jobs executions logs read EXECUTION_NAME --job=dipam-analytics-job --region=us-central1
```

### Validação

Após o job rodar, valide que os dados foram atualizados:

```sql
-- Verificar analytics mais recentes
SELECT mes_ano, COUNT(*) as total 
FROM analytics_vendedor_mes 
GROUP BY mes_ano 
ORDER BY mes_ano DESC 
LIMIT 5;

-- Verificar alertas mais recentes
SELECT mes_ano, COUNT(*) as total_alertas 
FROM analytics_alertas 
GROUP BY mes_ano 
ORDER BY mes_ano DESC 
LIMIT 5;
```

### Frequência Recomendada

- **Diário**: Recalcular últimos 6 meses (garante que novos dados sejam processados)
- **Semanal**: Recalcular últimos 12 meses (ajusta scores com mais histórico)
- **Mensal**: Recalcular todos os meses (reprocessamento completo)

### Próximos Passos (FASE 6)

Na próxima fase, será implementado:
- Endpoint `/admin/run_analytics_job` para execução via HTTP
- Dashboard de monitoramento de jobs
- Alertas quando jobs falharem
- Treinamento automático de modelos ML (já implementado na FASE 5, pode ser agendado)

## 🤖 Treino de Modelos de ML (FASE 5)

O DIPAM COPILOT™ utiliza modelos de Machine Learning para previsões de churn, risco de meta e oportunidades de crescimento.

### Pré-requisitos

- Banco de dados com analytics_* populados (execute `run_analytics_job.py` primeiro)
- Dados históricos suficientes (recomendado: pelo menos 6 meses)

### Treinar Modelos

#### Treinar Todos os Modelos

```bash
# Treinar churn, meta_risk e oportunidades
DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db \
  python -m scripts.train_ml_models \
  --tipo_modelo=all \
  --mes_inicio=2024-11 \
  --mes_fim=2025-10 \
  --mes_referencia=2025-10
```

#### Treinar Modelo Específico

```bash
# Apenas churn
DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db \
  python -m scripts.train_ml_models \
  --tipo_modelo=churn \
  --mes_inicio=2024-11 \
  --mes_fim=2025-10

# Apenas meta_risk
DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db \
  python -m scripts.train_ml_models \
  --tipo_modelo=meta_risk \
  --mes_inicio=2024-11 \
  --mes_fim=2025-10

# Apenas oportunidades (usa apenas mes_referencia)
DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db \
  python -m scripts.train_ml_models \
  --tipo_modelo=oportunidades \
  --mes_referencia=2025-10
```

### Verificar Status dos Modelos

```bash
# Via API
curl https://SUA_URL_CLOUD_RUN/ml/status

# Resposta esperada:
{
  "status": "ok",
  "modelos": {
    "churn": {
      "treinado": true,
      "trained_at": "2025-01-16T12:34:56",
      "mes_inicio": "2024-11",
      "mes_fim": "2025-10",
      "n_samples": 12345,
      "accuracy": 0.85,
      "roc_auc": 0.92
    },
    "meta_risk": {
      "treinado": true,
      ...
    },
    "oportunidades": {
      "treinado": false
    }
  }
}
```

### Localização dos Modelos

Os modelos treinados são salvos em:
- `models/churn_model.joblib`
- `models/meta_risk_model.joblib`
- `models/oportunidades_model.joblib`
- `models/registry.json` (metadados)

### Agendamento de Retreino

Recomenda-se retreinar os modelos periodicamente:

- **Mensal**: Retreinar com dados dos últimos 12 meses
- **Trimestral**: Retreinar com dados dos últimos 18 meses

Exemplo de agendamento via Cloud Scheduler:

```bash
# Criar job mensal de retreino
gcloud scheduler jobs create http dipam-ml-retrain-monthly \
  --schedule="0 3 1 * *" \
  --uri="https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/PROJECT_ID/jobs/dipam-ml-retrain:run" \
  --http-method=POST \
  --oauth-service-account-email=PROJECT_NUMBER-compute@developer.gserviceaccount.com \
  --time-zone="America/Sao_Paulo" \
  --region=us-central1
```

### Uso dos Modelos

Os modelos são carregados automaticamente pelo `AgentService` quando disponíveis:

- **Churn**: Usado em consultas sobre clientes em risco
- **Meta Risk**: Usado em consultas sobre metas (intent `consulta_meta`)
- **Oportunidades**: Usado em consultas sobre crescimento potencial

As previsões aparecem automaticamente nas respostas estruturadas quando os modelos estão treinados.

## 🔄 Atualizações

### Atualizar Backend

```bash
# Fazer mudanças no código
git add .
git commit -m "Atualização: ..."
git push origin main

# Cloud Build fará deploy automaticamente (se configurado)
# Ou executar manualmente:
gcloud builds submit --config cloudbuild.yaml
```

### Atualizar Frontend

```bash
# Fazer mudanças no código
git add .
git commit -m "Atualização: ..."
git push origin main

# Vercel fará deploy automaticamente (se configurado)
# Ou executar manualmente:
vercel --prod
```

## 🧪 Testes em Produção

### Testar Endpoint /ask

Use o script `test_prod_agent.py` para validar se o endpoint `/ask` está respondendo corretamente em produção:

```bash
# Testar com URL de produção
DIPAM_API_BASE_URL="https://dipam-ai-backend-xxxxx-uc.a.run.app" \
  python -m scripts.test_prod_agent

# Ou com URL customizada
python -m scripts.test_prod_agent --url https://outra-url.com

# Com timeout customizado
python -m scripts.test_prod_agent --url https://... --timeout 60
```

O script testa 6 perguntas diferentes (Diretor, Supervisor, RCA) e valida:
- ✅ Status HTTP 200
- ✅ Respostas não genéricas (sem fallback)
- ✅ Estrutura de resposta correta (resumo_executivo, tabelas, etc.)
- ✅ Tempo de resposta razoável (< 10s recomendado)

**Saída esperada:**
```
🧪 TESTES DO ENDPOINT /ask - DIPAM COPILOT™
================================================================================
URL base: https://dipam-ai-backend-xxxxx-uc.a.run.app
Timeout: 30s
================================================================================

[1/6] Diretor - Meta não batida (agosto 2025)
Pergunta: Sou o Diretor e preciso saber de forma detalhada porque não batemos...
Papel: diretor
Testando... ✅
  Status: OK
  Tempo: 2345ms
  HTTP: 200
  Resumo:
    No mês de agosto de 2025, a DIPAM não atingiu a meta principalmente...
    ...

📊 RESUMO FINAL
================================================================================
Total de testes: 6
✅ Sucessos: 6
❌ Falhas/Problemas: 0

Tempos de resposta:
  Média: 2156ms
  Mínimo: 1890ms
  Máximo: 3456ms
```

## ✅ Checklist de Deploy

- [ ] Banco SQLite enviado para Cloud Storage
- [ ] Secrets configurados no Secret Manager
- [ ] Variáveis de ambiente configuradas no Cloud Run
- [ ] Backend deployado e health checks passando
- [ ] Variável `NEXT_PUBLIC_API_BASE_URL` configurada na Vercel
- [ ] Frontend deployado na Vercel
- [ ] Testes de perguntas críticas passando
- [ ] Logs sendo monitorados
- [ ] Documentação atualizada

## 📞 Suporte

Em caso de problemas:

1. Verifique os logs do backend e frontend
2. Execute o script de teste: `python scripts/test_cloud_like_env.py`
3. Verifique este documento de troubleshooting
4. Entre em contato com a equipe de desenvolvimento

---

**Última atualização**: 2025-01-XX

