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
| `SQLITE_PATH` | Caminho do arquivo SQLite | `/app/data/dipam_dw.db` (Cloud Run)<br>`data/dipam_dw.db` (local) |

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
5. Arquivo SQLite (`dipam_dw.db`) no Cloud Storage

### Passo 1: Upload do Banco SQLite

```bash
# Upload do banco SQLite para Cloud Storage
gsutil cp data/dipam_dw.db gs://trivihair-dipam-data/dipam_dw.db
```

### Passo 2: Configurar Secrets no Secret Manager

```bash
# Criar secret para OPENAI_API_KEY
echo -n "sk-..." | gcloud secrets create openai-api-key --data-file=-

# Criar secret para outros valores sensíveis (se necessário)
echo -n "valor" | gcloud secrets create postgres-password --data-file=-
```

### Passo 3: Deploy via Cloud Build (ou Deploy Direto)

#### Opção A: Deploy Direto (Recomendado - Mais Rápido)

```bash
# Deploy direto usando source (Cloud Run builda automaticamente)
gcloud run deploy dipam-ai-backend \
  --source . \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --memory=2Gi \
  --cpu=1 \
  --timeout=300s \
  --max-instances=10 \
  --min-instances=0 \
  --set-env-vars="ENVIRONMENT=production,DB_TYPE=sqlite,SQLITE_PATH=/app/data/dipam_dw.db,LOG_LEVEL=INFO" \
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

### Passo 4: Configurar Variáveis de Ambiente no Cloud Run

Após o deploy, configure as variáveis de ambiente:

#### Para SQLite (configuração atual):

```bash
gcloud run services update dipam-ai-backend \
  --region=us-central1 \
  --set-env-vars="ENVIRONMENT=production,DB_TYPE=sqlite,SQLITE_PATH=/app/data/dipam_dw.db,LOG_LEVEL=INFO" \
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

### Passo 5: Verificar Deploy

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

### Passo 6: Testar Endpoint Principal

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
NEXT_PUBLIC_API_BASE_URL=https://dipam-ai-backend-xxx.run.app
```

**Importante**: 
- Use a URL completa do Cloud Run (sem barra final)
- Configure para **Production**, **Preview** e **Development** se necessário
- Após adicionar, faça um novo deploy para aplicar as mudanças

**Onde é usada**: `lib/dipamApi.ts:16`

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

