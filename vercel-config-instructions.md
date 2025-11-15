# Configuração do Projeto Vercel

## 📋 Checklist de Configuração

### 1. Root Directory
O diretório raiz do frontend deve ser **`.`** (raiz do repositório), já que:
- ✅ `package.json` está na raiz
- ✅ `next.config.mjs` está na raiz  
- ✅ `app/` está na raiz
- ✅ `components/` está na raiz

**Como verificar/corrigir no Vercel Dashboard:**
1. Acesse: https://vercel.com/south-medias-projects/dipa/settings
2. Vá em **"General"** → **"Root Directory"**
3. Deve estar configurado como **`.`** ou **`/`**
4. Se estiver diferente (ex: `frontend/` ou `app/`), altere para **`.`**

### 2. Framework Preset
- **Framework**: Next.js
- **Build Command**: `npm run build`
- **Output Directory**: `.next`
- **Install Command**: `npm install`

### 3. Variáveis de Ambiente (CRÍTICO)

**URL do Backend Cloud Run:**
```
https://dipam-ai-backend-6arhlm3mha-uc.a.run.app
```

**Como adicionar no Vercel Dashboard:**
1. Acesse: https://vercel.com/south-medias-projects/dipa/settings/environment-variables
2. Clique em **"Add New"**
3. Configure:
   - **Key**: `NEXT_PUBLIC_DIPAM_API_URL`
   - **Value**: `https://dipam-ai-backend-6arhlm3mha-uc.a.run.app`
   - **Environments**: ✅ Production ✅ Preview ✅ Development
4. Clique em **"Save"**

### 4. Via Vercel CLI (Alternativa)

Se preferir configurar via CLI:

```bash
# 1. Login no Vercel
vercel login

# 2. Linkar o projeto
vercel link --yes --scope=south-medias-projects --project=dipa

# 3. Adicionar variável de ambiente
vercel env add NEXT_PUBLIC_DIPAM_API_URL production
# Quando solicitado, digite: https://dipam-ai-backend-6arhlm3mha-uc.a.run.app

vercel env add NEXT_PUBLIC_DIPAM_API_URL preview
# Mesmo valor: https://dipam-ai-backend-6arhlm3mha-uc.a.run.app

vercel env add NEXT_PUBLIC_DIPAM_API_URL development
# Mesmo valor: https://dipam-ai-backend-6arhlm3mha-uc.a.run.app

# 4. Fazer deploy
vercel --prod
```

### 5. Verificar Configuração

Após configurar, faça um novo deploy e verifique:

1. **Logs do Build**: Deve mostrar `npm run build` executando corretamente
2. **Runtime Logs**: Não deve ter erros de conexão com a API
3. **Console do Browser**: Verificar se `NEXT_PUBLIC_DIPAM_API_URL` está definida

### 6. Troubleshooting

**Erro: "Cannot find module 'next'"**
- ✅ Root Directory está errado
- ✅ Solução: Configure Root Directory como `.`

**Erro: "Failed to fetch" no frontend**
- ✅ Variável `NEXT_PUBLIC_DIPAM_API_URL` não está configurada
- ✅ Solução: Adicione a variável de ambiente no Vercel

**Build falha com erro de TypeScript**
- ✅ Verifique se todos os arquivos TypeScript estão corretos
- ✅ Execute `npm run build` localmente para verificar

## 🔗 Links Úteis

- **Dashboard do Projeto**: https://vercel.com/south-medias-projects/dipa
- **Settings**: https://vercel.com/south-medias-projects/dipa/settings
- **Environment Variables**: https://vercel.com/south-medias-projects/dipa/settings/environment-variables
- **Deployments**: https://vercel.com/south-medias-projects/dipa/deployments

