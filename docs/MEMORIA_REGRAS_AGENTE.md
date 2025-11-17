# Memória de Regras do Agente DIPAM COPILOT™

## Visão Geral

A camada de memória de regras permite que o agente "aprenda" com feedbacks do Diretor e da equipe, sem modificar os pesos do modelo LLM.

### Arquitetura de Aprendizado

```
LLM = cérebro estável (não mexe nos pesos toda hora)
DW (SQLite/Postgres) = verdade absoluta dos dados
Camada de REGRAS & PREFERÊNCIAS = aprendizado
```

O aprendizado vem de:
- **Feedback explícito do Diretor** (ex.: "não use pasta verde nesse tipo de análise")
- **Decisões registradas no banco** como regras permanentes ou condicionais
- **Backend aplicando essas regras** toda vez antes de chamar o LLM

**Importante:** O modelo não "se lembra magicamente", quem lembra é o banco de regras; o agent só aplica o que o backend manda.

---

## Tabela `agent_feedback_rules`

### Estrutura

```sql
CREATE TABLE agent_feedback_rules (
    id INTEGER PRIMARY KEY,
    owner_role TEXT NOT NULL,         -- 'diretor', 'supervisor', etc.
    owner_id TEXT,                    -- opcional: id do usuário
    rule_scope TEXT NOT NULL,         -- 'meta', 'vendas', 'clientes_criticos', etc.
    condition_json TEXT NOT NULL,     -- JSON com condição, ex.: {"carteira":"pasta_verde"}
    action_json TEXT NOT NULL,        -- JSON com ação, ex.: {"excluir_dos_filtros":true}
    description TEXT,                 -- texto humano: "Ignorar pasta verde em análises de meta"
    priority INTEGER DEFAULT 10,      -- para resolver conflitos (menor = maior prioridade)
    active INTEGER DEFAULT 1,         -- 1=ativa, 0=desativada
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

### Exemplo de Regra: Excluir Pasta Verde

**Feedback do Diretor:**
> "Você deve excluir os dados da pasta verde para esse tipo de análise."

**Registro da regra:**

```json
{
  "owner_role": "diretor",
  "rule_scope": "meta",
  "condition_json": {
    "carteira": "pasta_verde"
  },
  "action_json": {
    "excluir_dos_filtros": true,
    "excluir_carteira": ["pasta_verde"]
  },
  "description": "Excluir pasta verde de todas as análises de meta, exceto se o diretor pedir explicitamente o contrário."
}
```

---

## Fluxo de Aplicação de Regras

### 1. Diretor faz a pergunta
> "Quais são as metas de agosto de 2025?"

### 2. Backend gera IntentSpec
```json
{
  "tipo": "meta",
  "periodo_inicio": "2025-08-01",
  "periodo_fim": "2025-08-31",
  "dimensao_principal": "mes"
}
```

### 3. Backend carrega regras ativas
- `owner_role = 'diretor'`
- `rule_scope = 'meta'`
- `active = 1`

### 4. Backend aplica regras no builder de consulta
- Adiciona `WHERE carteira <> 'PASTA VERDE'` (ou equivalente)
- Atualiza filtros do IntentSpec

### 5. Consulta DW com filtros ajustados
- Dados retornados já excluem pasta verde

### 6. LLM recebe dados + contexto de regras aplicadas
```json
{
  "dados": [...],
  "regras_aplicadas": {
    "excluir_carteira": ["pasta_verde"]
  }
}
```

### 7. LLM gera resposta respeitando as regras
- Não tenta "corrigir" ou ignorar as preferências
- Só contraria se houver instrução explícita na pergunta

---

## Exceções Explícitas

Se o Diretor disser explicitamente algo como:
- "incluindo pasta verde"
- "dessa vez considere também a pasta verde"
- "ignore a regra de excluir a pasta verde"

Então:
- Backend detecta override explícito
- Marca `override_regras=True` no contexto
- Não aplica a regra de exclusão para essa requisição específica
- LLM menciona a exceção na resposta

---

## Como Usar

### 1. Criar a tabela

```bash
python -m scripts.criar_tabela_agent_feedback_rules
```

### 2. Criar regra de exemplo (pasta verde)

```bash
python -m scripts.exemplo_regra_pasta_verde
```

### 3. Registrar nova regra via código

```python
from src.dw.connection import get_db_session
from src.agent.rules import salvar_regra_feedback

with get_db_session() as session:
    regra = salvar_regra_feedback(
        session=session,
        owner_role="diretor",
        rule_scope="meta",
        condition_json={"carteira": "pasta_verde"},
        action_json={"excluir_dos_filtros": True, "excluir_carteira": ["pasta_verde"]},
        description="Excluir pasta verde de análises de meta"
    )
```

### 4. Listar regras ativas

```python
from src.dw.connection import get_db_session
from src.agent.rules import listar_regras_ativas

with get_db_session() as session:
    regras = listar_regras_ativas(session, "diretor", "meta")
    for regra in regras:
        print(f"{regra.id}: {regra.description}")
```

---

## Integração Automática

As regras são aplicadas automaticamente no fluxo:

1. **Handler** (`handler_dw_refatorado.py`):
   - Detecta override explícito na pergunta
   - Passa contexto do usuário para o orquestrador

2. **Orquestrador** (`orquestrador_dw.py`):
   - Carrega regras ativas
   - Aplica regras aos filtros do IntentSpec
   - Inclui `regras_aplicadas` no payload

3. **LLM Integration** (`llm_integration_intent.py`):
   - Recebe `regras_aplicadas` no prompt
   - System prompt instrui a respeitar as regras
   - Só contraria se houver instrução explícita

---

## System Prompt Atualizado

O system prompt agora inclui:

```
-----------------------------------------------------------------------
REGRAS E PREFERÊNCIAS DO DIRETOR / USUÁRIOS
-----------------------------------------------------------------------
O backend pode lhe enviar, junto com os dados, um campo de contexto com 
REGRAS e PREFERÊNCIAS já aplicadas na consulta, por exemplo:

- "excluir_carteira": ["pasta_verde"]
- "foco_em_clientes_criticos": true
- "considerar_apenas_rotas": ["ROTA 75 VD", "ROTA 72 VD"]

Essas regras representam feedbacks e decisões anteriores do Diretor e da equipe.

SUAS OBRIGAÇÕES:
- Tratar esses filtros como VERDADE estabelecida para aquela resposta.
- Não tentar "corrigir" ou ignorar essas preferências.
- Só contrariar uma regra se o usuário trouxer uma instrução explícita na pergunta atual.
```

---

## Testes

Execute os testes:

```bash
# Todos os testes de regras
pytest tests/test_agent_rules.py -v

# Teste específico
pytest tests/test_agent_rules.py::test_aplicar_regras_com_pasta_verde -v
```

---

## Próximos Passos

1. **Captura automática de feedback:**
   - Endpoint para registrar feedback do Diretor
   - Parser de feedback em linguagem natural
   - Conversão automática em regras

2. **Interface de gerenciamento:**
   - Listar regras ativas
   - Editar/desativar regras
   - Visualizar histórico de aplicação

3. **Regras condicionais:**
   - Regras que se aplicam apenas em certas condições
   - Regras temporárias (com data de expiração)
   - Regras por região/supervisor específico

---

## Arquivos Criados

- `src/dw/models_agent.py` - Modelo SQLAlchemy da tabela
- `src/agent/rules.py` - Módulo de gerenciamento de regras
- `scripts/criar_tabela_agent_feedback_rules.py` - Script para criar tabela
- `scripts/exemplo_regra_pasta_verde.py` - Exemplo de criação de regra
- `tests/test_agent_rules.py` - Testes da camada de regras

## Arquivos Modificados

- `src/agent/orquestrador_dw.py` - Integração de aplicação de regras
- `src/agent/handler_dw_refatorado.py` - Detecção de override e passagem de contexto
- `src/llm_integration_intent.py` - System prompt atualizado e recebimento de regras
- `src/dw/connection.py` - Import de models_agent para criação de tabelas

