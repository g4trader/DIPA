# DIPAM COPILOT - Modo Mock (Vercel Only)

Este documento descreve como usar o **modo mock** do DIPAM Copilot, que permite rodar 100% na Vercel sem depender do backend no Cloud Run.

## 📋 Visão Geral

O modo mock é uma implementação que:
- ✅ Não quebra o projeto atual (produção continua igual)
- ✅ Roda 100% na Vercel, sem Cloud Run
- ✅ Usa dados mockados exportados da base local (DW)
- ✅ Simula o endpoint `/ask` com a mesma estrutura de resposta (especialmente Q1)

## 🏗️ Arquitetura

### Feature Flag

O modo mock é controlado por variáveis de ambiente:

- `NEXT_PUBLIC_DIPAM_ENV=mock` (frontend)
- `DIPAM_MOCK_ENABLED=true` (opcional, para camada de API)

### Comportamento

**Quando `NEXT_PUBLIC_DIPAM_ENV=mock`:**
- Frontend **NÃO** chama o backend real em Cloud Run
- Em vez disso, chama endpoint local: `/api/mock/ask`
- Endpoint responde com dados mockados de arquivos JSON estáticos

**Quando `NEXT_PUBLIC_DIPAM_ENV` não é "mock":**
- Comportamento atual permanece: frontend chama backend em Cloud Run normalmente

## 📁 Estrutura de Arquivos

```
DIPA/
├── lib/
│   ├── dipamApi.ts              # ✅ Modificado: detecta modo mock
│   └── mock/
│       └── dipamMockEngine.ts   # ✅ Novo: motor mock
├── app/
│   └── api/
│       └── mock/
│           └── ask/
│               └── route.ts     # ✅ Novo: endpoint mock
├── mock/
│   └── data/
│       ├── q1_dados_dw.json     # ✅ Dados Q1 exportados
│       └── q1_estatisticas.json  # ✅ Estatísticas Q1
└── scripts/
    └── export_mock_q1_from_local_db.py  # ✅ Script de exportação
```

## 🚀 Como Usar

### 1. Exportar Dados Mock (Local)

Primeiro, exporte os dados Q1 da base local para JSON:

```bash
python scripts/export_mock_q1_from_local_db.py
```

Isso cria:
- `mock/data/q1_dados_dw.json`: lista de clientes sem compra há mais de 60 dias
- `mock/data/q1_estatisticas.json`: estatísticas e faixas

**Importante:** Os arquivos JSON gerados devem ser commitados no repositório.

### 2. Configurar Projeto Vercel Mock

Crie um **segundo projeto** na Vercel apontando para o **mesmo repositório**:

**Nome sugerido:** `dipam-copilot-mock`

**Variáveis de ambiente:**
```
NEXT_PUBLIC_DIPAM_ENV=mock
DIPAM_MOCK_ENABLED=true
```

**NÃO é necessário:**
- `NEXT_PUBLIC_BACKEND_URL` (não será usado)
- `NEXT_PUBLIC_API_BASE_URL` (não será usado)

### 3. Projeto Vercel Produção (Existente)

O projeto de produção continua igual:

**Nome:** `DIPAM COPILOT PROD` (ou nome atual)

**Variáveis de ambiente:**
```
NEXT_PUBLIC_DIPAM_ENV=prod
NEXT_PUBLIC_BACKEND_URL=https://dipam-ai-backend-XXXX.run.app
```

## 🧪 Testes Locais

### Testar Modo Mock

1. Configure variável de ambiente:
```bash
export NEXT_PUBLIC_DIPAM_ENV=mock
```

2. Inicie o servidor:
```bash
npm run dev
```

3. Faça uma pergunta Q1:
```
"Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?"
```

4. Validações:
- ✅ Nenhuma chamada a `dipam-ai-backend-*.run.app` no Network
- ✅ Chamada apenas para `/api/mock/ask`
- ✅ UI mostra:
  - Big Number
  - Resumo Executivo
  - Tabela com dados mockados

### Testar Modo Produção (Local)

1. Configure variável de ambiente:
```bash
export NEXT_PUBLIC_DIPAM_ENV=prod
export NEXT_PUBLIC_BACKEND_URL=https://dipam-ai-backend-XXXX.run.app
```

2. Inicie o servidor:
```bash
npm run dev
```

3. Validações:
- ✅ Chamadas para backend real no Cloud Run
- ✅ Respostas reais do backend

## 📊 Consultas Mockadas

### Q1 - Clientes sem Compra há Mais de 60 Dias

**Perguntas que ativam Q1 mock:**
- "Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?"
- "Clientes sem compra há mais de 60 dias"
- "Quais clientes estão há mais de 60 dias sem comprar?"

**Resposta mock inclui:**
- `dados_dw`: lista completa de clientes
- `big_number`: total de clientes
- `faixas`: distribuição por faixas de dias (61-120, 121-180, 181-300, >300)
- `resumo_executivo`: texto gerado automaticamente
- `confianca`: 0.92 (fixo para mock)
- `structured`: resposta estruturada completa

### Outras Consultas

Para perguntas fora do escopo Q1, o mock retorna:
```
"Este é um ambiente de demonstração (modo mock). 
Apenas a consulta Q1 (clientes sem compra há mais de 60 dias) está mockada. 
Para outras consultas, use o ambiente de produção."
```

## 🔧 Manutenção

### Atualizar Dados Mock

Quando a base local for atualizada:

1. Execute o script de exportação:
```bash
python scripts/export_mock_q1_from_local_db.py
```

2. Commit os arquivos JSON atualizados:
```bash
git add mock/data/*.json
git commit -m "chore: atualiza dados mock Q1"
git push
```

3. O projeto Vercel mock será automaticamente redeployado

## ✅ Critérios de Aceitação

- [x] Projeto atual em produção continua intacto (nenhum comportamento alterado sem mudar env)
- [x] Modo mock funciona 100% na Vercel, sem Cloud Run, usando apenas JSON estático
- [x] Q1 mock reproduz o cenário real (dados vindos do DW local exportados)
- [x] Caminho de dados no modo mock: Frontend → `/api/mock/ask` → `dipamMockEngine` → `mock/data/*.json`
- [x] Código organizado:
  - `mock/data/` para dados
  - `lib/mock/` para lógica
  - `app/api/mock/ask/route.ts` para endpoint

## 📝 Notas Técnicas

### Detecção de Modo Mock

A função `isMockEnv()` em `lib/dipamApi.ts` verifica:
```typescript
process.env.NEXT_PUBLIC_DIPAM_ENV === "mock"
```

### Redirecionamento

Quando em modo mock, `buildUrl("/ask")` retorna:
```typescript
"/api/mock/ask"  // ao invés de URL do Cloud Run
```

### Motor Mock

O `dipamMockEngine.ts`:
1. Detecta se a pergunta é Q1 (usando padrões de texto)
2. Lê dados de `mock/data/q1_dados_dw.json`
3. Calcula faixas e estatísticas
4. Monta resposta no mesmo formato do backend real

## 🐛 Troubleshooting

### Erro: "Cannot find module '@/mock/data/q1_dados_dw.json'"

**Solução:** Execute o script de exportação:
```bash
python scripts/export_mock_q1_from_local_db.py
```

### Modo mock não está ativando

**Verifique:**
1. Variável `NEXT_PUBLIC_DIPAM_ENV=mock` está configurada
2. Reinicie o servidor Next.js após mudar variáveis de ambiente
3. Verifique no console do navegador se `isMockEnv()` retorna `true`

### Dados mock estão desatualizados

**Solução:** Re-execute o script de exportação e faça commit dos novos arquivos JSON.

