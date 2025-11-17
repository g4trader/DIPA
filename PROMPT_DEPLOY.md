# Regras de Deploy - DIPAM COPILOT™

## Você é responsável pelo deploy do backend DIPAM COPILOT™

### REGRAS OBRIGATÓRIAS

1) **O ÚNICO projeto válido para o backend de produção é:**
   - **project ID: `trivihair`**

2) **Você NUNCA deve usar:**
   - `automatizar-452311`
   - nenhum outro project ID
   - nenhum comando gcloud sem `--project=trivihair`

3) **Antes de sugerir qualquer comando de deploy, SEMPRE:**
   - inclua explicitamente: `--project=trivihair`
   - inclua: `--region=us-central1`
   - valide que o serviço é: `dipam-ai-backend`

4) **Exemplo de comando correto:**

```bash
gcloud run deploy dipam-ai-backend \
  --project=trivihair \
  --region=us-central1 \
  --platform=managed \
  --image=gcr.io/trivihair/dipam-ai-backend \
  --set-secrets=OPENAI_API_KEY=openai-api-key:latest \
  --allow-unauthenticated
```

5) **Nunca altere o project ID, nem "otimize" tirando o parâmetro `--project`.**

6) **Se em algum log aparecer outro project ID, isso é ERRO. Você deve:**
   - corrigi-lo
   - explicar o problema
   - propor o comando certo com `--project=trivihair`

### Configuração Inicial

Sempre que for fazer deploy, primeiro configure o projeto:

```bash
gcloud config set project trivihair
gcloud config list  # Verificar que project = trivihair
```

### URLs Importantes

- **Console Cloud Run:** https://console.cloud.google.com/run/detail/us-central1/dipam-ai-backend?project=trivihair
- **URL do serviço:** Será algo como `https://dipam-ai-backend-xxxxx-uc.a.run.app` (verificar no Console)

### Variáveis de Ambiente (Vercel Frontend)

A variável `NEXT_PUBLIC_API_BASE_URL` (ou similar) deve apontar para a URL do Cloud Run do projeto **trivihair**, nunca para outro projeto.

### Build da Imagem

Se a imagem estiver em outro registry, o pipeline de build deve publicar no projeto **trivihair**:

```bash
gcloud builds submit --tag gcr.io/trivihair/dipam-ai-backend --project=trivihair
```

