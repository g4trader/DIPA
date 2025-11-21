# 📋 INSTRUÇÕES PARA REDEPLOY DO FRONTEND (VERCEL)

## ⚠️ AÇÃO MANUAL NECESSÁRIA

Para completar o deploy em produção, é necessário fazer o redeploy do frontend na Vercel com a variável de ambiente correta.

---

## 🔧 OPÇÃO 1: Via Painel da Vercel (Recomendado)

1. **Acesse o painel da Vercel:**
   - URL: https://vercel.com
   - Faça login na sua conta

2. **Navegue até o projeto:**
   - Selecione o projeto "DIPAM COPILOT" ou similar

3. **Configure a variável de ambiente:**
   - Vá em **Settings** > **Environment Variables**
   - Adicione ou edite a variável:
     - **Nome:** `NEXT_PUBLIC_USE_OPTIMIZED_DASHBOARD`
     - **Valor:** `true`
     - **Ambientes:** Production, Preview, Development (ou apenas Production)

4. **Force um redeploy:**
   - Vá em **Deployments**
   - Clique nos três pontos (...) do último deployment
   - Selecione **Redeploy**
   - Aguarde o build finalizar

---

## 🔧 OPÇÃO 2: Via Vercel CLI

```bash
# Instalar Vercel CLI (se não tiver)
npm i -g vercel

# Fazer login
vercel login

# Configurar variável de ambiente
vercel env add NEXT_PUBLIC_USE_OPTIMIZED_DASHBOARD production
# Quando solicitado, digite: true

# Fazer deploy de produção
vercel --prod
```

---

## ✅ VALIDAÇÃO PÓS-REDEPLOY

Após o redeploy, valide:

1. **Acesse a aplicação:**
   - URL: https://dipam.smartiasolutions.com.br

2. **Faça a pergunta Q1:**
   ```
   "Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?"
   ```

3. **Valide visualmente:**
   - ✅ Big Number exibido no topo
   - ✅ Resumo Executivo abaixo do Big Number
   - ✅ Tabela "Dados Analíticos — Consulta Geral" com 20 registros/página
   - ✅ Colunas "Vendedor" e "Supervisor" preenchidas (>97%)
   - ✅ Zero duplicatas na tabela
   - ✅ Console do navegador sem erros

4. **Valide telemetria:**
   - Verifique logs do Cloud Run para eventos `frontend_performance`
   - Confirme que métricas estão sendo enviadas

---

## 📊 STATUS ATUAL

- ✅ Backend deployado e operacional
- ⏳ Frontend aguardando redeploy manual
- ✅ Scripts de validação disponíveis e funcionando

---

**Após o redeploy, execute as validações finais e atualize o relatório.**
