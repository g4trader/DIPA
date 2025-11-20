"""
Engine de Consultas SQL - DIPAM COPILOT™ V1

Este módulo implementa todas as consultas essenciais definidas em ENGINEERING_QUERIES.md.
Todas as funções retornam list[dict] prontas para o pós-processador.

ARQUITETURA:
- Compatível com SQLite (dev) e PostgreSQL (produção)
- Usa SQLAlchemy para abstração de banco
- Retorna sempre list[dict] normalizado
- Zero hallucination: apenas dados reais do DW
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case, desc, asc, text, extract, cast, String, select
import logging

from src.dw.models import (
    Cliente, Vendedor, Supervisor, Venda,
    MetaVendedor, MetaDepartamento, DimProduto
)
from src.config import config

logger = logging.getLogger(__name__)


# ============================================================================
# HELPERS PARA COMPATIBILIDADE SQLite/PostgreSQL
# ============================================================================

def _date_diff_days(session: Session, date1_col, date2_col):
    """
    Calcula diferença em dias entre duas datas, compatível com SQLite e PostgreSQL.
    """
    if config.database.db_type == "postgresql":
        return func.extract('day', date1_col - date2_col)
    else:  # SQLite
        return func.julianday(date1_col) - func.julianday(date2_col)


def _date_add_months(session: Session, date_col, months: int):
    """
    Adiciona meses a uma data, compatível com SQLite e PostgreSQL.
    """
    if config.database.db_type == "postgresql":
        return func.date_trunc('month', date_col) + func.make_interval(months=months)
    else:  # SQLite
        # SQLite não tem função direta, usar expressão
        return func.date(date_col, f'+{months} months')


def _current_date(session: Session):
    """
    Retorna data atual, compatível com SQLite e PostgreSQL.
    """
    if config.database.db_type == "postgresql":
        return func.current_date()
    else:  # SQLite
        return func.date('now')


# ============================================================================
# Q1: CLIENTES SEM COMPRA HÁ DIAS
# ============================================================================

def get_clientes_sem_compra_ha_dias(
    session: Session,
    dias: int = 60,
    data_referencia: Optional[str] = None,
    filtros_behavior: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Retorna clientes ativos sem compras por mais de N dias.
    
    Args:
        session: Sessão SQLAlchemy
        dias: Número de dias sem compra (padrão: 60)
        data_referencia: Data de referência (YYYY-MM-DD) ou None para hoje
        filtros_behavior: Filtros adicionais do Behavior Memory (ex.: excluir pasta verde)
        
    Returns:
        Lista de dicts com:
        - cliente_id
        - nome
        - segmento
        - rota_id
        - data_ultima_compra
        - dias_sem_compra
    """
    # Data de referência
    if data_referencia:
        ref_date = datetime.strptime(data_referencia, "%Y-%m-%d").date()
    else:
        ref_date = datetime.now().date()
    
    # Conforme Q1 em ENGINEERING_QUERIES.md:
    # - Deve usar fato_vendas_detalhado (no modelo atual: Venda)
    # - MAX(v.data) AS data_ultima_compra
    # - Como o modelo atual usa Venda.data_venda, mantemos essa coluna
    ultima_compra_subq = (
        session.query(
            Venda.cliente_id,
            func.max(Venda.data_venda).label('data_ultima_compra')  # Equivalente a MAX(v.data) do blueprint
        )
        .group_by(Venda.cliente_id)
        .subquery()
    )
    
    # Query principal
    # Para SQLite, calcula diferença de dias usando julianday
    if config.database.db_type == "sqlite":
        dias_sem_compra_expr = case(
            (ultima_compra_subq.c.data_ultima_compra.is_(None), None),
            else_=func.julianday(text(f"DATE('{ref_date}')")) - func.julianday(ultima_compra_subq.c.data_ultima_compra)
        )
    else:  # PostgreSQL
        dias_sem_compra_expr = case(
            (ultima_compra_subq.c.data_ultima_compra.is_(None), None),
            else_=func.extract('day', text(f"DATE('{ref_date}')") - ultima_compra_subq.c.data_ultima_compra)
        )
    
    # Conforme Q1 em ENGINEERING_QUERIES.md:
    # - FROM dim_cliente c LEFT JOIN ultima_compra u ON u.cliente_id = c.cliente_id
    # - WHERE c.ativo = 1
    # - JOIN com Vendedor e Supervisor para trazer nomes
    # ✅ CORREÇÃO: JOIN melhorado - usa vendedor_id se disponível, senão usa rota_rca
    # ✅ CORREÇÃO: Supervisor pode vir do Cliente ou do Vendedor (prioriza do Cliente)
    from sqlalchemy.orm import aliased
    SupervisorViaVendedor = aliased(Supervisor, name='supervisor_via_vendedor')
    
    query = (
        session.query(
            Cliente.id.label('cliente_id'),
            Cliente.nome,
            Cliente.segmento_venda.label('segmento'),  # Equivalente a c.segmento do blueprint
            Cliente.rota_rca.label('rota_id'),
            Vendedor.nome.label('vendedor_nome'),
            Vendedor.codigo.label('vendedor_codigo'),
            # Supervisor pode vir do Cliente ou do Vendedor (prioriza do Cliente)
            func.coalesce(
                Supervisor.nome,
                SupervisorViaVendedor.nome
            ).label('supervisor_nome'),
            func.coalesce(
                Supervisor.codigo,
                SupervisorViaVendedor.codigo
            ).label('supervisor_codigo'),
            ultima_compra_subq.c.data_ultima_compra,
            dias_sem_compra_expr.label('dias_sem_compra')
        )
        .outerjoin(ultima_compra_subq, Cliente.id == ultima_compra_subq.c.cliente_id)
        # ✅ CORREÇÃO: JOIN com Vendedor - prioriza vendedor_id, fallback para rota_rca
        .outerjoin(
            Vendedor,
            or_(
                Cliente.vendedor_id == Vendedor.id,  # Se houver FK direta
                Cliente.rota_rca == Vendedor.codigo   # Fallback: JOIN por rota_rca
            )
        )
        # Supervisor do Cliente (prioridade)
        .outerjoin(Supervisor, Cliente.supervisor_id == Supervisor.id)
        # Supervisor do Vendedor (fallback se Cliente não tiver supervisor)
        .outerjoin(
            SupervisorViaVendedor,
            Vendedor.supervisor_id == SupervisorViaVendedor.id
        )
        .filter(Cliente.ativo == True)  # c.ativo = 1 conforme blueprint
    )
    
    # Aplica filtros do Behavior Memory
    if filtros_behavior:
        if "excluir_pastas" in filtros_behavior:
            pastas_excluir = filtros_behavior["excluir_pastas"]
            if isinstance(pastas_excluir, list) and pastas_excluir:
                # Join com supervisor para filtrar por pasta
                query = query.join(Supervisor, Cliente.supervisor_id == Supervisor.id)
                query = query.filter(~Supervisor.pasta.in_(pastas_excluir))
        
        if "excluir_segmentos" in filtros_behavior:
            segmentos_excluir = filtros_behavior["excluir_segmentos"]
            if isinstance(segmentos_excluir, list) and segmentos_excluir:
                query = query.filter(~Cliente.segmento_venda.in_(segmentos_excluir))
    
    # Filtra por dias sem compra
    # IMPORTANTE: "mais de 60 dias" significa >= 61 dias (não pode trazer 0 dias)
    # Se dias = 60, então filtro deve ser >= 61
    dias_minimo = dias + 1  # "mais de 60 dias" = >= 61 dias
    
    if config.database.db_type == "sqlite":
        diff_expr = func.julianday(text(f"DATE('{ref_date}')")) - func.julianday(ultima_compra_subq.c.data_ultima_compra)
    else:
        diff_expr = func.extract('day', text(f"DATE('{ref_date}')") - ultima_compra_subq.c.data_ultima_compra)
    
    # Filtra apenas clientes com >= 61 dias sem compra
    # IMPORTANTE: Não inclui clientes com 0 dias ou None (só inclui se realmente >= 61 dias)
    query = query.filter(
        and_(
            # Deve ter última compra registrada (não None) para calcular dias corretamente
            ultima_compra_subq.c.data_ultima_compra.isnot(None),
            # E a diferença deve ser >= 61 dias
            diff_expr >= dias_minimo
        )
    )
    
    # Ordena por dias sem compra (crescente - menor primeiro, conforme pedido)
    query = query.order_by(asc('dias_sem_compra'))
    
    resultados = query.all()
    
    # Converte para list[dict] e filtra para garantir >= 61 dias
    # IMPORTANTE: Filtro adicional para garantir que nenhum cliente com 0 dias seja retornado
    dias_minimo = dias + 1  # "mais de 60 dias" = >= 61 dias
    clientes_filtrados = []
    for row in resultados:
        dias_sem_compra = int(row.dias_sem_compra) if row.dias_sem_compra is not None else None
        # Só inclui se dias_sem_compra >= 61 (não inclui 0, None ou < 61)
        if dias_sem_compra is not None and dias_sem_compra >= dias_minimo:
            clientes_filtrados.append({
                "cliente_id": row.cliente_id,
                "nome": row.nome or "",
                "segmento": row.segmento or "",
                "rota_id": row.rota_id or "",
                "vendedor_nome": row.vendedor_nome or row.vendedor_codigo or row.rota_id or "",
                "vendedor_codigo": row.vendedor_codigo or row.rota_id or "",
                "supervisor_nome": row.supervisor_nome or row.supervisor_codigo or "",
                "supervisor_codigo": row.supervisor_codigo or "",
                "data_ultima_compra": row.data_ultima_compra.isoformat() if row.data_ultima_compra else None,
                "dias_sem_compra": dias_sem_compra
            })
    
    return clientes_filtrados


def get_clientes_sem_compra_por_rota(
    session: Session,
    dias: int = 60,
    data_referencia: Optional[str] = None,
    filtros_behavior: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Retorna agregação de clientes sem compra por rota/vendedor.
    
    Args:
        session: Sessão SQLAlchemy
        dias: Número de dias sem compra (padrão: 60)
        data_referencia: Data de referência (YYYY-MM-DD) ou None para hoje
        filtros_behavior: Filtros adicionais do Behavior Memory
        
    Returns:
        Lista de dicts com:
        - vendedor_nome
        - vendedor_codigo
        - supervisor_nome
        - supervisor_codigo
        - total_clientes_sem_compra
    """
    # Usa a query principal para obter os dados
    clientes_sem_compra = get_clientes_sem_compra_ha_dias(
        session=session,
        dias=dias,
        data_referencia=data_referencia,
        filtros_behavior=filtros_behavior
    )
    
    # Agrega por vendedor
    agregacao_por_rota = {}
    for cliente in clientes_sem_compra:
        vendedor_key = cliente.get("vendedor_codigo") or cliente.get("rota_id") or "N/A"
        supervisor_nome = cliente.get("supervisor_nome") or cliente.get("supervisor_codigo") or ""
        
        if vendedor_key not in agregacao_por_rota:
            agregacao_por_rota[vendedor_key] = {
                "vendedor_nome": cliente.get("vendedor_nome") or cliente.get("vendedor_codigo") or cliente.get("rota_id") or "N/A",
                "vendedor_codigo": cliente.get("vendedor_codigo") or cliente.get("rota_id") or "N/A",
                "supervisor_nome": supervisor_nome,
                "supervisor_codigo": cliente.get("supervisor_codigo") or "",
                "total_clientes_sem_compra": 0
            }
        
        agregacao_por_rota[vendedor_key]["total_clientes_sem_compra"] += 1
    
    # Converte para lista e ordena por total decrescente
    resultados = list(agregacao_por_rota.values())
    resultados.sort(key=lambda x: x["total_clientes_sem_compra"], reverse=True)
    
    return resultados


# ============================================================================
# Q2: CLIENTES COM QUEDA DE FATURAMENTO ANO CONTRA ANO
# ============================================================================

def get_clientes_queda_faturamento_ano_contra_ano(
    session: Session,
    ano_base: int,
    ano_comparado: int,
    top_n: int = 50,
    filtros_behavior: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Retorna clientes com maior queda de faturamento entre dois anos.
    
    Args:
        session: Sessão SQLAlchemy
        ano_base: Ano base (ex.: 2024)
        ano_comparado: Ano comparado (ex.: 2025)
        top_n: Número máximo de resultados (padrão: 50)
        filtros_behavior: Filtros adicionais do Behavior Memory
        
    Returns:
        Lista de dicts com:
        - cliente_id
        - nome
        - faturamento_base
        - faturamento_comp
        - delta_faturamento
        - delta_percentual
    """
    # Faturamento no ano base
    fat_base_subq = (
        session.query(
            Venda.cliente_id,
            func.sum(Venda.valor_total_liquido).label('faturamento_base')
        )
        .filter(extract('year', Venda.data_venda) == ano_base)
        .group_by(Venda.cliente_id)
        .subquery()
    )
    
    # Faturamento no ano comparado
    fat_comp_subq = (
        session.query(
            Venda.cliente_id,
            func.sum(Venda.valor_total_liquido).label('faturamento_comp')
        )
        .filter(extract('year', Venda.data_venda) == ano_comparado)
        .group_by(Venda.cliente_id)
        .subquery()
    )
    
    # Query principal (FULL OUTER JOIN simulado para SQLite)
    # SQLite não suporta FULL OUTER JOIN, então usamos UNION de LEFT e RIGHT JOIN
    # IMPORTANTE: usar select() explícito para garantir nomes de colunas consistentes
    left_join = select(
        fat_base_subq.c.cliente_id.label('cliente_id'),
        func.coalesce(fat_base_subq.c.faturamento_base, 0).label('faturamento_base'),
        func.coalesce(fat_comp_subq.c.faturamento_comp, 0).label('faturamento_comp')
    ).select_from(
        fat_base_subq.outerjoin(fat_comp_subq, fat_base_subq.c.cliente_id == fat_comp_subq.c.cliente_id)
    )
    
    right_join = select(
        fat_comp_subq.c.cliente_id.label('cliente_id'),
        func.coalesce(fat_base_subq.c.faturamento_base, 0).label('faturamento_base'),
        func.coalesce(fat_comp_subq.c.faturamento_comp, 0).label('faturamento_comp')
    ).select_from(
        fat_comp_subq.outerjoin(fat_base_subq, fat_comp_subq.c.cliente_id == fat_base_subq.c.cliente_id)
    ).where(fat_base_subq.c.cliente_id.is_(None))
    
    uniao_subq = left_join.union(right_join).subquery()
    
    # Adiciona cálculos e filtros
    query = (
        session.query(
            uniao_subq.c.cliente_id,
            Cliente.nome,
            uniao_subq.c.faturamento_base,
            uniao_subq.c.faturamento_comp,
            (uniao_subq.c.faturamento_comp - uniao_subq.c.faturamento_base).label('delta_faturamento'),
            case(
                (uniao_subq.c.faturamento_base > 0,
                 (uniao_subq.c.faturamento_comp - uniao_subq.c.faturamento_base) * 100.0 / uniao_subq.c.faturamento_base),
                else_=None
            ).label('delta_percentual')
        )
        .join(Cliente, uniao_subq.c.cliente_id == Cliente.id)
        .filter(uniao_subq.c.faturamento_comp < uniao_subq.c.faturamento_base)
    )
    
    # Aplica filtros do Behavior Memory
    if filtros_behavior:
        if "excluir_pastas" in filtros_behavior:
            pastas_excluir = filtros_behavior["excluir_pastas"]
            if isinstance(pastas_excluir, list) and pastas_excluir:
                query = query.join(Supervisor, Cliente.supervisor_id == Supervisor.id)
                query = query.filter(~Supervisor.pasta.in_(pastas_excluir))
    
    # Ordena por maior queda (delta negativo)
    query = query.order_by(asc('delta_faturamento')).limit(top_n)
    
    resultados = query.all()
    
    return [
        {
            "cliente_id": row.cliente_id,
            "nome": row.nome or "",
            "faturamento_base": float(row.faturamento_base) if row.faturamento_base else 0.0,
            "faturamento_comp": float(row.faturamento_comp) if row.faturamento_comp else 0.0,
            "delta_faturamento": float(row.delta_faturamento) if row.delta_faturamento else 0.0,
            "delta_percentual": float(row.delta_percentual) if row.delta_percentual else None
        }
        for row in resultados
    ]


# ============================================================================
# Q3: INDÚSTRIAS COM MAIS VENDEDORES FORA DA META
# ============================================================================

def get_industrias_com_mais_vendedores_fora_meta(
    session: Session,
    ano: int,
    mes: int,
    atingimento_limite: float = 100.0,
    filtros_behavior: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Retorna indústrias com mais vendedores fora da meta.
    
    Conforme Q3 em ENGINEERING_QUERIES.md:
    - Usa fato_metas_vendedor_mensal.industria (MetaVendedor.industria)
    
    Args:
        session: Sessão SQLAlchemy
        ano: Ano (ex.: 2025)
        mes: Mês (ex.: 10)
        atingimento_limite: Limite de atingimento (padrão: 100.0)
        filtros_behavior: Filtros adicionais do Behavior Memory
        
    Returns:
        Lista de dicts com:
        - industria
        - qtd_vendedores_fora_meta
    """
    # Conforme Q3 em ENGINEERING_QUERIES.md:
    # SELECT fm.industria, COUNT(DISTINCT fm.vendedor_id) AS qtd_vendedores_fora_meta
    # FROM fato_metas_vendedor_mensal fm
    # WHERE fm.ano = :ano AND fm.mes = :mes AND fm.atingimento_pct < :atingimento_limite
    # GROUP BY fm.industria
    query = (
        session.query(
            MetaVendedor.industria,
            func.count(func.distinct(MetaVendedor.vendedor_id)).label('qtd_vendedores_fora_meta')
        )
        .filter(
            and_(
                MetaVendedor.ano == ano,
                MetaVendedor.mes == mes,
                MetaVendedor.percentual_atingido_valor < atingimento_limite,
                MetaVendedor.industria.isnot(None)  # Apenas vendedores com industria definida
            )
        )
        .group_by(MetaVendedor.industria)
    )
    
    # Aplica filtros do Behavior Memory
    if filtros_behavior:
        if "excluir_pastas" in filtros_behavior:
            pastas_excluir = filtros_behavior["excluir_pastas"]
            if isinstance(pastas_excluir, list) and pastas_excluir:
                query = query.join(Vendedor, MetaVendedor.vendedor_id == Vendedor.id)
                query = query.join(Supervisor, Vendedor.supervisor_id == Supervisor.id)
                query = query.filter(~Supervisor.pasta.in_(pastas_excluir))
    
    query = query.order_by(desc('qtd_vendedores_fora_meta'))
    
    resultados = query.all()
    
    return [
        {
            "industria": row.industria or "",
            "qtd_vendedores_fora_meta": int(row.qtd_vendedores_fora_meta) if row.qtd_vendedores_fora_meta else 0
        }
        for row in resultados
    ]


# ============================================================================
# Q4: ROTAS COM POSITIVAÇÃO DE INDÚSTRIA
# ============================================================================

def get_rotas_positivacao_industria(
    session: Session,
    industria: str,
    data_inicio: str,
    data_fim: str,
    filtros_behavior: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Retorna rotas com melhor/pior desempenho em positivação de clientes de uma indústria.
    
    Args:
        session: Sessão SQLAlchemy
        industria: Nome da indústria (ex.: "Mars", "Nissin")
        data_inicio: Data início (YYYY-MM-DD)
        data_fim: Data fim (YYYY-MM-DD)
        filtros_behavior: Filtros adicionais do Behavior Memory
        
    Returns:
        Lista de dicts com:
        - rota_id
        - total_clientes_ativos
        - clientes_positivados
        - positivacao_pct
    """
    data_inicio_dt = datetime.strptime(data_inicio, "%Y-%m-%d").date()
    data_fim_dt = datetime.strptime(data_fim, "%Y-%m-%d").date()
    
    # Clientes ativos por rota
    clientes_ativos_subq = (
        session.query(
            Cliente.id.label('cliente_id'),
            Cliente.rota_rca.label('rota_id')
        )
        .filter(Cliente.ativo == True)
        .subquery()
    )
    
    # Clientes positivados (com pelo menos 1 venda da indústria)
    # Conforme Q4 em ENGINEERING_QUERIES.md:
    # - Deve usar fato_vendas_detalhado JOIN dim_produto ON p.industria = :industria
    clientes_positivados_subq = (
        session.query(
            func.distinct(Venda.cliente_id).label('cliente_id')
        )
        .join(DimProduto, Venda.produto_id == DimProduto.id)
        .filter(
            and_(
                Venda.data_venda >= data_inicio_dt,
                Venda.data_venda <= data_fim_dt,
                DimProduto.industria == industria
            )
        )
        .subquery()
    )
    
    # Agregação por rota
    query = (
        session.query(
            clientes_ativos_subq.c.rota_id,
            func.count(func.distinct(clientes_ativos_subq.c.cliente_id)).label('total_clientes_ativos'),
            func.count(
                func.distinct(
                    case(
                        (clientes_positivados_subq.c.cliente_id.isnot(None), clientes_ativos_subq.c.cliente_id),
                        else_=None
                    )
                )
            ).label('clientes_positivados')
        )
        .outerjoin(
            clientes_positivados_subq,
            clientes_ativos_subq.c.cliente_id == clientes_positivados_subq.c.cliente_id
        )
        .group_by(clientes_ativos_subq.c.rota_id)
    )
    
    # Aplica filtros do Behavior Memory
    if filtros_behavior:
        if "excluir_rotas" in filtros_behavior:
            rotas_excluir = filtros_behavior["excluir_rotas"]
            if isinstance(rotas_excluir, list) and rotas_excluir:
                query = query.filter(~clientes_ativos_subq.c.rota_id.in_(rotas_excluir))
    
    resultados = query.all()
    
    # Calcula percentual de positivação
    return [
        {
            "rota_id": row.rota_id or "",
            "total_clientes_ativos": int(row.total_clientes_ativos) if row.total_clientes_ativos else 0,
            "clientes_positivados": int(row.clientes_positivados) if row.clientes_positivados else 0,
            "positivacao_pct": (
                (row.clientes_positivados * 100.0 / row.total_clientes_ativos)
                if row.total_clientes_ativos and row.total_clientes_ativos > 0
                else 0.0
            )
        }
        for row in resultados
    ]


# ============================================================================
# Q5: ITENS COM BAIXA MÉDIA MENSAL
# ============================================================================

def get_itens_baixa_media_mensal(
    session: Session,
    meses_janela: int = 12,
    limite_media: float = 10.0,
    data_referencia: Optional[str] = None,
    filtros_behavior: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Retorna itens com média de vendas mensal menor que o limite.
    
    Args:
        session: Sessão SQLAlchemy
        meses_janela: Janela de meses para calcular média (padrão: 12)
        limite_media: Limite de média mensal (padrão: 10.0)
        data_referencia: Data de referência (YYYY-MM-DD) ou None para hoje
        filtros_behavior: Filtros adicionais do Behavior Memory
        
    Returns:
        Lista de dicts com:
        - produto_id
        - descricao
        - sku
        - industria
        - qtd_total
        - meses_com_venda
        - media_mensal
    """
    if data_referencia:
        ref_date = datetime.strptime(data_referencia, "%Y-%m-%d").date()
    else:
        ref_date = datetime.now().date()
    
    # Calcula data início (N meses atrás) usando datas reais
    # Conforme ENGINEERING_QUERIES.md: usar datas reais, não aproximação de dias
    data_inicio = ref_date - relativedelta(months=meses_janela)
    
    # Agregação por produto e mês
    # Conforme Q5 em ENGINEERING_QUERIES.md: usar fato_vendas_detalhado JOIN dim_produto
    vendas_periodo_subq = (
        session.query(
            DimProduto.produto_id,
            extract('year', Venda.data_venda).label('ano'),
            extract('month', Venda.data_venda).label('mes'),
            func.sum(Venda.qtd_caixas).label('qtd_mes')
        )
        .join(DimProduto, Venda.produto_id == DimProduto.id)
        .filter(
            and_(
                Venda.data_venda >= data_inicio,
                Venda.data_venda <= ref_date
            )
        )
        .group_by(DimProduto.produto_id, extract('year', Venda.data_venda), extract('month', Venda.data_venda))
        .subquery()
    )
    
    # Agregação final por produto
    # Conforme Q5 em ENGINEERING_QUERIES.md: conta meses distintos com venda
    # SQLite não suporta distinct() com tuplas, então contamos meses distintos diretamente
    # Abordagem compatível: agrupar por produto e contar linhas (cada linha = 1 mês)
    agregado_subq = (
        session.query(
            vendas_periodo_subq.c.produto_id,
            func.count(vendas_periodo_subq.c.produto_id).label('meses_com_venda'),
            func.sum(vendas_periodo_subq.c.qtd_mes).label('qtd_total')
        )
        .group_by(vendas_periodo_subq.c.produto_id)
        .subquery()
    )
    
    # Query principal - usa dim_produto para descricao, sku e industria
    query = (
        session.query(
            agregado_subq.c.produto_id,
            DimProduto.descricao,
            DimProduto.sku,
            DimProduto.industria,
            agregado_subq.c.qtd_total,
            agregado_subq.c.meses_com_venda,
            case(
                (agregado_subq.c.meses_com_venda > 0,
                 agregado_subq.c.qtd_total * 1.0 / agregado_subq.c.meses_com_venda),
                else_=0
            ).label('media_mensal')
        )
        .join(DimProduto, agregado_subq.c.produto_id == DimProduto.produto_id)
        .group_by(
            agregado_subq.c.produto_id,
            DimProduto.descricao,
            DimProduto.sku,
            DimProduto.industria,
            agregado_subq.c.qtd_total,
            agregado_subq.c.meses_com_venda
        )
        .having(
            case(
                (agregado_subq.c.meses_com_venda > 0,
                 agregado_subq.c.qtd_total * 1.0 / agregado_subq.c.meses_com_venda),
                else_=0
            ) < limite_media
        )
    )
    
    query = query.order_by(asc('media_mensal'))
    
    resultados = query.all()
    
    return [
        {
            "produto_id": row.produto_id or "",
            "descricao": row.descricao or "",
            "sku": row.sku or "",
            "industria": row.industria or "",
            "qtd_total": int(row.qtd_total) if row.qtd_total else 0,
            "meses_com_venda": int(row.meses_com_venda) if row.meses_com_venda else 0,
            "media_mensal": float(row.media_mensal) if row.media_mensal else 0.0
        }
        for row in resultados
    ]


# ============================================================================
# Q6: CLIENTES SEM RECOMPRA DE SKU
# ============================================================================

def get_clientes_sem_recompra_sku(
    session: Session,
    sku: str,
    meses_janela: int = 6,
    data_referencia: Optional[str] = None,
    filtros_behavior: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Retorna clientes que compraram SKU mas não realizaram recompra.
    
    Args:
        session: Sessão SQLAlchemy
        sku: Descrição ou código do SKU
        meses_janela: Janela de meses (padrão: 6)
        data_referencia: Data de referência (YYYY-MM-DD) ou None para hoje
        filtros_behavior: Filtros adicionais do Behavior Memory
        
    Returns:
        Lista de dicts com:
        - cliente_id
        - nome
        - segmento
        - rota_id
        - qtd_compras
        - primeira_compra
        - ultima_compra
    """
    if data_referencia:
        ref_date = datetime.strptime(data_referencia, "%Y-%m-%d").date()
    else:
        ref_date = datetime.now().date()
    
    # Calcula data início usando datas reais
    data_inicio = ref_date - relativedelta(months=meses_janela)
    
    # Vendas do SKU no período
    # Conforme Q6 em ENGINEERING_QUERIES.md:
    # - Deve usar fato_vendas_detalhado JOIN dim_produto ON p.sku = :sku
    # - Usa comparação exata (não ILIKE) conforme blueprint
    vendas_sku_subq = (
        session.query(
            Venda.cliente_id,
            Venda.data_venda
        )
        .join(DimProduto, Venda.produto_id == DimProduto.id)
        .filter(
            and_(
                Venda.data_venda >= data_inicio,
                Venda.data_venda <= ref_date,
                DimProduto.sku == sku  # Comparação exata conforme blueprint
            )
        )
        .subquery()
    )
    
    # Agregação por cliente
    agregado_subq = (
        session.query(
            vendas_sku_subq.c.cliente_id,
            func.count().label('qtd_compras'),
            func.min(vendas_sku_subq.c.data_venda).label('primeira_compra'),
            func.max(vendas_sku_subq.c.data_venda).label('ultima_compra')
        )
        .group_by(vendas_sku_subq.c.cliente_id)
        .having(func.count() == 1)  # Apenas 1 compra
        .subquery()
    )
    
    # Query principal
    query = (
        session.query(
            agregado_subq.c.cliente_id,
            Cliente.nome,
            Cliente.segmento_venda.label('segmento'),
            Cliente.rota_rca.label('rota_id'),
            agregado_subq.c.qtd_compras,
            agregado_subq.c.primeira_compra,
            agregado_subq.c.ultima_compra
        )
        .join(Cliente, agregado_subq.c.cliente_id == Cliente.id)
    )
    
    # Aplica filtros do Behavior Memory
    if filtros_behavior:
        if "excluir_pastas" in filtros_behavior:
            pastas_excluir = filtros_behavior["excluir_pastas"]
            if isinstance(pastas_excluir, list) and pastas_excluir:
                query = query.join(Supervisor, Cliente.supervisor_id == Supervisor.id)
                query = query.filter(~Supervisor.pasta.in_(pastas_excluir))
    
    query = query.order_by(agregado_subq.c.primeira_compra)
    
    resultados = query.all()
    
    return [
        {
            "cliente_id": row.cliente_id,
            "nome": row.nome or "",
            "segmento": row.segmento or "",
            "rota_id": row.rota_id or "",
            "qtd_compras": int(row.qtd_compras) if row.qtd_compras else 0,
            "primeira_compra": row.primeira_compra.isoformat() if row.primeira_compra else None,
            "ultima_compra": row.ultima_compra.isoformat() if row.ultima_compra else None
        }
        for row in resultados
    ]


# ============================================================================
# Q7: CLIENTES SEGMENTO SEM SKU NO PERÍODO
# ============================================================================

def get_clientes_segmento_sem_sku_no_periodo(
    session: Session,
    segmento: str,
    sku: str,
    data_inicio: str,
    data_fim: str,
    filtros_behavior: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Retorna clientes de um segmento que não compraram um SKU no período.
    
    Args:
        session: Sessão SQLAlchemy
        segmento: Segmento do cliente (ex.: "conveniencia")
        sku: Descrição ou código do SKU
        data_inicio: Data início (YYYY-MM-DD)
        data_fim: Data fim (YYYY-MM-DD)
        filtros_behavior: Filtros adicionais do Behavior Memory
        
    Returns:
        Lista de dicts com:
        - cliente_id
        - nome
        - rota_id
    """
    data_inicio_dt = datetime.strptime(data_inicio, "%Y-%m-%d").date()
    data_fim_dt = datetime.strptime(data_fim, "%Y-%m-%d").date()
    
    # Clientes do segmento
    clientes_segmento_subq = (
        session.query(
            Cliente.id.label('cliente_id'),
            Cliente.nome,
            Cliente.rota_rca.label('rota_id')
        )
        .filter(Cliente.segmento_venda == segmento)
        .subquery()
    )
    
    # Clientes que compraram o SKU
    # Conforme Q7/Q9 em ENGINEERING_QUERIES.md: usar dim_produto
    clientes_com_sku_subq = (
        session.query(
            func.distinct(Venda.cliente_id).label('cliente_id')
        )
        .join(DimProduto, Venda.produto_id == DimProduto.id)
        .filter(
            and_(
                Venda.data_venda >= data_inicio_dt,
                Venda.data_venda <= data_fim_dt,
                DimProduto.sku == sku  # Comparação exata conforme blueprint
            )
        )
        .subquery()
    )
    
    # Query principal (clientes do segmento SEM o SKU)
    query = (
        session.query(
            clientes_segmento_subq.c.cliente_id,
            clientes_segmento_subq.c.nome,
            clientes_segmento_subq.c.rota_id
        )
        .outerjoin(
            clientes_com_sku_subq,
            clientes_segmento_subq.c.cliente_id == clientes_com_sku_subq.c.cliente_id
        )
        .filter(clientes_com_sku_subq.c.cliente_id.is_(None))
    )
    
    # Aplica filtros do Behavior Memory
    if filtros_behavior:
        if "excluir_pastas" in filtros_behavior:
            pastas_excluir = filtros_behavior["excluir_pastas"]
            if isinstance(pastas_excluir, list) and pastas_excluir:
                query = query.join(Cliente, clientes_segmento_subq.c.cliente_id == Cliente.id)
                query = query.join(Supervisor, Cliente.supervisor_id == Supervisor.id)
                query = query.filter(~Supervisor.pasta.in_(pastas_excluir))
    
    query = query.order_by(clientes_segmento_subq.c.nome)
    
    resultados = query.all()
    
    return [
        {
            "cliente_id": row.cliente_id,
            "nome": row.nome or "",
            "rota_id": row.rota_id or ""
        }
        for row in resultados
    ]


# ============================================================================
# Q8: CLIENTES COM UMA UNIDADE DE INDÚSTRIA NO MÊS
# ============================================================================

def get_clientes_uma_unidade_industria_mes(
    session: Session,
    industria: str,
    ano: int,
    mes: int,
    filtros_behavior: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Retorna clientes com somente 1 unidade vendida de uma indústria no mês.
    
    Args:
        session: Sessão SQLAlchemy
        industria: Nome da indústria (ex.: "AB Brasil")
        ano: Ano (ex.: 2025)
        mes: Mês (ex.: 10)
        filtros_behavior: Filtros adicionais do Behavior Memory
        
    Returns:
        Lista de dicts com:
        - cliente_id
        - nome
        - segmento
        - rota_id
        - qtd_total
    """
    # Conforme Q8 em ENGINEERING_QUERIES.md:
    # - Deve usar fato_vendas_detalhado JOIN dim_produto ON p.industria = :industria
    query = (
        session.query(
            Venda.cliente_id,
            Cliente.nome,
            Cliente.segmento_venda.label('segmento'),
            Cliente.rota_rca.label('rota_id'),
            func.sum(Venda.qtd_unidades).label('qtd_total')
        )
        .join(Cliente, Venda.cliente_id == Cliente.id)
        .join(DimProduto, Venda.produto_id == DimProduto.id)
        .filter(
            and_(
                extract('year', Venda.data_venda) == ano,
                extract('month', Venda.data_venda) == mes,
                DimProduto.industria == industria
            )
        )
        .group_by(Venda.cliente_id, Cliente.nome, Cliente.segmento_venda, Cliente.rota_rca)
        .having(func.sum(Venda.qtd_unidades) == 1)
    )
    
    # Aplica filtros do Behavior Memory
    if filtros_behavior:
        if "excluir_pastas" in filtros_behavior:
            pastas_excluir = filtros_behavior["excluir_pastas"]
            if isinstance(pastas_excluir, list) and pastas_excluir:
                query = query.join(Supervisor, Cliente.supervisor_id == Supervisor.id)
                query = query.filter(~Supervisor.pasta.in_(pastas_excluir))
    
    query = query.order_by(Cliente.nome)
    
    resultados = query.all()
    
    return [
        {
            "cliente_id": row.cliente_id,
            "nome": row.nome or "",
            "segmento": row.segmento or "",
            "rota_id": row.rota_id or "",
            "qtd_total": int(row.qtd_total) if row.qtd_total else 0
        }
        for row in resultados
    ]


# ============================================================================
# Q9/Q10/Q11: CLIENTES SEM SKU NO PERÍODO
# ============================================================================

def get_clientes_sem_sku_no_periodo(
    session: Session,
    sku: str,
    data_inicio: str,
    data_fim: str,
    filtros_behavior: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Retorna clientes ativos que não tiveram positivação de um SKU no período.
    
    Args:
        session: Sessão SQLAlchemy
        sku: Descrição ou código do SKU
        data_inicio: Data início (YYYY-MM-DD)
        data_fim: Data fim (YYYY-MM-DD)
        filtros_behavior: Filtros adicionais do Behavior Memory
        
    Returns:
        Lista de dicts com:
        - cliente_id
        - nome
        - rota_id
    """
    data_inicio_dt = datetime.strptime(data_inicio, "%Y-%m-%d").date()
    data_fim_dt = datetime.strptime(data_fim, "%Y-%m-%d").date()
    
    # Clientes ativos
    clientes_ativos_subq = (
        session.query(
            Cliente.id.label('cliente_id'),
            Cliente.nome,
            Cliente.rota_rca.label('rota_id')
        )
        .filter(Cliente.ativo == True)
        .subquery()
    )
    
    # Clientes que compraram o SKU
    # Conforme Q7/Q9 em ENGINEERING_QUERIES.md: usar dim_produto
    clientes_com_sku_subq = (
        session.query(
            func.distinct(Venda.cliente_id).label('cliente_id')
        )
        .join(DimProduto, Venda.produto_id == DimProduto.id)
        .filter(
            and_(
                Venda.data_venda >= data_inicio_dt,
                Venda.data_venda <= data_fim_dt,
                DimProduto.sku == sku  # Comparação exata conforme blueprint
            )
        )
        .subquery()
    )
    
    # Query principal (clientes ativos SEM o SKU)
    query = (
        session.query(
            clientes_ativos_subq.c.cliente_id,
            clientes_ativos_subq.c.nome,
            clientes_ativos_subq.c.rota_id
        )
        .outerjoin(
            clientes_com_sku_subq,
            clientes_ativos_subq.c.cliente_id == clientes_com_sku_subq.c.cliente_id
        )
        .filter(clientes_com_sku_subq.c.cliente_id.is_(None))
    )
    
    # Aplica filtros do Behavior Memory
    if filtros_behavior:
        if "excluir_pastas" in filtros_behavior:
            pastas_excluir = filtros_behavior["excluir_pastas"]
            if isinstance(pastas_excluir, list) and pastas_excluir:
                query = query.join(Cliente, clientes_ativos_subq.c.cliente_id == Cliente.id)
                query = query.join(Supervisor, Cliente.supervisor_id == Supervisor.id)
                query = query.filter(~Supervisor.pasta.in_(pastas_excluir))
    
    query = query.order_by(clientes_ativos_subq.c.rota_id, clientes_ativos_subq.c.nome)
    
    resultados = query.all()
    
    return [
        {
            "cliente_id": row.cliente_id,
            "nome": row.nome or "",
            "rota_id": row.rota_id or ""
        }
        for row in resultados
    ]


# ============================================================================
# Q12: CLIENTES COM MIX MÍNIMO DE NISSIN
# ============================================================================

def get_clientes_mix_minimo_nissin_mes(
    session: Session,
    ano: int,
    mes: int,
    filtros_behavior: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Retorna clientes que atingiram o mix mínimo de Nissin no mês.
    
    Mix Mínimo: itens 2257 / 2087 / 2086 + 1 item entre (2101 / 2102 / 2103)
    
    Args:
        session: Sessão SQLAlchemy
        ano: Ano (ex.: 2025)
        mes: Mês (ex.: 10)
        filtros_behavior: Filtros adicionais do Behavior Memory
        
    Returns:
        Lista de dicts com:
        - cliente_id
        - nome
        - rota_id
    """
    # Conforme Q12 em ENGINEERING_QUERIES.md:
    # - Mix Mínimo: itens 2257 / 2087 / 2086 + 1 item entre (2101 / 2102 / 2103)
    # - Deve usar fato_vendas_detalhado JOIN dim_produto ON p.industria = 'Nissin' AND p.sku IN (...)
    vendas_nissin_subq = (
        session.query(
            Venda.cliente_id,
            DimProduto.sku,
            func.sum(Venda.qtd_caixas).label('qtd')
        )
        .join(DimProduto, Venda.produto_id == DimProduto.id)
        .filter(
            and_(
                extract('year', Venda.data_venda) == ano,
                extract('month', Venda.data_venda) == mes,
                DimProduto.industria == 'Nissin',
                DimProduto.sku.in_(['2257', '2087', '2086', '2101', '2102', '2103'])  # SKUs exatos do blueprint
            )
        )
        .group_by(Venda.cliente_id, DimProduto.sku)
        .subquery()
    )
    
    # Pivot: verifica quais SKUs cada cliente tem
    pivot_subq = (
        session.query(
            vendas_nissin_subq.c.cliente_id,
            func.sum(case((vendas_nissin_subq.c.sku == '2257', 1), else_=0)).label('tem_2257'),
            func.sum(case((vendas_nissin_subq.c.sku == '2087', 1), else_=0)).label('tem_2087'),
            func.sum(case((vendas_nissin_subq.c.sku == '2086', 1), else_=0)).label('tem_2086'),
            func.sum(
                case(
                    (vendas_nissin_subq.c.sku.in_(['2101', '2102', '2103']), 1),
                    else_=0
                )
            ).label('tem_complementar')
        )
        .group_by(vendas_nissin_subq.c.cliente_id)
        .subquery()
    )
    
    # Clientes com mix OK
    clientes_mix_ok_subq = (
        session.query(pivot_subq.c.cliente_id)
        .filter(
            and_(
                pivot_subq.c.tem_2257 > 0,
                pivot_subq.c.tem_2087 > 0,
                pivot_subq.c.tem_2086 > 0,
                pivot_subq.c.tem_complementar > 0
            )
        )
        .subquery()
    )
    
    # Query principal
    query = (
        session.query(
            clientes_mix_ok_subq.c.cliente_id,
            Cliente.nome,
            Cliente.rota_rca.label('rota_id')
        )
        .join(Cliente, clientes_mix_ok_subq.c.cliente_id == Cliente.id)
    )
    
    # Aplica filtros do Behavior Memory
    if filtros_behavior:
        if "excluir_pastas" in filtros_behavior:
            pastas_excluir = filtros_behavior["excluir_pastas"]
            if isinstance(pastas_excluir, list) and pastas_excluir:
                query = query.join(Supervisor, Cliente.supervisor_id == Supervisor.id)
                query = query.filter(~Supervisor.pasta.in_(pastas_excluir))
    
    query = query.order_by(Cliente.rota_rca, Cliente.nome)
    
    resultados = query.all()
    
    return [
        {
            "cliente_id": row.cliente_id,
            "nome": row.nome or "",
            "rota_id": row.rota_id or ""
        }
        for row in resultados
    ]


# ============================================================================
# Q13: ROTAS COM DESEMPENHO MIX MÍNIMO NISSIN
# ============================================================================

def get_rotas_desempenho_mix_minimo_nissin_mes(
    session: Session,
    ano: int,
    mes: int,
    filtros_behavior: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Retorna rotas com melhor/pior desempenho no mix mínimo de Nissin.
    
    Args:
        session: Sessão SQLAlchemy
        ano: Ano (ex.: 2025)
        mes: Mês (ex.: 10)
        filtros_behavior: Filtros adicionais do Behavior Memory
        
    Returns:
        Lista de dicts com:
        - rota_id
        - total_clientes_ativos
        - clientes_mix_ok
        - pct_mix_ok
    """
    # Clientes ativos por rota
    clientes_ativos_subq = (
        session.query(
            Cliente.id.label('cliente_id'),
            Cliente.rota_rca.label('rota_id')
        )
        .filter(Cliente.ativo == True)
        .subquery()
    )
    
    # Clientes com mix OK (reutiliza lógica de Q12)
    # Conforme Q13 em ENGINEERING_QUERIES.md: usar dim_produto
    vendas_nissin_subq = (
        session.query(
            Venda.cliente_id,
            DimProduto.sku
        )
        .join(DimProduto, Venda.produto_id == DimProduto.id)
        .filter(
            and_(
                extract('year', Venda.data_venda) == ano,
                extract('month', Venda.data_venda) == mes,
                DimProduto.industria == 'Nissin',
                DimProduto.sku.in_(['2257', '2087', '2086', '2101', '2102', '2103'])
            )
        )
        .distinct()
        .subquery()
    )
    
    pivot_subq = (
        session.query(
            vendas_nissin_subq.c.cliente_id,
            func.sum(case((vendas_nissin_subq.c.sku == '2257', 1), else_=0)).label('tem_2257'),
            func.sum(case((vendas_nissin_subq.c.sku == '2087', 1), else_=0)).label('tem_2087'),
            func.sum(case((vendas_nissin_subq.c.sku == '2086', 1), else_=0)).label('tem_2086'),
            func.sum(
                case(
                    (vendas_nissin_subq.c.sku.in_(['2101', '2102', '2103']), 1),
                    else_=0
                )
            ).label('tem_complementar')
        )
        .group_by(vendas_nissin_subq.c.cliente_id)
        .subquery()
    )
    
    clientes_mix_ok_subq = (
        session.query(pivot_subq.c.cliente_id)
        .filter(
            and_(
                pivot_subq.c.tem_2257 > 0,
                pivot_subq.c.tem_2087 > 0,
                pivot_subq.c.tem_2086 > 0,
                pivot_subq.c.tem_complementar > 0
            )
        )
        .subquery()
    )
    
    # Agregação por rota
    query = (
        session.query(
            clientes_ativos_subq.c.rota_id,
            func.count(func.distinct(clientes_ativos_subq.c.cliente_id)).label('total_clientes_ativos'),
            func.count(
                func.distinct(
                    case(
                        (clientes_mix_ok_subq.c.cliente_id.isnot(None), clientes_ativos_subq.c.cliente_id),
                        else_=None
                    )
                )
            ).label('clientes_mix_ok')
        )
        .outerjoin(
            clientes_mix_ok_subq,
            clientes_ativos_subq.c.cliente_id == clientes_mix_ok_subq.c.cliente_id
        )
        .group_by(clientes_ativos_subq.c.rota_id)
    )
    
    # Aplica filtros do Behavior Memory
    if filtros_behavior:
        if "excluir_rotas" in filtros_behavior:
            rotas_excluir = filtros_behavior["excluir_rotas"]
            if isinstance(rotas_excluir, list) and rotas_excluir:
                query = query.filter(~clientes_ativos_subq.c.rota_id.in_(rotas_excluir))
    
    resultados = query.all()
    
    # Calcula percentual
    return [
        {
            "rota_id": row.rota_id or "",
            "total_clientes_ativos": int(row.total_clientes_ativos) if row.total_clientes_ativos else 0,
            "clientes_mix_ok": int(row.clientes_mix_ok) if row.clientes_mix_ok else 0,
            "pct_mix_ok": (
                (row.clientes_mix_ok * 100.0 / row.total_clientes_ativos)
                if row.total_clientes_ativos and row.total_clientes_ativos > 0
                else 0.0
            )
        }
        for row in resultados
    ]

