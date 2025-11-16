# Notas sobre Cloud Run - DIPAM COPILOT™

Este documento descreve o estado atual do backend e como ele é iniciado no Cloud Run.

## 🏗️ Como o Servidor é Iniciado

### Comando no Dockerfile

```bash
CMD ["python", "-m", "src.api.main"]
```

Este comando executa `python -m src.api.main`, que:
1. Carrega o módulo `src.api.main`
2. Executa o bloco `if __name__ == "__main__":` em `src/api/main.py`
3. Inicia o uvicorn na porta definida por `PORT` (padrão: 8080)

### Bloco de Inicialização (`src/api/main.py`)

```python
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))  # Fallback: 8080 (Cloud Run padrão)
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",  # IMPORTANTE: 0.0.0.0 para Cloud Run
        port=port,
        reload=False,  # Desabilitado em produção
        log_level="info"
    )
```

**Importante**: 
- O host DEVE ser `0.0.0.0` para Cloud Run (não `127.0.0.1` ou `localhost`)
- A porta DEVE usar `os.getenv("PORT", 8080)` (Cloud Run define PORT=8080)

## 🔧 Como a Porta é Definida

1. **Cloud Run**: Define `PORT=8080` via variável de ambiente
2. **Código**: Usa `os.getenv("PORT", 8080)` com fallback para 8080
3. **Dockerfile**: Define `ENV PORT=8080` como padrão

**Ordem de prioridade**:
1. Variável de ambiente `PORT` do Cloud Run
2. Fallback no código: `8080` (Cloud Run padrão)

## 📋 O que o `startup_event` Faz

### Antes (problemático)

O `startup_event` fazia `raise RuntimeError` em produção se:
- `OPENAI_API_KEY` não configurada
- Banco de dados não encontrado
- Erro ao inicializar DB
- Erro ao carregar modelos

**Problema**: Qualquer `raise` no `startup_event` derruba o container antes de escutar na porta.

### Depois (resiliente)

O `startup_event` agora:
1. **NUNCA faz raise** - apenas loga erros e seta flags em `app.state`
2. **Inicializa flags de estado**:
   - `app.state.db_available = False`
   - `app.state.openai_available = False`
   - `app.state.agent_service_available = False`
   - `app.state.startup_errors = []`

3. **Para cada componente**:
   - Tenta inicializar (DB, OpenAI, AgentService)
   - Se falhar: loga erro, adiciona em `startup_errors`, seta flag `False`
   - **NÃO faz raise** - servidor continua subindo

4. **Resumo final**: Loga warnings se houver erros, mas servidor sempre sobe

**Resultado**: Servidor sempre escuta na porta 8080, mesmo que componentes falhem.
Os health endpoints (`/health`, `/health/db`, `/health/openai`) reportam o status.

## 🚨 Em Quais Casos o App Poderia "Morrer" na Inicialização

### Antes das Correções

1. ✅ **Erro de importação de módulos** - Tratado (não deveria acontecer se dependências estão instaladas)
2. ✅ **raise RuntimeError no startup_event** - **CORRIGIDO** (agora não faz raise)
3. ✅ **raise FileNotFoundError no startup** - **CORRIGIDO** (agora apenas loga)
4. ✅ **Exceções não tratadas no startup** - **CORRIGIDO** (try/except em todos os blocos)

### Depois das Correções

O servidor **SEMPRE** sobe, exceto:
- Erro fatal de importação de módulos Python (dependências não instaladas)
- Erro fatal no próprio FastAPI/uvicorn (improvável)

**Todos os erros de configuração** (DB, OpenAI) são tratados e reportados via health endpoints.

## 🔍 Health Endpoints

### `/health` (básico)

- **Status**: Sempre retorna 200 se servidor rodando
- **Status geral**: 
  - `"healthy"` - Todos componentes disponíveis
  - `"degraded"` - Alguns componentes indisponíveis, mas servidor funciona
- **Componentes**: Reporta status de DB, OpenAI, AgentService
- **Startup errors**: Lista erros do startup (se houver)

### `/health/db`

- **Status**: 
  - 200 - Banco disponível e funcionando
  - 503 - Banco não disponível (mas servidor continua rodando)
- **Verifica**: Flag `app.state.db_available` + query de teste

### `/health/openai`

- **Status**: 
  - 200 - OpenAI disponível e funcionando
  - 503 - OpenAI não disponível (mas servidor continua rodando)
- **Verifica**: Flag `app.state.openai_available` + chamada de teste

## 🧪 Como Testar Localmente

### Script Automatizado (Recomendado)

```bash
./scripts/run_cloud_run_local.sh
```

Este script:
1. Ativa venv
2. Configura variáveis de ambiente (PORT=8080, ENVIRONMENT=production, etc.)
3. Carrega OPENAI_API_KEY do .env se existir
4. Inicia servidor com `python -m src.api.main`

### Manual

```bash
export PORT=8080
export ENVIRONMENT=production
export DB_TYPE=sqlite
export SQLITE_PATH="data/dipam_dw.db"
export OPENAI_API_KEY="sk-..."  # Opcional para testes

source venv/bin/activate
python -m src.api.main
```

**Testar**:
```bash
curl http://localhost:8080/health
curl http://localhost:8080/health/db
curl http://localhost:8080/health/openai
```

## 📊 Fluxo de Inicialização (Corrigido)

```
1. Cloud Run inicia container
2. Executa: python -m src.api.main
3. Carrega src/api/main.py
4. Cria app FastAPI
5. Define flags app.state.* (todas False inicialmente)
6. Executa startup_event():
   a. Tenta validar OpenAI → se falhar: loga erro, seta flag False (NÃO faz raise)
   b. Tenta inicializar DB → se falhar: loga erro, seta flag False (NÃO faz raise)
   c. Tenta carregar modelos → se falhar: loga erro, seta flag False (NÃO faz raise)
7. uvicorn.run() inicia servidor na porta PORT (8080)
8. Servidor escuta em 0.0.0.0:8080 ✅
9. Health endpoints podem ser chamados e reportam status real
```

## ✅ Garantias Implementadas

1. ✅ Servidor **SEMPRE** escuta na porta `PORT` (8080 no Cloud Run)
2. ✅ Servidor **SEMPRE** sobe, mesmo que DB/OpenAI falhem
3. ✅ Health endpoints reportam status real dos componentes
4. ✅ Erros são logados claramente para diagnóstico
5. ✅ Não há `sys.exit()` ou `raise` fatal no startup
6. ✅ Comando CMD no Dockerfile compatível com Cloud Run

## 🔄 Comandos de Deploy e Verificação

### Deploy no Cloud Run

```bash
# IMPORTANTE: Ajustar PROJECT_ID, SERVICE_NAME e REGION conforme seu projeto
gcloud run deploy SERVICE_NAME \
  --project=PROJECT_ID \
  --region=REGION \
  --source=. \
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

**Importante**: Não codificar `OPENAI_API_KEY` em texto plano. Use Secret Manager:
1. Criar secret: `echo -n "sk-..." | gcloud secrets create openai-api-key --data-file=-`
2. Referenciar no deploy: `--set-secrets="OPENAI_API_KEY=openai-api-key:latest"`

### Verificação Após Deploy

Após o deploy, substitua `SUA_URL_CLOUD_RUN` pela URL real retornada pelo Cloud Run:

```bash
# Health básico
curl https://SUA_URL_CLOUD_RUN/health

# Health do banco
curl https://SUA_URL_CLOUD_RUN/health/db

# Health da OpenAI
curl https://SUA_URL_CLOUD_RUN/health/openai

# Teste de pergunta real
curl -X POST https://SUA_URL_CLOUD_RUN/ask \
  -H "Content-Type: application/json" \
  -d '{"pergunta": "qual a meta de vendas do mês de outubro 2025", "papel": "diretor"}'
```

## 🔄 Próximos Passos

1. ✅ Testar script `run_cloud_run_local.sh` localmente
2. ⏳ Fazer deploy no Cloud Run usando comandos acima
3. ⏳ Verificar logs para confirmar que servidor sobe corretamente
4. ⏳ Testar health endpoints em produção

---

**Última atualização**: 2025-11-15
**Versão**: 2.0.0 (Cloud Run Friendly)
