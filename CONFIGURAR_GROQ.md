# 🚀 Configuração do Groq - Guia Rápido

## Passo 1: Obter a chave de API do Groq

1. Acesse: https://console.groq.com/
2. Faça login ou crie uma conta
3. Navegue até "API Keys" ou "Keys"
4. Crie uma nova chave de API
5. Copie a chave (formato: `gsk_...`)

## Passo 2: Configurar no Cloud Run

Execute o script de configuração:

```bash
./setup-groq-secret.sh <SUA_CHAVE_GROQ>
```

Ou usando variável de ambiente:

```bash
GROQ_API_KEY=<sua-chave> ./setup-groq-secret.sh
```

## O que o script faz:

1. ✅ Cria/atualiza o secret `groq-api-key` no Secret Manager
2. ✅ Concede permissões ao Cloud Run service account
3. ✅ Atualiza o Cloud Run service para usar o secret
4. ✅ Faz deploy final com o Groq configurado

## Verificação

Após executar o script, verifique os logs:

```bash
gcloud run services logs read dipam-ai-backend --region=us-central1 --limit=20 | grep -i groq
```

Você deve ver: `✅ LLM configurado: GROQ (model=mixtral-8x7b-32768)`

## Modelos disponíveis no Groq

- `mixtral-8x7b-32768` (padrão)
- `llama2-70b-4096`
- `llama3-70b-8192`
- `llama3-8b-8192`

Para usar outro modelo, defina a variável `GROQ_MODEL` no Secret Manager ou no Cloud Run.


