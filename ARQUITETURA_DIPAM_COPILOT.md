# Arquitetura do DIPAM COPILOT™

## Resumo das Implementações

Este documento descreve as melhorias arquiteturais implementadas para transformar o DIPAM COPILOT™ em um agente de IA corporativo de alto nível.

## FASE 1 - Organização da Arquitetura ✅

### Schemas Pydantic (`src/agent/schemas.py`)

Criado arquivo com modelos Pydantic para garantir tipagem forte e contratos claros entre camadas:

- `InsightMetasUltimosMeses`: Resumo de metas dos últimos N meses
- `InsightClientesChurnProduto`: Clientes que abandonaram um produto
- `InsightClientesOportunidades`: Oportunidades de crescimento
- `InsightClientesRisco`: Clientes em risco de churn
- `InsightProdutosBaixaVenda`: Produtos com baixo desempenho
- `InsightDesempenhoSupervisores`: Comparação de supervisores
- `InsightOportunidadesDiretoria`: Resumo executivo
- `InsightBundle`: Bundle unificado para orquestração

### Módulos de Análise Organizados

**`src/analysis/clientes.py`**:
- `clientes_positivados_sem_compra_produto()`: Clientes que pararam de comprar um produto
- `clientes_risco_churn()`: **NOVO** - Radar de risco de clientes
- `clientes_oportunidades_crescimento()`: **NOVO** - Mapa de oportunidades

**`src/analysis/supervisores.py`**: **NOVO**
- `desempenho_supervisores()`: Comparação de supervisores/equipes

**`src/analysis/metas.py`**: Mantido e melhorado
- `metas_resumo_ultimos_meses()`: Análise de metas dos últimos N meses

**`src/analysis/produtos.py`**: Mantido
- `get_produtos_menos_vendidos()`: Produtos com baixa venda
- `get_top_produtos_para_recuperar()`: Produtos para recuperar

## FASE 2 - Intents Expandidas ✅

### Novas Intents Adicionadas (`src/agent/intent.py`)

- `CLIENTES_OPORTUNIDADES`: Oportunidades de crescimento com clientes
- `DESEMPENHO_SUPERVISORES`: Comparação de desempenho de supervisores
- `OPORTUNIDADES_DIRETORIA`: Resumo executivo de oportunidades

### Padrões de Detecção Expandidos

Novos padrões regex adicionados para cada intent, garantindo melhor reconhecimento de perguntas como:
- "onde posso crescer mais"
- "qual supervisor está mais distante da meta"
- "maiores oportunidades de recuperação"

## FASE 4 - LLM: Prompts Profissionais ✅

### Sistema de Prompts (`src/llm_integration.py`)

**`_get_system_prompt_dipam_copilot()`**: Prompt profissional padrão com:
- Persona definida (DIPAM COPILOT™)
- Regras fundamentais (nunca inventar dados)
- Estrutura de resposta padronizada
- Adaptação por papel (diretor, supervisor, vendedor)

**`gerar_resposta_analytics()`**: Nova função principal para respostas estruturadas:
- Valida dados suficientes antes de processar
- Usa `InsightBundle` padronizado
- Tratamento de erros robusto
- Fallbacks baseados em pontos-chave

## FASE 6 - Capacidades "Wow" ✅

### 1. Radar de Risco de Clientes

**Função**: `clientes_risco_churn()` em `src/analysis/clientes.py`

**Capacidades**:
- Detecta clientes com redução > 30% no faturamento
- Calcula score de risco (0-100) baseado em múltiplos critérios
- Identifica perda de frequência de compras
- Filtra por supervisor/rota

**Uso**:
```python
clientes_risco = clientes_risco_churn(
    session,
    periodo_meses=3,
    limite=50,
    supervisor="SUPERVISÃO SINOS"
)
```

### 2. Mapa de Oportunidades por Produto

**Função**: `clientes_oportunidades_crescimento()` em `src/analysis/clientes.py`

**Capacidades**:
- Identifica clientes que reduziram volume
- Calcula potencial de recuperação (R$)
- Score de oportunidade (0-100)
- Pode filtrar por produto específico

**Uso**:
```python
oportunidades = clientes_oportunidades_crescimento(
    session,
    periodo_dias=90,
    produto="Nissin",
    limite=50
)
```

### 3. Desempenho de Supervisores e Equipes

**Função**: `desempenho_supervisores()` em `src/analysis/supervisores.py`

**Capacidades**:
- Compara supervisores em múltiplas métricas:
  - Atingimento de metas
  - Cobertura de clientes ativos
  - Concentração de faturamento (dependência de poucos clientes)
  - Score de desempenho composto (0-100)
- Calcula métricas por equipe

**Uso**:
```python
desempenho = desempenho_supervisores(
    session,
    periodo_meses=6,
    mes_base="2025-11"
)
```

## Garantias de Dados Reais

### Todas as funções de análise:

1. **Agregações no banco**: Usam SQLAlchemy com GROUP BY, SUM, MAX - nunca carregam milhões de linhas em memória
2. **Validação de dados**: Retornam listas vazias se não houver dados, não inventam valores
3. **Mensagens explícitas**: Se não houver dados suficientes, o agente informa claramente

### Prompts LLM:

1. **Regra fundamental**: "Use APENAS os dados fornecidos no contexto"
2. **Sem invenção**: "NÃO invente valores, períodos, produtos ou quantidades"
3. **Explicação clara**: "Se um dado não estiver presente, diga explicitamente"

## Próximos Passos (Pendentes)

### FASE 3 - Refatorar service.py para usar InsightBundle

O `service.py` ainda precisa ser refatorado para usar `InsightBundle` de forma consistente em todos os handlers de intent. Atualmente, alguns handlers já usam estruturas similares, mas precisam ser padronizados.

**Exemplo de padrão desejado**:
```python
# Em process_question():
insight_bundle = InsightBundle(
    intent=intent.value,
    usuario_id=usuario_id,
    papel=papel,
    dados_brutos={...},
    scores_ml={...},
    pontos_chave=[...],
    tem_dados_suficientes=True
)
resposta = gerar_resposta_analytics(intent.value, insight_bundle, pergunta, papel)
```

### FASE 5 - Eliminar Mocks e Fallbacks Genéricos

Buscar e remover todos os casos onde:
- Textos genéricos são retornados sem dados
- Valores são inventados
- Fallbacks genéricos são usados sem verificar dados reais

### FASE 7 - Testes

Criar testes de integração em `tests/` para:
- Validar funções de análise retornam dados consistentes
- Garantir `InsightBundle` tem sempre as chaves esperadas
- Teste end-to-end para perguntas típicas

## Exemplos de Perguntas Suportadas

### 2 Focadas em Metas/Diretor:
1. "preciso saber meta e realizado de vendas dos últimos 6 meses, mostre-me separado por mês"
2. "como está o atingimento das metas por supervisor nos últimos 3 meses?"

### 2 Focadas em Clientes/Produtos:
1. "quais clientes positivados no produto nissin e que não compram há mais de 60 dias"
2. "quais clientes têm potencial desperdiçado em massas? onde tenho gap de share?"

### 1 Focada em Supervisores/Equipe:
1. "qual supervisor está mais distante da meta? quem está puxando o resultado pra baixo?"

## Estrutura de Arquivos Criados/Modificados

```
src/
├── agent/
│   ├── schemas.py           # ✅ NOVO - Schemas Pydantic
│   ├── intent.py            # ✅ MODIFICADO - Novas intents
│   └── service.py           # ⏳ PENDENTE - Refatorar para InsightBundle
├── analysis/
│   ├── __init__.py          # ✅ MODIFICADO - Novos exports
│   ├── clientes.py          # ✅ MODIFICADO - Novas funções
│   ├── supervisores.py      # ✅ NOVO
│   ├── metas.py             # ✅ MANTIDO (já bom)
│   └── produtos.py          # ✅ MANTIDO (já bom)
└── llm_integration.py       # ✅ MODIFICADO - Novos prompts e funções
```

## Como Garantir Respostas Baseadas em Dados Reais

1. **Nunca use `mock` ou dados inventados** - sempre consulte o banco
2. **Valide dados suficientes** - se a query retornar vazio, informe claramente
3. **Use agregações no banco** - SQLAlchemy GROUP BY/SUM, nunca pandas para milhões de linhas
4. **Prompt LLM restritivo** - instruções claras para não inventar dados
5. **Fallbacks informativos** - se LLM falhar, retorne dados numéricos simples, não texto genérico

## Notas de Implementação

- Todas as funções de análise são **puramente analíticas** (sem LLM)
- Separação clara: análise → orquestração → LLM
- Tipagem forte com Pydantic garante contratos entre camadas
- Otimização de contexto para limitar custos LLM




