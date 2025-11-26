# Integração Q2 com LLM - Documentação

## Resumo

Integração completa da análise Q2 (queda de faturamento) com a camada de LLM, permitindo que perguntas em linguagem natural sobre "queda de faturamento" sejam roteadas corretamente para a Q2.

## Arquitetura

### Fluxo de Detecção

1. **Detecção baseada em regras** (`src/llm_integration_intent_q2.py`):
   - Detecta perguntas sobre queda de faturamento usando palavras-chave
   - Parseia período mencionado na pergunta
   - Gera IntentSpec automaticamente

2. **Integração com LLM** (`src/llm_integration_intent.py`):
   - Tenta detecção Q2 antes de chamar LLM
   - Se Q2 detectada, usa detecção baseada em regras
   - Caso contrário, usa LLM para gerar IntentSpec

3. **Orquestração** (`src/agent/orquestrador_dw.py`):
   - Recebe IntentSpec Q2
   - Executa query DW `get_clientes_queda_faturamento_periodo()`
   - Retorna dados estruturados

## Componentes Implementados

### 1. Detecção de Intent Q2

**Função:** `detectar_intent_q2(pergunta: str) -> bool`

**Palavras-chave detectadas:**
- "queda de faturamento"
- "queda nas vendas"
- "despencaram"
- "reduziram as compras"
- "pararam de comprar"
- etc.

**Exemplos de perguntas detectadas:**
- "Quais clientes tiveram queda de faturamento de setembro para outubro?"
- "Me mostre os clientes que despencaram em vendas no último mês."
- "Top clientes com maior queda de faturamento neste trimestre."
- "Qual rota mais sofreu queda de faturamento em outubro?"

### 2. Parse de Período

**Função:** `parse_periodo_queda_faturamento(texto_usuario: str) -> Dict[str, Any]`

**Formatos suportados:**
- "de setembro para outubro" → set/25 → out/25
- "último mês" → mês anterior → mês atual
- "no trimestre atual" → primeiro mês do trimestre → segundo mês
- "set/25 x out/25" → setembro/2025 → outubro/2025
- Menciona meses específicos: "setembro e outubro de 2025"

**Retorna:**
```python
{
    "data_ini_mes_anterior": "2025-09-01",
    "data_fim_mes_anterior": "2025-09-30",
    "data_ini_mes_atual": "2025-10-01",
    "data_fim_mes_atual": "2025-10-31",
    "ano": 2025
}
```

### 3. Geração de IntentSpec

**Função:** `gerar_intent_spec_q2(pergunta: str) -> IntentSpec`

**Características:**
- Tipo: `"queda_faturamento"`
- Dimensão: `"cliente"`
- Filtros padrão:
  - `min_faturamento_mes_anterior: 500.0`
  - `min_queda_percentual: 10.0`
  - `limit: 100`
- Detecta "top N" e ajusta `limit`

### 4. Integração com Orquestrador

**Função:** `executar_q2_via_orquestrador(pergunta: str, intent_spec: Optional[IntentSpec]) -> Dict[str, Any]`

**Retorna:**
```python
{
    "tipo": "Q2_QUEDA_FATURAMENTO",
    "dados_dw": {
        "status": "ok",
        "dados": [...],
        "metrics": {...}
    },
    "periodo": {
        "data_ini_mes_anterior": "2025-09-01",
        "data_fim_mes_anterior": "2025-09-30",
        "data_ini_mes_atual": "2025-10-01",
        "data_fim_mes_atual": "2025-10-31"
    },
    "intent_spec": IntentSpec
}
```

## Exemplos de Uso

### Exemplo 1: Pergunta básica

```python
from src.llm_integration_intent_q2 import processar_pergunta_q2

pergunta = "Quais clientes tiveram queda de faturamento de setembro para outubro?"
resultado = processar_pergunta_q2(pergunta)

print(resultado["tipo"])  # "Q2_QUEDA_FATURAMENTO"
print(resultado["dados_dw"]["status"])  # "ok"
print(len(resultado["dados_dw"]["dados"]))  # 100 (ou menos)
```

### Exemplo 2: Via integração LLM principal

```python
from src.llm_integration_intent import gerar_intent_spec_via_llm

pergunta = "Quais clientes tiveram queda de faturamento de setembro para outubro?"
intent_spec = gerar_intent_spec_via_llm(pergunta)

# Se Q2 detectada, retorna IntentSpec gerado por regras
# Caso contrário, retorna IntentSpec gerado por LLM
```

### Exemplo 3: Parse de período manual

```python
from src.llm_integration_intent_q2 import parse_periodo_queda_faturamento

texto = "de setembro para outubro"
periodo = parse_periodo_queda_faturamento(texto)

print(periodo["data_ini_mes_anterior"])  # "2025-09-01"
print(periodo["data_fim_mes_atual"])     # "2025-10-31"
```

## Testes

**Arquivo:** `tests/test_llm_integration_q2.py`

**Cobertura:**
- ✅ Detecção de intent Q2 (8 testes)
- ✅ Parse de período (6 testes)
- ✅ Geração de IntentSpec (2 testes)
- ✅ Integração com orquestrador (1 teste)
- ✅ Validação de perguntas não-Q2 (1 teste)

**Total:** 18 testes, todos passando ✅

## Critérios de Aceite

✅ **Perguntas em linguagem natural sobre "queda de faturamento" são roteadas consistentemente para a Q2**

✅ **O período é inferido corretamente em pelo menos três casos:**
- "de setembro para outubro" ✅
- "último mês" ✅
- "no trimestre atual" ✅

✅ **A integração não quebra fluxos existentes da Q1**
- Detecção Q2 é opcional (tenta detectar, mas não força)
- Se falhar, usa LLM normalmente

✅ **Há testes automatizados cobrindo:**
- Mapeamento da intent ✅
- Parse de período ✅
- Chamada do orquestrador (estrutura validada) ✅

## Arquivos Criados/Modificados

1. ✅ `src/llm_integration_intent_q2.py` (novo)
   - Detecção de intent Q2
   - Parse de período
   - Geração de IntentSpec
   - Integração com orquestrador

2. ✅ `src/llm_integration_intent.py` (modificado)
   - Adicionada detecção Q2 antes de chamar LLM
   - Importa módulo Q2 se disponível

3. ✅ `tests/test_llm_integration_q2.py` (novo)
   - 18 testes cobrindo todas as funcionalidades

4. ✅ `docs/INTEGRACAO_Q2_LLM.md` (este arquivo)

## Próximos Passos

1. **Integração com resposta executiva:**
   - Usar dados Q2 para gerar resposta executiva via LLM
   - Focar em rotas/vendedores mais impactados
   - Faixas de queda (10-20%, 20-40%, >40%)

2. **Frontend:**
   - Renderizar tabela Q2 com colunas específicas
   - Big Number com total de clientes com queda
   - Gráficos de distribuição por faixas

3. **Melhorias no parse:**
   - Suporte a mais formatos de período
   - Detecção de ano quando não mencionado
   - Validação de períodos inválidos

## Notas Técnicas

- **Abordagem:** Detecção baseada em regras (regex + palavras-chave) antes de chamar LLM
- **Vantagem:** Mais rápido, mais previsível, não depende de LLM para Q2
- **Fallback:** Se detecção Q2 falhar, usa LLM normalmente
- **Compatibilidade:** Não quebra fluxos existentes (Q1, outras intents)

