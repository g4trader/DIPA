"""
Funções de queries para analytics com agregações corretas.

Este módulo contém funções reutilizáveis para calcular KPIs mensais
de forma consistente, evitando duplicação e garantindo precisão.
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from decimal import Decimal
import logging

from src.dw.models_analytics import AnalyticsVendedorMes

logger = logging.getLogger(__name__)


def get_metas_realizado_por_mes(
    session: Session,
    mes_ano: str,
    excluir_totais: bool = True
) -> Dict[str, Any]:
    """
    Calcula KPIs agregados de meta e realizado para um mês específico.
    
    Esta função é a FONTE ÚNICA DE VERDADE para cálculos de KPIs mensais.
    Deve ser usada em todos os lugares que precisam de meta_total, realizado_total, etc.
    
    Args:
        session: Sessão SQLAlchemy
        mes_ano: Mês/ano no formato "YYYY-MM" (ex.: "2025-08")
        excluir_totais: Se True, exclui linhas onde vendedor_nome contém "Total" ou "Totais"
        
    Returns:
        dict com:
        - meta_total: float
        - realizado_total: float
        - gap_total: float
        - atingimento_medio: float (percentual)
        - total_vendedores: int
        - linhas_detalhadas: List[AnalyticsVendedorMes] (sem Totais se excluir_totais=True)
    """
    # Query base - busca todos os registros do mês
    query = session.query(AnalyticsVendedorMes).filter(
        AnalyticsVendedorMes.mes_ano == mes_ano
    )
    
    # Exclui linhas de "Totais" se solicitado
    if excluir_totais:
        query = query.filter(
            ~func.lower(AnalyticsVendedorMes.vendedor_nome).like('%total%'),
            AnalyticsVendedorMes.vendedor_nome != 'Totais',
            AnalyticsVendedorMes.vendedor_id.isnot(None)  # Garante que tem vendedor_id válido
        )
    
    # Busca todas as linhas
    linhas = query.all()
    
    if not linhas:
        logger.warning(f"[AUDIT_KPIS] mes={mes_ano} Nenhum registro encontrado")
        return {
            "meta_total": 0.0,
            "realizado_total": 0.0,
            "gap_total": 0.0,
            "atingimento_medio": 0.0,
            "total_vendedores": 0,
            "linhas_detalhadas": []
        }
    
    # Calcula totais
    meta_total = sum(float(v.meta_total) for v in linhas)
    realizado_total = sum(float(v.realizado_total) for v in linhas)
    gap_total = realizado_total - meta_total
    atingimento_medio = (realizado_total / meta_total * 100) if meta_total > 0 else 0.0
    
    # Log de auditoria
    logger.info(
        f"[AUDIT_KPIS] mes={mes_ano} "
        f"meta_total={meta_total:,.2f} "
        f"realizado_total={realizado_total:,.2f} "
        f"atingimento={atingimento_medio:.2f}% "
        f"total_vendedores={len(linhas)} "
        f"excluir_totais={excluir_totais}"
    )
    
    return {
        "meta_total": meta_total,
        "realizado_total": realizado_total,
        "gap_total": gap_total,
        "atingimento_medio": atingimento_medio,
        "total_vendedores": len(linhas),
        "linhas_detalhadas": linhas
    }


def get_piores_vendedores_por_gap(
    session: Session,
    mes_ano: str,
    limite: int = 10,
    excluir_totais: bool = True
) -> List[AnalyticsVendedorMes]:
    """
    Busca piores vendedores por gap negativo, excluindo linhas de Totais.
    
    Args:
        session: Sessão SQLAlchemy
        mes_ano: Mês/ano no formato "YYYY-MM"
        limite: Número máximo de vendedores a retornar
        excluir_totais: Se True, exclui linhas de Totais
        
    Returns:
        Lista de AnalyticsVendedorMes ordenada por gap (menor primeiro)
    """
    query = session.query(AnalyticsVendedorMes).filter(
        AnalyticsVendedorMes.mes_ano == mes_ano,
        AnalyticsVendedorMes.meta_risk_flag == True
    )
    
    if excluir_totais:
        query = query.filter(
            ~func.lower(AnalyticsVendedorMes.vendedor_nome).like('%total%'),
            AnalyticsVendedorMes.vendedor_nome != 'Totais',
            AnalyticsVendedorMes.vendedor_id.isnot(None)
        )
    
    return query.order_by(
        AnalyticsVendedorMes.gap_valor.asc().nulls_last(),
        AnalyticsVendedorMes.meta_risk_score.desc().nulls_last()
    ).limit(limite).all()
