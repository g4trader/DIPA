"""
Funções de leitura para tabelas de Analytics.

Este módulo fornece funções utilitárias que leem das tabelas analytics_*
em vez de fazer queries pesadas diretamente em vendas/metas_*.

Essas funções devem ser usadas pelo AgentService para acelerar consultas.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc, asc
from typing import List, Dict, Any, Optional
import logging

from src.dw.models_analytics import (
    AnalyticsVendedorMes, AnalyticsClienteMes,
    AnalyticsProdutoMes, AnalyticsAlerta
)

logger = logging.getLogger(__name__)


def get_resumo_meta_por_vendedor(session: Session, mes_ano: str) -> List[Dict[str, Any]]:
    """
    Retorna resumo de meta por vendedor usando analytics_vendedor_mes.
    
    Args:
        session: Sessão SQLAlchemy
        mes_ano: Mês/ano no formato "YYYY-MM"
        
    Returns:
        list: Lista de dicionários com dados agregados por vendedor
    """
    try:
        resultados = session.query(AnalyticsVendedorMes).filter(
            AnalyticsVendedorMes.mes_ano == mes_ano
        ).order_by(
            AnalyticsVendedorMes.atingimento_pct.asc().nulls_last()
        ).all()
        
        return [
            {
                "vendedor_id": r.vendedor_id,
                "vendedor_nome": r.vendedor_nome,
                "supervisor_id": r.supervisor_id,
                "meta_total": float(r.meta_total),
                "realizado_total": float(r.realizado_total),
                "atingimento_pct": float(r.atingimento_pct) if r.atingimento_pct else None,
                "gap_valor": float(r.gap_valor) if r.gap_valor else None,
                "rank_atingimento": r.rank_atingimento,
                "qtd_clientes_positivados": r.qtd_clientes_positivados,
                "qtd_clientes_churn": r.qtd_clientes_churn,
                "qtd_skus": r.qtd_skus,
            }
            for r in resultados
        ]
    except Exception as e:
        logger.error(f"Erro ao buscar resumo de meta por vendedor: {str(e)}")
        return []


def get_piores_vendedores_por_gap(session: Session, mes_ano: str, limite: int = 10) -> List[Dict[str, Any]]:
    """
    Retorna os piores vendedores por gap (maior gap negativo) usando analytics_vendedor_mes.
    
    Args:
        session: Sessão SQLAlchemy
        mes_ano: Mês/ano no formato "YYYY-MM"
        limite: Número máximo de vendedores a retornar
        
    Returns:
        list: Lista de dicionários com os piores vendedores ordenados por gap (pior primeiro)
    """
    try:
        resultados = session.query(AnalyticsVendedorMes).filter(
            AnalyticsVendedorMes.mes_ano == mes_ano,
            AnalyticsVendedorMes.gap_valor < 0  # Apenas gaps negativos
        ).order_by(
            AnalyticsVendedorMes.gap_valor.asc()  # Menor gap (mais negativo) primeiro
        ).limit(limite).all()
        
        return [
            {
                "vendedor_id": r.vendedor_id,
                "vendedor_nome": r.vendedor_nome,
                "supervisor_id": r.supervisor_id,
                "meta_total": float(r.meta_total),
                "realizado_total": float(r.realizado_total),
                "atingimento_pct": float(r.atingimento_pct) if r.atingimento_pct else None,
                "gap_valor": float(r.gap_valor),
                "rank_atingimento": r.rank_atingimento,
                "qtd_clientes_positivados": r.qtd_clientes_positivados,
                "qtd_clientes_churn": r.qtd_clientes_churn,
            }
            for r in resultados
        ]
    except Exception as e:
        logger.error(f"Erro ao buscar piores vendedores por gap: {str(e)}")
        return []


def get_melhores_vendedores_por_atingimento(session: Session, mes_ano: str, limite: int = 10) -> List[Dict[str, Any]]:
    """
    Retorna os melhores vendedores por atingimento usando analytics_vendedor_mes.
    
    Args:
        session: Sessão SQLAlchemy
        mes_ano: Mês/ano no formato "YYYY-MM"
        limite: Número máximo de vendedores a retornar
        
    Returns:
        list: Lista de dicionários com os melhores vendedores ordenados por atingimento (melhor primeiro)
    """
    try:
        resultados = session.query(AnalyticsVendedorMes).filter(
            AnalyticsVendedorMes.mes_ano == mes_ano,
            AnalyticsVendedorMes.atingimento_pct.isnot(None)
        ).order_by(
            AnalyticsVendedorMes.atingimento_pct.desc()  # Maior atingimento primeiro
        ).limit(limite).all()
        
        return [
            {
                "vendedor_id": r.vendedor_id,
                "vendedor_nome": r.vendedor_nome,
                "supervisor_id": r.supervisor_id,
                "meta_total": float(r.meta_total),
                "realizado_total": float(r.realizado_total),
                "atingimento_pct": float(r.atingimento_pct),
                "gap_valor": float(r.gap_valor) if r.gap_valor else None,
                "rank_atingimento": r.rank_atingimento,
                "qtd_clientes_positivados": r.qtd_clientes_positivados,
            }
            for r in resultados
        ]
    except Exception as e:
        logger.error(f"Erro ao buscar melhores vendedores por atingimento: {str(e)}")
        return []


def get_clientes_criticos_churn(session: Session, mes_ano: str, limite: int = 20) -> List[Dict[str, Any]]:
    """
    Retorna clientes críticos com indicadores de churn usando analytics_cliente_mes.
    
    Args:
        session: Sessão SQLAlchemy
        mes_ano: Mês/ano no formato "YYYY-MM"
        limite: Número máximo de clientes a retornar
        
    Returns:
        list: Lista de dicionários com clientes críticos ordenados por dias desde última compra (mais críticos primeiro)
    """
    try:
        resultados = session.query(AnalyticsClienteMes).filter(
            AnalyticsClienteMes.mes_ano == mes_ano,
            AnalyticsClienteMes.dias_desde_ultima_compra.isnot(None)
        ).order_by(
            AnalyticsClienteMes.dias_desde_ultima_compra.desc()  # Mais dias sem comprar primeiro
        ).limit(limite).all()
        
        return [
            {
                "cliente_id": r.cliente_id,
                "cliente_nome": r.cliente_nome,
                "vendedor_id": r.vendedor_id,
                "faturamento_total": float(r.faturamento_total),
                "qtd_compras": r.qtd_compras,
                "dias_desde_ultima_compra": r.dias_desde_ultima_compra,
                "churn_score": float(r.churn_score) if r.churn_score else None,
                "tendencia_faturamento_3m": float(r.tendencia_faturamento_3m) if r.tendencia_faturamento_3m else None,
            }
            for r in resultados
        ]
    except Exception as e:
        logger.error(f"Erro ao buscar clientes críticos de churn: {str(e)}")
        return []


def get_produtos_em_queda(session: Session, mes_ano: str, limite: int = 20) -> List[Dict[str, Any]]:
    """
    Retorna produtos com queda de volume usando analytics_produto_mes e comparação com meses anteriores.
    
    Args:
        session: Sessão SQLAlchemy
        mes_ano: Mês/ano no formato "YYYY-MM"
        limite: Número máximo de produtos a retornar
        
    Returns:
        list: Lista de dicionários com produtos em queda ordenados por maior queda primeiro
    """
    try:
        # Busca produtos do mês atual
        produtos_atual = session.query(
            AnalyticsProdutoMes.codigo_produto,
            AnalyticsProdutoMes.desc_produto,
            AnalyticsProdutoMes.qtd_vendida.label('qtd_atual'),
            AnalyticsProdutoMes.faturamento_total.label('faturamento_atual')
        ).filter(
            AnalyticsProdutoMes.mes_ano == mes_ano
        ).subquery()
        
        # Calcula média dos 3 meses anteriores
        from datetime import datetime, timedelta
        mes_1_antes = (datetime.strptime(mes_ano, "%Y-%m") - timedelta(days=32)).strftime("%Y-%m")
        mes_2_antes = (datetime.strptime(mes_ano, "%Y-%m") - timedelta(days=62)).strftime("%Y-%m")
        mes_3_antes = (datetime.strptime(mes_ano, "%Y-%m") - timedelta(days=92)).strftime("%Y-%m")
        
        produtos_media = session.query(
            AnalyticsProdutoMes.codigo_produto,
            func.avg(AnalyticsProdutoMes.qtd_vendida).label('qtd_media_3m')
        ).filter(
            AnalyticsProdutoMes.mes_ano.in_([mes_1_antes, mes_2_antes, mes_3_antes])
        ).group_by(
            AnalyticsProdutoMes.codigo_produto
        ).subquery()
        
        # Combina e filtra produtos com queda
        resultados = session.query(
            produtos_atual.c.codigo_produto,
            produtos_atual.c.desc_produto,
            produtos_atual.c.qtd_atual,
            produtos_atual.c.faturamento_atual,
            produtos_media.c.qtd_media_3m
        ).outerjoin(
            produtos_media, produtos_atual.c.codigo_produto == produtos_media.c.codigo_produto
        ).filter(
            produtos_media.c.qtd_media_3m.isnot(None),
            produtos_atual.c.qtd_atual < produtos_media.c.qtd_media_3m * 0.8  # Queda > 20%
        ).order_by(
            (produtos_atual.c.qtd_atual - produtos_media.c.qtd_media_3m).asc()  # Maior queda primeiro
        ).limit(limite).all()
        
        return [
            {
                "codigo_produto": r.codigo_produto,
                "desc_produto": r.desc_produto,
                "qtd_atual": float(r.qtd_atual),
                "qtd_media_3m": float(r.qtd_media_3m),
                "queda_pct": ((r.qtd_media_3m - r.qtd_atual) / r.qtd_media_3m * 100) if r.qtd_media_3m > 0 else 0,
                "faturamento_atual": float(r.faturamento_atual),
            }
            for r in resultados
        ]
    except Exception as e:
        logger.error(f"Erro ao buscar produtos em queda: {str(e)}")
        return []


def get_alertas_criticos(session: Session, mes_ano: str) -> List[Dict[str, Any]]:
    """
    Retorna alertas críticos usando analytics_alertas.
    
    Args:
        session: Sessão SQLAlchemy
        mes_ano: Mês/ano no formato "YYYY-MM"
        
    Returns:
        list: Lista de dicionários com alertas ordenados por nível (alto primeiro)
    """
    try:
        # Ordena por nível: alto primeiro, depois médio, depois baixo
        nivel_prioridade = {
            "alto": 1,
            "medio": 2,
            "baixo": 3
        }
        
        resultados = session.query(AnalyticsAlerta).filter(
            AnalyticsAlerta.mes_ano == mes_ano
        ).all()
        
        # Ordena manualmente por nível
        resultados_ordenados = sorted(
            resultados,
            key=lambda x: nivel_prioridade.get(x.nivel, 99)
        )
        
        return [
            {
                "tipo_alerta": r.tipo_alerta,
                "referencia_id": r.referencia_id,
                "referencia_nome": r.referencia_nome,
                "descricao": r.descricao,
                "detalhes_json": r.detalhes_json,
                "nivel": r.nivel,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in resultados_ordenados
        ]
    except Exception as e:
        logger.error(f"Erro ao buscar alertas críticos: {str(e)}")
        return []

