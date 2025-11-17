# Pós-processador de Respostas - DIPAM COPILOT™

## Visão Geral

O módulo `src/agent/post_processor.py` refatora o pós-processamento de respostas usando modelos narrativos claros, alinhados ao TEMPLATE DE RESPOSTA NEGATIVA e POSITIVA.

## Função Principal

### `processar_resposta(intent_spec, dados_dw, causas_detector, behavior_rules_aplicadas) -> Dict[str, Any]`

Processa resposta estruturada baseado nos dados do DW e causas detectadas.

**Parâmetros:**
- `intent_spec`: IntentSpec como dict
- `dados_dw`: Dados retornados do DW
- `causas_detector`: Resultado de `detectar_causas_para_mes` (opcional)
- `behavior_rules_aplicadas`: Lista de regras comportamentais aplicadas (opcional)

**Retorno:**
Dict estruturado com seções:
- `resumo_executivo`
- `diagnostico_causas` (template negativo)
- `checklist_problemas` (template negativo)
- `plano_acao_7_dias` (template negativo)
- `plano_acao_30_dias` (template negativo)
- `tendencias_previsao` (template negativo)
- `oportunidades_crescimento` (template positivo)
- `detalhes_tecnicos`

**Exemplo:**
```python
from src.agent.post_processor import processar_resposta

resposta = processar_resposta(
    intent_spec=intent_spec,
    dados_dw=dados_dw,
    causas_detector=causas_detector
)
print(resposta["resumo_executivo"])
print(resposta["checklist_problemas"])
```

## Templates

### Template Negativo

Ativado quando `atingimento_medio < 100.0` ou `gap_total < 0`.

**Estrutura:**
```python
{
    "resumo_executivo": str,  # 3 linhas, números chave, gap e impacto
    "diagnostico_causas": {
        "vendedores_pior_desempenho": List[Dict],
        "rotas_maior_gap": List[Dict],
        "clientes_reduziram_compra": List[Dict],
        "skus_queda_expressiva": List[Dict],
        "outras_causas": List[Dict]
    },
    "checklist_problemas": List[Dict],  # Mínimo 5 itens
    "plano_acao_7_dias": List[Dict],
    "plano_acao_30_dias": List[Dict],
    "tendencias_previsao": Dict,
    "detalhes_tecnicos": Dict
}
```

### Template Positivo

Ativado quando `atingimento >= 100%`.

**Estrutura:**
```python
{
    "resumo_executivo": str,  # Destaque de superação
    "oportunidades_crescimento": {
        "vendedores_destaque": List[Dict],
        "rotas_superaram_meta": List[Dict],
        "clientes_expansao": List[Dict],
        "riscos_concentracao": List[Dict]
    },
    "detalhes_tecnicos": Dict
}
```

## Funções Auxiliares

### `_gerar_resumo_executivo_negativo(gap_total, atingimento_medio, resumo_causas) -> str`

Gera resumo executivo para template negativo.

### `_gerar_resumo_executivo_positivo(meta_total, realizado_total, atingimento_medio) -> str`

Gera resumo executivo para template positivo.

### `_gerar_checklist_problemas(causas, gap_total) -> List[Dict]`

Gera checklist de problemas baseado nas causas.

**Estrutura de cada item:**
```python
{
    "problema": str,
    "impacto": str,  # Ex.: "R$ X.XXX,XX"
    "causa_provavel": str,
    "urgencia": "alta" | "media" | "baixa"
}
```

### `_gerar_plano_acao_7_dias(causas) -> List[Dict]`

Gera plano de ação imediata (7 dias).

**Estrutura de cada ação:**
```python
{
    "acao": str,
    "responsavel": str,
    "prazo": str,  # Ex.: "48 horas"
    "como_medir": str
}
```

### `_gerar_plano_acao_30_dias(causas) -> List[Dict]`

Gera plano de ação de mitigação (30 dias).

**Estrutura de cada ação:**
```python
{
    "acao": str,
    "objetivo": str,
    "responsavel": str,
    "prazo": str,  # Ex.: "30 dias"
    "metrica_sucesso": str
}
```

### `_gerar_tendencias_previsao(dados_dw, gap_total, atingimento_medio) -> Dict`

Gera tendências e previsão baseado nos dados.

**Estrutura:**
```python
{
    "tendencias_identificadas": List[str],
    "probabilidade_recuperacao": float,  # Percentual
    "cenario_atual": Dict,
    "cenario_otimista": Dict,
    "cenario_pessimista": Dict
}
```

## Integração

O `post_processor` é chamado automaticamente pelo `handler_dw_refatorado.py` no PASSO 3, antes da geração da resposta executiva pelo LLM.

A resposta estruturada é então passada para o LLM, que a usa como base para gerar o texto final em linguagem natural.

## Arquitetura

- **Não inventa dados**: Apenas estrutura o que vem do DW
- **Templates claros**: Separação clara entre negativo e positivo
- **Estruturação completa**: Todas as seções obrigatórias são preenchidas
- **Compatibilidade**: Funciona com ou sem `causas_detector`

## Notas Importantes

1. **Checklist mínimo**: O checklist sempre tem pelo menos 5 itens
2. **Planos de ação**: Baseados nas causas detectadas
3. **Tendências**: Usa dados atuais para projetar cenários
4. **Detalhes técnicos**: Sempre inclui IntentSpec, filtros e regras aplicadas

