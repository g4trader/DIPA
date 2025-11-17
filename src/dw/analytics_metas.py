"""
Camada Analítica de Metas e Vendas - Data Warehouse.

Este módulo fornece funções de consulta reutilizáveis para acessar dados
de metas, vendas e clientes do Data Warehouse.

ARQUITETURA:
- DW é uma abstração lógica acessada via este módulo
- Estado atual: SQLite (data/dipam_dw.db) - POC
- Estado futuro: PostgreSQL - Migração planejada
- BigQuery: NÃO implementado - Apenas roadmap futuro

ESQUEMA DE TABELAS:
- metas_vendedor: Metas mensais por vendedor (mes_ano, valor_meta, valor_faturado)
- metas_departamento: Metas mensais por supervisor/departamento
- vendas: Vendas individuais (data_venda, valor_total_liquido, cliente_id, vendedor_id)
- analytics_vendedor_mes: Agregações pré-calculadas por vendedor/mês
- analytics_cliente_mes: Agregações pré-calculadas por cliente/mês

PERÍODO COBERTO:
- POC: Nov/2024 a Out/2025 (ou conforme dados disponíveis)
- Funções retornam lista vazia se não houver dados no período

USO:
- Sempre use get_db_session() de dw/connection.py para obter sessão
- Funções retornam objetos tipados (dataclasses) em vez de dicionários
- Todas as funções são independentes do banco físico (SQLite/PostgreSQL)
"""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import logging

from src.dw.models import MetaVendedor, MetaDepartamento, Venda
from src.dw.models_analytics import AnalyticsVendedorMes, AnalyticsClienteMes

logger = logging.getLogger(__name__)


# ============================================================================
# DATACLASSES DE RETORNO (Tipagem Forte)
# ============================================================================

@dataclass
class MetaMes:
    """Representa metas agregadas por mês."""
    mes_ano: str  # "2024-11"
    meta_total: float
    realizado_total: float
    gap_total: float
    atingimento_medio: float  # Percentual
    total_vendedores: int


@dataclass
class VendaMes:
    """Representa vendas agregadas por mês."""
    mes_ano: str  # "2024-11"
    faturamento_total: float
    quantidade_vendas: int
    quantidade_clientes: int
    ticket_medio: float


@dataclass
class SupervisorMeta:
    """Representa metas por supervisor."""
    supervisor_id: int
    supervisor_nome: str
    mes_ano: str
    meta_total: float
    realizado_total: float
    gap_total: float
    atingimento_pct: float
    quantidade_vendedores: int


@dataclass
class ClienteCritico:
    """Representa cliente em situação crítica (churn ou risco)."""
    cliente_id: int
    cliente_nome: str
    vendedor_id: Optional[int]
    vendedor_nome: Optional[str]
    mes_ano: str
    faturamento_total: float
    dias_sem_compra: int
    churn_score: float  # 0-100
    churn_flag: bool
    variacao_pct_vs_3m: Optional[float]  # Variação vs média 3 meses anteriores


# ============================================================================
# FUNÇÕES DE CONSULTA
# ============================================================================

def listar_metas_por_mes(
    session: Session,
    periodo_inicio: str,
    periodo_fim: str,
    excluir_totais: bool = True
) -> List[MetaMes]:
    """
    Lista metas agregadas por mês no período especificado.
    
    Esta função é a FONTE ÚNICA DE VERDADE para listar metas por mês.
    Retorna uma lista com um registro por mês, não apenas um agregado total.
    
    Args:
        session: Sessão SQLAlchemy (obtida via get_db_session())
        periodo_inicio: Mês inicial no formato "YYYY-MM" (ex.: "2024-11")
        periodo_fim: Mês final no formato "YYYY-MM" (ex.: "2025-10")
        excluir_totais: Se True, exclui linhas onde vendedor_nome contém "Total" ou "Totais"
        
    Returns:
        Lista de MetaMes, uma entrada por mês no período, ordenada por mes_ano
        
    Exemplo:
        >>> metas = listar_metas_por_mes(session, "2024-11", "2025-10")
        >>> len(metas)  # 12 meses
        >>> metas[0].mes_ano  # "2024-11"
        >>> metas[0].meta_total  # R$ X.XXX.XXX,XX
    """
    # Query base - agrupa por mes_ano
    query = session.query(
        AnalyticsVendedorMes.mes_ano,
        func.sum(AnalyticsVendedorMes.meta_total).label('meta_total'),
        func.sum(AnalyticsVendedorMes.realizado_total).label('realizado_total'),
        func.count(AnalyticsVendedorMes.vendedor_id.distinct()).label('total_vendedores')
    ).filter(
        and_(
            AnalyticsVendedorMes.mes_ano >= periodo_inicio,
            AnalyticsVendedorMes.mes_ano <= periodo_fim
        )
    )
    
    # Exclui linhas de "Totais" se solicitado
    if excluir_totais:
        query = query.filter(
            ~func.lower(AnalyticsVendedorMes.vendedor_nome).like('%total%'),
            AnalyticsVendedorMes.vendedor_nome != 'Totais',
            AnalyticsVendedorMes.vendedor_id.isnot(None)
        )
    
    # Agrupa por mês
    query = query.group_by(AnalyticsVendedorMes.mes_ano)
    
    # Ordena por mês
    query = query.order_by(AnalyticsVendedorMes.mes_ano)
    
    # Executa query
    resultados = query.all()
    
    # Converte para dataclasses
    metas_mes = []
    for row in resultados:
        meta_total = float(row.meta_total) if row.meta_total else 0.0
        realizado_total = float(row.realizado_total) if row.realizado_total else 0.0
        gap_total = realizado_total - meta_total
        atingimento_medio = (realizado_total / meta_total * 100) if meta_total > 0 else 0.0
        
        metas_mes.append(MetaMes(
            mes_ano=row.mes_ano,
            meta_total=meta_total,
            realizado_total=realizado_total,
            gap_total=gap_total,
            atingimento_medio=atingimento_medio,
            total_vendedores=row.total_vendedores or 0
        ))
    
    logger.info(
        f"[analytics_metas] listar_metas_por_mes: "
        f"periodo={periodo_inicio} a {periodo_fim}, "
        f"encontrados {len(metas_mes)} meses"
    )
    
    return metas_mes


def listar_vendas_por_mes(
    session: Session,
    periodo_inicio: str,
    periodo_fim: str
) -> List[VendaMes]:
    """
    Lista vendas agregadas por mês no período especificado.
    
    Args:
        session: Sessão SQLAlchemy
        periodo_inicio: Mês inicial no formato "YYYY-MM"
        periodo_fim: Mês final no formato "YYYY-MM"
        
    Returns:
        Lista de VendaMes, uma entrada por mês no período, ordenada por mes_ano
        
    Exemplo:
        >>> vendas = listar_vendas_por_mes(session, "2024-11", "2025-10")
        >>> len(vendas)  # 12 meses
        >>> vendas[0].faturamento_total  # R$ X.XXX.XXX,XX
        
    NOTA: Usa func.strftime para SQLite. Para PostgreSQL, seria func.to_char.
    Esta função funciona com ambos via SQLAlchemy.
    """
    # Extrai ano e mês da data_venda e agrupa
    # Solução portável: usa extract (funciona com SQLite e PostgreSQL)
    # SQLite: extract('year', date) funciona
    # PostgreSQL: extract('year', date) funciona
    from sqlalchemy import cast, String
    
    ano = func.extract('year', Venda.data_venda)
    mes = func.extract('month', Venda.data_venda)
    # Constrói 'YYYY-MM' usando concatenação
    mes_ano_expr = (
        cast(ano, String) + '-' + 
        func.lpad(cast(mes, String), 2, '0')
    )
    
    query = session.query(
        mes_ano_expr.label('mes_ano'),
        func.sum(Venda.valor_total_liquido).label('faturamento_total'),
        func.count(Venda.id).label('quantidade_vendas'),
        func.count(func.distinct(Venda.cliente_id)).label('quantidade_clientes')
    ).filter(
        and_(
            mes_ano_expr >= periodo_inicio,
            mes_ano_expr <= periodo_fim
        )
    ).group_by(
        mes_ano_expr
    ).order_by(
        mes_ano_expr
    )
    
    resultados = query.all()
    
    # Converte para dataclasses
    vendas_mes = []
    for row in resultados:
        faturamento_total = float(row.faturamento_total) if row.faturamento_total else 0.0
        quantidade_vendas = row.quantidade_vendas or 0
        quantidade_clientes = row.quantidade_clientes or 0
        ticket_medio = (faturamento_total / quantidade_vendas) if quantidade_vendas > 0 else 0.0
        
        vendas_mes.append(VendaMes(
            mes_ano=row.mes_ano,
            faturamento_total=faturamento_total,
            quantidade_vendas=quantidade_vendas,
            quantidade_clientes=quantidade_clientes,
            ticket_medio=ticket_medio
        ))
    
    logger.info(
        f"[analytics_metas] listar_vendas_por_mes: "
        f"periodo={periodo_inicio} a {periodo_fim}, "
        f"encontrados {len(vendas_mes)} meses"
    )
    
    return vendas_mes


def listar_metas_realizado_por_supervisor(
    session: Session,
    mes: str
) -> List[SupervisorMeta]:
    """
    Lista metas e realizados por supervisor para um mês específico.
    
    Args:
        session: Sessão SQLAlchemy
        mes: Mês no formato "YYYY-MM" (ex.: "2025-08")
        
    Returns:
        Lista de SupervisorMeta, uma entrada por supervisor
        
    Exemplo:
        >>> supervisores = listar_metas_realizado_por_supervisor(session, "2025-08")
        >>> len(supervisores)  # Número de supervisores
        >>> supervisores[0].supervisor_nome  # "Supervisor Leandro"
    """
    # Agrupa analytics_vendedor_mes por supervisor
    query = session.query(
        AnalyticsVendedorMes.supervisor_id,
        func.max(AnalyticsVendedorMes.vendedor_nome).label('supervisor_nome'),  # Placeholder, precisa join
        func.sum(AnalyticsVendedorMes.meta_total).label('meta_total'),
        func.sum(AnalyticsVendedorMes.realizado_total).label('realizado_total'),
        func.count(func.distinct(AnalyticsVendedorMes.vendedor_id)).label('quantidade_vendedores')
    ).filter(
        and_(
            AnalyticsVendedorMes.mes_ano == mes,
            AnalyticsVendedorMes.supervisor_id.isnot(None),
            ~func.lower(AnalyticsVendedorMes.vendedor_nome).like('%total%'),
            AnalyticsVendedorMes.vendedor_nome != 'Totais'
        )
    ).group_by(
        AnalyticsVendedorMes.supervisor_id
    )
    
    resultados = query.all()
    
    # Busca nomes de supervisores (se necessário, pode fazer join)
    from src.dw.models import Supervisor
    
    supervisores_meta = []
    for row in resultados:
        if not row.supervisor_id:
            continue
            
        # Busca nome do supervisor
        supervisor = session.query(Supervisor).filter(
            Supervisor.id == row.supervisor_id
        ).first()
        
        supervisor_nome = supervisor.nome if supervisor else f"Supervisor {row.supervisor_id}"
        
        meta_total = float(row.meta_total) if row.meta_total else 0.0
        realizado_total = float(row.realizado_total) if row.realizado_total else 0.0
        gap_total = realizado_total - meta_total
        atingimento_pct = (realizado_total / meta_total * 100) if meta_total > 0 else 0.0
        
        supervisores_meta.append(SupervisorMeta(
            supervisor_id=row.supervisor_id,
            supervisor_nome=supervisor_nome,
            mes_ano=mes,
            meta_total=meta_total,
            realizado_total=realizado_total,
            gap_total=gap_total,
            atingimento_pct=atingimento_pct,
            quantidade_vendedores=row.quantidade_vendedores or 0
        ))
    
    logger.info(
        f"[analytics_metas] listar_metas_realizado_por_supervisor: "
        f"mes={mes}, encontrados {len(supervisores_meta)} supervisores"
    )
    
    return supervisores_meta


def listar_clientes_criticos(
    session: Session,
    periodo_inicio: str,
    periodo_fim: str,
    supervisor_id: Optional[int] = None,
    rota_id: Optional[int] = None,
    limite: int = 50
) -> List[ClienteCritico]:
    """
    Lista clientes críticos (em risco de churn) no período especificado.
    
    Cliente crítico = churn_flag = True OU churn_score >= 70 OU dias_sem_compra > 60
    
    Args:
        session: Sessão SQLAlchemy
        periodo_inicio: Mês inicial no formato "YYYY-MM"
        periodo_fim: Mês final no formato "YYYY-MM"
        supervisor_id: Filtrar por supervisor (opcional)
        rota_id: Filtrar por vendedor/rota (opcional)
        limite: Número máximo de clientes a retornar (padrão: 50)
        
    Returns:
        Lista de ClienteCritico, ordenada por churn_score (maior primeiro)
        
    Exemplo:
        >>> clientes = listar_clientes_criticos(session, "2025-08", "2025-08", limite=20)
        >>> len(clientes)  # Até 20 clientes
        >>> clientes[0].churn_score  # Score mais alto primeiro
    """
    query = session.query(AnalyticsClienteMes).filter(
        and_(
            AnalyticsClienteMes.mes_ano >= periodo_inicio,
            AnalyticsClienteMes.mes_ano <= periodo_fim,
            or_(
                AnalyticsClienteMes.churn_flag == True,
                AnalyticsClienteMes.churn_score >= 70,
                AnalyticsClienteMes.dias_desde_ultima_compra > 60
            )
        )
    )
    
    # Filtros opcionais
    if supervisor_id:
        # Precisa join com vendedor para pegar supervisor_id
        from src.dw.models import Vendedor
        query = query.join(Vendedor, AnalyticsClienteMes.vendedor_id == Vendedor.id).filter(
            Vendedor.supervisor_id == supervisor_id
        )
    
    if rota_id:
        query = query.filter(AnalyticsClienteMes.vendedor_id == rota_id)
    
    # Ordena por churn_score (maior primeiro) e limita
    query = query.order_by(
        AnalyticsClienteMes.churn_score.desc().nulls_last(),
        AnalyticsClienteMes.dias_desde_ultima_compra.desc().nulls_last()
    ).limit(limite)
    
    resultados = query.all()
    
    # Busca nomes de vendedores
    from src.dw.models import Vendedor
    
    clientes_criticos = []
    for row in resultados:
        # Busca nome do vendedor se houver
        vendedor_nome = None
        if row.vendedor_id:
            vendedor = session.query(Vendedor).filter(
                Vendedor.id == row.vendedor_id
            ).first()
            vendedor_nome = vendedor.nome if vendedor else None
        
        clientes_criticos.append(ClienteCritico(
            cliente_id=row.cliente_id,
            cliente_nome=row.cliente_nome,
            vendedor_id=row.vendedor_id,
            vendedor_nome=vendedor_nome,
            mes_ano=row.mes_ano,
            faturamento_total=float(row.faturamento_total) if row.faturamento_total else 0.0,
            dias_sem_compra=row.dias_desde_ultima_compra or 0,
            churn_score=float(row.churn_score) if row.churn_score else 0.0,
            churn_flag=row.churn_flag or False,
            variacao_pct_vs_3m=float(row.variacao_pct_vs_3m) if row.variacao_pct_vs_3m else None
        ))
    
    logger.info(
        f"[analytics_metas] listar_clientes_criticos: "
        f"periodo={periodo_inicio} a {periodo_fim}, "
        f"encontrados {len(clientes_criticos)} clientes críticos"
    )
    
    return clientes_criticos

