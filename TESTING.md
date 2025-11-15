# 🧪 Guia de Testes - Dipam AI Frontend + Backend

Este guia mostra como testar a integração completa do frontend Next.js com a API FastAPI do Dipam AI.

## 📋 Pré-requisitos

- **Python 3.11+** instalado
- **Node.js 18+** e **npm** instalados
- **Banco de dados SQLite** (configuração padrão para testes)
- Opcional: PostgreSQL via Docker

---

## 🚀 Passo 1: Configurar o Backend (API FastAPI)

### 1.1 Ativar ambiente virtual (se houver)

```bash
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows
```

### 1.2 Instalar dependências Python

```bash
pip install -r requirements.txt
```

### 1.3 Configurar banco de dados (SQLite - mais simples)

Para testes rápidos, use SQLite:

```bash
# Define a variável de ambiente
export DB_TYPE=sqlite
```

Ou no Windows:
```cmd
set DB_TYPE=sqlite
```

### 1.4 Inicializar banco de dados (se necessário)

```bash
python src/db_init.py
```

### 1.5 Rodar a API do Dipam AI

**No diretório raiz do projeto**, execute:

```bash
DB_TYPE=sqlite python -m src.run_api
```

Ou no Windows:
```cmd
set DB_TYPE=sqlite && python -m src.run_api
```

**A API estará rodando em:** `http://localhost:8000`

### 1.6 Verificar se a API está funcionando

Abra em outro terminal:

```bash
# Teste de health check
curl http://localhost:8000/health

# Ou no navegador
open http://localhost:8000/health  # Mac
start http://localhost:8000/health  # Windows
```

Você deve ver uma resposta JSON como:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-14T...",
  "environment": "development",
  "version": "1.0.0",
  "database": "sqlite"
}
```

### 1.7 Acessar documentação interativa

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🎨 Passo 2: Configurar o Frontend (Next.js)

### 2.1 Instalar dependências Node.js

Em um novo terminal, na raiz do projeto:

```bash
npm install
```

### 2.2 Configurar variável de ambiente

O arquivo `.env.local` já foi criado com a configuração padrão:

```env
NEXT_PUBLIC_DIPAM_API_URL=http://localhost:8000
```

Se precisar alterar, edite `.env.local` na raiz do projeto.

### 2.3 Rodar o frontend

```bash
npm run dev
```

**O frontend estará rodando em:** `http://localhost:3000`

---

## 🧪 Passo 3: Testar a Integração

### 3.1 Testar Chat com o Agente

1. Abra o navegador em: `http://localhost:3000`
2. Você verá o painel do DIPAM COPILOT™
3. Digite uma pergunta, por exemplo:
   - "Por que o vendedor ROTA 77 não bateu a meta em dezembro?"
   - "Quais são os top vendedores este mês?"
   - "Analise as vendas do vendedor João Silva"
4. Clique em "Perguntar ao copiloto"
5. Aguarde a resposta do agente
6. Verifique:
   - ✅ Resposta textual aparece
   - ✅ Intent e confiança são exibidos
   - ✅ Botão "Ver detalhes de dados" expande o contexto JSON

### 3.2 Testar Preview de Vendedor

Para testar o componente `VendedorPreviewCard`, você pode criar uma página de teste ou adicionar em algum componente existente:

```tsx
import { VendedorPreviewCard } from "@/components/VendedorPreviewCard";

// No seu componente
<VendedorPreviewCard 
  vendedor="ROTA 77" 
  mesAno="2025-11" 
/>
```

---

## 🔍 Testar Endpoints da API Manualmente

### Teste 1: Health Check

```bash
curl http://localhost:8000/health
```

### Teste 2: Endpoint `/ask`

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "pergunta": "Por que o vendedor ROTA 77 não bateu a meta em dezembro?",
    "usuario_id": "fabiano",
    "papel": "diretor"
  }'
```

**Resposta esperada:**
```json
{
  "resposta": "...",
  "intent": "meta_vendedor",
  "contexto": {...},
  "confianca": 0.8,
  "timestamp": "2025-11-14T..."
}
```

### Teste 3: Endpoint `/preview/vendedor`

```bash
curl "http://localhost:8000/preview/vendedor/ROTA%2077/2025-11"
```

**Resposta esperada:**
```json
{
  "vendedor": "ROTA 77",
  "mes_ano": "2025-11",
  "dados": {...},
  "timestamp": "2025-11-14T..."
}
```

---

## 🐛 Troubleshooting

### Problema: "Erro de conexão com a API"

**Solução:**
1. Verifique se a API está rodando: `curl http://localhost:8000/health`
2. Verifique se a variável `NEXT_PUBLIC_DIPAM_API_URL` no `.env.local` está correta
3. Reinicie o frontend após alterar `.env.local`
4. Verifique se não há conflito de portas

### Problema: "Erro ao conectar com banco de dados"

**Solução:**
1. Verifique se `DB_TYPE=sqlite` está definido
2. Execute `python src/db_init.py` para inicializar o banco
3. Verifique se o arquivo `data/dipam_dw.db` existe

### Problema: "Erro ao processar pergunta" na API

**Solução:**
1. Verifique os logs da API no terminal onde está rodando
2. Verifique se os modelos de ML foram treinados (opcional)
3. Verifique se há dados no banco de dados

### Problema: Frontend não atualiza após mudanças

**Solução:**
1. O Next.js deve ter hot reload ativo
2. Se não funcionar, pare o servidor (`Ctrl+C`) e rode `npm run dev` novamente
3. Limpe o cache: `rm -rf .next` e rode novamente

---

## 📝 Checklist de Testes

### Backend
- [ ] API inicia sem erros
- [ ] Health check retorna status `healthy`
- [ ] Documentação Swagger acessível em `/docs`
- [ ] Endpoint `/ask` responde corretamente
- [ ] Endpoint `/preview/vendedor/{vendedor}/{mes_ano}` responde corretamente

### Frontend
- [ ] Frontend inicia sem erros
- [ ] Página principal carrega corretamente
- [ ] Input de pergunta funciona
- [ ] Loading state aparece durante requisição
- [ ] Resposta do agente é exibida corretamente
- [ ] Intent e confiança são exibidos
- [ ] Botão "Ver detalhes de dados" expande o contexto
- [ ] Erros são tratados e exibidos de forma amigável

### Integração
- [ ] Frontend consegue comunicar com backend
- [ ] Respostas são formatadas corretamente
- [ ] Estados de loading e erro funcionam
- [ ] Histórico de mensagens persiste durante a sessão

---

## 🎯 Exemplos de Teste

### Teste Completo do Chat

1. **Inicie o backend:**
   ```bash
   DB_TYPE=sqlite python -m src.run_api
   ```

2. **Inicie o frontend:**
   ```bash
   npm run dev
   ```

3. **No navegador (`http://localhost:3000`):**
   - Digite: "Qual foi a receita total em novembro?"
   - Clique em "Perguntar ao copiloto"
   - Verifique:
     - ✅ Loading aparece
     - ✅ Resposta é exibida
     - ✅ Intent e confiança aparecem
     - ✅ Contexto pode ser expandido

### Teste do Preview de Vendedor

```bash
# No terminal
curl "http://localhost:8000/preview/vendedor/João%20Silva/2025-11"
```

---

## 🚀 Comandos Rápidos (Resumo)

### Terminal 1 - Backend
```bash
cd /Users/lucianoterres/Documents/GitHub/DIPA
DB_TYPE=sqlite python -m src.run_api
```

### Terminal 2 - Frontend
```bash
cd /Users/lucianoterres/Documents/GitHub/DIPA
npm run dev
```

### Terminal 3 - Testes
```bash
# Health check
curl http://localhost:8000/health

# Teste /ask
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"pergunta": "Qual foi a receita em novembro?", "papel": "diretor"}'

# Teste /preview
curl "http://localhost:8000/preview/vendedor/ROTA%2077/2025-11"
```

---

## 📚 Recursos Adicionais

- **Documentação da API**: http://localhost:8000/docs
- **Código do cliente HTTP**: `lib/dipamApi.ts`
- **Componente de chat**: `components/DipaPanel.tsx`
- **Componente de preview**: `components/VendedorPreviewCard.tsx`
- **Documentação da API (Backend)**: `API_README.md`

---

**Dica:** Para testes mais rápidos, você pode usar o Swagger UI em `http://localhost:8000/docs` para testar os endpoints diretamente sem precisar do frontend!



