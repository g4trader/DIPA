"""
Executor de Consultas DW - DIPAM COPILOT™.

Este módulo executa consultas na camada DW baseado em IntentSpec.

ARQUITETURA:
- Recebe IntentSpec (especificação de consulta)
- Executa consulta usando camada DW (analytics_metas.py, queries_*.py)
- Retorna dados estruturados para montagem de resposta
- NUNCA faz queries diretas no SQLite
- BigQuery NÃO implementado (apenas roadmap)
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
import logging

from src.agent.intent_spec import IntentSpec
from src.dw.analytics_metas import (
    listar_metas_por_mes,
    listar_vendas_por_mes,
    listar_metas_realizado_por_supervisor,
    listar_clientes_criticos,
    MetaMes,
    VendaMes,
    SupervisorMeta,
    ClienteCritico
)
from src.agent.queries_analytics import (
    get_metas_realizado_por_mes,
    get_piores_vendedores_por_gap
)

logger = logging.getLogger(__name__)


def executar_consulta_meta(
    session: Session,
    intent_spec: IntentSpec
) -> Dict[str, Any]:
    """
    Executa consulta de meta baseada em IntentSpec.
    
    Args:
        session: Sessão SQLAlchemy
        intent_spec: Especificação de intenção
        
    Returns:
        dict com dados de meta:
        - kpis_mes: KPIs agregados (se período único)
        - metas_por_mes: Lista de MetaMes (se período múltiplo)
        - piores_vendedores: Lista de vendedores em risco
        - tem_dados: bool
    """
    periodo_inicio = intent_spec.periodo_inicio
    periodo_fim = intent_spec.periodo_fim or intent_spec.periodo_inicio
    
    # Se período único, retorna KPIs agregados
    if periodo_inicio == periodo_fim:
        kpis_mes = get_metas_realizado_por_mes(
            session,
            periodo_inicio,
            excluir_totais=True
        )
        
        # Busca piores vendedores se solicitado
        piores_vendedores = []
        if intent_spec.filtros.get("incluir_ranking", True):
            limite = intent_spec.filtros.get("limite_ranking", 10)
            piores_vendedores = get_piores_vendedores_por_gap(
                session,
                periodo_inicio,
                limite=limite,
                excluir_totais=True
            )
        
        return {
            "kpis_mes": kpis_mes,
            "piores_vendedores": piores_vendedores,
            "tem_dados": kpis_mes["total_vendedores"] > 0,
            "periodo": periodo_inicio
        }
    
    # Se período múltiplo, retorna lista por mês
    metas_por_mes = listar_metas_por_mes(
        session,
        periodo_inicio,
        periodo_fim,
        excluir_totais=True
    )
    
    return {
        "metas_por_mes": metas_por_mes,
        "tem_dados": len(metas_por_mes) > 0,
        "periodo_inicio": periodo_inicio,
        "periodo_fim": periodo_fim
    }


def executar_consulta_vendas(
    session: Session,
    intent_spec: IntentSpec
) -> Dict[str, Any]:
    """
    Executa consulta de vendas baseada em IntentSpec.
    
    Args:
        session: Sessão SQLAlchemy
        intent_spec: Especificação de intenção
        
    Returns:
        dict com dados de vendas:
        - vendas_por_mes: Lista de VendaMes
        - tem_dados: bool
    """
    periodo_inicio = intent_spec.periodo_inicio
    periodo_fim = intent_spec.periodo_fim or intent_spec.periodo_inicio
    
    vendas_por_mes = listar_vendas_por_mes(
        session,
        periodo_inicio,
        periodo_fim
    )
    
    return {
        "vendas_por_mes": vendas_por_mes,
        "tem_dados": len(vendas_por_mes) > 0,
        "periodo_inicio": periodo_inicio,
        "periodo_fim": periodo_fim
    }


def executar_consulta_clientes_criticos(
    session: Session,
    intent_spec: IntentSpec
) -> Dict[str, Any]:
    """
    Executa consulta de clientes críticos baseada em IntentSpec.
    
    Args:
        session: Sessão SQLAlchemy
        intent_spec: Especificação de intenção
        
    Returns:
        dict com dados de clientes críticos:
        - clientes_criticos: Lista de ClienteCritico
        - tem_dados: bool
    """
    periodo_inicio = intent_spec.periodo_inicio
    periodo_fim = intent_spec.periodo_fim or intent_spec.periodo_inicio
    
    supervisor_id = intent_spec.filtros.get("supervisor_id")
    rota_id = intent_spec.filtros.get("rota_id")
    limite = intent_spec.filtros.get("limite", 50)
    
    clientes_criticos = listar_clientes_criticos(
        session,
        periodo_inicio,
        periodo_fim,
        supervisor_id=supervisor_id,
        rota_id=rota_id,
        limite=limite
    )
    
    return {
        "clientes_criticos": clientes_criticos,
        "tem_dados": len(clientes_criticos) > 0,
        "periodo_inicio": periodo_inicio,
        "periodo_fim": periodo_fim
    }


def executar_consulta_metas_por_supervisor(
    session: Session,
    intent_spec: IntentSpec
) -> Dict[str, Any]:
    """
    Executa consulta de metas por supervisor baseada em IntentSpec.
    
    Args:
        session: Sessão SQLAlchemy
        intent_spec: Especificação de intenção
        
    Returns:
        dict com dados de metas por supervisor:
        - supervisores_meta: Lista de SupervisorMeta
        - tem_dados: bool
    """
    mes = intent_spec.periodo_inicio or intent_spec.periodo_fim
    
    if not mes:
        return {
            "supervisores_meta": [],
            "tem_dados": False
        }
    
    supervisores_meta = listar_metas_realizado_por_supervisor(
        session,
        mes
    )
    
    return {
        "supervisores_meta": supervisores_meta,
        "tem_dados": len(supervisores_meta) > 0,
        "mes": mes
    }


def executar_consulta_dw(
    session: Session,
    intent_spec: IntentSpec
) -> Dict[str, Any]:
    """
    Executa consulta na camada DW baseada em IntentSpec.
    
    Esta é a função principal que roteia para as funções específicas
    baseado no tipo de intenção.
    
    Args:
        session: Sessão SQLAlchemy (obtida via get_db_session())
        intent_spec: Especificação de intenção
        
    Returns:
        dict com dados estruturados conforme o tipo de intenção
        
    Exemplo:
        >>> intent_spec = criar_intent_spec_meta("2024-11", "2025-10")
        >>> dados = executar_consulta_dw(session, intent_spec)
        >>> dados["metas_por_mes"]  # Lista de MetaMes
    """
    logger.info(
        f"[query_executor] Executando consulta DW: "
        f"tipo={intent_spec.tipo}, "
        f"periodo={intent_spec.periodo_inicio} a {intent_spec.periodo_fim}"
    )
    
    tipo = intent_spec.tipo
    
    if tipo == "meta":
        return executar_consulta_meta(session, intent_spec)
    elif tipo == "vendas":
        return executar_consulta_vendas(session, intent_spec)
    elif tipo == "clientes_criticos" or tipo == "churn":
        return executar_consulta_clientes_criticos(session, intent_spec)
    elif tipo == "metas_por_supervisor":
        return executar_consulta_metas_por_supervisor(session, intent_spec)
    else:
        logger.warning(f"[query_executor] Tipo de intenção não suportado: {tipo}")
        return {
            "tem_dados": False,
            "erro": f"Tipo de intenção não suportado: {tipo}"
        }

