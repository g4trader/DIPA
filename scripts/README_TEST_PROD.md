# Script de Testes em Produção - test_prod_agent.py

## 📋 Descrição

Script para validar o endpoint `/ask` em produção, testando perguntas reais e verificando se as respostas estão "inteligentes" (sem fallback genérico).

## 🚀 Uso

### Básico

```bash
# Usando variável de ambiente
DIPAM_API_BASE_URL="https://dipam-ai-backend-xxxxx-uc.a.run.app" \
  python -m scripts.test_prod_agent
```

### Com URL customizada

```bash
# Sobrescrever URL via argumento
python -m scripts.test_prod_agent --url https://outra-url.com
```

### Com timeout customizado

```bash
# Aumentar timeout para 60 segundos
python -m scripts.test_prod_agent --url https://... --timeout 60
```

## 📊 Perguntas Testadas

O script testa 6 perguntas diferentes:

1. **Diretor - Meta não batida**: "Sou o Diretor e preciso saber de forma detalhada porque não batemos a meta no mês de agosto 2025."
2. **Diretor - Vendedores em risco**: "Quais são os vendedores com maior risco de não bater a meta em agosto 2025?"
3. **Supervisor - Clientes em risco de churn**: "Quais clientes da minha carteira estão em maior risco de churn em agosto 2025?"
4. **RCA - Clientes sem compra**: "Quais clientes positivados no produto Nissin não compram há mais de 60 dias?"
5. **Geral - Impacto negativo**: "Quais foram os vendedores que mais impactaram negativamente o realizado de agosto 2025?"
6. **Geral - Oportunidades**: "Quais clientes têm maior potencial de crescimento na rota 22 em agosto 2025?"

## ✅ Validações

Para cada pergunta, o script valida:

- ✅ **Status HTTP 200**: Resposta bem-sucedida
- ✅ **Estrutura de resposta**: Presença de `resposta`, `resumoExecutivo` ou `structured`
- ✅ **Sem fallback genérico**: Detecta frases como:
  - "não tenho informações suficientes"
  - "não encontrei dados"
  - "não foi possível processar"
  - "erro ao consultar"
  - etc.
- ✅ **Tempo de resposta**: Medido e reportado (recomendado < 10s)

## 📈 Saída

### Exemplo de Saída

```
🧪 TESTES DO ENDPOINT /ask - DIPAM COPILOT™
================================================================================
URL base: https://dipam-ai-backend-xxxxx-uc.a.run.app
Timeout: 30s
================================================================================

[1/6] Diretor - Meta não batida (agosto 2025)
Pergunta: Sou o Diretor e preciso saber de forma detalhada porque não batemos...
Papel: diretor
Testando... ✅
  Status: OK
  Tempo: 2345ms
  HTTP: 200
  Resumo:
    No mês de agosto de 2025, a DIPAM não atingiu a meta principalmente...
    As principais responsáveis foram: ROTA 77, ROTA 22, ROTA 94...

[2/6] Diretor - Vendedores em risco (agosto 2025)
...

📊 RESUMO FINAL
================================================================================
Total de testes: 6
✅ Sucessos: 6
❌ Falhas/Problemas: 0

Tempos de resposta:
  Média: 2156ms
  Mínimo: 1890ms
  Máximo: 3456ms
```

## ⚠️ Status Possíveis

- **OK**: Teste passou (HTTP 200, resposta válida, sem fallback)
- **POSSÍVEL PROBLEMA**: Teste falhou parcialmente (ex.: HTTP 200 mas com fallback, ou estrutura incompleta)
- **ERRO**: Erro de conexão, timeout, ou HTTP != 200

## 🔧 Troubleshooting

### Erro: "URL base da API não fornecida"

**Solução**: Defina `DIPAM_API_BASE_URL` ou use `--url`:

```bash
python -m scripts.test_prod_agent --url https://sua-url.com
```

### Erro: "Timeout após 30s"

**Solução**: Aumente o timeout:

```bash
python -m scripts.test_prod_agent --url https://... --timeout 60
```

### Erro: "biblioteca 'requests' não encontrada"

**Solução**: Instale a biblioteca:

```bash
pip install requests
```

### Respostas com fallback genérico

**Possíveis causas**:
- Banco de dados sem dados para o período solicitado
- Erro no processamento da pergunta
- Modelos ML não treinados (para insights preditivos)

**Ação**: Verifique logs do backend e dados disponíveis no banco.

## 📝 Notas

- O script não valida se há dados no banco para o período solicitado
- Frases de fallback são detectadas, mas podem ser legítimas se realmente não houver dados
- O script é robusto a mudanças leves na estrutura da resposta (usa `.get()`)

## 🎯 Critérios de Aceitação

O script é considerado bem-sucedido quando:

- ✅ Todas (ou maioria) das perguntas retornam HTTP 200
- ✅ Tempo de resposta < 10s por pergunta
- ✅ Respostas não são genéricas/fallback
- ✅ Respostas contêm resumo/tabelas/insights estruturados

