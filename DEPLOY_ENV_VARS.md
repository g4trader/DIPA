# Variáveis de Ambiente - DIPAM COPILOT™

Este documento é a **fonte única da verdade** para todas as variáveis de ambiente usadas no sistema DIPAM COPILOT™.

## 📋 Índice

- [Backend (Cloud Run)](#backend-cloud-run)
- [Frontend (Vercel)](#frontend-vercel)
- [Mapeamento Completo](#mapeamento-completo)

---

## 🔧 Backend (Cloud Run)

### Variáveis Obrigatórias

| Variável | Onde é Usada | Descrição | Exemplo | Obrigatória em Prod? |
|----------|--------------|-----------|---------|---------------------|
| `OPENAI_API_KEY` | `src/llm_openai_client.py:42`<br>`src/agent/memory.py:38`<br>`app/api/query/route.ts:74` | Chave de API da OpenAI para chamadas LLM | `sk-proj-...` | ✅ **SIM** |
| `DB_TYPE` | `src/config.py:39` | Tipo de banco: `sqlite` ou `postgresql` | `sqlite` | ✅ **SIM** |
| `ENVIRONMENT` | `src/config.py:166`<br>`src/api/main.py:55` | Ambiente: `development`, `staging`, `production` | `production` | ✅ **SIM** |

### Variáveis Condicionais (dependem de DB_TYPE)

#### Se DB_TYPE=sqlite

| Variável | Onde é Usada | Descrição | Exemplo | Obrigatória? |
|----------|--------------|-----------|---------|--------------|
| `SQLITE_PATH` | `src/config.py:54` | Caminho do arquivo SQLite | `/app/data/dipam_dw.db` (Cloud Run)<br>`data/dipam_dw.db` (local) | ✅ **SIM** |

#### Se DB_TYPE=postgresql

| Variável | Onde é Usada | Descrição | Exemplo | Obrigatória? |
|----------|--------------|-----------|---------|--------------|
| `POSTGRES_HOST` | `src/config.py:44` | Host do PostgreSQL | `localhost` ou Cloud SQL socket | ✅ **SIM** |
| `POSTGRES_PORT` | `src/config.py:45` | Porta do PostgreSQL | `5432` | ⚠️ Opcional (padrão: 5432) |
| `POSTGRES_USER` | `src/config.py:46` | Usuário do PostgreSQL | `dipam_user` | ✅ **SIM** |
| `POSTGRES_PASSWORD` | `src/config.py:47` | Senha do PostgreSQL | `***` | ✅ **SIM** |
| `POSTGRES_DB` | `src/config.py:48` | Nome do banco | `dipam_dw` | ✅ **SIM** |

### Variáveis Opcionais

| Variável | Onde é Usada | Descrição | Padrão | Obrigatória? |
|----------|--------------|-----------|--------|--------------|
| `PORT` | `src/api/main.py:990` | Porta do servidor FastAPI | `8080` (Cloud Run)<br>`8000` (local) | ⚠️ Opcional |
| `LOG_LEVEL` | `src/config.py:174` | Nível de log: `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` | ⚠️ Opcional |
| `DEBUG` | `src/config.py:171` | Modo debug (True/False) | `True` (dev)<br>`False` (prod) | ⚠️ Opcional |
| `OPENAI_BASE_URL` | `src/llm_openai_client.py:49`<br>`src/agent/memory.py:45` | URL base da API OpenAI | `https://api.openai.com/v1` | ⚠️ Opcional |
| `OPENAI_MODEL` | `src/llm_openai_client.py:50` | Modelo OpenAI a usar | `gpt-4o-mini` | ⚠️ Opcional |
| `OPENAI_EMBEDDING_MODEL` | `src/agent/memory.py:23` | Modelo de embeddings | `text-embedding-3-small` | ⚠️ Opcional |
| `OPENAI_EMBEDDING_DIMENSION` | `src/agent/memory.py:25` | Dimensão dos embeddings | `1536` | ⚠️ Opcional |
| `DB_URL` | `src/config.py:58` | URL completa de conexão (sobrescreve outras configs) | - | ⚠️ Opcional |
| `DATABASE_TYPE` | `src/config.py:40` | Alias para DB_TYPE (compatibilidade) | - | ⚠️ Opcional |
| `API_HOST` | `src/run_api.py:28` | Host da API | `0.0.0.0` | ⚠️ Opcional |
| `API_PORT` | `src/run_api.py:29` | Porta da API (alias para PORT) | `8000` | ⚠️ Opcional |

### Variáveis de ML (Opcionais)

| Variável | Onde é Usada | Descrição | Padrão |
|----------|--------------|-----------|--------|
| `ML_RANDOM_SEED` | `src/config.py:143` | Seed para reprodutibilidade | `42` |
| `ML_TEST_SIZE` | `src/config.py:146` | Tamanho do conjunto de teste | `0.2` |
| `ML_CV_FOLDS` | `src/config.py:149` | Folds de cross-validation | `5` |

---

## 🎨 Frontend (Vercel)

### Variáveis Obrigatórias

| Variável | Onde é Usada | Descrição | Exemplo | Obrigatória? |
|----------|--------------|-----------|---------|--------------|
| `NEXT_PUBLIC_API_BASE_URL` | `lib/dipamApi.ts:16` | URL base da API do backend | `https://dipam-ai-backend-xxx.run.app` | ✅ **SIM** |

### Variáveis Opcionais

| Variável | Onde é Usada | Descrição | Padrão |
|----------|--------------|-----------|--------|
| `NEXT_PUBLIC_DIPAM_API_URL` | `lib/dipamApi.ts:17` | Alias para NEXT_PUBLIC_API_BASE_URL (compatibilidade) | - |
| `NEXT_PUBLIC_USE_LLM` | `components/DipaPanel.tsx:92` | Flag para usar LLM no frontend | `false` |

---

## 📊 Mapeamento Completo

### Backend - Ordem de Prioridade

1. **OPENAI_API_KEY** → `src/llm_openai_client.py`, `src/agent/memory.py`
   - **Validação**: Falha rápido no startup se ausente em produção
   - **Localização no código**: `src/api/main.py:61-71`

2. **DB_TYPE** → `src/config.py:39`
   - **Valores aceitos**: `sqlite`, `postgresql`
   - **Validação**: Verificado no startup

3. **SQLITE_PATH** (se DB_TYPE=sqlite) → `src/config.py:54`
   - **Validação**: Arquivo deve existir em produção
   - **Localização no código**: `src/api/main.py:94-108`

4. **ENVIRONMENT** → `src/config.py:166`
   - **Valores aceitos**: `development`, `staging`, `production`
   - **Impacto**: Em `production`, validações são mais rigorosas

### Frontend - Ordem de Prioridade

1. **NEXT_PUBLIC_API_BASE_URL** → `lib/dipamApi.ts:16`
   - **Fallback**: `NEXT_PUBLIC_DIPAM_API_URL` → `http://localhost:8000` (apenas dev)
   - **Importante**: Deve ser URL completa sem barra final

---

## 🔍 Validação no Startup

O backend valida variáveis críticas no startup (`src/api/main.py:49-138`):

1. ✅ **OPENAI_API_KEY**: Tenta obter via `get_openai_client()`
   - Se falhar em produção → aplicação não inicia
   - Se falhar em dev → apenas warning

2. ✅ **Configuração de Banco**: Valida `connection_string`
   - Se DB_TYPE=sqlite → verifica se arquivo existe
   - Se falhar em produção → aplicação não inicia

3. ✅ **Teste de Conexão**: Executa `SELECT COUNT(*) FROM metas_vendedor`
   - Se falhar em produção → aplicação não inicia

---

## 📝 Exemplos de Configuração

### Cloud Run (SQLite)

```bash
gcloud run services update dipam-ai-backend \
  --region=us-central1 \
  --set-env-vars="ENVIRONMENT=production,DB_TYPE=sqlite,SQLITE_PATH=/app/data/dipam_dw.db,LOG_LEVEL=INFO" \
  --set-secrets="OPENAI_API_KEY=openai-api-key:latest"
```

### Cloud Run (PostgreSQL)

```bash
gcloud run services update dipam-ai-backend \
  --region=us-central1 \
  --set-env-vars="ENVIRONMENT=production,DB_TYPE=postgresql,POSTGRES_HOST=/cloudsql/PROJECT:REGION:INSTANCE,POSTGRES_PORT=5432,POSTGRES_DB=dipam_dw" \
  --set-secrets="OPENAI_API_KEY=openai-api-key:latest,POSTGRES_USER=postgres-user:latest,POSTGRES_PASSWORD=postgres-password:latest"
```

### Vercel

No painel da Vercel → Settings → Environment Variables:

```
NEXT_PUBLIC_API_BASE_URL=https://dipam-ai-backend-xxx.run.app
```

---

## ⚠️ Troubleshooting

### "OPENAI_API_KEY não encontrada"

**Causa**: Secret não configurado ou não referenciado no Cloud Run.

**Solução**:
```bash
# Criar secret
echo -n "sk-..." | gcloud secrets create openai-api-key --data-file=-

# Referenciar no Cloud Run
gcloud run services update dipam-ai-backend \
  --set-secrets="OPENAI_API_KEY=openai-api-key:latest"
```

### "Arquivo SQLite não encontrado"

**Causa**: Arquivo não existe no caminho especificado ou não foi baixado do Cloud Storage.

**Solução**:
1. Verificar se arquivo existe: `ls -lh /app/data/dipam_dw.db`
2. Verificar se foi baixado no Dockerfile
3. Verificar logs do Cloud Build

### Frontend não conecta com backend

**Causa**: `NEXT_PUBLIC_API_BASE_URL` não configurada ou URL incorreta.

**Solução**:
1. Verificar variável na Vercel
2. Verificar se URL está correta (sem barra final)
3. Verificar CORS no backend

---

**Última atualização**: 2025-01-XX
**Versão**: 1.0.0

