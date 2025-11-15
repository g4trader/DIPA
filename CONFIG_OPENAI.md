# Configuração da OpenAI API

Este documento explica como configurar as variáveis de ambiente da OpenAI para o backend da Dipam AI.

## Variáveis Necessárias

O backend precisa das seguintes variáveis de ambiente:

- `OPENAI_API_KEY`: Sua chave de API da OpenAI (obrigatória)
- `OPENAI_BASE_URL`: URL base da API (opcional, padrão: `https://api.openai.com/v1`)
- `OPENAI_MODEL`: Modelo a ser usado (opcional, padrão: `gpt-4o-mini`)

## Configuração

### Opção 1: Arquivo `.env` (Recomendado)

1. Crie um arquivo `.env` na raiz do projeto:
```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-proj-sua-chave-aqui
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

2. O arquivo `.env` já está no `.gitignore` para não ser versionado.

### Opção 2: Variáveis de Ambiente do Sistema

Exporte as variáveis antes de iniciar a API:

```bash
export OPENAI_API_KEY="sk-proj-sua-chave-aqui"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_MODEL="gpt-4o-mini"
```

## Iniciar a API

Para iniciar a API com as variáveis configuradas:

```bash
# Com arquivo .env na raiz
DB_TYPE=sqlite python -m src.run_api

# Ou exportando variáveis manualmente
export OPENAI_API_KEY="sua-chave"
DB_TYPE=sqlite python -m src.run_api
```

## Verificação

Para verificar se está funcionando:

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "pergunta": "quem bateu meta em agosto?",
    "usuario_id": "teste",
    "papel": "diretor"
  }'
```

## Nota de Segurança

⚠️ **IMPORTANTE**: 
- Nunca commite sua chave de API no Git
- O arquivo `.env` já está no `.gitignore`
- Use variáveis de ambiente em produção



