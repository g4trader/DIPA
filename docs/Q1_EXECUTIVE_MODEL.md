# 📊 MODELO EXECUTIVO Q1 - Clientes Sem Compra +60 Dias

## 🎯 Objetivo de Negócio

A resposta da Q1 deve orientar a Diretoria Comercial e Supervisão sobre:

- **Onde existe potencial real de recuperação de receita**
- **Quais clientes são recuperáveis no curto prazo**
- **Onde alocar energia operacional** (rota, vendedor, supervisão)
- **Quais ações práticas geram resultado**

### ❌ A Q1 NÃO deve:

- Gerar textos longos sem valor
- Produzir redundâncias
- Usar linguagem informal ou consultiva demais
- Misturar clientes recuperáveis com "clientes mortos"

---

## 📋 Estrutura Executiva Obrigatória

A resposta final deve seguir **EXATAMENTE** esta estrutura:

### 1. VISÃO GERAL EXECUTIVA (3-4 linhas)

- Quantidade total de clientes ativos sem compra >60 dias
- Concentração por rotas/supervisões (quando disponível)
- Insight principal: **foco em clientes recentes (≤120 dias)**
- Risco comercial real, sem exageros

### 2. INDICADORES COMERCIAIS

Tabela (ou bloco estruturado) com faixas de dias:

| Faixa | Probabilidade | Prioridade |
|-------|---------------|------------|
| 61-120 dias | Alta probabilidade | **Prioridade 1** |
| 121-180 dias | Média probabilidade | Prioridade 2 |
| 181-300 dias | Baixa probabilidade | Prioridade 3 |
| >300 dias | Muito baixa | **Não priorizar** |

Esses dados devem ser calculados dinamicamente a partir dos registros do DW.

### 3. DIAGNÓSTICO COMERCIAL

Bloco estruturado com:

- **Riscos reais**: perda de share, roteiros frios, concentração em poucas rotas
- **Oportunidades**: rotas e supervisões com maior potencial (foco em 61-120 dias)
- **Tendências**: faixa mais crítica vs faixa mais recuperável

### 4. RECOMENDAÇÕES ESTRATÉGICAS

Sempre dividir em:

- **Prioridade 1 (61-120 dias)**: Recontato imediato, campanhas de reativação, SKU âncora por rota
- **Prioridade 2 (121-180 dias)**: Ações com supervisão, acompanhamento de rotas específicas
- **Não priorizar (>300 dias)**: Clientes com muito tempo sem compra não devem aparecer como oportunidade

Com recomendações acionáveis:
- Recontato
- Campanhas de reativação
- SKU âncora por rota
- Ações com supervisão

### 5. IMPACTO ESPERADO

Bloco curto e formal, focado em receita recuperável.

---

## 🔧 Implementação Técnica

### Função de Classificação por Faixas

```python
def _classificar_clientes_por_faixa(dados: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Classifica clientes por faixa de dias sem compra.
    
    Retorna:
    - total: Total de clientes
    - faixa_61_120: Clientes com 61-120 dias (Prioridade 1)
    - faixa_121_180: Clientes com 121-180 dias (Prioridade 2)
    - faixa_181_300: Clientes com 181-300 dias (Prioridade 3)
    - faixa_mais_300: Clientes com mais de 300 dias (não priorizar)
    """
```

### Cálculo de Confiança

A confiança é calculada baseada em:

1. **% de clientes ativos sem vendedor faltante** (≥95% = +0.2, ≥85% = +0.15, ≥70% = +0.1)
2. **Presença de supervisão** (≥90% = +0.15, ≥70% = +0.1, ≥50% = +0.05)
3. **Coerência estatística das faixas** (soma das faixas = total ±5 = +0.1)
4. **Ausência de inconsistências** (0% inconsistente = +0.05, ≤2% = +0.02)

Confiança base: 0.5  
Confiança máxima: 1.0

### Estrutura JSON Obrigatória

```json
{
  "resumo_executivo": "string (3-5 linhas)",
  "tabela_principal": [...],
  "insights": [...],
  "diagnostico_comercial": {
    "riscos": "string",
    "oportunidades": "string",
    "tendencias": "string"
  },
  "recomendacoes_estrategicas": {
    "prioridade_1": "string (61-120 dias)",
    "prioridade_2": "string (121-180 dias)",
    "nao_priorizar": "string (>300 dias)"
  },
  "impacto_esperado": "string (curto e formal)"
}
```

---

## 🚫 Palavras Proibidas

A resposta da Q1 **NUNCA** deve conter:

- "criticozinho"
- "movimento"
- "blitz"
- "talvez"
- "pode ser que"
- "pode ser"

---

## ✅ Critérios de Aceitação

1. ✅ A resposta final da Q1 segue rigorosamente a estrutura executiva
2. ✅ Não há linguagem informal
3. ✅ A Q1 prioriza clientes 61-120 dias como OPORTUNIDADE principal
4. ✅ Clientes >300 dias são classificados como "não prioritários"
5. ✅ O texto é 100% acionável: cada bloco leva a uma decisão real
6. ✅ Resposta curta, limpa e sem redundâncias
7. ✅ Confiança não é mais fixa em 50% (calculada dinamicamente)
8. ✅ Teste automatizado valida a estrutura

---

## 🧪 Validação

Execute o script de validação:

```bash
python scripts/test_q1_estrutura_executiva.py
```

O script valida:
- Presença de todos os blocos obrigatórios
- Ausência de palavras proibidas
- Coerência entre faixas de dias e prioridades
- Cliente >300 dias não aparece como oportunidade

---

## 📝 Arquivos Modificados

1. `src/llm_integration_intent.py`
   - Função `_classificar_clientes_por_faixa()` criada
   - Prompt Q1 reescrito com estrutura executiva
   - Fallback ajustado para seguir estrutura executiva

2. `src/api/mapper_handler_refatorado.py`
   - Função `_calcular_confianca_q1()` criada
   - Confiança calculada dinamicamente para Q1

3. `scripts/test_q1_estrutura_executiva.py`
   - Script de validação criado

4. `docs/Q1_EXECUTIVE_MODEL.md`
   - Documentação criada

---

## 🔄 Fluxo de Processamento

1. **Query DW**: `get_clientes_sem_compra_ha_dias()` retorna lista de clientes
2. **Classificação**: `_classificar_clientes_por_faixa()` agrupa por faixas
3. **LLM**: Gera resposta seguindo estrutura executiva obrigatória
4. **Validação**: Verifica palavras proibidas e estrutura
5. **Confiança**: Calculada dinamicamente baseada em critérios reais
6. **Mapper**: Converte para formato AskResponse com confiança ajustada

---

**Última atualização:** 2025-11-21

