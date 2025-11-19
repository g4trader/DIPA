# 🔧 Fix: Permissões do Secret Manager para Grok

**Erro**: Permission denied on secret para service account do Cloud Run

---

## 🎯 **SOLUÇÃO RÁPIDA**

### **Opção 1: Conceder Permissão ao Secret (Recomendado)**

```bash
# 1. Obter o nome da service account do Cloud Run
SERVICE_ACCOUNT="642830139828-compute@developer.gserviceaccount.com"
PROJECT_ID="642830139828"
SECRET_NAME="grok-api-key"

# 2. Conceder permissão de acesso ao secret
gcloud secrets add-iam-policy-binding $SECRET_NAME \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor" \
  --project=$PROJECT_ID

# 3. Verificar se funcionou
gcloud secrets get-iam-policy $SECRET_NAME --project=$PROJECT_ID
```

### **Opção 2: Usar Variável de Ambiente Direta (Mais Simples)**

Se não quiser usar Secret Manager, pode configurar diretamente como variável de ambiente:

```bash
PROJECT_ID="642830139828"
SERVICE_NAME="dipam-ai-backend"
REGION="us-central1"
GROK_KEY="SUA_CHAVE_GROK_AQUI"

gcloud run services update $SERVICE_NAME \
  --set-env-vars="GROK_API_KEY=${GROK_KEY}" \
  --region=$REGION \
  --project=$PROJECT_ID
```

---

## 📋 **PASSO A PASSO COMPLETO (Opção 1 - Secret Manager)**

### **1. Verificar se o Secret Existe**

```bash
gcloud secrets list --project=642830139828 | grep grok-api-key
```

Se não existir, criar:
```bash
echo -n "SUA_CHAVE_GROK_AQUI" | \
  gcloud secrets create grok-api-key \
    --data-file=- \
    --project=642830139828 \
    --replication-policy="automatic"
```

### **2. Conceder Permissão à Service Account**

```bash
# Service account do Cloud Run (padrão)
SERVICE_ACCOUNT="642830139828-compute@developer.gserviceaccount.com"

# Conceder permissão
gcloud secrets add-iam-policy-binding grok-api-key \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor" \
  --project=642830139828
```

### **3. Atualizar o Cloud Run Service**

```bash
gcloud run services update dipam-ai-backend \
  --set-secrets="GROK_API_KEY=grok-api-key:latest" \
  --region=us-central1 \
  --project=642830139828
```

### **4. Verificar Configuração**

```bash
# Ver variáveis de ambiente e secrets
gcloud run services describe dipam-ai-backend \
  --region=us-central1 \
  --project=642830139828 \
  --format="value(spec.template.spec.containers[0].env)"
```

---

## 🔍 **VERIFICAÇÃO DE PERMISSÕES**

### **Verificar Permissões Atuais do Secret:**

```bash
gcloud secrets get-iam-policy grok-api-key \
  --project=642830139828
```

Deve mostrar algo como:
```
bindings:
- members:
  - serviceAccount:642830139828-compute@developer.gserviceaccount.com
  role: roles/secretmanager.secretAccessor
```

### **Verificar Service Account do Cloud Run:**

```bash
gcloud run services describe dipam-ai-backend \
  --region=us-central1 \
  --project=642830139828 \
  --format="value(spec.template.spec.serviceAccountName)"
```

Se retornar vazio, está usando a service account padrão do projeto.

---

## 🚨 **TROUBLESHOOTING**

### **Erro: "Secret not found"**
```bash
# Criar o secret primeiro
echo -n "SUA_CHAVE_GROK_AQUI" | \
  gcloud secrets create grok-api-key \
    --data-file=- \
    --project=642830139828
```

### **Erro: "Permission denied" mesmo após conceder permissão**
```bash
# Verificar se a service account está correta
gcloud run services describe dipam-ai-backend \
  --region=us-central1 \
  --project=642830139828 \
  --format="value(spec.template.spec.serviceAccountName)"

# Se retornar uma service account customizada, usar ela:
CUSTOM_SA="sua-service-account@642830139828.iam.gserviceaccount.com"
gcloud secrets add-iam-policy-binding grok-api-key \
  --member="serviceAccount:${CUSTOM_SA}" \
  --role="roles/secretmanager.secretAccessor" \
  --project=642830139828
```

### **Erro: "Service account not found"**
```bash
# Listar service accounts do projeto
gcloud iam service-accounts list --project=642830139828

# Usar a service account correta do Cloud Run
```

---

## ✅ **COMANDO ÚNICO (Tudo de uma vez)**

```bash
#!/bin/bash
PROJECT_ID="642830139828"
SERVICE_NAME="dipam-ai-backend"
REGION="us-central1"
SECRET_NAME="grok-api-key"
GROK_KEY="SUA_CHAVE_GROK_AQUI"
SERVICE_ACCOUNT="${PROJECT_ID}-compute@developer.gserviceaccount.com"

# 1. Criar secret (se não existir)
if ! gcloud secrets describe $SECRET_NAME --project=$PROJECT_ID &>/dev/null; then
  echo "Criando secret..."
  echo -n "$GROK_KEY" | \
    gcloud secrets create $SECRET_NAME \
      --data-file=- \
      --project=$PROJECT_ID \
      --replication-policy="automatic"
else
  echo "Secret já existe, atualizando..."
  echo -n "$GROK_KEY" | \
    gcloud secrets versions add $SECRET_NAME \
      --data-file=- \
      --project=$PROJECT_ID
fi

# 2. Conceder permissão
echo "Concedendo permissão à service account..."
gcloud secrets add-iam-policy-binding $SECRET_NAME \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor" \
  --project=$PROJECT_ID

# 3. Atualizar Cloud Run
echo "Atualizando Cloud Run service..."
gcloud run services update $SERVICE_NAME \
  --set-secrets="GROK_API_KEY=${SECRET_NAME}:latest" \
  --region=$REGION \
  --project=$PROJECT_ID

echo "✅ Configuração concluída!"
```

---

## 📝 **NOTAS IMPORTANTES**

1. **Service Account Padrão**: Cloud Run usa `{PROJECT_NUMBER}-compute@developer.gserviceaccount.com` por padrão
2. **Permissões**: A role `roles/secretmanager.secretAccessor` é necessária para ler secrets
3. **Versão do Secret**: Use `:latest` para sempre pegar a versão mais recente
4. **Alternativa Simples**: Se Secret Manager for complexo, use variável de ambiente direta (Opção 2)

---

**Última Atualização**: 19/11/2025

