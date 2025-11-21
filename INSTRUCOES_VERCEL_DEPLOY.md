# 📋 Instruções para Deploy do Frontend Otimizado na Vercel

## 🟩 FASE 3 — Ativar Dashboard Otimizado no Frontend (Vercel)

### Passo a Passo:

1. **Acessar o painel da Vercel:**
   - URL: https://vercel.com
   - Fazer login na conta do projeto DIPAM

2. **Navegar para o projeto:**
   - Selecionar o projeto `dipam-copilot` (ou nome equivalente)

3. **Configurar variável de ambiente:**
   - Ir em **Settings** → **Environment Variables**
   - Clicar em **Add New**
   - Preencher:
     - **Name:** `NEXT_PUBLIC_USE_OPTIMIZED_DASHBOARD`
     - **Value:** `true`
     - **Environment:** Selecionar **Production** (e opcionalmente Preview/Development)
   - Clicar em **Save**

4. **Verificar que não há variável duplicada:**
   - Procurar por `NEXT_PUBLIC_USE_OPTIMIZED_DASHBOARD` na lista
   - Se existir com valor diferente, editar para `true`
   - Se não existir, criar nova

5. **Fazer redeploy:**
   - Ir em **Deployments**
   - Clicar nos três pontos (...) do último deployment
   - Selecionar **Redeploy**
   - Ou fazer push de um commit para trigger automático

6. **Aguardar build concluir:**
   - Monitorar o build no painel
   - Verificar que não há erros
   - Aguardar status "Ready"

### ✅ Validação:

Após o deploy, verificar:
- Build concluído sem erros
- URL de produção acessível: https://dipam.smartiasolutions.com.br
- Variável de ambiente ativa em produção

---

**Status:** ⏳ Aguardando execução manual no painel da Vercel

