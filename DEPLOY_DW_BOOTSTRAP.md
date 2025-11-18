# Implementação: Carregamento Automático do DW SQLite do GCS + Healthcheck

## Status: ✅ IMPLEMENTADO E DEPLOYADO

**Data:** 2025-11-18  
**Revisão Cloud Run:** dipam-ai-backend-00071-rm7

## Resumo da Implementação

Implementação completa do carregamento automático do DW SQLite a partir do Google Cloud Storage (GCS) e healthcheck específico do DW.

## Componentes Implementados

### 1. Módulo Bootstrap DW (`src/dw/bootstrap_dw.py`)

**Função principal:** `ensure_sqlite_dw_available()`

**Comportamento:**
- Verifica se `DB_TYPE=sqlite`
- Verifica se arquivo SQLite existe em `SQLITE_PATH`
- Se não existir, baixa automaticamente de `DIPAM_DW_GCS_URI`
- Usa `google-cloud-storage` para download
- Cria diretório pai se necessário
- Loga progresso e tamanho do arquivo
- Trata erros de forma clara

**Tratamento de erros:**
- Em produção (`ENV=production`): falha bloqueia inicialização
- Em desenvolvimento: apenas loga aviso e continua

### 2. Integração na Inicialização

**Arquivos modificados:**
- `src/dw/connection.py`: chama `ensure_sqlite_dw_available()` antes de criar engine
- `src/api/main.py`: `startup_event` chama `ensure_sqlite_dw_available()` antes de `init_db()`

**Ordem de execução:**
1. Startup event verifica configuração
2. Chama `ensure_sqlite_dw_available()` (baixa do GCS se necessário)
3. Chama `init_db()` (cria engine e sessão)
4. Marca banco como disponível

### 3. Endpoint `/health/dw`

**Comportamento:**
- Retorna HTTP 200 se `DB_TYPE != sqlite` (ignora check)
- Retorna HTTP 200 se arquivo existe e query funciona
- Retorna HTTP 500 se arquivo não existe ou query falha
- Inclui `path` e `size_mb` na resposta

**Query de teste:**
- Tenta várias tabelas possíveis: `dim_cliente`, `clientes`, `dim_tempo`, `vendedores`
- Garante compatibilidade com schema antigo (raw data) e novo (DW)

### 4. Configuração GCS

**Bucket:** `gs://dipam-dw-prod/dipam_dw.db`  
**Arquivo:** `dipam_dw.db` (2.0GB)  
**Status:** ✅ Upload concluído

**Permissões:**
- Service account do Cloud Run: `609095880025-compute@developer.gserviceaccount.com`
- Role: `roles/storage.objectViewer`
- Status: ✅ Configurado

### 5. Variáveis de Ambiente no Cloud Run

**Configuração atual:**
- `ENV=production`
- `DB_TYPE=sqlite`
- `SQLITE_PATH=/app/data/dipam_dw.db`
- `DIPAM_DW_GCS_URI=gs://dipam-dw-prod/dipam_dw.db` ✅ **NOVA**
- `OPENAI_API_KEY` via Secret Manager

**Recursos:**
- Memória: 8Gi (aumentada de 4Gi para suportar banco de 2GB)
- CPU: 2
- Timeout: 300s

### 6. Dependências

**Biblioteca:** `google-cloud-storage==2.14.0`  
**Status:** ✅ Já estava no `requirements.txt`

## Fluxo de Funcionamento

### No Cloud Run (Produção):

1. **Container inicia**
2. **Startup event executa:**
   - Verifica `DB_TYPE=sqlite`
   - Verifica se `/app/data/dipam_dw.db` existe
   - Se não existe:
     - Lê `DIPAM_DW_GCS_URI=gs://dipam-dw-prod/dipam_dw.db`
     - Baixa arquivo do GCS usando Application Default Credentials
     - Salva em `/app/data/dipam_dw.db`
     - Loga progresso e tamanho
   - Se existe: pula download
3. **Inicializa conexão:**
   - Cria engine SQLAlchemy
   - Cria sessão
   - Marca banco como disponível
4. **Servidor pronto:**
   - Endpoint `/health/dw` retorna 200
   - Endpoint `/ask` pode consultar DW

### Localmente (Desenvolvimento):

1. **App inicia**
2. **Se `DIPAM_DW_GCS_URI` configurado:**
   - Baixa do GCS se arquivo não existir
3. **Se não configurado:**
   - Usa arquivo local se existir
   - Loga aviso se não existir (não bloqueia)

## Testes

### Healthcheck DW:
```bash
curl https://dipam-ai-backend-642830139828.us-central1.run.app/health/dw
```

**Resposta esperada (sucesso):**
```json
{
  "status": "ok",
  "message": "DW SQLite acessível",
  "path": "/app/data/dipam_dw.db",
  "size_mb": 2048.0
}
```

### Teste de pergunta:
```bash
curl -X POST https://dipam-ai-backend-642830139828.us-central1.run.app/ask \
  -H "Content-Type: application/json" \
  -d '{"pergunta": "Quais clientes estão sem compra há mais de 60 dias?"}'
```

## Logs Importantes

**Bootstrap DW:**
```
[DW-BOOTSTRAP] Arquivo SQLite não encontrado em /app/data/dipam_dw.db
[DW-BOOTSTRAP] Baixando DW SQLite de gs://dipam-dw-prod/dipam_dw.db para /app/data/dipam_dw.db
[DW-BOOTSTRAP] ✅ Arquivo SQLite baixado com sucesso: /app/data/dipam_dw.db
[DW-BOOTSTRAP] Tamanho do arquivo: 2048.00 MB
```

**Erros críticos:**
```
[DW-BOOTSTRAP] ❌ Erro ao baixar SQLite do GCS: <erro>
[init_db] Erro crítico ao garantir SQLite disponível: <erro>
```

## Troubleshooting

### Problema: Arquivo não baixa
**Causa:** Permissões do GCS ou `DIPAM_DW_GCS_URI` não configurado  
**Solução:** Verificar IAM do service account e variável de ambiente

### Problema: Timeout no download
**Causa:** Arquivo muito grande (2GB)  
**Solução:** Aumentar timeout do Cloud Run (já configurado para 300s)

### Problema: Memória insuficiente
**Causa:** Banco de 2GB + aplicação  
**Solução:** Aumentar memória do Cloud Run (já configurado para 8Gi)

### Problema: Tabela não encontrada no healthcheck
**Causa:** Schema antigo (raw data) vs novo (DW)  
**Solução:** Healthcheck tenta várias tabelas (já implementado)

## Próximos Passos

1. ✅ Bootstrap DW implementado
2. ✅ Healthcheck DW implementado
3. ✅ Upload para GCS concluído
4. ✅ Permissões configuradas
5. ✅ Variáveis de ambiente configuradas
6. ✅ Deploy concluído
7. ⚠️ Testar com perguntas reais (Q1-Q13)
8. ⚠️ Validar que queries DW funcionam corretamente

## Arquivos Criados/Modificados

- ✅ `src/dw/bootstrap_dw.py` (novo)
- ✅ `src/dw/connection.py` (modificado)
- ✅ `src/api/main.py` (modificado - healthcheck ajustado)
- ✅ `requirements.txt` (já tinha google-cloud-storage)

## Comandos Úteis

### Upload do banco para GCS:
```bash
gsutil cp data/dipam_dw.db gs://dipam-dw-prod/dipam_dw.db
```

### Verificar permissões:
```bash
gcloud projects get-iam-policy trivihair \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:609095880025-compute@developer.gserviceaccount.com"
```

### Ver logs do bootstrap:
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=dipam-ai-backend AND textPayload=~'DW-BOOTSTRAP'" \
  --limit 20 \
  --project=trivihair
```

