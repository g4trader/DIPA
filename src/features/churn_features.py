"""
Features para modelo de risco de churn.

Este módulo contém funções para criar features relacionadas ao
risco de churn de clientes.
"""

import pandas as pd
import numpy as np
from sqlalchemy import text
from typing import Optional, Dict, List
import logging
from datetime import datetime, timedelta

from src.config import config
from src.dw.connection import get_db_engine

logger = logging.getLogger(__name__)


def create_churn_features(
    cliente_ids: Optional[List[int]] = None,
    data_referencia: Optional[datetime] = None
) -> pd.DataFrame:
    """
    Cria features para modelo de risco de churn.
    
    Args:
        cliente_ids: Lista de IDs de clientes (None = todos)
        data_referencia: Data de referência para cálculo (None = hoje)
        
    Returns:
        pd.DataFrame: DataFrame com features para cada cliente
    """
    try:
        engine = get_db_engine()
        
        if data_referencia is None:
            data_referencia = datetime.now()
        
        # Query para extrair features
        query = text("""
            SELECT 
                c.id as cliente_id,
                c.codigo,
                c.nome,
                c.ativo,
                c.data_cadastro,
                c.cidade,
                c.estado,
                
                -- Features de vendas (últimos 90 dias)
                COALESCE(SUM(CASE 
                    WHEN v.data_venda >= :data_90dias THEN v.valor 
                    ELSE 0 
                END), 0) as total_vendas_90dias,
                
                COALESCE(COUNT(CASE 
                    WHEN v.data_venda >= :data_90dias THEN v.id 
                END), 0) as num_vendas_90dias,
                
                -- Features de vendas (últimos 30 dias)
                COALESCE(SUM(CASE 
                    WHEN v.data_venda >= :data_30dias THEN v.valor 
                    ELSE 0 
                END), 0) as total_vendas_30dias,
                
                COALESCE(COUNT(CASE 
                    WHEN v.data_venda >= :data_30dias THEN v.id 
                END), 0) as num_vendas_30dias,
                
                -- Features de vendas (últimos 180 dias)
                COALESCE(SUM(CASE 
                    WHEN v.data_venda >= :data_180dias THEN v.valor 
                    ELSE 0 
                END), 0) as total_vendas_180dias,
                
                -- Última venda
                MAX(v.data_venda) as ultima_venda,
                
                -- Dias desde última venda
                CASE 
                    WHEN MAX(v.data_venda) IS NULL THEN 
                        EXTRACT(EPOCH FROM (:data_referencia::date - c.data_cadastro::date)) / 86400
                    ELSE 
                        EXTRACT(EPOCH FROM (:data_referencia::date - MAX(v.data_venda)::date)) / 86400
                END as dias_sem_venda,
                
                -- Total de vendas históricas
                COALESCE(SUM(v.valor), 0) as total_vendas_historico,
                COALESCE(COUNT(v.id), 0) as num_vendas_historico,
                
                -- Média de vendas por mês
                COALESCE(SUM(v.valor) / NULLIF(
                    EXTRACT(EPOCH FROM (:data_referencia::date - c.data_cadastro::date)) / 86400 / 30, 0
                ), 0) as media_vendas_mes,
                
                -- Recência (R), Frequência (F), Valor (V)
                CASE 
                    WHEN MAX(v.data_venda) IS NULL THEN 0
                    WHEN EXTRACT(EPOCH FROM (:data_referencia::date - MAX(v.data_venda)::date)) / 86400 <= 30 THEN 5
                    WHEN EXTRACT(EPOCH FROM (:data_referencia::date - MAX(v.data_venda)::date)) / 86400 <= 60 THEN 4
                    WHEN EXTRACT(EPOCH FROM (:data_referencia::date - MAX(v.data_venda)::date)) / 86400 <= 90 THEN 3
                    WHEN EXTRACT(EPOCH FROM (:data_referencia::date - MAX(v.data_venda)::date)) / 86400 <= 180 THEN 2
                    ELSE 1
                END as recencia_score,
                
                CASE 
                    WHEN COUNT(v.id) = 0 THEN 1
                    WHEN COUNT(v.id) <= 5 THEN 2
                    WHEN COUNT(v.id) <= 10 THEN 3
                    WHEN COUNT(v.id) <= 20 THEN 4
                    ELSE 5
                END as frequencia_score,
                
                CASE 
                    WHEN SUM(v.valor) = 0 THEN 1
                    WHEN SUM(v.valor) <= 1000 THEN 2
                    WHEN SUM(v.valor) <= 5000 THEN 3
                    WHEN SUM(v.valor) <= 10000 THEN 4
                    ELSE 5
                END as valor_score,
                
                -- Target (churn - não comprou nos últimos 90 dias)
                CASE 
                    WHEN MAX(v.data_venda) IS NULL THEN 1
                    WHEN EXTRACT(EPOCH FROM (:data_referencia::date - MAX(v.data_venda)::date)) / 86400 > 90 THEN 1
                    ELSE 0
                END as churn
                
            FROM clientes c
            LEFT JOIN vendas v ON v.cliente_id = c.id
            WHERE c.ativo = 1
            GROUP BY c.id, c.codigo, c.nome, c.ativo, c.data_cadastro, 
                     c.cidade, c.estado
        """)
        
        # Calcula datas de referência
        data_30dias = data_referencia - timedelta(days=30)
        data_90dias = data_referencia - timedelta(days=90)
        data_180dias = data_referencia - timedelta(days=180)
        
        # Executa query
        with engine.connect() as conn:
            df = pd.read_sql(
                query,
                conn,
                params={
                    "data_referencia": data_referencia,
                    "data_30dias": data_30dias,
                    "data_90dias": data_90dias,
                    "data_180dias": data_180dias,
                }
            )
        
        # Filtra clientes se especificado
        if cliente_ids:
            df = df[df["cliente_id"].isin(cliente_ids)]
        
        # Preenche valores faltantes
        df = df.fillna({
            "dias_sem_venda": 999,  # Cliente nunca comprou
            "ultima_venda": None,
            "total_vendas_90dias": 0,
            "num_vendas_90dias": 0,
            "total_vendas_30dias": 0,
            "num_vendas_30dias": 0,
            "total_vendas_180dias": 0,
            "total_vendas_historico": 0,
            "num_vendas_historico": 0,
            "media_vendas_mes": 0,
        })
        
        # Calcula features derivadas
        df["tendencia_vendas"] = (
            df["total_vendas_30dias"] - df["total_vendas_90dias"]
        ) / (df["total_vendas_90dias"] + 1)
        
        df["rfv_score"] = (
            df["recencia_score"] + 
            df["frequencia_score"] + 
            df["valor_score"]
        )
        
        logger.info(f"Features criadas para {len(df)} clientes")
        
        return df
    
    except Exception as e:
        logger.error(f"Erro ao criar features de churn: {str(e)}")
        raise

