# DEPLOY ENTERPRISE CLOUD RUN – DIPAM COPILOT™

## Status do Deploy

**Data:** 2025-11-18  
**Projeto GCP:** trivihair  
**Serviço:** dipam-ai-backend  
**Região:** us-central1

## URLs

**URL do Serviço:** https://dipam-ai-backend-642830139828.us-central1.run.app  
**URL Alternativa:** https://dipam-ai-backend-6arhlm3mha-uc.a.run.app

## Configuração

### Variáveis de Ambiente
- `ENV=production`
- `DB_TYPE=sqlite`
- `SQLITE_PATH=/app/data/dipam_dw.db`
- `OPENAI_API_KEY` (via Secret Manager: `openai-api-key:latest`)

### Imagem Docker
- **Registry:** gcr.io/trivihair/dipam-ai-backend
- **Build ID:** 1c85cccc-9a5d-48e1-bd6f-d5bd373e6827
- **Status:** SUCCESS

### Revisão Atual
- **Revision:** dipam-ai-backend-00065-dvt
- **Status:** Deployed and serving 100% of traffic

## Testes de Aceitação

Para rodar os testes de aceitação contra o backend em produção:

```bash
DIPAM_BACKEND_URL=https://dipam-ai-backend-642830139828.us-central1.run.app \
python scripts/run_acceptance_cli.py
```

## Frontend (Vercel)

**Variável de Ambiente Necessária:**
```
NEXT_PUBLIC_BACKEND_URL=https://dipam-ai-backend-642830139828.us-central1.run.app
```

**Ação Necessária:**
Atualizar a variável de ambiente `NEXT_PUBLIC_BACKEND_URL` no painel da Vercel para apontar para a URL acima.

## Observações

1. O endpoint `/ask` está respondendo (HTTP 200)
2. As intents estão sendo detectadas corretamente
3. Há um problema conhecido com a tabela `interacoes_agent` (coluna `intent_prevista` não existe) - não bloqueia o funcionamento
4. O banco SQLite deve estar disponível em `/app/data/dipam_dw.db` no container

## Próximos Passos

1. ✅ Build da imagem Docker concluído
2. ✅ Deploy no Cloud Run concluído
3. ✅ Variáveis de ambiente configuradas
4. ⚠️ Atualizar variável no Vercel (manual)
5. ⚠️ Verificar se banco SQLite está sendo carregado corretamente
6. ⚠️ Corrigir schema da tabela `interacoes_agent` (opcional, não bloqueia)
