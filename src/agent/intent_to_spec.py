"""
Conversor de Intenção para IntentSpec - DIPAM COPILOT™.

Este módulo converte a intenção detectada (IntentType) e entidades
extraídas em uma IntentSpec estruturada para execução na camada DW.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from src.agent.intent import IntentType
from src.agent.intent_spec import (
    IntentSpec,
    criar_intent_spec_meta,
    criar_intent_spec_clientes_criticos,
    criar_intent_spec_vendas,
    criar_intent_spec_ranking_vendedores
)

logger = logging.getLogger(__name__)


def calcular_periodo_ultimos_meses(n_meses: int) -> tuple[Optional[str], Optional[str]]:
    """
    Calcula período inicial e final para "últimos N meses".
    
    Args:
        n_meses: Número de meses (ex.: 6 para "últimos 6 meses")
        
    Returns:
        tuple: (periodo_inicio, periodo_fim) no formato "YYYY-MM"
    """
    hoje = datetime.now()
    # Calcula mês inicial (N meses atrás)
    mes_inicio = hoje - timedelta(days=30 * n_meses)
    periodo_inicio = mes_inicio.strftime("%Y-%m")
    periodo_fim = hoje.strftime("%Y-%m")
    
    return periodo_inicio, periodo_fim


def intent_to_spec(
    intent: IntentType,
    entities: Dict[str, Any]
) -> IntentSpec:
    """
    Converte intenção detectada e entidades em IntentSpec.
    
    Args:
        intent: Tipo de intenção detectada
        entities: Entidades extraídas da pergunta
        
    Returns:
        IntentSpec configurada para execução na camada DW
    """
    mes_ano = entities.get("mes_ano")
    n_meses = entities.get("n_meses") or entities.get("janela_meses")
    
    # Calcula período
    periodo_inicio = mes_ano
    periodo_fim = mes_ano
    
    # Se tem "últimos N meses", calcula período
    if n_meses:
        periodo_inicio, periodo_fim = calcular_periodo_ultimos_meses(n_meses)
    
    # Se não tem período, usa mês atual como padrão
    if not periodo_inicio:
        hoje = datetime.now()
        periodo_inicio = hoje.strftime("%Y-%m")
        periodo_fim = periodo_inicio
    
    # Extrai filtros
    supervisor_id = entities.get("supervisor_id")  # Se já foi resolvido
    vendedor_id = entities.get("vendedor_id")  # Se já foi resolvido
    rota = entities.get("rota")
    
    # Mapeia intenção para tipo de IntentSpec
    if intent == IntentType.CONSULTA_META or intent == IntentType.MOTIVO_NAO_BATEU_META:
        return criar_intent_spec_meta(
            periodo_inicio=periodo_inicio,
            periodo_fim=periodo_fim,
            supervisor_id=supervisor_id,
            vendedor_id=vendedor_id,
            rota=rota,
            confianca=0.8
        )
    
    elif intent == IntentType.CLIENTES_RISCO_CHURN or intent == IntentType.CHURN_CLIENTES:
        return criar_intent_spec_clientes_criticos(
            periodo_inicio=periodo_inicio,
            periodo_fim=periodo_fim,
            supervisor_id=supervisor_id,
            rota_id=vendedor_id,
            limite=50,
            confianca=0.8
        )
    
    elif intent == IntentType.VENDAS_ANALISE:
        dimensao = "mes"  # Padrão
        if entities.get("vendedor") or entities.get("rota"):
            dimensao = "vendedor"
        elif entities.get("supervisor"):
            dimensao = "supervisor"
        
        return criar_intent_spec_vendas(
            periodo_inicio=periodo_inicio,
            periodo_fim=periodo_fim,
            dimensao=dimensao,
            confianca=0.8
        )
    
    elif intent == IntentType.CONSULTA_VENDEDORES_PERFORMANCE:
        # Ranking de vendedores
        mes = periodo_inicio
        ordenacao = "gap"  # Padrão: ordena por gap negativo
        if "atingimento" in entities.get("pergunta_original", "").lower():
            ordenacao = "atingimento"
        elif "faturamento" in entities.get("pergunta_original", "").lower():
            ordenacao = "faturamento"
        
        return criar_intent_spec_ranking_vendedores(
            mes=mes,
            ordenacao=ordenacao,
            limite=10,
            confianca=0.8
        )
    
    else:
        # Fallback: intent genérica
        logger.warning(f"[intent_to_spec] Intent não mapeada: {intent.value}, usando fallback")
        return IntentSpec(
            tipo="outros",
            periodo_inicio=periodo_inicio,
            periodo_fim=periodo_fim,
            dimensao_principal="nenhuma",
            filtros={},
            metricas=[],
            confianca=0.5,
            entidades_extraidas=entities
        )

