"""
Serviço de previsão ML (FASE 5).

Carrega modelos treinados e oferece funções de alto nível para previsões.
Implementa cache em memória para evitar recálculos desnecessários.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from functools import lru_cache
import joblib
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from src.ml.training_pipeline import (
    preparar_dataset_churn,
    preparar_dataset_meta_risk,
    preparar_dataset_oportunidades
)
from src.ml.model_registry import get_model_info
from src.dw.models_analytics import AnalyticsClienteMes, AnalyticsVendedorMes
from src.dw.models import Venda

logger = logging.getLogger(__name__)

# Diretório de modelos
ROOT_DIR = Path(__file__).parent.parent.parent
MODELS_DIR = ROOT_DIR / "models"

# Cache simples em memória (LRU com limite)
_cache = {}
_cache_max_size = 100


def _get_cache_key(tipo: str, mes_referencia: str, filtro_id: Optional[int] = None) -> str:
    """Gera chave de cache."""
    return f"{tipo}:{mes_referencia}:{filtro_id}"


def _load_model(tipo: str):
    """
    Carrega modelo treinado com lazy loading.
    
    Args:
        tipo: Tipo do modelo ("churn", "meta_risk", "oportunidades")
        
    Returns:
        Modelo scikit-learn ou None se não encontrado
    """
    model_info = get_model_info(tipo)
    
    if not model_info or not model_info.get("treinado"):
        logger.warning(f"⚠️  Modelo '{tipo}' não encontrado ou não treinado")
        return None
    
    model_path = ROOT_DIR / model_info["path"]
    
    if not model_path.exists():
        logger.warning(f"⚠️  Arquivo do modelo não encontrado: {model_path}")
        return None
    
    try:
        modelo = joblib.load(model_path)
        logger.info(f"✅ Modelo '{tipo}' carregado de {model_path}")
        return modelo
    except Exception as e:
        logger.error(f"❌ Erro ao carregar modelo '{tipo}': {str(e)}")
        return None


def prever_churn_clientes(
    session: Session,
    mes_referencia: str,
    vendedor_id: Optional[int] = None,
    limite: int = 20
) -> List[Dict[str, Any]]:
    """
    Prevê risco de churn para clientes.
    
    Args:
        session: Sessão SQLAlchemy
        mes_referencia: Mês de referência no formato "YYYY-MM"
        vendedor_id: ID do vendedor para filtrar (opcional)
        limite: Número máximo de clientes a retornar (top N por probabilidade)
        
    Returns:
        Lista de dicts com cliente_id, cliente_nome, prob_churn, etc.
    """
    cache_key = _get_cache_key("churn", mes_referencia, vendedor_id)
    
    # Verifica cache
    if cache_key in _cache:
        logger.debug(f"📦 Usando cache para churn: {mes_referencia}")
        return _cache[cache_key]
    
    # Carrega modelo
    modelo = _load_model("churn")
    if modelo is None:
        logger.warning("⚠️  Modelo de churn não disponível, retornando lista vazia")
        return []
    
    # Busca clientes do mês
    query = session.query(AnalyticsClienteMes).filter(
        AnalyticsClienteMes.mes_ano == mes_referencia
    )
    
    if vendedor_id:
        query = query.filter(AnalyticsClienteMes.vendedor_id == vendedor_id)
    
    clientes_analytics = query.all()
    
    if not clientes_analytics:
        return []
    
    # Prepara features para cada cliente (reutiliza lógica do training_pipeline)
    ano_ref, mes_ref_int = map(int, mes_referencia.split("-"))
    data_ref = datetime(ano_ref, mes_ref_int, 1)
    data_12m_atras = data_ref - timedelta(days=365)
    
    resultados = []
    
    for cliente_analytics in clientes_analytics:
        cliente_id = cliente_analytics.cliente_id
        
        # Calcula features (mesma lógica do training_pipeline)
        recency_dias_sem_compra = cliente_analytics.dias_desde_ultima_compra or 0
        faturamento_mes = float(cliente_analytics.faturamento_total)
        qtd_compras_mes = cliente_analytics.qtd_compras
        variacao_faturamento_3m = float(cliente_analytics.variacao_pct_vs_3m) if cliente_analytics.variacao_pct_vs_3m else 0.0
        faturamento_media_3m = float(cliente_analytics.faturamento_media_3m) if cliente_analytics.faturamento_media_3m else 0.0
        
        # Calcula Frequency e Monetary
        vendas_12m = session.query(Venda).filter(
            and_(
                Venda.cliente_id == cliente_id,
                Venda.data_venda >= data_12m_atras,
                Venda.data_venda < data_ref
            )
        ).all()
        
        meses_com_compra = set()
        monetary_12m = 0.0
        for venda in vendas_12m:
            meses_com_compra.add((venda.data_venda.year, venda.data_venda.month))
            monetary_12m += float(venda.valor_total_liquido)
        
        frequency_fat_12m = len(meses_com_compra)
        ticket_medio_mes = faturamento_mes / qtd_compras_mes if qtd_compras_mes > 0 else 0.0
        qtd_itens_mes = qtd_compras_mes
        
        # Monta features
        features = np.array([[
            recency_dias_sem_compra,
            frequency_fat_12m,
            monetary_12m,
            ticket_medio_mes,
            qtd_itens_mes,
            variacao_faturamento_3m,
            faturamento_media_3m
        ]], dtype=np.float32)
        
        # Previsão
        try:
            prob_churn = float(modelo.predict_proba(features)[0, 1])
        except Exception as e:
            logger.warning(f"⚠️  Erro ao prever churn para cliente {cliente_id}: {str(e)}")
            continue
        
        resultados.append({
            "cliente_id": cliente_id,
            "cliente_nome": cliente_analytics.cliente_nome,
            "prob_churn": prob_churn,
            "vendedor_id": cliente_analytics.vendedor_id,
            "dias_desde_ultima_compra": recency_dias_sem_compra,
            "faturamento_12m": monetary_12m
        })
    
    # Ordena por probabilidade (maior primeiro) e limita
    resultados.sort(key=lambda x: x["prob_churn"], reverse=True)
    resultados = resultados[:limite]
    
    # Atualiza cache (com limite de tamanho)
    if len(_cache) >= _cache_max_size:
        # Remove entrada mais antiga (simples: remove primeira)
        _cache.pop(next(iter(_cache)))
    _cache[cache_key] = resultados
    
    logger.info(f"✅ Previsão de churn: {len(resultados)} clientes (top {limite})")
    return resultados


def prever_risco_meta_vendedores(
    session: Session,
    mes_referencia: str,
    supervisor_id: Optional[int] = None,
    limite: int = 20
) -> List[Dict[str, Any]]:
    """
    Prevê risco de não bater meta para vendedores.
    
    Args:
        session: Sessão SQLAlchemy
        mes_referencia: Mês de referência no formato "YYYY-MM"
        supervisor_id: ID do supervisor para filtrar (opcional)
        limite: Número máximo de vendedores a retornar (top N por probabilidade)
        
    Returns:
        Lista de dicts com vendedor_id, vendedor_nome, prob_nao_bater_meta, etc.
    """
    cache_key = _get_cache_key("meta_risk", mes_referencia, supervisor_id)
    
    # Verifica cache
    if cache_key in _cache:
        logger.debug(f"📦 Usando cache para meta_risk: {mes_referencia}")
        return _cache[cache_key]
    
    # Carrega modelo
    modelo = _load_model("meta_risk")
    if modelo is None:
        logger.warning("⚠️  Modelo de meta_risk não disponível, retornando lista vazia")
        return []
    
    # Busca vendedores do mês
    query = session.query(AnalyticsVendedorMes).filter(
        AnalyticsVendedorMes.mes_ano == mes_referencia
    )
    
    if supervisor_id:
        query = query.filter(AnalyticsVendedorMes.supervisor_id == supervisor_id)
    
    vendedores_analytics = query.all()
    
    if not vendedores_analytics:
        return []
    
    # Prepara features e faz previsões
    ano_ref, mes_ref_int = map(int, mes_referencia.split("-"))
    data_ref = datetime(ano_ref, mes_ref_int, 1)
    data_12m_atras = data_ref - timedelta(days=365)
    
    resultados = []
    
    for vendedor_analytics in vendedores_analytics:
        vendedor_id = vendedor_analytics.vendedor_id
        
        # Calcula features (mesma lógica do training_pipeline)
        atingimento_meta_atual = float(vendedor_analytics.atingimento_pct) if vendedor_analytics.atingimento_pct else 0.0
        faturamento_mes = float(vendedor_analytics.realizado_total)
        qtd_clientes_ativos_mes = vendedor_analytics.qtd_clientes_positivados
        qtd_clientes_churn_3m = vendedor_analytics.qtd_clientes_churn
        qtd_skus = vendedor_analytics.qtd_skus
        
        # Calcula features históricas
        vendas_12m = session.query(func.sum(Venda.valor_total_liquido)).filter(
            and_(
                Venda.vendedor_id == vendedor_id,
                Venda.data_venda >= data_12m_atras,
                Venda.data_venda < data_ref
            )
        ).scalar()
        faturamento_12m = float(vendas_12m) if vendas_12m else 0.0
        
        # Variação de atingimento 3m
        meses_anteriores = []
        for i in range(1, 4):
            data_anterior = data_ref - timedelta(days=30*i)
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
        
        media_faturamento_cliente = faturamento_mes / qtd_clientes_ativos_mes if qtd_clientes_ativos_mes > 0 else 0.0
        mix_produtos = qtd_skus
        
        # Monta features
        features = np.array([[
            atingimento_meta_atual,
            variacao_atingimento_3m,
            faturamento_mes,
            faturamento_12m,
            qtd_clientes_ativos_mes,
            media_faturamento_cliente,
            qtd_clientes_churn_3m,
            mix_produtos
        ]], dtype=np.float32)
        
        # Previsão
        try:
            prob_nao_bater = float(modelo.predict_proba(features)[0, 1])
        except Exception as e:
            logger.warning(f"⚠️  Erro ao prever meta_risk para vendedor {vendedor_id}: {str(e)}")
            continue
        
        resultados.append({
            "vendedor_id": vendedor_id,
            "vendedor_nome": vendedor_analytics.vendedor_nome,
            "prob_nao_bater_meta": prob_nao_bater,
            "meta": float(vendedor_analytics.meta_total),
            "realizado": float(vendedor_analytics.realizado_total),
            "atingimento": atingimento_meta_atual,
            "gap": float(vendedor_analytics.gap_valor) if vendedor_analytics.gap_valor else 0.0
        })
    
    # Ordena por probabilidade (maior primeiro) e limita
    resultados.sort(key=lambda x: x["prob_nao_bater_meta"], reverse=True)
    resultados = resultados[:limite]
    
    # Atualiza cache
    if len(_cache) >= _cache_max_size:
        _cache.pop(next(iter(_cache)))
    _cache[cache_key] = resultados
    
    logger.info(f"✅ Previsão de meta_risk: {len(resultados)} vendedores (top {limite})")
    return resultados


def sugerir_oportunidades(
    session: Session,
    mes_referencia: str,
    vendedor_id: Optional[int] = None,
    limite: int = 20
) -> List[Dict[str, Any]]:
    """
    Sugere clientes com potencial de crescimento (upsell/cross-sell).
    
    Args:
        session: Sessão SQLAlchemy
        mes_referencia: Mês de referência no formato "YYYY-MM"
        vendedor_id: ID do vendedor para filtrar (opcional)
        limite: Número máximo de clientes a retornar (top N por score)
        
    Returns:
        Lista de dicts com cliente_id, cliente_nome, score_oportunidade, etc.
    """
    cache_key = _get_cache_key("oportunidades", mes_referencia, vendedor_id)
    
    # Verifica cache
    if cache_key in _cache:
        logger.debug(f"📦 Usando cache para oportunidades: {mes_referencia}")
        return _cache[cache_key]
    
    # Carrega modelo
    modelo = _load_model("oportunidades")
    if modelo is None:
        logger.warning("⚠️  Modelo de oportunidades não disponível, retornando lista vazia")
        return []
    
    # Busca clientes do mês
    query = session.query(AnalyticsClienteMes).filter(
        AnalyticsClienteMes.mes_ano == mes_referencia
    )
    
    if vendedor_id:
        query = query.filter(AnalyticsClienteMes.vendedor_id == vendedor_id)
    
    clientes_analytics = query.all()
    
    if not clientes_analytics:
        return []
    
    # Prepara features e faz previsões
    ano_ref, mes_ref_int = map(int, mes_referencia.split("-"))
    data_ref = datetime(ano_ref, mes_ref_int, 1)
    data_12m_atras = data_ref - timedelta(days=365)
    
    resultados = []
    
    for cliente_analytics in clientes_analytics:
        cliente_id = cliente_analytics.cliente_id
        
        # Calcula features (mesma lógica do training_pipeline)
        faturamento_atual = float(cliente_analytics.faturamento_total)
        ticket_medio = faturamento_atual / cliente_analytics.qtd_compras if cliente_analytics.qtd_compras > 0 else 0.0
        
        # Faturamento máximo 12m
        vendas_12m = session.query(Venda).filter(
            and_(
                Venda.cliente_id == cliente_id,
                Venda.data_venda >= data_12m_atras,
                Venda.data_venda < data_ref
            )
        ).all()
        
        faturamento_por_mes = {}
        for venda in vendas_12m:
            mes_key = (venda.data_venda.year, venda.data_venda.month)
            if mes_key not in faturamento_por_mes:
                faturamento_por_mes[mes_key] = 0.0
            faturamento_por_mes[mes_key] += float(venda.valor_total_liquido)
        
        faturamento_max_12m = max(faturamento_por_mes.values()) if faturamento_por_mes else faturamento_atual
        percentual_atual_vs_max_12m = (faturamento_atual / faturamento_max_12m * 100) if faturamento_max_12m > 0 else 0.0
        qtd_categorias_compradas = cliente_analytics.qtd_compras
        qtd_categorias_disponiveis = 10.0
        
        # Monta features
        features = np.array([[
            faturamento_atual,
            faturamento_max_12m,
            percentual_atual_vs_max_12m,
            ticket_medio,
            qtd_categorias_compradas,
            qtd_categorias_disponiveis
        ]], dtype=np.float32)
        
        # Previsão
        try:
            score_oportunidade = float(modelo.predict_proba(features)[0, 1])
        except Exception as e:
            logger.warning(f"⚠️  Erro ao prever oportunidades para cliente {cliente_id}: {str(e)}")
            continue
        
        resultados.append({
            "cliente_id": cliente_id,
            "cliente_nome": cliente_analytics.cliente_nome,
            "score_oportunidade": score_oportunidade,
            "fat_atual": faturamento_atual,
            "fat_max_12m": faturamento_max_12m,
            "percentual_vs_max": percentual_atual_vs_max_12m,
            "vendedor_id": cliente_analytics.vendedor_id
        })
    
    # Ordena por score (maior primeiro) e limita
    resultados.sort(key=lambda x: x["score_oportunidade"], reverse=True)
    resultados = resultados[:limite]
    
    # Atualiza cache
    if len(_cache) >= _cache_max_size:
        _cache.pop(next(iter(_cache)))
    _cache[cache_key] = resultados
    
    logger.info(f"✅ Previsão de oportunidades: {len(resultados)} clientes (top {limite})")
    return resultados

