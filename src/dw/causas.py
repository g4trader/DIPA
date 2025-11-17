"""
Camada DW de Causas - DIPAM COPILOT™.

Este módulo fornece funções de alto nível para análise de causas quando a meta não foi batida.
Todas as funções consultam exclusivamente o DW (SQLite hoje, PostgreSQL no futuro).

ARQUITETURA:
- Nunca acessa banco fora da camada DW
- Usa sempre connection.py e models.py
- Retorna dataclasses tipadas
- Logs legíveis para auditoria
- Compatível com SQLite e PostgreSQL
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc, asc, extract, cast, String
import logging

from src.dw.models import Venda, MetaVendedor, Vendedor, Cliente, Supervisor
from src.dw.models_analytics import AnalyticsVendedorMes, AnalyticsClienteMes

logger = logging.getLogger(__name__)


# ============================================================================
# DATACLASSES DE RETORNO
# ============================================================================

@dataclass
class MetaRealizadoMes:
    """Representa meta e realizado agregados por mês."""
    mes: str  # YYYY-MM
    meta_total: float
    realizado_total: float
    gap_total: float
    atingimento_medio: float  # Percentual


@dataclass
class VendedorCausa:
    """Representa vendedor com pior desempenho no mês."""
    vendedor_id: int
    vendedor_nome: str
    supervisor_id: Optional[int]
    supervisor_nome: Optional[str]
    rota_id: Optional[int]
    rota_nome: Optional[str]
    meta_vendedor_mes: float
    realizado_vendedor_mes: float
    gap_vendedor: float
    atingimento_vendedor: float  # Percentual


@dataclass
class RotaCausa:
    """Representa rota com maior gap no mês."""
    rota_id: Optional[int]
    rota_nome: str
    supervisor_id: Optional[int]
    supervisor_nome: Optional[str]
    meta_rota_mes: float
    realizado_rota_mes: float
    gap_rota: float
    percent_gap_do_total: float  # gap_rota / gap_total_mes * 100


@dataclass
class ClienteQueda:
    """Representa cliente com queda de compra no mês."""
    cliente_id: int
    cliente_nome: str
    faturamento_mes_atual: float
    faturamento_mes_anterior: float
    variacao_abs: float
    variacao_pct: float  # Percentual


@dataclass
class SKUQueda:
    """Representa SKU com queda de vendas no mês."""
    sku_id: Optional[str]  # codigo_produto
    sku_nome: Optional[str]  # desc_produto
    faturamento_mes_atual: float
    faturamento_mes_anterior: float
    variacao_abs: float
    variacao_pct: float  # Percentual


# ============================================================================
# FUNÇÕES DE CONSULTA
# ============================================================================

def get_metas_realizado_por_mes(
    session: Session,
    periodo_inicio: str,
    periodo_fim: str
) -> List[MetaRealizadoMes]:
    """
    Retorna meta e realizado agregados por mês no período especificado.
    
    Args:
        session: Sessão SQLAlchemy
        periodo_inicio: Mês inicial no formato "YYYY-MM" (ex.: "2024-11")
        periodo_fim: Mês final no formato "YYYY-MM" (ex.: "2025-10")
        
    Returns:
        Lista de MetaRealizadoMes, uma entrada por mês, ordenada por mes
        
    Exemplo:
        >>> resultados = get_metas_realizado_por_mes(session, "2025-08", "2025-08")
        >>> len(resultados)  # 1 mês
        >>> resultados[0].mes  # "2025-08"
        >>> resultados[0].gap_total  # R$ X.XXX,XX
    """
    query = session.query(
        AnalyticsVendedorMes.mes_ano.label('mes'),
        func.sum(AnalyticsVendedorMes.meta_total).label('meta_total'),
        func.sum(AnalyticsVendedorMes.realizado_total).label('realizado_total')
    ).filter(
        and_(
            AnalyticsVendedorMes.mes_ano >= periodo_inicio,
            AnalyticsVendedorMes.mes_ano <= periodo_fim,
            ~func.lower(AnalyticsVendedorMes.vendedor_nome).like('%total%'),
            AnalyticsVendedorMes.vendedor_nome != 'Totais',
            AnalyticsVendedorMes.vendedor_id.isnot(None)
        )
    ).group_by(
        AnalyticsVendedorMes.mes_ano
    ).order_by(
        AnalyticsVendedorMes.mes_ano
    )
    
    resultados = query.all()
    
    metas_mes = []
    for row in resultados:
        meta_total = float(row.meta_total) if row.meta_total else 0.0
        realizado_total = float(row.realizado_total) if row.realizado_total else 0.0
        gap_total = realizado_total - meta_total
        atingimento_medio = (realizado_total / meta_total * 100) if meta_total > 0 else 0.0
        
        metas_mes.append(MetaRealizadoMes(
            mes=row.mes,
            meta_total=meta_total,
            realizado_total=realizado_total,
            gap_total=gap_total,
            atingimento_medio=atingimento_medio
        ))
    
    logger.info(
        f"[dw.causas] get_metas_realizado_por_mes: "
        f"periodo={periodo_inicio} a {periodo_fim}, "
        f"encontrados {len(metas_mes)} meses"
    )
    
    return metas_mes


def get_piores_vendedores_no_mes(
    session: Session,
    ano_mes: str,
    limite: int = 10
) -> List[VendedorCausa]:
    """
    Retorna lista de piores vendedores no mês, ordenados por menor atingimento / maior gap.
    
    Args:
        session: Sessão SQLAlchemy
        ano_mes: Mês/ano no formato "YYYY-MM" (ex.: "2025-08")
        limite: Número máximo de vendedores a retornar (padrão: 10)
        
    Returns:
        Lista de VendedorCausa ordenada por menor atingimento primeiro
        
    Exemplo:
        >>> vendedores = get_piores_vendedores_no_mes(session, "2025-08", limite=10)
        >>> len(vendedores)  # Até 10 vendedores
        >>> vendedores[0].atingimento_vendedor  # Menor atingimento primeiro
    """
    query = session.query(
        AnalyticsVendedorMes.vendedor_id,
        AnalyticsVendedorMes.vendedor_nome,
        AnalyticsVendedorMes.supervisor_id,
        func.sum(AnalyticsVendedorMes.meta_total).label('meta_vendedor_mes'),
        func.sum(AnalyticsVendedorMes.realizado_total).label('realizado_vendedor_mes')
    ).filter(
        and_(
            AnalyticsVendedorMes.mes_ano == ano_mes,
            ~func.lower(AnalyticsVendedorMes.vendedor_nome).like('%total%'),
            AnalyticsVendedorMes.vendedor_nome != 'Totais',
            AnalyticsVendedorMes.vendedor_id.isnot(None)
        )
    ).group_by(
        AnalyticsVendedorMes.vendedor_id,
        AnalyticsVendedorMes.vendedor_nome,
        AnalyticsVendedorMes.supervisor_id
    )
    
    resultados = query.all()
    
    vendedores = []
    for row in resultados:
        meta = float(row.meta_vendedor_mes) if row.meta_vendedor_mes else 0.0
        realizado = float(row.realizado_vendedor_mes) if row.realizado_vendedor_mes else 0.0
        gap = realizado - meta
        atingimento = (realizado / meta * 100) if meta > 0 else 0.0
        
        # Busca supervisor e rota
        supervisor_nome = None
        rota_id = None
        rota_nome = None
        
        if row.vendedor_id:
            vendedor = session.query(Vendedor).filter(Vendedor.id == row.vendedor_id).first()
            if vendedor:
                rota_id = vendedor.id
                rota_nome = vendedor.nome or vendedor.codigo or ""
                
                if vendedor.supervisor_id:
                    supervisor = session.query(Supervisor).filter(Supervisor.id == vendedor.supervisor_id).first()
                    if supervisor:
                        supervisor_nome = supervisor.nome
        
        vendedores.append(VendedorCausa(
            vendedor_id=row.vendedor_id,
            vendedor_nome=row.vendedor_nome or "",
            supervisor_id=row.supervisor_id,
            supervisor_nome=supervisor_nome,
            rota_id=rota_id,
            rota_nome=rota_nome,
            meta_vendedor_mes=meta,
            realizado_vendedor_mes=realizado,
            gap_vendedor=gap,
            atingimento_vendedor=atingimento
        ))
    
    # Ordena por menor atingimento primeiro (piores primeiro)
    vendedores.sort(key=lambda x: x.atingimento_vendedor)
    
    # Aplica limite
    vendedores = vendedores[:limite]
    
    logger.info(
        f"[dw.causas] get_piores_vendedores_no_mes: "
        f"mes={ano_mes}, retornados {len(vendedores)} vendedores"
    )
    
    return vendedores


def get_rotas_com_maior_gap_no_mes(
    session: Session,
    ano_mes: str,
    limite: int = 10
) -> List[RotaCausa]:
    """
    Retorna rotas com maior gap no mês, ordenadas por maior gap.
    
    Args:
        session: Sessão SQLAlchemy
        ano_mes: Mês/ano no formato "YYYY-MM" (ex.: "2025-08")
        limite: Número máximo de rotas a retornar (padrão: 10)
        
    Returns:
        Lista de RotaCausa ordenada por maior gap primeiro
        
    Exemplo:
        >>> rotas = get_rotas_com_maior_gap_no_mes(session, "2025-08", limite=10)
        >>> len(rotas)  # Até 10 rotas
        >>> rotas[0].gap_rota  # Maior gap primeiro
    """
    # Primeiro, calcula gap_total do mês
    gap_total_mes = 0.0
    metas_mes = get_metas_realizado_por_mes(session, ano_mes, ano_mes)
    if metas_mes:
        gap_total_mes = abs(metas_mes[0].gap_total) if metas_mes[0].gap_total < 0 else 0.0
    
    # Agrega por vendedor (rota)
    query = session.query(
        AnalyticsVendedorMes.vendedor_id,
        AnalyticsVendedorMes.vendedor_nome,
        AnalyticsVendedorMes.supervisor_id,
        func.sum(AnalyticsVendedorMes.meta_total).label('meta_rota_mes'),
        func.sum(AnalyticsVendedorMes.realizado_total).label('realizado_rota_mes')
    ).filter(
        and_(
            AnalyticsVendedorMes.mes_ano == ano_mes,
            ~func.lower(AnalyticsVendedorMes.vendedor_nome).like('%total%'),
            AnalyticsVendedorMes.vendedor_nome != 'Totais',
            AnalyticsVendedorMes.vendedor_id.isnot(None)
        )
    ).group_by(
        AnalyticsVendedorMes.vendedor_id,
        AnalyticsVendedorMes.vendedor_nome,
        AnalyticsVendedorMes.supervisor_id
    )
    
    resultados = query.all()
    
    rotas = []
    for row in resultados:
        meta = float(row.meta_rota_mes) if row.meta_rota_mes else 0.0
        realizado = float(row.realizado_rota_mes) if row.realizado_rota_mes else 0.0
        gap = realizado - meta
        
        # Calcula percent_gap_do_total
        percent_gap_do_total = (abs(gap) / gap_total_mes * 100) if gap_total_mes > 0 else 0.0
        
        # Busca supervisor
        supervisor_nome = None
        if row.supervisor_id:
            supervisor = session.query(Supervisor).filter(Supervisor.id == row.supervisor_id).first()
            if supervisor:
                supervisor_nome = supervisor.nome
        
        rotas.append(RotaCausa(
            rota_id=row.vendedor_id,
            rota_nome=row.vendedor_nome or "",
            supervisor_id=row.supervisor_id,
            supervisor_nome=supervisor_nome,
            meta_rota_mes=meta,
            realizado_rota_mes=realizado,
            gap_rota=gap,
            percent_gap_do_total=percent_gap_do_total
        ))
    
    # Ordena por maior gap primeiro (mais negativo primeiro)
    rotas.sort(key=lambda x: x.gap_rota)
    
    # Aplica limite
    rotas = rotas[:limite]
    
    logger.info(
        f"[dw.causas] get_rotas_com_maior_gap_no_mes: "
        f"mes={ano_mes}, retornadas {len(rotas)} rotas"
    )
    
    return rotas


def get_clientes_com_queda_no_mes(
    session: Session,
    ano_mes: str,
    limite: int = 20
) -> List[ClienteQueda]:
    """
    Retorna clientes com queda de compra no mês, comparando com mês anterior.
    
    Args:
        session: Sessão SQLAlchemy
        ano_mes: Mês/ano no formato "YYYY-MM" (ex.: "2025-08")
        limite: Número máximo de clientes a retornar (padrão: 20)
        
    Returns:
        Lista de ClienteQueda ordenada por maior queda primeiro (mais negativo)
        
    Exemplo:
        >>> clientes = get_clientes_com_queda_no_mes(session, "2025-08", limite=20)
        >>> len(clientes)  # Até 20 clientes
        >>> clientes[0].variacao_pct  # Maior queda primeiro
    """
    # Calcula mês anterior
    try:
        dt_mes = datetime.strptime(ano_mes + "-01", "%Y-%m-%d")
        dt_anterior = dt_mes - timedelta(days=32)
        mes_anterior = dt_anterior.strftime("%Y-%m")
    except:
        logger.error(f"[dw.causas] Erro ao calcular mês anterior para {ano_mes}")
        return []
    
    # Extrai ano e mês da data_venda
    ano = extract('year', Venda.data_venda)
    mes = extract('month', Venda.data_venda)
    mes_ano_expr = cast(ano, String) + '-' + func.lpad(cast(mes, String), 2, '0')
    
    # Agrega faturamento atual
    query_atual = session.query(
        Venda.cliente_id,
        func.max(Cliente.nome).label('cliente_nome'),
        func.sum(Venda.valor_total_liquido).label('faturamento_mes_atual')
    ).join(
        Cliente, Venda.cliente_id == Cliente.id
    ).filter(
        mes_ano_expr == ano_mes
    ).group_by(
        Venda.cliente_id
    ).subquery()
    
    # Agrega faturamento anterior
    query_anterior = session.query(
        Venda.cliente_id,
        func.sum(Venda.valor_total_liquido).label('faturamento_mes_anterior')
    ).filter(
        mes_ano_expr == mes_anterior
    ).group_by(
        Venda.cliente_id
    ).subquery()
    
    # Join e calcula variação
    query = session.query(
        query_atual.c.cliente_id,
        query_atual.c.cliente_nome,
        query_atual.c.faturamento_mes_atual,
        func.coalesce(query_anterior.c.faturamento_mes_anterior, 0.0).label('faturamento_mes_anterior')
    ).outerjoin(
        query_anterior, query_atual.c.cliente_id == query_anterior.c.cliente_id
    )
    
    resultados = query.all()
    
    clientes_queda = []
    for row in resultados:
        fat_atual = float(row.faturamento_mes_atual) if row.faturamento_mes_atual else 0.0
        fat_anterior = float(row.faturamento_mes_anterior) if row.faturamento_mes_anterior else 0.0
        
        variacao_abs = fat_atual - fat_anterior
        
        if fat_anterior == 0:
            variacao_pct = -100.0 if fat_atual == 0 else 0.0
        else:
            variacao_pct = ((fat_atual - fat_anterior) / fat_anterior) * 100
        
        # Filtra apenas quedas (variacao_pct < 0)
        if variacao_pct < 0:
            clientes_queda.append(ClienteQueda(
                cliente_id=row.cliente_id,
                cliente_nome=row.cliente_nome or "",
                faturamento_mes_atual=fat_atual,
                faturamento_mes_anterior=fat_anterior,
                variacao_abs=variacao_abs,
                variacao_pct=variacao_pct
            ))
    
    # Ordena por maior queda primeiro (mais negativo primeiro)
    clientes_queda.sort(key=lambda x: x.variacao_pct)
    
    # Aplica limite
    clientes_queda = clientes_queda[:limite]
    
    logger.info(
        f"[dw.causas] get_clientes_com_queda_no_mes: "
        f"mes={ano_mes}, encontrados {len(clientes_queda)} clientes com queda"
    )
    
    return clientes_queda


def get_skus_com_queda_no_mes(
    session: Session,
    ano_mes: str,
    limite: int = 20
) -> List[SKUQueda]:
    """
    Retorna SKUs com queda de vendas no mês, comparando com mês anterior.
    
    Args:
        session: Sessão SQLAlchemy
        ano_mes: Mês/ano no formato "YYYY-MM" (ex.: "2025-08")
        limite: Número máximo de SKUs a retornar (padrão: 20)
        
    Returns:
        Lista de SKUQueda ordenada por maior queda primeiro (mais negativo)
        
    Exemplo:
        >>> skus = get_skus_com_queda_no_mes(session, "2025-08", limite=20)
        >>> len(skus)  # Até 20 SKUs
        >>> skus[0].variacao_pct  # Maior queda primeiro
    """
    # Calcula mês anterior
    try:
        dt_mes = datetime.strptime(ano_mes + "-01", "%Y-%m-%d")
        dt_anterior = dt_mes - timedelta(days=32)
        mes_anterior = dt_anterior.strftime("%Y-%m")
    except:
        logger.error(f"[dw.causas] Erro ao calcular mês anterior para {ano_mes}")
        return []
    
    # Extrai ano e mês da data_venda
    ano = extract('year', Venda.data_venda)
    mes = extract('month', Venda.data_venda)
    mes_ano_expr = cast(ano, String) + '-' + func.lpad(cast(mes, String), 2, '0')
    
    # Agrega faturamento atual
    query_atual = session.query(
        Venda.codigo_produto,
        func.max(Venda.desc_produto).label('sku_nome'),
        func.sum(Venda.valor_total_liquido).label('faturamento_mes_atual')
    ).filter(
        and_(
            mes_ano_expr == ano_mes,
            Venda.codigo_produto.isnot(None)
        )
    ).group_by(
        Venda.codigo_produto
    ).subquery()
    
    # Agrega faturamento anterior
    query_anterior = session.query(
        Venda.codigo_produto,
        func.sum(Venda.valor_total_liquido).label('faturamento_mes_anterior')
    ).filter(
        and_(
            mes_ano_expr == mes_anterior,
            Venda.codigo_produto.isnot(None)
        )
    ).group_by(
        Venda.codigo_produto
    ).subquery()
    
    # Join e calcula variação
    query = session.query(
        query_atual.c.codigo_produto,
        query_atual.c.sku_nome,
        query_atual.c.faturamento_mes_atual,
        func.coalesce(query_anterior.c.faturamento_mes_anterior, 0.0).label('faturamento_mes_anterior')
    ).outerjoin(
        query_anterior, query_atual.c.codigo_produto == query_anterior.c.codigo_produto
    )
    
    resultados = query.all()
    
    skus_queda = []
    for row in resultados:
        fat_atual = float(row.faturamento_mes_atual) if row.faturamento_mes_atual else 0.0
        fat_anterior = float(row.faturamento_mes_anterior) if row.faturamento_mes_anterior else 0.0
        
        variacao_abs = fat_atual - fat_anterior
        
        if fat_anterior == 0:
            variacao_pct = -100.0 if fat_atual == 0 else 0.0
        else:
            variacao_pct = ((fat_atual - fat_anterior) / fat_anterior) * 100
        
        # Filtra apenas quedas (variacao_pct < 0)
        if variacao_pct < 0:
            skus_queda.append(SKUQueda(
                sku_id=row.codigo_produto,
                sku_nome=row.sku_nome,
                faturamento_mes_atual=fat_atual,
                faturamento_mes_anterior=fat_anterior,
                variacao_abs=variacao_abs,
                variacao_pct=variacao_pct
            ))
    
    # Ordena por maior queda primeiro (mais negativo primeiro)
    skus_queda.sort(key=lambda x: x.variacao_pct)
    
    # Aplica limite
    skus_queda = skus_queda[:limite]
    
    logger.info(
        f"[dw.causas] get_skus_com_queda_no_mes: "
        f"mes={ano_mes}, encontrados {len(skus_queda)} SKUs com queda"
    )
    
    return skus_queda

