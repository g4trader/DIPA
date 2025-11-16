#!/usr/bin/env python3
"""
ETL para construir tabelas de Analytics.

Este script popula as tabelas analytics_* com métricas pré-calculadas
para acelerar consultas e reduzir queries pesadas em tempo real.

Uso:
    DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db python -m scripts.build_analytics --mes-ano 2025-08
    DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db python -m scripts.build_analytics  # Usa mês anterior
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from decimal import Decimal

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from sqlalchemy import func, and_, or_, text
from sqlalchemy.orm import Session

from src.config import config
from src.dw.connection import init_db, get_db_session
from src.dw.models import (
    Vendedor, Cliente, Venda, MetaVendedor, Supervisor
)
from src.dw.models_analytics import (
    AnalyticsVendedorMes, AnalyticsClienteMes, 
    AnalyticsProdutoMes, AnalyticsAlerta
)
from src.ml.features import (
    calcular_variacao_faturamento_cliente,
    calcular_variacao_faturamento_produto,
    calcular_trend_atingimento_vendedor
)
from src.ml.scoring import (
    calcular_churn_score, classificar_churn_flag,
    calcular_meta_risk_score, classificar_meta_risk_flag,
    calcular_queda_score, classificar_queda_flag
)

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_mes_ano(mes_ano_str: str) -> tuple:
    """
    Parse mes_ano string (YYYY-MM) para (ano, mes).
    
    Args:
        mes_ano_str: String no formato "YYYY-MM"
        
    Returns:
        tuple: (ano, mes) como inteiros
    """
    try:
        ano, mes = mes_ano_str.split("-")
        return int(ano), int(mes)
    except ValueError:
        raise ValueError(f"Formato inválido de mes_ano: {mes_ano_str}. Use YYYY-MM")


def get_mes_anterior() -> str:
    """
    Retorna o mes_ano do mês anterior ao atual.
    
    Returns:
        str: mes_ano no formato "YYYY-MM"
    """
    hoje = datetime.now()
    primeiro_dia_mes_atual = hoje.replace(day=1)
    ultimo_dia_mes_anterior = primeiro_dia_mes_atual - timedelta(days=1)
    return ultimo_dia_mes_anterior.strftime("%Y-%m")


def build_analytics_vendedor_mes(session: Session, mes_ano: Optional[str] = None) -> int:
    """
    Constrói analytics agregado por vendedor e mês.
    
    Args:
        session: Sessão SQLAlchemy
        mes_ano: Mês/ano no formato "YYYY-MM" (opcional, usa mês anterior se None)
        
    Returns:
        int: Número de registros criados/atualizados
    """
    if mes_ano is None:
        mes_ano = get_mes_anterior()
    
    ano, mes = parse_mes_ano(mes_ano)
    
    logger.info(f"📊 Construindo analytics_vendedor_mes para {mes_ano}...")
    
    # Detecta tipo de banco para usar função de data correta
    db_type = config.database.db_type
    
    # Query para agregar metas por vendedor
    if db_type == "sqlite":
        # SQLite usa strftime
        metas_query = session.query(
            MetaVendedor.vendedor_id,
            func.sum(MetaVendedor.valor_meta).label('meta_total'),
            func.max(Vendedor.nome).label('vendedor_nome'),
            func.max(Vendedor.supervisor_id).label('supervisor_id')
        ).join(
            Vendedor, MetaVendedor.vendedor_id == Vendedor.id
        ).filter(
            MetaVendedor.mes_ano == mes_ano
        ).group_by(
            MetaVendedor.vendedor_id
        ).subquery()
    else:
        # PostgreSQL usa extract
        metas_query = session.query(
            MetaVendedor.vendedor_id,
            func.sum(MetaVendedor.valor_meta).label('meta_total'),
            func.max(Vendedor.nome).label('vendedor_nome'),
            func.max(Vendedor.supervisor_id).label('supervisor_id')
        ).join(
            Vendedor, MetaVendedor.vendedor_id == Vendedor.id
        ).filter(
            MetaVendedor.mes_ano == mes_ano
        ).group_by(
            MetaVendedor.vendedor_id
        ).subquery()
    
    # Query para agregar vendas por vendedor
    if db_type == "sqlite":
        vendas_query = session.query(
            Venda.vendedor_id,
            func.sum(Venda.valor_total_liquido).label('realizado_total'),
            func.count(func.distinct(Venda.cliente_id)).label('qtd_clientes_positivados'),
            func.count(func.distinct(Venda.codigo_produto)).label('qtd_skus')
        ).filter(
            func.strftime("%Y", Venda.data_venda) == str(ano),
            func.strftime("%m", Venda.data_venda) == f"{mes:02d}"
        ).group_by(
            Venda.vendedor_id
        ).subquery()
    else:
        from sqlalchemy import extract
        vendas_query = session.query(
            Venda.vendedor_id,
            func.sum(Venda.valor_total_liquido).label('realizado_total'),
            func.count(func.distinct(Venda.cliente_id)).label('qtd_clientes_positivados'),
            func.count(func.distinct(Venda.codigo_produto)).label('qtd_skus')
        ).filter(
            extract('year', Venda.data_venda) == ano,
            extract('month', Venda.data_venda) == mes
        ).group_by(
            Venda.vendedor_id
        ).subquery()
    
    # Calcula churn de clientes (clientes que compraram no mês anterior mas não neste)
    mes_anterior_obj = datetime(ano, mes, 1) - timedelta(days=1)
    mes_anterior_str = mes_anterior_obj.strftime("%Y-%m")
    mes_anterior_ano, mes_anterior_mes = parse_mes_ano(mes_anterior_str)
    
    if db_type == "sqlite":
        # Clientes que compraram no mês anterior
        clientes_mes_anterior = session.query(
            Venda.vendedor_id,
            Venda.cliente_id
        ).filter(
            func.strftime("%Y", Venda.data_venda) == str(mes_anterior_ano),
            func.strftime("%m", Venda.data_venda) == f"{mes_anterior_mes:02d}"
        ).distinct().subquery()
        
        # Clientes que compraram neste mês
        clientes_mes_atual = session.query(
            Venda.vendedor_id,
            Venda.cliente_id
        ).filter(
            func.strftime("%Y", Venda.data_venda) == str(ano),
            func.strftime("%m", Venda.data_venda) == f"{mes:02d}"
        ).distinct().subquery()
    else:
        from sqlalchemy import extract
        clientes_mes_anterior = session.query(
            Venda.vendedor_id,
            Venda.cliente_id
        ).filter(
            extract('year', Venda.data_venda) == mes_anterior_ano,
            extract('month', Venda.data_venda) == mes_anterior_mes
        ).distinct().subquery()
        
        clientes_mes_atual = session.query(
            Venda.vendedor_id,
            Venda.cliente_id
        ).filter(
            extract('year', Venda.data_venda) == ano,
            extract('month', Venda.data_venda) == mes
        ).distinct().subquery()
    
    # Churn: clientes que compraram no mês anterior mas não neste
    churn_query = session.query(
        clientes_mes_anterior.c.vendedor_id,
        func.count(clientes_mes_anterior.c.cliente_id).label('qtd_clientes_churn')
    ).outerjoin(
        clientes_mes_atual,
        and_(
            clientes_mes_anterior.c.vendedor_id == clientes_mes_atual.c.vendedor_id,
            clientes_mes_anterior.c.cliente_id == clientes_mes_atual.c.cliente_id
        )
    ).filter(
        clientes_mes_atual.c.cliente_id.is_(None)
    ).group_by(
        clientes_mes_anterior.c.vendedor_id
    ).subquery()
    
    # Busca todos os vendedores únicos (de metas e vendas)
    vendedores_metas_ids = {row.vendedor_id for row in session.query(metas_query.c.vendedor_id).all()}
    vendedores_vendas_ids = {row.vendedor_id for row in session.query(vendas_query.c.vendedor_id).all()}
    vendedores_unicos_ids = vendedores_metas_ids | vendedores_vendas_ids
    
    # Para cada vendedor, busca dados de todas as fontes
    resultado = []
    for vendedor_id in vendedores_unicos_ids:
        # Busca dados de meta
        meta_row = session.query(metas_query).filter(
            metas_query.c.vendedor_id == vendedor_id
        ).first()
        
        # Busca dados de vendas
        venda_row = session.query(vendas_query).filter(
            vendas_query.c.vendedor_id == vendedor_id
        ).first()
        
        # Busca dados de churn
        churn_row = session.query(churn_query).filter(
            churn_query.c.vendedor_id == vendedor_id
        ).first()
        
        # Combina dados
        resultado.append({
            'vendedor_id': vendedor_id,
            'vendedor_nome': meta_row.vendedor_nome if meta_row else '',
            'supervisor_id': meta_row.supervisor_id if meta_row else None,
            'meta_total': float(meta_row.meta_total) if meta_row else 0,
            'realizado_total': float(venda_row.realizado_total) if venda_row else 0,
            'qtd_clientes_positivados': venda_row.qtd_clientes_positivados if venda_row else 0,
            'qtd_skus': venda_row.qtd_skus if venda_row else 0,
            'qtd_clientes_churn': churn_row.qtd_clientes_churn if churn_row else 0,
        })
    
    # Calcula atingimento e gap, e faz UPSERT
    registros_processados = 0
    
    for row_data in resultado:
        meta_total = Decimal(str(row_data['meta_total'] or 0))
        realizado_total = Decimal(str(row_data['realizado_total'] or 0))
        
        # Calcula atingimento (com tratamento de divisão por zero)
        if meta_total > 0:
            atingimento_pct = (realizado_total / meta_total) * 100
        else:
            atingimento_pct = None
        
        gap_valor = realizado_total - meta_total
        
        # Busca ou cria registro
        analytics = session.query(AnalyticsVendedorMes).filter(
            AnalyticsVendedorMes.vendedor_id == row_data['vendedor_id'],
            AnalyticsVendedorMes.mes_ano == mes_ano
        ).first()
        
        if analytics is None:
            analytics = AnalyticsVendedorMes(
                vendedor_id=row_data['vendedor_id'],
                vendedor_nome=row_data['vendedor_nome'] or '',
                supervisor_id=row_data['supervisor_id'],
                mes_ano=mes_ano,
                ano=ano,
                mes=mes,
                meta_total=meta_total,
                realizado_total=realizado_total,
                atingimento_pct=atingimento_pct,
                gap_valor=gap_valor,
                qtd_clientes_positivados=row_data['qtd_clientes_positivados'] or 0,
                qtd_clientes_churn=row_data['qtd_clientes_churn'] or 0,
                qtd_skus=row_data['qtd_skus'] or 0
            )
            session.add(analytics)
        else:
            analytics.vendedor_nome = row_data['vendedor_nome'] or ''
            analytics.supervisor_id = row_data['supervisor_id']
            analytics.meta_total = meta_total
            analytics.realizado_total = realizado_total
            analytics.atingimento_pct = atingimento_pct
            analytics.gap_valor = gap_valor
            analytics.qtd_clientes_positivados = row_data['qtd_clientes_positivados'] or 0
            analytics.qtd_clientes_churn = row_data['qtd_clientes_churn'] or 0
            analytics.qtd_skus = row_data['qtd_skus'] or 0
        
        registros_processados += 1
    
    # Calcula ranking de atingimento (menor atingimento = pior rank)
    # Atualiza rank após inserir todos os registros
    session.flush()
    
    vendedores_ranking = session.query(
        AnalyticsVendedorMes.id,
        AnalyticsVendedorMes.atingimento_pct,
        AnalyticsVendedorMes.supervisor_id
    ).filter(
        AnalyticsVendedorMes.mes_ano == mes_ano
    ).order_by(
        AnalyticsVendedorMes.atingimento_pct.asc().nulls_last()
    ).all()
    
    # Atribui ranks (1 = pior, maior número = melhor)
    for rank, vendedor in enumerate(vendedores_ranking, start=1):
        analytics = session.query(AnalyticsVendedorMes).filter(
            AnalyticsVendedorMes.id == vendedor.id
        ).first()
        if analytics:
            analytics.rank_atingimento = rank
    
    session.commit()
    logger.info(f"✅ analytics_vendedor_mes: {registros_processados} registros processados para {mes_ano}")
    
    return registros_processados


def build_analytics_cliente_mes(session: Session, mes_ano: Optional[str] = None) -> int:
    """
    Constrói analytics agregado por cliente e mês.
    
    Args:
        session: Sessão SQLAlchemy
        mes_ano: Mês/ano no formato "YYYY-MM" (opcional, usa mês anterior se None)
        
    Returns:
        int: Número de registros criados/atualizados
    """
    if mes_ano is None:
        mes_ano = get_mes_anterior()
    
    ano, mes = parse_mes_ano(mes_ano)
    
    logger.info(f"📊 Construindo analytics_cliente_mes para {mes_ano}...")
    
    db_type = config.database.db_type
    
    # Query para agregar vendas por cliente
    if db_type == "sqlite":
        vendas_query = session.query(
            Venda.cliente_id,
            func.max(Cliente.nome).label('cliente_nome'),
            func.max(Venda.vendedor_id).label('vendedor_id'),  # Pega o vendedor mais frequente
            func.sum(Venda.valor_total_liquido).label('faturamento_total'),
            func.count(func.distinct(Venda.numero_nf)).label('qtd_compras'),
            func.max(Venda.data_venda).label('data_ultima_compra')
        ).join(
            Cliente, Venda.cliente_id == Cliente.id
        ).filter(
            func.strftime("%Y", Venda.data_venda) == str(ano),
            func.strftime("%m", Venda.data_venda) == f"{mes:02d}"
        ).group_by(
            Venda.cliente_id
        ).all()
    else:
        from sqlalchemy import extract
        vendas_query = session.query(
            Venda.cliente_id,
            func.max(Cliente.nome).label('cliente_nome'),
            func.max(Venda.vendedor_id).label('vendedor_id'),
            func.sum(Venda.valor_total_liquido).label('faturamento_total'),
            func.count(func.distinct(Venda.numero_nf)).label('qtd_compras'),
            func.max(Venda.data_venda).label('data_ultima_compra')
        ).join(
            Cliente, Venda.cliente_id == Cliente.id
        ).filter(
            extract('year', Venda.data_venda) == ano,
            extract('month', Venda.data_venda) == mes
        ).group_by(
            Venda.cliente_id
        ).all()
    
    registros_processados = 0
    ultimo_dia_mes = datetime(ano, mes, 28)  # Aproximação para calcular dias desde última compra
    
    for row in vendas_query:
        # Calcula dias desde última compra
        if row.data_ultima_compra:
            dias_desde_ultima_compra = (ultimo_dia_mes.date() - row.data_ultima_compra).days
        else:
            dias_desde_ultima_compra = None
        
        # Busca ou cria registro
        analytics = session.query(AnalyticsClienteMes).filter(
            AnalyticsClienteMes.cliente_id == row.cliente_id,
            AnalyticsClienteMes.mes_ano == mes_ano
        ).first()
        
        if analytics is None:
            analytics = AnalyticsClienteMes(
                cliente_id=row.cliente_id,
                cliente_nome=row.cliente_nome or '',
                vendedor_id=row.vendedor_id,
                mes_ano=mes_ano,
                ano=ano,
                mes=mes,
                faturamento_total=Decimal(str(row.faturamento_total or 0)),
                qtd_compras=row.qtd_compras or 0,
                dias_desde_ultima_compra=dias_desde_ultima_compra,
                churn_score=None  # Será preenchido na Fase 2 - ML
            )
            session.add(analytics)
        else:
            analytics.cliente_nome = row.cliente_nome or ''
            analytics.vendedor_id = row.vendedor_id
            analytics.faturamento_total = Decimal(str(row.faturamento_total or 0))
            analytics.qtd_compras = row.qtd_compras or 0
            analytics.dias_desde_ultima_compra = dias_desde_ultima_compra
        
        registros_processados += 1
    
    session.commit()
    logger.info(f"✅ analytics_cliente_mes: {registros_processados} registros processados para {mes_ano}")
    
    return registros_processados


def build_analytics_produto_mes(session: Session, mes_ano: Optional[str] = None) -> int:
    """
    Constrói analytics agregado por produto e mês.
    
    Args:
        session: Sessão SQLAlchemy
        mes_ano: Mês/ano no formato "YYYY-MM" (opcional, usa mês anterior se None)
        
    Returns:
        int: Número de registros criados/atualizados
    """
    if mes_ano is None:
        mes_ano = get_mes_anterior()
    
    ano, mes = parse_mes_ano(mes_ano)
    
    logger.info(f"📊 Construindo analytics_produto_mes para {mes_ano}...")
    
    db_type = config.database.db_type
    
    # Query para agregar vendas por produto
    if db_type == "sqlite":
        vendas_query = session.query(
            Venda.codigo_produto,
            func.max(Venda.desc_produto).label('desc_produto'),
            func.sum(Venda.valor_total_liquido).label('faturamento_total'),
            func.sum(Venda.qtd_unidades).label('qtd_vendida'),
            func.count(func.distinct(Venda.cliente_id)).label('qtd_clientes_ativos')
        ).filter(
            Venda.codigo_produto.isnot(None),
            func.strftime("%Y", Venda.data_venda) == str(ano),
            func.strftime("%m", Venda.data_venda) == f"{mes:02d}"
        ).group_by(
            Venda.codigo_produto
        ).all()
    else:
        from sqlalchemy import extract
        vendas_query = session.query(
            Venda.codigo_produto,
            func.max(Venda.desc_produto).label('desc_produto'),
            func.sum(Venda.valor_total_liquido).label('faturamento_total'),
            func.sum(Venda.qtd_unidades).label('qtd_vendida'),
            func.count(func.distinct(Venda.cliente_id)).label('qtd_clientes_ativos')
        ).filter(
            Venda.codigo_produto.isnot(None),
            extract('year', Venda.data_venda) == ano,
            extract('month', Venda.data_venda) == mes
        ).group_by(
            Venda.codigo_produto
        ).all()
    
    # Calcula faturamento total do mês para calcular participação
    faturamento_total_mes = sum(Decimal(str(row.faturamento_total or 0)) for row in vendas_query)
    
    registros_processados = 0
    
    for row in vendas_query:
        faturamento_produto = Decimal(str(row.faturamento_total or 0))
        
        # Calcula participação no faturamento
        if faturamento_total_mes > 0:
            participacao = (faturamento_produto / faturamento_total_mes) * 100
        else:
            participacao = None
        
        # Busca ou cria registro
        analytics = session.query(AnalyticsProdutoMes).filter(
            AnalyticsProdutoMes.codigo_produto == row.codigo_produto,
            AnalyticsProdutoMes.mes_ano == mes_ano
        ).first()
        
        if analytics is None:
            analytics = AnalyticsProdutoMes(
                codigo_produto=row.codigo_produto,
                desc_produto=row.desc_produto,
                mes_ano=mes_ano,
                ano=ano,
                mes=mes,
                faturamento_total=faturamento_produto,
                qtd_vendida=row.qtd_vendida or 0,
                qtd_clientes_ativos=row.qtd_clientes_ativos or 0,
                participacao_no_faturamento=participacao
            )
            session.add(analytics)
        else:
            analytics.desc_produto = row.desc_produto
            analytics.faturamento_total = faturamento_produto
            analytics.qtd_vendida = row.qtd_vendida or 0
            analytics.qtd_clientes_ativos = row.qtd_clientes_ativos or 0
            analytics.participacao_no_faturamento = participacao
        
        registros_processados += 1
    
    session.commit()
    logger.info(f"✅ analytics_produto_mes: {registros_processados} registros processados para {mes_ano}")
    
    return registros_processados


def aplicar_scores_clientes(session: Session, mes_ano: Optional[str] = None) -> int:
    """
    Aplica scores de churn para clientes em analytics_cliente_mes.
    
    Args:
        session: Sessão SQLAlchemy
        mes_ano: Mês/ano no formato "YYYY-MM" (opcional, usa mês anterior se None)
        
    Returns:
        int: Número de clientes processados
    """
    if mes_ano is None:
        mes_ano = get_mes_anterior()
    
    logger.info(f"📊 Aplicando scores de churn para clientes em {mes_ano}...")
    
    # Busca todos os clientes do mês
    clientes = session.query(AnalyticsClienteMes).filter(
        AnalyticsClienteMes.mes_ano == mes_ano
    ).all()
    
    registros_processados = 0
    
    for cliente in clientes:
        try:
            # Calcula features
            features = calcular_variacao_faturamento_cliente(
                session, cliente.cliente_id, mes_ano
            )
            
            faturamento_media_3m = features.get("faturamento_media_3m")
            variacao_pct_vs_3m = features.get("variacao_pct_vs_3m")
            
            # Calcula churn_score
            churn_score = calcular_churn_score(
                faturamento_atual=float(cliente.faturamento_total),
                faturamento_media_3m=faturamento_media_3m,
                dias_desde_ultima_compra=cliente.dias_desde_ultima_compra,
                variacao_pct_vs_3m=variacao_pct_vs_3m
            )
            
            # Classifica flag
            churn_flag = classificar_churn_flag(churn_score)
            
            # Atualiza campos
            cliente.churn_score = churn_score
            cliente.churn_flag = churn_flag
            if faturamento_media_3m is not None:
                cliente.faturamento_media_3m = Decimal(str(faturamento_media_3m))
            if variacao_pct_vs_3m is not None:
                cliente.variacao_pct_vs_3m = Decimal(str(variacao_pct_vs_3m))
            
            registros_processados += 1
        
        except Exception as e:
            logger.warning(f"Erro ao aplicar score para cliente {cliente.cliente_id}: {str(e)}")
            continue
    
    session.commit()
    logger.info(f"✅ Scores de churn aplicados: {registros_processados} clientes processados")
    
    return registros_processados


def aplicar_scores_vendedores(session: Session, mes_ano: Optional[str] = None) -> int:
    """
    Aplica scores de risco de meta para vendedores em analytics_vendedor_mes.
    
    Args:
        session: Sessão SQLAlchemy
        mes_ano: Mês/ano no formato "YYYY-MM" (opcional, usa mês anterior se None)
        
    Returns:
        int: Número de vendedores processados
    """
    if mes_ano is None:
        mes_ano = get_mes_anterior()
    
    logger.info(f"📊 Aplicando scores de risco de meta para vendedores em {mes_ano}...")
    
    # Busca todos os vendedores do mês
    vendedores = session.query(AnalyticsVendedorMes).filter(
        AnalyticsVendedorMes.mes_ano == mes_ano
    ).all()
    
    registros_processados = 0
    
    for vendedor in vendedores:
        try:
            # Calcula trend (opcional, pode ser None)
            trend = calcular_trend_atingimento_vendedor(
                session, vendedor.vendedor_id, mes_ano
            )
            tendencia = trend.get("tendencia")
            
            # Calcula meta_risk_score
            meta_risk_score = calcular_meta_risk_score(
                atingimento_pct=float(vendedor.atingimento_pct) if vendedor.atingimento_pct else None,
                gap_valor=float(vendedor.gap_valor) if vendedor.gap_valor else None,
                tendencia=tendencia
            )
            
            # Classifica flag
            meta_risk_flag = classificar_meta_risk_flag(meta_risk_score)
            
            # Atualiza campos
            vendedor.meta_risk_score = meta_risk_score
            vendedor.meta_risk_flag = meta_risk_flag
            
            registros_processados += 1
        
        except Exception as e:
            logger.warning(f"Erro ao aplicar score para vendedor {vendedor.vendedor_id}: {str(e)}")
            continue
    
    session.commit()
    logger.info(f"✅ Scores de risco de meta aplicados: {registros_processados} vendedores processados")
    
    return registros_processados


def aplicar_scores_produtos(session: Session, mes_ano: Optional[str] = None) -> int:
    """
    Aplica scores de queda para produtos em analytics_produto_mes.
    
    Args:
        session: Sessão SQLAlchemy
        mes_ano: Mês/ano no formato "YYYY-MM" (opcional, usa mês anterior se None)
        
    Returns:
        int: Número de produtos processados
    """
    if mes_ano is None:
        mes_ano = get_mes_anterior()
    
    logger.info(f"📊 Aplicando scores de queda para produtos em {mes_ano}...")
    
    # Busca todos os produtos do mês
    produtos = session.query(AnalyticsProdutoMes).filter(
        AnalyticsProdutoMes.mes_ano == mes_ano
    ).all()
    
    registros_processados = 0
    
    for produto in produtos:
        try:
            # Calcula features
            features = calcular_variacao_faturamento_produto(
                session, produto.codigo_produto, mes_ano
            )
            
            variacao_pct_vs_3m = features.get("variacao_pct_vs_3m")
            
            # Calcula queda_score
            queda_score = calcular_queda_score(
                variacao_pct_vs_3m=variacao_pct_vs_3m,
                qtd_vendida_atual=produto.qtd_vendida,
                qtd_media_3m=None  # Pode ser calculado se necessário
            )
            
            # Classifica flag
            queda_flag = classificar_queda_flag(queda_score)
            
            # Atualiza campos
            produto.queda_score = queda_score
            produto.queda_flag = queda_flag
            if variacao_pct_vs_3m is not None:
                produto.variacao_pct_vs_3m = Decimal(str(variacao_pct_vs_3m))
            
            registros_processados += 1
        
        except Exception as e:
            logger.warning(f"Erro ao aplicar score para produto {produto.codigo_produto}: {str(e)}")
            continue
    
    session.commit()
    logger.info(f"✅ Scores de queda aplicados: {registros_processados} produtos processados")
    
    return registros_processados


def build_analytics_alertas(session: Session, mes_ano: Optional[str] = None) -> int:
    """
    Constrói alertas baseados nas análises de analytics.
    
    Args:
        session: Sessão SQLAlchemy
        mes_ano: Mês/ano no formato "YYYY-MM" (opcional, usa mês anterior se None)
        
    Returns:
        int: Número de alertas criados
    """
    if mes_ano is None:
        mes_ano = get_mes_anterior()
    
    ano, mes = parse_mes_ano(mes_ano)
    
    logger.info(f"📊 Construindo analytics_alertas para {mes_ano}...")
    
    # Remove alertas antigos do mesmo mês
    session.query(AnalyticsAlerta).filter(
        AnalyticsAlerta.mes_ano == mes_ano
    ).delete()
    
    alertas_criados = 0
    
    # 1. Alertas de vendedores em risco (usando meta_risk_flag)
    vendedores_risco = session.query(AnalyticsVendedorMes).filter(
        AnalyticsVendedorMes.mes_ano == mes_ano,
        AnalyticsVendedorMes.meta_risk_flag == True
    ).order_by(
        AnalyticsVendedorMes.meta_risk_score.desc().nulls_last()
    ).limit(30).all()
    
    for vendedor in vendedores_risco:
        # Determina nível baseado no score
        score_val = float(vendedor.meta_risk_score) if vendedor.meta_risk_score else 0.0
        if score_val >= 80:
            nivel = "alto"
        elif score_val >= 60:
            nivel = "medio"
        else:
            nivel = "baixo"
        
        descricao = f"Vendedor {vendedor.vendedor_nome} com risco de meta (score: {score_val:.1f})"
        if vendedor.atingimento_pct:
            descricao += f" - Atingimento: {vendedor.atingimento_pct:.1f}%"
        if vendedor.gap_valor:
            descricao += f" - Gap: R$ {vendedor.gap_valor:,.2f}"
        
        alerta = AnalyticsAlerta(
            tipo_alerta="vendedor_meta_em_risco",
            referencia_id=vendedor.vendedor_id,
            referencia_nome=vendedor.vendedor_nome,
            mes_ano=mes_ano,
            ano=ano,
            mes=mes,
            descricao=descricao,
            detalhes_json={
                "vendedor_id": vendedor.vendedor_id,
                "meta_risk_score": score_val,
                "atingimento_pct": float(vendedor.atingimento_pct) if vendedor.atingimento_pct else None,
                "gap_valor": float(vendedor.gap_valor) if vendedor.gap_valor else None,
                "meta_total": float(vendedor.meta_total),
                "realizado_total": float(vendedor.realizado_total)
            },
            nivel=nivel
        )
        session.add(alerta)
        alertas_criados += 1
    
    # 2. Alertas de clientes em risco de churn (usando churn_flag)
    clientes_churn = session.query(AnalyticsClienteMes).filter(
        AnalyticsClienteMes.mes_ano == mes_ano,
        AnalyticsClienteMes.churn_flag == True
    ).order_by(
        AnalyticsClienteMes.churn_score.desc().nulls_last()
    ).limit(30).all()
    
    for cliente in clientes_churn:
        # Determina nível baseado no score
        score_val = float(cliente.churn_score) if cliente.churn_score else 0.0
        if score_val >= 80:
            nivel = "alto"
        elif score_val >= 60:
            nivel = "medio"
        else:
            nivel = "baixo"
        
        descricao = f"Cliente {cliente.cliente_nome} em risco de churn (score: {score_val:.1f})"
        if cliente.variacao_pct_vs_3m:
            descricao += f" - Variação vs média 3m: {cliente.variacao_pct_vs_3m:.1f}%"
        if cliente.dias_desde_ultima_compra:
            descricao += f" - Dias sem comprar: {cliente.dias_desde_ultima_compra}"
        
        alerta = AnalyticsAlerta(
            tipo_alerta="cliente_churn_alto",
            referencia_id=cliente.cliente_id,
            referencia_nome=cliente.cliente_nome,
            mes_ano=mes_ano,
            ano=ano,
            mes=mes,
            descricao=descricao,
            detalhes_json={
                "cliente_id": cliente.cliente_id,
                "churn_score": score_val,
                "faturamento_atual": float(cliente.faturamento_total),
                "faturamento_media_3m": float(cliente.faturamento_media_3m) if cliente.faturamento_media_3m else None,
                "variacao_pct_vs_3m": float(cliente.variacao_pct_vs_3m) if cliente.variacao_pct_vs_3m else None,
                "dias_desde_ultima_compra": cliente.dias_desde_ultima_compra
            },
            nivel=nivel
        )
        session.add(alerta)
        alertas_criados += 1
    
    # 3. Alertas de produtos em queda (usando queda_flag)
    produtos_queda = session.query(AnalyticsProdutoMes).filter(
        AnalyticsProdutoMes.mes_ano == mes_ano,
        AnalyticsProdutoMes.queda_flag == True
    ).order_by(
        AnalyticsProdutoMes.queda_score.desc().nulls_last()
    ).limit(30).all()
    
    for produto in produtos_queda:
        # Determina nível baseado no score
        score_val = float(produto.queda_score) if produto.queda_score else 0.0
        if score_val >= 80:
            nivel = "alto"
        elif score_val >= 60:
            nivel = "medio"
        else:
            nivel = "baixo"
        
        descricao = f"Produto {produto.desc_produto or produto.codigo_produto} em queda (score: {score_val:.1f})"
        if produto.variacao_pct_vs_3m:
            descricao += f" - Variação vs média 3m: {produto.variacao_pct_vs_3m:.1f}%"
        descricao += f" - Qtd vendida: {produto.qtd_vendida:,}"
        
        alerta = AnalyticsAlerta(
            tipo_alerta="produto_queda_forte",
            referencia_id=None,  # Produto não tem ID numérico, usa código
            referencia_nome=produto.desc_produto or produto.codigo_produto,
            mes_ano=mes_ano,
            ano=ano,
            mes=mes,
            descricao=descricao,
            detalhes_json={
                "codigo_produto": produto.codigo_produto,
                "queda_score": score_val,
                "variacao_pct_vs_3m": float(produto.variacao_pct_vs_3m) if produto.variacao_pct_vs_3m else None,
                "qtd_vendida": produto.qtd_vendida,
                "faturamento_total": float(produto.faturamento_total)
            },
            nivel=nivel
        )
        session.add(alerta)
        alertas_criados += 1
    
    session.commit()
    logger.info(f"✅ analytics_alertas: {alertas_criados} alertas criados para {mes_ano}")
    
    return alertas_criados


def run_all_analytics(mes_ano: Optional[str] = None) -> Dict[str, int]:
    """
    Executa todas as funções de build de analytics.
    
    Args:
        mes_ano: Mês/ano no formato "YYYY-MM" (opcional, usa mês anterior se None)
        
    Returns:
        dict: Estatísticas de registros processados por tabela
    """
    if mes_ano is None:
        mes_ano = get_mes_anterior()
    
    logger.info(f"🚀 Iniciando build de analytics para {mes_ano}...")
    
    # Inicializa banco
    init_db()
    
    # Cria sessão
    session_gen = get_db_session()
    session = next(session_gen)
    
    try:
        stats = {}
        
        # Executa na ordem: build de analytics primeiro
        stats['vendedor_mes'] = build_analytics_vendedor_mes(session, mes_ano)
        stats['cliente_mes'] = build_analytics_cliente_mes(session, mes_ano)
        stats['produto_mes'] = build_analytics_produto_mes(session, mes_ano)
        
        # Aplica scores (ML baseline)
        stats['scores_clientes'] = aplicar_scores_clientes(session, mes_ano)
        stats['scores_vendedores'] = aplicar_scores_vendedores(session, mes_ano)
        stats['scores_produtos'] = aplicar_scores_produtos(session, mes_ano)
        
        # Gera alertas baseados nos scores
        stats['alertas'] = build_analytics_alertas(session, mes_ano)
        
        logger.info(f"✅ Build de analytics concluído para {mes_ano}")
        logger.info(f"   - analytics_vendedor_mes: {stats['vendedor_mes']} registros")
        logger.info(f"   - analytics_cliente_mes: {stats['cliente_mes']} registros")
        logger.info(f"   - analytics_produto_mes: {stats['produto_mes']} registros")
        logger.info(f"   - Scores aplicados: {stats['scores_clientes']} clientes, {stats['scores_vendedores']} vendedores, {stats['scores_produtos']} produtos")
        logger.info(f"   - analytics_alertas: {stats['alertas']} alertas")
        
        return stats
    
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Erro ao executar build de analytics: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise
    finally:
        session.close()


def main():
    """Entry point para CLI."""
    parser = argparse.ArgumentParser(
        description="ETL para construir tabelas de Analytics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Usa mês anterior automaticamente
  python -m scripts.build_analytics
  
  # Especifica mês/ano
  python -m scripts.build_analytics --mes-ano 2025-08
  
  # Com variáveis de ambiente
  DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db python -m scripts.build_analytics --mes-ano 2025-08
        """
    )
    
    parser.add_argument(
        '--mes-ano',
        type=str,
        help='Mês/ano no formato YYYY-MM (ex.: 2025-08). Se não especificado, usa o mês anterior.'
    )
    
    args = parser.parse_args()
    
    try:
        stats = run_all_analytics(mes_ano=args.mes_ano)
        
        print("\n" + "=" * 60)
        print("✅ BUILD DE ANALYTICS CONCLUÍDO")
        print("=" * 60)
        print(f"📊 Registros processados:")
        print(f"   - analytics_vendedor_mes: {stats['vendedor_mes']}")
        print(f"   - analytics_cliente_mes: {stats['cliente_mes']}")
        print(f"   - analytics_produto_mes: {stats['produto_mes']}")
        print(f"   - analytics_alertas: {stats['alertas']}")
        print("=" * 60 + "\n")
        
        return 0
    
    except Exception as e:
        print(f"\n❌ Erro: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

