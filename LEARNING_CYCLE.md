# Sistema de Aprendizado Contínuo - DIPAM COPILOT™

## Visão Geral

Este documento descreve o sistema de aprendizado contínuo implementado para o DIPAM COPILOT™. O sistema permite que o agente aprenda com interações passadas e melhore automaticamente suas respostas ao longo do tempo.

## Arquitetura

### 1. Log de Interações

Todas as interações do agente são registradas na tabela `interacoes_agent` com os seguintes campos:

- `pergunta`: Pergunta do usuário
- `resposta`: Resposta gerada pelo agente
- `intent`: Intent detectada
- `intent_prevista`: Compatibilidade com campo específico
- `entities_json`: Entidades extraídas (JSON)
- `sql_executado`: SQL executado se teve query
- `resposta_resumida`: Resumo curto da resposta
- `sucesso`: Boolean indicando se a resposta foi baseada em dados reais (True) ou fallback (False)
- `confianca`: Nível de confiança (0-1)
- `usuario_id`, `papel`: Informações do usuário (opcional)

Cada pergunta também gera um embedding vetorial armazenado em `interacoes_embedding` para agrupamento posterior.

### 2. Catálogo de Skills Analíticas

**Skills** são templates SQL reutilizáveis que representam análises específicas. Quando o agente detecta uma pergunta compatível com uma skill, ele usa o template SQL parametrizado para executar a query.

#### Tabela `skills`:
- `nome`: Identificador único da skill
- `descricao`: Descrição do que a skill faz
- `intent_alvo`: Intent que essa skill atende
- `schema_entrada`: JSON com parâmetros esperados (ex.: `{"produto": "string", "mes_ano": "string (opcional)"}`)
- `sql_template`: Template SQL com placeholders `:parametro`
- `tipo_saida`: Tipo de saída (ex.: "tabela_clientes", "ranking_vendedores")
- `ativo`: Flag de ativação

#### Tabela `skills_sugestoes`:
- `interacao_id_orig`: ID da interação que gerou a sugestão
- `pergunta`: Pergunta original
- `intent_sugerida`: Intent sugerida
- `skill_json_proposta`: JSON completo da skill proposta
- `status`: "pending", "approved", "rejected"
- `comentario_revisor`: Comentário do revisor (opcional)

### 3. Fluxo de Uso de Skills no Agente

1. Usuário faz uma pergunta
2. Agente detecta intent e extrai entidades
3. **Agente verifica se existe skill ativa para essa intent**
4. Se existe skill:
   - Preenche template SQL com parâmetros extraídos
   - Executa query
   - Formata resultado
   - Gera resposta com LLM
5. Se não existe skill, usa fluxo normal
6. **Registra interação** (pergunta, resposta, intent, entidades, SQL, sucesso/fracasso)

### 4. Job de Aprendizado Contínuo

O script `scripts/train_skills_from_logs.py` roda periodicamente (ex.: 1x por dia via Cloud Scheduler):

1. **Lê interações mal atendidas** dos últimos N dias com:
   - `sucesso = False` OU
   - `intent = 'outros'` OU
   - `intent = 'desconhecida'`

2. **Agrupa perguntas similares** usando embeddings (similaridade de cosseno)

3. **Para cada grupo representativo**, chama LLM com:
   - Schema das tabelas
   - Exemplos de perguntas do grupo
   - Entidades extraídas
   - Instruções para gerar uma skill

4. **Valida SQL gerado** (verifica se tabelas existem)

5. **Salva sugestão** em `skills_sugestoes` com status 'pending'

6. **Aprovação manual**: Um humano revisa e aprova skills sugeridas (por enquanto via SQL)

## Como Usar

### 1. Executar Job de Aprendizado

```bash
# Analisa interações dos últimos 7 dias (padrão)
python scripts/train_skills_from_logs.py

# Analisa interações dos últimos 14 dias
python scripts/train_skills_from_logs.py --dias 14

# Ajusta threshold de similaridade (padrão: 0.85)
python scripts/train_skills_from_logs.py --threshold 0.90
```

### 2. Aprovar Skills Sugeridas

Por enquanto, a aprovação é manual via SQL:

```sql
-- Ver skills pendentes
SELECT id, pergunta, intent_sugerida, skill_json_proposta, created_at
FROM skills_sugestoes
WHERE status = 'pending'
ORDER BY created_at DESC;

-- Aprovar uma skill (ex.: ID 1)
INSERT INTO skills (
    nome, descricao, intent_alvo, schema_entrada, sql_template, tipo_saida, ativo
)
SELECT 
    skill_json_proposta->>'nome',
    skill_json_proposta->>'descricao',
    intent_sugerida,
    skill_json_proposta->'schema_entrada',
    skill_json_proposta->>'sql_template',
    skill_json_proposta->>'tipo_saida',
    true
FROM skills_sugestoes
WHERE id = 1;

-- Marcar sugestão como aprovada
UPDATE skills_sugestoes
SET status = 'approved', comentario_revisor = 'Skill aprovada manualmente'
WHERE id = 1;

-- Rejeitar uma skill
UPDATE skills_sugestoes
SET status = 'rejected', comentario_revisor = 'SQL inválido / não aplicável'
WHERE id = 2;
```

### 3. Exemplo de Skill Aprovada

Após aprovar, a skill fica disponível automaticamente. Exemplo de skill para "clientes positivados por rota para um produto":

```json
{
    "nome": "clientes_positivados_por_rota_produto",
    "descricao": "Retorna, para um produto e período, quantos clientes tiveram ao menos uma venda (clientes positivados) agrupados por rota.",
    "intent_alvo": "clientes_churn_produto",
    "schema_entrada": {
        "produto": "string",
        "mes_ano": "string (opcional)"
    },
    "sql_template": "
        SELECT
            v.rota_rca as rota,
            COUNT(DISTINCT v.cliente_id) AS clientes_positivados,
            SUM(v.valor_total_liquido) AS faturamento
        FROM vendas v
        JOIN clientes c ON c.id = v.cliente_id
        WHERE v.desc_produto ILIKE :produto
            AND v.data_venda >= :data_inicio
            AND v.data_venda < :data_fim
        GROUP BY v.rota_rca
        ORDER BY clientes_positivados DESC
        LIMIT 10;
    ",
    "tipo_saida": "tabela_clientes"
}
```

### 4. Desativar/Reativar Skills

```sql
-- Desativar uma skill
UPDATE skills SET ativo = false WHERE nome = 'clientes_positivados_por_rota_produto';

-- Reativar uma skill
UPDATE skills SET ativo = true WHERE nome = 'clientes_positivados_por_rota_produto';
```

## Detecção de Sucesso/Fracasso

O sistema detecta automaticamente se uma resposta foi bem-sucedida:

**Sucesso = True** quando:
- SQL foi executado (campo `sql_executado` não é None)
- Há dados no contexto (tabelas, listas não vazias)
- Resposta não contém mensagens de "não encontrei dados"

**Sucesso = False** quando:
- Resposta caiu em fallback ("não encontrei dados", "sem dados", etc.)
- Intent detectada foi "outros" ou "desconhecida"
- Contexto indica `tem_dados_suficientes = False`

## Próximos Passos (Futuro)

1. **UI para Aprovação**: Criar painel interno para revisar e aprovar skills sugeridas
2. **Feedback do Usuário**: Permitir que usuários marquem respostas como úteis/não úteis
3. **Fine-tuning de Intent/NER**: Usar perguntas + intents corrigidas para melhorar modelo
4. **Atualização de Sinônimos**: Expandir dicionários automaticamente (ex.: "Nissin miojo" → produto=NISSIN)
5. **Validação Automática de SQL**: Executar SQL gerado em ambiente sandbox antes de aprovar

## Estrutura de Arquivos

```
src/
├── agent/
│   ├── skills.py                    # Funções para buscar e usar skills
│   ├── interaction_logger.py        # Registro de interações e embeddings
│   └── service.py                   # Agente principal (modificado para usar skills)
├── dw/
│   └── models.py                    # Modelos: Skill, SkillSugestao, InteracaoAgent (ajustado)
scripts/
└── train_skills_from_logs.py        # Job de aprendizado contínuo
```

## Notas Importantes

- O logging de interações é **automático** e acontece em cada chamada ao agente
- O job de aprendizado deve ser executado **periodicamente** (ex.: 1x por dia)
- Skills sugeridas precisam ser **aprovadas manualmente** antes de serem ativadas
- O sistema não altera o **contrato das rotas da API** existentes
- Todas as mudanças são **internas** ao agente



