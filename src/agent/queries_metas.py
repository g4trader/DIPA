"""
Funções centralizadas para queries de metas_vendedor com exclusão de totalizadores.

Este módulo contém funções reutilizáveis para calcular KPIs mensais
a partir da tabela metas_vendedor, garantindo que linhas de totalizador
(como "Totais", "Total", etc.) sejam sempre excluídas.
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from decimal import Decimal
import logging

from src.dw.models import MetaVendedor, Vendedor, Supervisor

logger = logging.getLogger(__name__)


def _filtrar_totalizadores(query, excluir_totais: bool = True):
    """
    Aplica filtros para excluir linhas de totalizador de uma query.
    
    Args:
        query: Query SQLAlchemy a ser filtrada
        excluir_totais: Se True, exclui linhas onde vendedor_nome contém "Total" ou "Totais"
        
    Returns:
        Query filtrada
    """
    if excluir_totais:
        query = query.filter(
            ~func.lower(MetaVendedor.vendedor_nome).like('%total%'),
            MetaVendedor.vendedor_nome != 'Totais',
            MetaVendedor.vendedor_id.isnot(None)  # Garante que tem vendedor_id válido
        )
    return query


def get_metas_realizado_por_mes_direto(
    session: Session,
    mes_ano: str,
    excluir_totais: bool = True
) -> Dict[str, Any]:
    """
    Calcula KPIs agregados de meta e realizado para um mês específico
    diretamente da tabela metas_vendedor.
    
    Esta função é a FONTE ÚNICA DE VERDADE para cálculos de KPIs mensais
    a partir de metas_vendedor. Deve ser usada em todos os lugares que
    precisam de meta_total, realizado_total, etc. a partir da tabela original.
    
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
        - linhas_detalhadas: List[dict] com dados por vendedor
    """
    # Query base - busca todos os registros do mês
    query = session.query(
        MetaVendedor.vendedor_id,
        MetaVendedor.vendedor_nome,
        func.sum(MetaVendedor.valor_meta).label("meta_total"),
        func.sum(MetaVendedor.valor_faturado).label("realizado_total"),
    ).filter(
        MetaVendedor.mes_ano == mes_ano
    )
    
    # Exclui linhas de "Totais" se solicitado
    query = _filtrar_totalizadores(query, excluir_totais)
    
    # Agrupa por vendedor
    query = query.group_by(
        MetaVendedor.vendedor_id,
        MetaVendedor.vendedor_nome
    )
    
    # Busca todas as linhas
    linhas = query.all()
    
    if not linhas:
        logger.warning(f"[AUDIT_KPIS] mes={mes_ano} Nenhum registro encontrado em metas_vendedor")
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
    realizado_total = sum(float(v.realizado_total or 0) for v in linhas)
    gap_total = realizado_total - meta_total
    atingimento_medio = (realizado_total / meta_total * 100) if meta_total > 0 else 0.0
    
    # Log de auditoria
    logger.info(
        f"[AUDIT_KPIS] mes={mes_ano} "
        f"meta_total={meta_total:,.2f} "
        f"realizado_total={realizado_total:,.2f} "
        f"atingimento={atingimento_medio:.2f}% "
        f"total_vendedores={len(linhas)} "
        f"excluir_totais={excluir_totais} "
        f"fonte=metas_vendedor"
    )
    
    # Monta linhas detalhadas
    linhas_detalhadas = []
    for linha in linhas:
        meta = float(linha.meta_total)
        realizado = float(linha.realizado_total or 0)
        atingimento = (realizado / meta * 100) if meta > 0 else 0.0
        gap = realizado - meta
        
        linhas_detalhadas.append({
            "vendedor_id": linha.vendedor_id,
            "vendedor_nome": linha.vendedor_nome,
            "meta_total": meta,
            "realizado_total": realizado,
            "gap_total": gap,
            "atingimento_pct": atingimento
        })
    
    return {
        "meta_total": meta_total,
        "realizado_total": realizado_total,
        "gap_total": gap_total,
        "atingimento_medio": atingimento_medio,
        "total_vendedores": len(linhas),
        "linhas_detalhadas": linhas_detalhadas
    }


def query_meta_realizado_por_vendedor_filtrado(
    session: Session,
    mes_ano: str,
    excluir_totais: bool = True
) -> List[Dict[str, Any]]:
    """
    Para um determinado mês (YYYY-MM), retorna meta x realizado por vendedor,
    EXCLUINDO linhas de totalizador.
    
    Args:
        session: Sessão SQLAlchemy
        mes_ano: Mês/ano no formato YYYY-MM
        excluir_totais: Se True, exclui linhas de totalizador
        
    Returns:
        List[Dict]: Lista de vendedores com meta, realizado e atingimento
    """
    logger.info(f"Buscando meta x realizado por vendedor para {mes_ano} (excluir_totais={excluir_totais})...")
    
    try:
        query = (
            session.query(
                MetaVendedor.vendedor_id,
                MetaVendedor.vendedor_nome,
                func.sum(MetaVendedor.valor_meta).label("meta_total"),
                func.sum(MetaVendedor.valor_faturado).label("realizado_total"),
            )
            .filter(MetaVendedor.mes_ano == mes_ano)
        )
        
        # Exclui totalizadores
        query = _filtrar_totalizadores(query, excluir_totais)
        
        # Agrupa por vendedor
        rows = query.group_by(
            MetaVendedor.vendedor_id,
            MetaVendedor.vendedor_nome
        ).all()
        
        resultados = []
        for row in rows:
            meta = float(row.meta_total or 0)
            realizado = float(row.realizado_total or 0)
            atingimento = (realizado / meta * 100.0) if meta > 0 else None
            
            resultados.append({
                "vendedor_id": row.vendedor_id,
                "vendedor_nome": row.vendedor_nome or "N/A",
                "meta_total": meta,
                "realizado_total": realizado,
                "atingimento_pct": atingimento
            })
        
        logger.info(f"Encontrados {len(resultados)} vendedores (excluindo totalizadores)")
        return resultados
        
    except Exception as e:
        logger.error(f"Erro ao buscar meta x realizado por vendedor: {str(e)}")
        return []

