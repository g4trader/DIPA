"""
Pipeline de treinamento de modelos ML (FASE 5 - Implementação Real).

Este módulo contém funções para preparar datasets (X, y, feature_names) a partir de analytics_*
e tabelas de vendas, prontos para treinar modelos scikit-learn.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case
import numpy as np

from src.dw.models_analytics import (
    AnalyticsVendedorMes, AnalyticsClienteMes, AnalyticsProdutoMes
)
from src.dw.models import InteracaoAgent, Venda, Cliente

logger = logging.getLogger(__name__)


def preparar_dataset_churn(
    session: Session,
    mes_inicio: str,
    mes_fim: str
) -> Tuple[np.ndarray, np.ndarray, List[str], List[Dict[str, Any]]]:
    """
    Monta dataset para predição de churn por cliente, usando dados de analytics_cliente_mes.
    
    Args:
        session: Sessão SQLAlchemy
        mes_inicio: Mês inicial no formato "YYYY-MM"
        mes_fim: Mês final no formato "YYYY-MM"
        
    Returns:
        Tuple (X, y, feature_names, metadata):
        - X: Array numpy com features numéricas (n_samples, n_features)
        - y: Array numpy com labels binários (0=no churn, 1=churn) (n_samples,)
        - feature_names: Lista de nomes das features
        - metadata: Lista de dicts com cliente_id, mes_ano para debug
    """
    logger.info(f"📊 Preparando dataset de churn de {mes_inicio} a {mes_fim}...")
    
    # Busca analytics_cliente_mes no período
    clientes_analytics = session.query(AnalyticsClienteMes).filter(
        and_(
            AnalyticsClienteMes.mes_ano >= mes_inicio,
            AnalyticsClienteMes.mes_ano <= mes_fim
        )
    ).order_by(AnalyticsClienteMes.cliente_id, AnalyticsClienteMes.mes_ano).all()
    
    # Calcula features históricas RFM para cada cliente
    ano_fim, mes_fim_int = map(int, mes_fim.split("-"))
    data_fim = datetime(ano_fim, mes_fim_int, 1)
    data_12m_atras = data_fim - timedelta(days=365)
    
    X_rows = []
    y_rows = []
    metadata_rows = []
    
    for cliente_analytics in clientes_analytics:
        cliente_id = cliente_analytics.cliente_id
        mes_ano = cliente_analytics.mes_ano
        
        # Features básicas de analytics_cliente_mes
        recency_dias_sem_compra = cliente_analytics.dias_desde_ultima_compra or 0
        faturamento_mes = float(cliente_analytics.faturamento_total)
        qtd_compras_mes = cliente_analytics.qtd_compras
        variacao_faturamento_3m = float(cliente_analytics.variacao_pct_vs_3m) if cliente_analytics.variacao_pct_vs_3m else 0.0
        faturamento_media_3m = float(cliente_analytics.faturamento_media_3m) if cliente_analytics.faturamento_media_3m else 0.0
        
        # Calcula Frequency e Monetary dos últimos 12 meses
        ano_mes, mes_mes = map(int, mes_ano.split("-"))
        data_mes = datetime(ano_mes, mes_mes, 1)
        data_12m_atras_mes = data_mes - timedelta(days=365)
        
        # Busca vendas dos últimos 12 meses
        vendas_12m = session.query(Venda).filter(
            and_(
                Venda.cliente_id == cliente_id,
                Venda.data_venda >= data_12m_atras_mes,
                Venda.data_venda < data_mes
            )
        ).all()
        
        # Frequency: número de meses distintos com compras nos últimos 12 meses
        meses_com_compra = set()
        monetary_12m = 0.0
        for venda in vendas_12m:
            meses_com_compra.add((venda.data_venda.year, venda.data_venda.month))
            monetary_12m += float(venda.valor_total_liquido)
        
        frequency_fat_12m = len(meses_com_compra)
        
        # Ticket médio do mês
        ticket_medio_mes = faturamento_mes / qtd_compras_mes if qtd_compras_mes > 0 else 0.0
        
        # Qtd de itens diferentes comprados no mês (aproximação: usa qtd_compras como proxy)
        qtd_itens_mes = qtd_compras_mes  # Simplificação: usa número de compras como proxy
        
        # Monta vetor de features
        features = [
            recency_dias_sem_compra,  # recency_dias_sem_compra
            frequency_fat_12m,  # frequency_fat_12m
            monetary_12m,  # monetary_fat_12m
            ticket_medio_mes,  # ticket_medio_mes
            qtd_itens_mes,  # qtd_itens_mes
            variacao_faturamento_3m,  # variacao_faturamento_3m
            faturamento_media_3m,  # faturamento_media_3m
        ]
        
        # Label: usa churn_flag se disponível, senão deriva
        if cliente_analytics.churn_flag is not None:
            label = 1 if cliente_analytics.churn_flag else 0
        else:
            # Deriva label: churn se não comprou nos próximos 2-3 meses
            # Por enquanto, usa dias_desde_ultima_compra > 60 como proxy
            label = 1 if recency_dias_sem_compra > 60 else 0
        
        X_rows.append(features)
        y_rows.append(label)
        metadata_rows.append({
            "cliente_id": cliente_id,
            "mes_ano": mes_ano,
            "cliente_nome": cliente_analytics.cliente_nome
        })
    
    # Converte para numpy arrays
    X = np.array(X_rows, dtype=np.float32)
    y = np.array(y_rows, dtype=np.int32)
    
    feature_names = [
        "recency_dias_sem_compra",
        "frequency_fat_12m",
        "monetary_fat_12m",
        "ticket_medio_mes",
        "qtd_itens_mes",
        "variacao_faturamento_3m",
        "faturamento_media_3m"
    ]
    
    logger.info(f"✅ Dataset de churn preparado: {len(X_rows)} registros, {np.sum(y)} churns ({np.sum(y)/len(y)*100:.1f}%)")
    return X, y, feature_names, metadata_rows


def preparar_dataset_meta_risk(
    session: Session,
    mes_inicio: str,
    mes_fim: str
) -> Tuple[np.ndarray, np.ndarray, List[str], List[Dict[str, Any]]]:
    """
    Dataset para risco de não bater meta por vendedor, usando analytics_vendedor_mes.
    
    Args:
        session: Sessão SQLAlchemy
        mes_inicio: Mês inicial no formato "YYYY-MM"
        mes_fim: Mês final no formato "YYYY-MM"
        
    Returns:
        Tuple (X, y, feature_names, metadata):
        - X: Array numpy com features numéricas (n_samples, n_features)
        - y: Array numpy com labels binários (0=baixo risco, 1=alto risco) (n_samples,)
        - feature_names: Lista de nomes das features
        - metadata: Lista de dicts com vendedor_id, mes_ano para debug
    """
    logger.info(f"📊 Preparando dataset de meta_risk de {mes_inicio} a {mes_fim}...")
    
    # Busca analytics_vendedor_mes no período
    vendedores_analytics = session.query(AnalyticsVendedorMes).filter(
        and_(
            AnalyticsVendedorMes.mes_ano >= mes_inicio,
            AnalyticsVendedorMes.mes_ano <= mes_fim
        )
    ).order_by(AnalyticsVendedorMes.vendedor_id, AnalyticsVendedorMes.mes_ano).all()
    
    X_rows = []
    y_rows = []
    metadata_rows = []
    
    for vendedor_analytics in vendedores_analytics:
        vendedor_id = vendedor_analytics.vendedor_id
        mes_ano = vendedor_analytics.mes_ano
        
        # Features básicas
        atingimento_meta_atual = float(vendedor_analytics.atingimento_pct) if vendedor_analytics.atingimento_pct else 0.0
        faturamento_mes = float(vendedor_analytics.realizado_total)
        qtd_clientes_ativos_mes = vendedor_analytics.qtd_clientes_positivados
        qtd_clientes_churn_3m = vendedor_analytics.qtd_clientes_churn
        qtd_skus = vendedor_analytics.qtd_skus
        
        # Calcula features históricas
        ano_mes, mes_mes = map(int, mes_ano.split("-"))
        data_mes = datetime(ano_mes, mes_mes, 1)
        data_12m_atras = data_mes - timedelta(days=365)
        data_3m_atras = data_mes - timedelta(days=90)
        
        # Busca vendas dos últimos 12 meses para calcular faturamento_12m
        vendas_12m = session.query(func.sum(Venda.valor_total_liquido)).filter(
            and_(
                Venda.vendedor_id == vendedor_id,
                Venda.data_venda >= data_12m_atras,
                Venda.data_venda < data_mes
            )
        ).scalar()
        faturamento_12m = float(vendas_12m) if vendas_12m else 0.0
        
        # Calcula variação de atingimento nos últimos 3 meses
        # Busca analytics dos últimos 3 meses
        meses_anteriores = []
        for i in range(1, 4):  # 1, 2, 3 meses atrás
            data_anterior = data_mes - timedelta(days=30*i)
            mes_ano_anterior = data_anterior.strftime("%Y-%m")
            meses_anteriores.append(mes_ano_anterior)
        
        atingimentos_anteriores = []
        for mes_ant in meses_anteriores:
            analytics_ant = session.query(AnalyticsVendedorMes).filter(
                and_(
                    AnalyticsVendedorMes.vendedor_id == vendedor_id,
                    AnalyticsVendedorMes.mes_ano == mes_ant
                )
            ).first()
            if analytics_ant and analytics_ant.atingimento_pct:
                atingimentos_anteriores.append(float(analytics_ant.atingimento_pct))
        
        variacao_atingimento_3m = 0.0
        if len(atingimentos_anteriores) > 0:
            media_atingimento_3m = sum(atingimentos_anteriores) / len(atingimentos_anteriores)
            variacao_atingimento_3m = atingimento_meta_atual - media_atingimento_3m
        
        # Média de faturamento por cliente
        media_faturamento_cliente = faturamento_mes / qtd_clientes_ativos_mes if qtd_clientes_ativos_mes > 0 else 0.0
        
        # Mix de produtos (diversidade) - usa qtd_skus como proxy
        mix_produtos = qtd_skus
        
        # Monta vetor de features
        features = [
            atingimento_meta_atual,  # atingimento_meta_atual
            variacao_atingimento_3m,  # variacao_atingimento_3m
            faturamento_mes,  # faturamento_mes
            faturamento_12m,  # faturamento_12m
            qtd_clientes_ativos_mes,  # qtd_clientes_ativos_mes
            media_faturamento_cliente,  # media_faturamento_cliente
            qtd_clientes_churn_3m,  # qtd_clientes_churn_3m
            mix_produtos,  # mix_produtos (diversidade)
        ]
        
        # Label: 1 se atingimento < 95% (não bateu/ficou muito abaixo), 0 caso contrário
        label = 1 if atingimento_meta_atual < 95.0 else 0
        
        X_rows.append(features)
        y_rows.append(label)
        metadata_rows.append({
            "vendedor_id": vendedor_id,
            "mes_ano": mes_ano,
            "vendedor_nome": vendedor_analytics.vendedor_nome
        })
    
    # Converte para numpy arrays
    X = np.array(X_rows, dtype=np.float32)
    y = np.array(y_rows, dtype=np.int32)
    
    feature_names = [
        "atingimento_meta_atual",
        "variacao_atingimento_3m",
        "faturamento_mes",
        "faturamento_12m",
        "qtd_clientes_ativos_mes",
        "media_faturamento_cliente",
        "qtd_clientes_churn_3m",
        "mix_produtos"
    ]
    
    logger.info(f"✅ Dataset de meta_risk preparado: {len(X_rows)} registros, {np.sum(y)} em risco ({np.sum(y)/len(y)*100:.1f}%)")
    return X, y, feature_names, metadata_rows


def preparar_dataset_oportunidades(
    session: Session,
    mes_referencia: str
) -> Tuple[np.ndarray, np.ndarray, List[str], List[Dict[str, Any]]]:
    """
    Monta dataset para identificar clientes com potencial de crescimento (upsell/cross-sell).
    
    Args:
        session: Sessão SQLAlchemy
        mes_referencia: Mês de referência no formato "YYYY-MM"
        
    Returns:
        Tuple (X, y, feature_names, metadata):
        - X: Array numpy com features numéricas (n_samples, n_features)
        - y: Array numpy com labels binários (0=baixo potencial, 1=alto potencial) (n_samples,)
        - feature_names: Lista de nomes das features
        - metadata: Lista de dicts com cliente_id, mes_ano para debug
    """
    logger.info(f"📊 Preparando dataset de oportunidades para {mes_referencia}...")
    
    # Busca analytics_cliente_mes no mês de referência
    clientes_analytics = session.query(AnalyticsClienteMes).filter(
        AnalyticsClienteMes.mes_ano == mes_referencia
    ).all()
    
    X_rows = []
    y_rows = []
    metadata_rows = []
    
    ano_ref, mes_ref_int = map(int, mes_referencia.split("-"))
    data_ref = datetime(ano_ref, mes_ref_int, 1)
    data_12m_atras = data_ref - timedelta(days=365)
    
    for cliente_analytics in clientes_analytics:
        cliente_id = cliente_analytics.cliente_id
        
        # Features básicas
        faturamento_atual = float(cliente_analytics.faturamento_total)
        ticket_medio = faturamento_atual / cliente_analytics.qtd_compras if cliente_analytics.qtd_compras > 0 else 0.0
        
        # Calcula faturamento máximo dos últimos 12 meses
        vendas_12m = session.query(Venda).filter(
            and_(
                Venda.cliente_id == cliente_id,
                Venda.data_venda >= data_12m_atras,
                Venda.data_venda < data_ref
            )
        ).all()
        
        # Agrupa por mês para encontrar máximo
        faturamento_por_mes = {}
        for venda in vendas_12m:
            mes_key = (venda.data_venda.year, venda.data_venda.month)
            if mes_key not in faturamento_por_mes:
                faturamento_por_mes[mes_key] = 0.0
            faturamento_por_mes[mes_key] += float(venda.valor_total_liquido)
        
        faturamento_max_12m = max(faturamento_por_mes.values()) if faturamento_por_mes else faturamento_atual
        
        # Percentual atual vs máximo
        percentual_atual_vs_max_12m = (faturamento_atual / faturamento_max_12m * 100) if faturamento_max_12m > 0 else 0.0
        
        # Qtd de categorias compradas (aproximação: usa qtd_compras como proxy de diversidade)
        qtd_categorias_compradas = cliente_analytics.qtd_compras  # Simplificação
        
        # Qtd de categorias disponíveis (fixo por enquanto, pode ser calculado no futuro)
        qtd_categorias_disponiveis = 10.0  # Valor fixo como placeholder
        
        # Monta vetor de features
        features = [
            faturamento_atual,  # faturamento_atual
            faturamento_max_12m,  # faturamento_max_12m
            percentual_atual_vs_max_12m,  # percentual_atual_vs_max_12m
            ticket_medio,  # ticket_medio
            qtd_categorias_compradas,  # qtd_categorias_compradas
            qtd_categorias_disponiveis,  # qtd_categorias_disponiveis
        ]
        
        # Label: 1 se faturamento_atual < 60% do faturamento_max_12m (potencial de crescimento)
        label = 1 if percentual_atual_vs_max_12m < 60.0 else 0
        
        X_rows.append(features)
        y_rows.append(label)
        metadata_rows.append({
            "cliente_id": cliente_id,
            "mes_ano": mes_referencia,
            "cliente_nome": cliente_analytics.cliente_nome
        })
    
    # Converte para numpy arrays
    X = np.array(X_rows, dtype=np.float32)
    y = np.array(y_rows, dtype=np.int32)
    
    feature_names = [
        "faturamento_atual",
        "faturamento_max_12m",
        "percentual_atual_vs_max_12m",
        "ticket_medio",
        "qtd_categorias_compradas",
        "qtd_categorias_disponiveis"
    ]
    
    logger.info(f"✅ Dataset de oportunidades preparado: {len(X_rows)} registros, {np.sum(y)} com potencial ({np.sum(y)/len(y)*100:.1f}%)")
    return X, y, feature_names, metadata_rows


def preparar_dataset_qa_respostas(
    session: Session,
    limite: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Prepara dataset de qualidade de resposta baseado em interacoes_agent com feedback_qualidade.
    
    Por enquanto, apenas retorna features + labels dos feedbacks explícitos.
    No futuro, este dataset será usado para treinar um modelo de qualidade de resposta.
    
    Args:
        session: Sessão SQLAlchemy
        limite: Número máximo de registros a retornar (opcional)
        
    Returns:
        Lista de dicts com features e labels para cada interação
    """
    logger.info("📊 Preparando dataset de qualidade de resposta (QA)...")
    
    # Busca interações com feedback_qualidade preenchido
    query = session.query(InteracaoAgent).filter(
        InteracaoAgent.feedback_qualidade.isnot(None)
    ).order_by(InteracaoAgent.timestamp.desc())
    
    if limite:
        query = query.limit(limite)
    
    interacoes = query.all()
    
    dataset = []
    
    for interacao in interacoes:
        # Features básicas
        features = {
            "interacao_id": interacao.id,
            "timestamp": interacao.timestamp.isoformat() if interacao.timestamp else None,
            "papel": interacao.papel,
            "intent": interacao.intent,
            "confianca": float(interacao.confianca) if interacao.confianca else None,
            "sucesso_resposta": interacao.sucesso_resposta,
            "fonte_dados_principal": interacao.fonte_dados_principal,
            "num_registros_usados": interacao.num_registros_usados,
            "tempo_processamento_ms": interacao.tempo_processamento_ms,
        }
        
        # Label: feedback_qualidade (1-5)
        label = interacao.feedback_qualidade
        
        # Comentário (opcional)
        comentario = interacao.feedback_comentario or interacao.comentario
        
        dataset.append({
            **features,
            "qualidade_label": label,
            "comentario": comentario
        })
    
    logger.info(f"✅ Dataset de QA preparado: {len(dataset)} registros")
    return dataset


def preparar_dataset_produto_queda(
    session: Session,
    mes_inicio: str,
    mes_fim: str
) -> List[Dict[str, Any]]:
    """
    Monta dataset para queda de produtos.
    
    Por enquanto, apenas retorna features + label calculados com heurísticas.
    No futuro, este dataset será usado para treinar um modelo de queda de produtos.
    
    Args:
        session: Sessão SQLAlchemy
        mes_inicio: Mês inicial no formato "YYYY-MM"
        mes_fim: Mês final no formato "YYYY-MM"
        
    Returns:
        Lista de dicts com features e labels para cada produto/mês
    """
    logger.info(f"📊 Preparando dataset de queda de produtos de {mes_inicio} a {mes_fim}...")
    
    # Busca analytics_produto_mes no período
    produtos_analytics = session.query(AnalyticsProdutoMes).filter(
        and_(
            AnalyticsProdutoMes.mes_ano >= mes_inicio,
            AnalyticsProdutoMes.mes_ano <= mes_fim
        )
    ).order_by(AnalyticsProdutoMes.codigo_produto, AnalyticsProdutoMes.mes_ano).all()
    
    dataset = []
    
    for produto in produtos_analytics:
        # Features básicas
        features = {
            "codigo_produto": produto.codigo_produto,
            "mes_ano": produto.mes_ano,
            "faturamento_total": float(produto.faturamento_total),
            "qtd_vendida": produto.qtd_vendida,
            "qtd_clientes_ativos": produto.qtd_clientes_ativos,
            "variacao_pct_vs_3m": float(produto.variacao_pct_vs_3m) if produto.variacao_pct_vs_3m else None,
            "participacao_no_faturamento": float(produto.participacao_no_faturamento) if produto.participacao_no_faturamento else None,
        }
        
        # Label: queda_flag (já calculado por heurística)
        label = produto.queda_flag
        
        # Score atual (baseline)
        score = float(produto.queda_score) if produto.queda_score else None
        
        dataset.append({
            **features,
            "queda_label": label,
            "queda_score_baseline": score
        })
    
    logger.info(f"✅ Dataset de queda de produtos preparado: {len(dataset)} registros")
    return dataset


def exportar_datasets_para_treino(
    session: Session,
    mes_inicio: str,
    mes_fim: str,
    output_dir: Optional[str] = None
) -> Dict[str, int]:
    """
    Exporta todos os datasets preparados para arquivos (futuro: CSV, Parquet, etc.).
    
    Por enquanto, apenas retorna estatísticas. No futuro, salvará em arquivos.
    
    Args:
        session: Sessão SQLAlchemy
        mes_inicio: Mês inicial no formato "YYYY-MM"
        mes_fim: Mês final no formato "YYYY-MM"
        output_dir: Diretório para salvar arquivos (opcional, não implementado ainda)
        
    Returns:
        Dict com contagem de registros por dataset
    """
    logger.info(f"📦 Exportando datasets para treino de {mes_inicio} a {mes_fim}...")
    
    datasets = {
        "churn": preparar_dataset_churn(session, mes_inicio, mes_fim),
        "meta_risk": preparar_dataset_meta_risk(session, mes_inicio, mes_fim),
        "produto_queda": preparar_dataset_produto_queda(session, mes_inicio, mes_fim),
        "qa_respostas": preparar_dataset_qa_respostas(session, limite=1000)
    }
    
    stats = {nome: len(dataset) for nome, dataset in datasets.items()}
    
    logger.info(f"✅ Datasets exportados: {stats}")
    
    # TODO (FASE 5): Salvar em arquivos CSV/Parquet para treino
    if output_dir:
        logger.warning("⚠️  Salvamento em arquivos ainda não implementado (será na FASE 5)")
    
    return stats

