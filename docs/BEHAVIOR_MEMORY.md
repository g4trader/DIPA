# Behavior Memory - DIPAM COPILOT™

## Visão Geral

O módulo `src/agent/behavior_memory.py` gerencia a memória comportamental do agente, armazenando instruções permanentes do Diretor (ex.: "ignorar pasta verde") em arquivo JSON.

## Arquivo de Armazenamento

As regras são armazenadas em `data/behavior_rules.json` com a seguinte estrutura:

```json
{
  "regras_por_tipo_analise": {
    "analise_meta_mensal": {
      "excluir_carteira": ["pasta_verde"],
      "comentario": "Regra definida pelo Diretor em 2025-11-17."
    },
    "analise_clientes_queda": {
      "priorizar_rotas": ["rota_22", "rota_75"]
    }
  }
}
```

## Funções Disponíveis

### 1. `carregar_regras() -> Dict[str, Any]`

Carrega regras comportamentais do arquivo JSON.

**Retorno:**
- Dict com estrutura de regras

**Exemplo:**
```python
from src.agent.behavior_memory import carregar_regras

regras = carregar_regras()
print(regras["regras_por_tipo_analise"]["analise_meta_mensal"])
```

### 2. `salvar_regras(regras: Dict[str, Any]) -> None`

Salva regras comportamentais no arquivo JSON.

**Parâmetros:**
- `regras`: Dict com estrutura de regras

**Exemplo:**
```python
from src.agent.behavior_memory import salvar_regras

regras = {
    "regras_por_tipo_analise": {
        "analise_meta_mensal": {
            "excluir_carteira": ["pasta_verde"]
        }
    }
}
salvar_regras(regras)
```

### 3. `registrar_feedback(tipo_analise, tipo_regra, valor, ...) -> None`

Registra feedback do Diretor como regra comportamental permanente.

**Parâmetros:**
- `tipo_analise`: Tipo de análise (ex.: "analise_meta_mensal", "analise_clientes_queda")
- `tipo_regra`: Tipo de regra (ex.: "excluir_carteira", "priorizar_rota")
- `valor`: Valor da regra (ex.: "pasta_verde", ["rota_22", "rota_75"])
- `comentario`: Comentário opcional explicando a regra
- `payload_opcional`: Dados adicionais opcionais

**Exemplo:**
```python
from src.agent.behavior_memory import registrar_feedback

registrar_feedback(
    tipo_analise="analise_meta_mensal",
    tipo_regra="excluir_carteira",
    valor="pasta_verde",
    comentario="Regra definida pelo Diretor em 2025-11-17"
)
```

### 4. `aplicar_regras_ao_intent(intent_spec: Dict[str, Any]) -> Dict[str, Any]`

Aplica regras comportamentais ao IntentSpec, ajustando filtros conforme necessário.

**Parâmetros:**
- `intent_spec`: IntentSpec como dict (ou objeto com .to_dict())

**Retorno:**
- IntentSpec ajustado com filtros aplicados

**Exemplo:**
```python
from src.agent.behavior_memory import aplicar_regras_ao_intent

intent = {"tipo": "meta", "filtros": {}}
intent_ajustado = aplicar_regras_ao_intent(intent)
print(intent_ajustado["filtros"])  # Pode conter "excluir_carteiras": ["pasta_verde"]
```

## Tipos de Regras Suportadas

### `excluir_carteira`
Exclui carteiras específicas das análises.

**Exemplo:**
```python
registrar_feedback(
    tipo_analise="analise_meta_mensal",
    tipo_regra="excluir_carteira",
    valor="pasta_verde"
)
```

### `excluir_rotas`
Exclui rotas específicas das análises.

**Exemplo:**
```python
registrar_feedback(
    tipo_analise="analise_meta_mensal",
    tipo_regra="excluir_rotas",
    valor=["rota_22", "rota_75"]
)
```

### `priorizar_rotas`
Prioriza análise de rotas específicas.

**Exemplo:**
```python
registrar_feedback(
    tipo_analise="analise_clientes_queda",
    tipo_regra="priorizar_rotas",
    valor=["rota_22", "rota_75"]
)
```

## Mapeamento de Tipos de Análise

O sistema mapeia automaticamente tipos de intent para tipos de análise:

- `"meta"` → `"analise_meta_mensal"`
- `"analise_meta_detalhada"` → `"analise_meta_mensal"`
- `"clientes_criticos"` → `"analise_clientes_queda"`
- `"churn"` → `"analise_clientes_queda"`
- `"vendas"` → `"analise_vendas"`
- `"ranking_vendedores"` → `"analise_meta_mensal"`

## Arquitetura

- **Não toca dados do DW**: Behavior memory apenas ajusta filtros do IntentSpec
- **Aplicação automática**: Regras são aplicadas automaticamente antes da consulta DW
- **Logs**: Todas as operações são logadas para auditoria
- **Persistência**: Regras são persistidas em JSON para sobreviver a reinicializações

## Integração

O `behavior_memory` é chamado automaticamente pelo `orquestrador_dw.py` no PASSO 1.5, antes da validação do IntentSpec.

## Notas Importantes

1. **Criação automática**: O arquivo `behavior_rules.json` é criado automaticamente se não existir
2. **Sem duplicatas**: O sistema evita duplicatas ao adicionar valores a listas
3. **Compatibilidade**: Aceita tanto objetos IntentSpec quanto dicts
4. **Privacidade**: Regras não expõem dados brutos, apenas ajustam filtros

