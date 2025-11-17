"""
Instrutor Analítico - DIPAM COPILOT™.

Este módulo é responsável por orientar o raciocínio interno da IA principal.

IMPORTANTE:
- NÃO fala com o usuário final
- NÃO produz a resposta final
- Ajuda a IA principal a:
  * Interpretar corretamente o IntentSpec
  * Entender o que significam as colunas dos dados
  * Identificar padrões relevantes
  * Priorizar quais insights são realmente importantes

FLUXO:
1. Recebe: pergunta original, IntentSpec, dados do DW
2. Gera "PLANO DE RACIOCÍNIO INTERNO" estruturado
3. IA principal usa esse plano para montar resumo executivo e insights
"""

import json
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from src.agent.intent_spec import IntentSpec
from src.llm_integration_intent import call_openai_llm

logger = logging.getLogger(__name__)


def _get_system_prompt_instrutor() -> str:
    """Retorna system prompt para o instrutor analítico."""
    return """Você é o MODELO INSTRUTOR do DIPAM COPILOT™, responsável por orientar o raciocínio interno da IA principal.

SUA FUNÇÃO:
- Você NÃO fala com o usuário final
- Você NÃO produz a resposta final
- Você ajuda a IA principal a:
  * Interpretar corretamente o IntentSpec
  * Entender o que significam as colunas dos dados
  * Identificar padrões relevantes
  * Priorizar quais insights são realmente importantes

CONTEXTO:
- Você trabalha com dados comerciais da DIPAM Gaúcha
- Os dados vêm do data warehouse DIPAM (camada DW)
- Período disponível: nov/2024 a out/2025 (ou conforme enviado)
- BigQuery NÃO está implementado (apenas roadmap)

REGRAS FUNDAMENTAIS:
1. Use APENAS os dados fornecidos, não invente números
2. Foque sempre no que é relevante para diretoria, supervisor ou RCA
3. Simplifique: priorize 3-5 pontos fortes em vez de listas enormes
4. Seja objetivo e direto
5. Identifique padrões claros, não hipóteses vagas

SEU PAPEL:
Você é o consultor analítico interno, não o apresentador.
Você orienta a análise, não apresenta os resultados."""


def gerar_plano_raciocinio_interno(
    pergunta: str,
    intent_spec: IntentSpec,
    dados_dw: Dict[str, Any],
    papel: Optional[str] = None
) -> Dict[str, Any]:
    """
    Gera plano de raciocínio interno para orientar a IA principal.
    
    Args:
        pergunta: Pergunta original do usuário
        intent_spec: IntentSpec gerado pela IA
        dados_dw: Dados brutos retornados pelo orquestrador DW
        papel: Papel do usuário (diretor, supervisor, vendedor)
        
    Returns:
        dict com estrutura:
        {
            "foco_analitico": List[str],
            "achados_relevantes": List[str],
            "prioridades_de_comunicacao": List[str],
            "alertas": List[str]
        }
    """
    system_prompt = _get_system_prompt_instrutor()
    
    # Prepara dados para o prompt
    dados_str = json.dumps(dados_dw, ensure_ascii=False, indent=2, default=str)
    
    # Determina contexto do papel
    contexto_papel = "Diretor Comercial"
    if papel:
        papel_lower = papel.lower()
        if "supervisor" in papel_lower:
            contexto_papel = "Supervisor"
        elif "vendedor" in papel_lower or "rca" in papel_lower:
            contexto_papel = "Vendedor/RCA"
    
    prompt = f"""Você recebeu:
1. Pergunta original do usuário
2. IntentSpec (especificação de intenção)
3. Dados brutos retornados do data warehouse DIPAM

Sua tarefa: Gerar um PLANO DE RACIOCÍNIO INTERNO estruturado para orientar a IA principal.

Pergunta original: {pergunta}

IntentSpec:
{json.dumps(intent_spec.to_dict(), ensure_ascii=False, indent=2)}

Dados brutos do DW:
{dados_str}

Contexto do usuário: {contexto_papel}

ANÁLISE DOS DADOS:

1. FOCO ANALÍTICO:
   - O que é mais importante analisar primeiro?
   - Quais comparações são críticas?
   - Quais cortes (por vendedor/rota/cliente) são chave?
   
   Exemplos:
   - "Comparar atingimento médio vs meta total para identificar gap principal"
   - "Analisar top 5 vendedores com maior gap negativo"
   - "Verificar concentração de risco em rotas específicas"

2. ACHADOS RELEVANTES:
   - Padrões claros de alta ou queda
   - Rotas, supervisores ou produtos fora da curva
   - Concentração de risco ou oportunidade
   
   Exemplos:
   - "ROTA 75 VD apresenta gap de R$ 15.380,29, 23% abaixo da meta"
   - "3 supervisores concentram 60% do gap total"
   - "Cliente X teve queda de 200% vs média dos últimos 3 meses"

3. PRIORIDADES DE COMUNICAÇÃO:
   - O que precisa ir para o resumo executivo?
   - Quais dados merecem entrar na tabela?
   - Quais recomendações são mais acionáveis?
   
   Exemplos:
   - "Destaque no resumo: gap total de R$ 1.4M e 5 vendedores em risco crítico"
   - "Tabela deve mostrar top 10 vendedores com maior gap"
   - "Recomendação prioritária: coaching imediato para ROTA 75 VD"

4. ALERTAS:
   - Qualquer ponto que pode ser sensível para diretoria
   - Situações críticas como perda de clientes ou metas muito abaixo
   
   Exemplos:
   - "ALERTA: 3 clientes críticos com churn_score > 80% na mesma rota"
   - "ALERTA: Meta não batida em 8 dos 12 meses do período"
   - "ALERTA: Supervisor X tem 5 vendedores abaixo de 90% de atingimento"

REGRAS:
- Use APENAS os dados fornecidos, não invente números
- Foque no que é relevante para {contexto_papel}
- Simplifique: priorize 3-5 pontos fortes em vez de listas enormes
- Se não houver dados suficientes, indique claramente

Retorne APENAS um JSON válido com a seguinte estrutura:

{{
  "foco_analitico": [
    "O que é mais importante analisar primeiro",
    "Quais comparações são críticas",
    "Quais cortes (por vendedor/rota/cliente) são chave"
  ],
  "achados_relevantes": [
    "Padrão 1: descrição específica com números reais",
    "Padrão 2: descrição específica com números reais",
    "Padrão 3: descrição específica com números reais"
  ],
  "prioridades_de_comunicacao": [
    "O que precisa ir para o resumo executivo",
    "Quais dados merecem entrar na tabela",
    "Quais recomendações são mais acionáveis"
  ],
  "alertas": [
    "Alerta 1: situação crítica específica",
    "Alerta 2: situação crítica específica"
  ]
}}

Retorne APENAS o JSON, sem markdown, sem texto adicional antes ou depois."""

    try:
        resposta_llm = call_openai_llm(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.3,  # Baixa temperatura para análise mais precisa
            max_tokens=1500
        )
        
        # Limpa a resposta
        resposta_limpa = resposta_llm.strip()
        if resposta_limpa.startswith("```json"):
            resposta_limpa = resposta_limpa[7:]
        if resposta_limpa.startswith("```"):
            resposta_limpa = resposta_limpa[3:]
        if resposta_limpa.endswith("```"):
            resposta_limpa = resposta_limpa[:-3]
        resposta_limpa = resposta_limpa.strip()
        
        # Parseia JSON
        plano = json.loads(resposta_limpa)
        
        # Valida estrutura
        campos_obrigatorios = ["foco_analitico", "achados_relevantes", "prioridades_de_comunicacao", "alertas"]
        for campo in campos_obrigatorios:
            if campo not in plano:
                plano[campo] = []
            elif not isinstance(plano[campo], list):
                plano[campo] = []
        
        logger.info(
            f"[instrutor_analitico] Plano gerado: "
            f"foco={len(plano['foco_analitico'])} itens, "
            f"achados={len(plano['achados_relevantes'])} itens, "
            f"prioridades={len(plano['prioridades_de_comunicacao'])} itens, "
            f"alertas={len(plano['alertas'])} itens"
        )
        
        return plano
        
    except json.JSONDecodeError as e:
        logger.error(f"[instrutor_analitico] Erro ao parsear JSON: {e}")
        logger.error(f"[instrutor_analitico] Resposta LLM: {resposta_llm[:500]}")
        # Fallback: retorna estrutura básica
        return {
            "foco_analitico": [
                "Analisar os dados fornecidos para identificar padrões principais",
                "Comparar valores reais vs esperados (meta vs realizado)",
                "Identificar concentrações de risco ou oportunidade"
            ],
            "achados_relevantes": [],
            "prioridades_de_comunicacao": [
                "Destacar no resumo executivo os principais achados",
                "Incluir na tabela os dados mais relevantes",
                "Priorizar recomendações acionáveis"
            ],
            "alertas": []
        }
    except Exception as e:
        logger.error(f"[instrutor_analitico] Erro ao gerar plano: {e}", exc_info=True)
        # Fallback: retorna estrutura básica
        return {
            "foco_analitico": [
                "Analisar os dados fornecidos para identificar padrões principais"
            ],
            "achados_relevantes": [],
            "prioridades_de_comunicacao": [
                "Destacar no resumo executivo os principais achados"
            ],
            "alertas": []
        }

