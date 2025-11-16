"""
Módulo de Features para ML Baseline.

Este módulo contém funções para calcular features temporárias
a partir das tabelas analytics_* e dados brutos quando necessário.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

from src.config import config
from src.dw.models_analytics import (
    AnalyticsClienteMes, AnalyticsVendedorMes, AnalyticsProdutoMes
)
from src.dw.models import Venda

logger = logging.getLogger(__name__)


def calcular_faturamento_historico_cliente(
    session: Session, 
    cliente_id: int,
    meses_retroativos: int = 6
) -> List[Dict[str, any]]:
    """
    Calcula série histórica de faturamento para um cliente.
    
    Args:
        session: Sessão SQLAlchemy
        cliente_id: ID do cliente
        meses_retroativos: Número de meses para buscar (padrão: 6)
        
    Returns:
        list: Lista de dicionários com {'mes_ano': 'YYYY-MM', 'faturamento_total': float}
    """
    try:
        # Calcula data de corte
        hoje = datetime.now()
        data_corte = hoje.replace(day=1) - timedelta(days=1)  # Último dia do mês anterior
        
        # Busca registros em analytics_cliente_mes (mais eficiente)
        resultados = session.query(
            AnalyticsClienteMes.mes_ano,
            AnalyticsClienteMes.faturamento_total
        ).filter(
            AnalyticsClienteMes.cliente_id == cliente_id,
            AnalyticsClienteMes.faturamento_total > 0
        ).order_by(
            AnalyticsClienteMes.mes_ano.desc()
        ).limit(meses_retroativos).all()
        
        serie = [
            {
                'mes_ano': r.mes_ano,
                'faturamento_total': float(r.faturamento_total)
            }
            for r in resultados
        ]
        
        return serie
    
    except Exception as e:
        logger.warning(f"Erro ao calcular faturamento histórico para cliente {cliente_id}: {str(e)}")
        return []


def calcular_variacao_faturamento_cliente(
    session: Session,
    cliente_id: int,
    mes_ano_ref: str
) -> Dict[str, Optional[float]]:
    """
    Calcula variação de faturamento do cliente vs média dos últimos 3 meses.
    
    Args:
        session: Sessão SQLAlchemy
        cliente_id: ID do cliente
        mes_ano_ref: Mês/ano de referência no formato "YYYY-MM"
        
    Returns:
        dict: {
            "faturamento_media_3m": float ou None,
            "variacao_pct_vs_3m": float ou None
        }
    """
    try:
        # Parse mes_ano_ref
        ano_ref, mes_ref = mes_ano_ref.split("-")
        ano_ref, mes_ref = int(ano_ref), int(mes_ref)
        
        # Calcula os 3 meses anteriores
        mes_1_antes = (datetime(ano_ref, mes_ref, 1) - timedelta(days=32)).strftime("%Y-%m")
        mes_2_antes = (datetime(ano_ref, mes_ref, 1) - timedelta(days=62)).strftime("%Y-%m")
        mes_3_antes = (datetime(ano_ref, mes_ref, 1) - timedelta(days=92)).strftime("%Y-%m")
        
        # Busca faturamento dos 3 meses anteriores
        faturamentos_3m = session.query(
            AnalyticsClienteMes.faturamento_total
        ).filter(
            AnalyticsClienteMes.cliente_id == cliente_id,
            AnalyticsClienteMes.mes_ano.in_([mes_1_antes, mes_2_antes, mes_3_antes])
        ).all()
        
        if not faturamentos_3m:
            return {
                "faturamento_media_3m": None,
                "variacao_pct_vs_3m": None
            }
        
        # Calcula média
        valores = [float(f.faturamento_total) for f in faturamentos_3m]
        faturamento_media_3m = sum(valores) / len(valores)
        
        # Busca faturamento do mês de referência
        faturamento_atual = session.query(
            AnalyticsClienteMes.faturamento_total
        ).filter(
            AnalyticsClienteMes.cliente_id == cliente_id,
            AnalyticsClienteMes.mes_ano == mes_ano_ref
        ).scalar()
        
        if faturamento_atual is None:
            return {
                "faturamento_media_3m": faturamento_media_3m,
                "variacao_pct_vs_3m": None
            }
        
        faturamento_atual = float(faturamento_atual)
        
        # Calcula variação percentual
        if faturamento_media_3m > 0:
            variacao_pct = ((faturamento_atual - faturamento_media_3m) / faturamento_media_3m) * 100
        else:
            variacao_pct = 0.0 if faturamento_atual == 0 else 100.0
        
        return {
            "faturamento_media_3m": faturamento_media_3m,
            "variacao_pct_vs_3m": variacao_pct
        }
    
    except Exception as e:
        logger.warning(f"Erro ao calcular variação de faturamento para cliente {cliente_id}: {str(e)}")
        return {
            "faturamento_media_3m": None,
            "variacao_pct_vs_3m": None
        }


def calcular_variacao_faturamento_produto(
    session: Session,
    codigo_produto: str,
    mes_ano_ref: str
) -> Dict[str, Optional[float]]:
    """
    Calcula variação de faturamento do produto vs média dos últimos 3 meses.
    
    Args:
        session: Sessão SQLAlchemy
        codigo_produto: Código do produto
        mes_ano_ref: Mês/ano de referência no formato "YYYY-MM"
        
    Returns:
        dict: {
            "faturamento_media_3m": float ou None,
            "variacao_pct_vs_3m": float ou None
        }
    """
    try:
        # Parse mes_ano_ref
        ano_ref, mes_ref = mes_ano_ref.split("-")
        ano_ref, mes_ref = int(ano_ref), int(mes_ref)
        
        # Calcula os 3 meses anteriores
        mes_1_antes = (datetime(ano_ref, mes_ref, 1) - timedelta(days=32)).strftime("%Y-%m")
        mes_2_antes = (datetime(ano_ref, mes_ref, 1) - timedelta(days=62)).strftime("%Y-%m")
        mes_3_antes = (datetime(ano_ref, mes_ref, 1) - timedelta(days=92)).strftime("%Y-%m")
        
        # Busca faturamento dos 3 meses anteriores
        faturamentos_3m = session.query(
            AnalyticsProdutoMes.faturamento_total
        ).filter(
            AnalyticsProdutoMes.codigo_produto == codigo_produto,
            AnalyticsProdutoMes.mes_ano.in_([mes_1_antes, mes_2_antes, mes_3_antes])
        ).all()
        
        if not faturamentos_3m:
            return {
                "faturamento_media_3m": None,
                "variacao_pct_vs_3m": None
            }
        
        # Calcula média
        valores = [float(f.faturamento_total) for f in faturamentos_3m]
        faturamento_media_3m = sum(valores) / len(valores)
        
        # Busca faturamento do mês de referência
        faturamento_atual = session.query(
            AnalyticsProdutoMes.faturamento_total
        ).filter(
            AnalyticsProdutoMes.codigo_produto == codigo_produto,
            AnalyticsProdutoMes.mes_ano == mes_ano_ref
        ).scalar()
        
        if faturamento_atual is None:
            return {
                "faturamento_media_3m": faturamento_media_3m,
                "variacao_pct_vs_3m": None
            }
        
        faturamento_atual = float(faturamento_atual)
        
        # Calcula variação percentual
        if faturamento_media_3m > 0:
            variacao_pct = ((faturamento_atual - faturamento_media_3m) / faturamento_media_3m) * 100
        else:
            variacao_pct = 0.0 if faturamento_atual == 0 else 100.0
        
        return {
            "faturamento_media_3m": faturamento_media_3m,
            "variacao_pct_vs_3m": variacao_pct
        }
    
    except Exception as e:
        logger.warning(f"Erro ao calcular variação de faturamento para produto {codigo_produto}: {str(e)}")
        return {
            "faturamento_media_3m": None,
            "variacao_pct_vs_3m": None
        }


def calcular_trend_atingimento_vendedor(
    session: Session,
    vendedor_id: int,
    mes_ano_ref: str,
    meses_retroativos: int = 3
) -> Dict[str, Optional[float]]:
    """
    Calcula tendência de atingimento do vendedor nos últimos meses.
    
    Args:
        session: Sessão SQLAlchemy
        vendedor_id: ID do vendedor
        mes_ano_ref: Mês/ano de referência no formato "YYYY-MM"
        meses_retroativos: Número de meses para analisar (padrão: 3)
        
    Returns:
        dict: {
            "atingimento_media_3m": float ou None,
            "tendencia": str ou None  # "melhorando", "piorando", "estavel"
        }
    """
    try:
        # Calcula meses anteriores
        ano_ref, mes_ref = mes_ano_ref.split("-")
        ano_ref, mes_ref = int(ano_ref), int(mes_ref)
        
        meses = []
        for i in range(1, meses_retroativos + 1):
            mes_obj = datetime(ano_ref, mes_ref, 1) - timedelta(days=32 * i)
            meses.append(mes_obj.strftime("%Y-%m"))
        
        # Busca atingimentos dos meses anteriores
        atingimentos = session.query(
            AnalyticsVendedorMes.atingimento_pct
        ).filter(
            AnalyticsVendedorMes.vendedor_id == vendedor_id,
            AnalyticsVendedorMes.mes_ano.in_(meses),
            AnalyticsVendedorMes.atingimento_pct.isnot(None)
        ).order_by(
            AnalyticsVendedorMes.mes_ano.asc()
        ).all()
        
        if len(atingimentos) < 2:
            return {
                "atingimento_media_3m": None,
                "tendencia": None
            }
        
        valores = [float(a.atingimento_pct) for a in atingimentos]
        atingimento_media_3m = sum(valores) / len(valores)
        
        # Calcula tendência (simples: compara primeiro vs último)
        if len(valores) >= 2:
            if valores[-1] > valores[0] + 5:  # Melhorou mais de 5 pontos
                tendencia = "melhorando"
            elif valores[-1] < valores[0] - 5:  # Piorou mais de 5 pontos
                tendencia = "piorando"
            else:
                tendencia = "estavel"
        else:
            tendencia = None
        
        return {
            "atingimento_media_3m": atingimento_media_3m,
            "tendencia": tendencia
        }
    
    except Exception as e:
        logger.warning(f"Erro ao calcular trend de atingimento para vendedor {vendedor_id}: {str(e)}")
        return {
            "atingimento_media_3m": None,
            "tendencia": None
        }

