# 🔄 Migração para Grok (xAI) - Guia Completo

**Data**: 18/11/2025  
**Status**: ✅ Implementado

---

## 📋 **RESUMO DAS MUDANÇAS**

O sistema foi atualizado para suportar **Grok (xAI)** como provedor LLM, mantendo compatibilidade com OpenAI. O sistema detecta automaticamente qual provedor usar baseado nas variáveis de ambiente configuradas.

---

## 🔑 **CONFIGURAÇÃO DA API KEY**

### **Chave de API:**
A chave de API do Grok deve ser configurada nas variáveis de ambiente. **NUNCA** commite a chave no código.

### **Onde Configurar:**

#### **1. Frontend (Vercel)**
1. Acesse o dashboard da Vercel: https://vercel.com/dashboard
2. Selecione o projeto DIPAM
3. Vá em **Settings** → **Environment Variables**
4. Adicione/atualize:
   - **Nome**: `GROK_API_KEY`
   - **Valor**: `sua-chave-grok-aqui` (chave fornecida separadamente)
   - **Environment**: Production, Preview, Development (conforme necessário)
5. Clique em **Save**

#### **2. Backend (Cloud Run)**
```bash
# Opção 1: Via Google Cloud Console
# 1. Acesse Cloud Run no GCP Console
# 2. Selecione o serviço dipam-ai-backend
# 3. Vá em "Edit & Deploy New Revision"
# 4. Na aba "Variables & Secrets", adicione:
#    - Name: GROK_API_KEY
#    - Value: SUA_CHAVE_GROK_AQUI

# Opção 2: Via gcloud CLI
gcloud run services update dipam-ai-backend \
  --set-env-vars="GROK_API_KEY=SUA_CHAVE_AQUI" \
  --region=us-central1

# Opção 3: Via Secret Manager (recomendado para produção)
echo -n "SUA_CHAVE_AQUI" | \
  gcloud secrets create grok-api-key --data-file=-

gcloud run services update dipam-ai-backend \
  --set-secrets="GROK_API_KEY=grok-api-key:latest" \
  --region=us-central1
```

#### **3. Local (.env)**
Crie/atualize o arquivo `.env` na raiz do projeto:
```bash
# Grok (xAI) - Prioridade alta
GROK_API_KEY=sua-chave-grok-aqui
GROK_MODEL=grok-beta
GROK_BASE_URL=https://api.x.ai/v1

# OpenAI - Fallback (opcional)
# OPENAI_API_KEY=sk-...
# OPENAI_MODEL=gpt-4o-mini
```

---

## 🔧 **ARQUIVOS MODIFICADOS**

### **Backend Python:**
1. ✅ **`src/llm_client.py`** (NOVO)
   - Cliente LLM genérico que suporta OpenAI e Grok
   - Detecta automaticamente qual provedor usar
   - Funções de compatibilidade mantidas

2. ✅ **`src/llm_integration_intent.py`**
   - Atualizado para usar `llm_client` ao invés de `llm_openai_client`
   - Mantém compatibilidade com código existente

3. ✅ **`src/api/main.py`**
   - Atualizado para validar Grok ou OpenAI
   - Logs indicam qual provedor está sendo usado

### **Frontend Next.js:**
1. ✅ **`app/api/query/route.ts`**
   - Detecta automaticamente Grok ou OpenAI
   - Prioridade: Grok > OpenAI
   - Mensagens de erro atualizadas

---

## 🎯 **COMO FUNCIONA**

### **Detecção Automática:**
O sistema detecta qual provedor usar na seguinte ordem:

1. **Se `GROK_API_KEY` estiver configurada** → Usa Grok
2. **Se `OPENAI_API_KEY` estiver configurada** → Usa OpenAI
3. **Se nenhuma estiver configurada** → Erro

### **Configuração do Grok:**
- **URL Base**: `https://api.x.ai/v1` (padrão)
- **Modelo**: `grok-beta` (padrão)
- **Endpoint**: `/chat/completions` (compatível com OpenAI)

### **Variáveis de Ambiente:**

#### **Grok:**
- `GROK_API_KEY` (obrigatória)
- `GROK_BASE_URL` (opcional, padrão: `https://api.x.ai/v1`)
- `GROK_MODEL` (opcional, padrão: `grok-beta`)

#### **OpenAI (fallback):**
- `OPENAI_API_KEY` (obrigatória se Grok não estiver configurado)
- `OPENAI_BASE_URL` (opcional, padrão: `https://api.openai.com/v1`)
- `OPENAI_MODEL` (opcional, padrão: `gpt-4o-mini`)

---

## ✅ **VALIDAÇÃO**

### **1. Verificar Configuração Local:**
```bash
# Testar se a chave está configurada
python -c "import os; print('GROK_API_KEY:', '✅ Configurada' if os.getenv('GROK_API_KEY') else '❌ Não configurada')"
```

### **2. Testar Backend:**
```bash
# Verificar logs do backend
# Deve aparecer: "✅ LLM configurado: GROK (model=grok-beta)"
```

### **3. Testar Frontend:**
```bash
# Fazer uma pergunta no frontend
# Deve funcionar normalmente usando Grok
```

### **4. Verificar Health Check:**
```bash
# Backend health check
curl https://dipam-ai-backend-642830139828.us-central1.run.app/health/llm
# Deve retornar status do LLM (Grok ou OpenAI)
```

---

## 🔄 **COMPATIBILIDADE**

### **Código Existente:**
- ✅ **100% compatível** - Código existente continua funcionando
- ✅ Funções de compatibilidade mantidas (`get_openai_client`, `OpenAIError`)
- ✅ Migração transparente - apenas configure `GROK_API_KEY`

### **APIs Suportadas:**
- ✅ Chat Completions (compatível com OpenAI)
- ✅ Function Calling (tools)
- ✅ System/User messages
- ✅ Parâmetros: temperature, max_tokens, top_p, etc.

---

## 📝 **NOTAS IMPORTANTES**

### **Segurança:**
- ⚠️ **NUNCA** commite a chave de API no código
- ⚠️ Use variáveis de ambiente ou Secret Manager
- ⚠️ A chave fornecida deve ser mantida segura

### **Performance:**
- Grok pode ter latências diferentes da OpenAI
- Timeout padrão: 30 segundos (configurável)
- Monitorar logs para identificar problemas

### **Modelos Disponíveis:**
- `grok-beta` (padrão) - Modelo principal do Grok
- Outros modelos podem estar disponíveis conforme documentação do xAI

---

## 🚀 **PRÓXIMOS PASSOS**

1. ✅ Configurar `GROK_API_KEY` no Vercel (Frontend)
2. ✅ Configurar `GROK_API_KEY` no Cloud Run (Backend)
3. ✅ Testar uma pergunta no frontend
4. ✅ Verificar logs para confirmar uso do Grok
5. ✅ Monitorar performance e ajustar se necessário

---

## 🐛 **TROUBLESHOOTING**

### **Erro: "LLM não configurado"**
- Verifique se `GROK_API_KEY` está configurada
- Verifique se a variável está no ambiente correto (Production/Preview)

### **Erro: "Failed to contact Grok API"**
- Verifique se a chave está correta
- Verifique se há problemas de rede/firewall
- Verifique logs do backend para detalhes

### **Erro: "Timeout"**
- Aumente o timeout nas configurações
- Verifique latência da API do Grok

---

## 📚 **REFERÊNCIAS**

- **Grok API Docs**: https://docs.x.ai/
- **xAI Website**: https://x.ai/
- **API Endpoint**: https://api.x.ai/v1/chat/completions

---

**Última Atualização**: 18/11/2025  
**Status**: ✅ Pronto para uso

