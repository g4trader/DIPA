"""
Features para modelo de probabilidade de bater meta.

Este módulo contém funções para criar features relacionadas à
probabilidade de um vendedor bater a meta em um determinado mês.
"""

import pandas as pd
import numpy as np
from sqlalchemy import text
from typing import Optional, Dict, List
import logging

from src.config import config
from src.dw.connection import get_db_engine

logger = logging.getLogger(__name__)


def create_meta_features(
    ano: int,
    mes: int,
    vendedor_ids: Optional[List[int]] = None
) -> pd.DataFrame:
    """
    Cria features para modelo de probabilidade de bater meta.
    
    Args:
        ano: Ano para criar features
        mes: Mês para criar features
        vendedor_ids: Lista de IDs de vendedores (None = todos)
        
    Returns:
        pd.DataFrame: DataFrame com features para cada vendedor/mês
    """
    try:
        engine = get_db_engine()
        
        # Query para extrair features
        query = text("""
            SELECT 
                mv.vendedor_id,
                mv.ano,
                mv.mes,
                mv.meta_valor,
                mv.realizado_valor,
                mv.percentual_atingido,
                
                -- Features históricas (últimos 3 meses)
                LAG(mv.percentual_atingido, 1) OVER (
                    PARTITION BY mv.vendedor_id 
                    ORDER BY mv.ano, mv.mes
                ) as percentual_mes_anterior,
                LAG(mv.percentual_atingido, 2) OVER (
                    PARTITION BY mv.vendedor_id 
                    ORDER BY mv.ano, mv.mes
                ) as percentual_2meses_atras,
                LAG(mv.percentual_atingido, 3) OVER (
                    PARTITION BY mv.vendedor_id 
                    ORDER BY mv.ano, mv.mes
                ) as percentual_3meses_atras,
                
                -- Média móvel dos últimos 3 meses
                AVG(mv.percentual_atingido) OVER (
                    PARTITION BY mv.vendedor_id 
                    ORDER BY mv.ano, mv.mes 
                    ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING
                ) as media_3meses,
                
                -- Desvio padrão dos últimos 3 meses
                STDDEV(mv.percentual_atingido) OVER (
                    PARTITION BY mv.vendedor_id 
                    ORDER BY mv.ano, mv.mes 
                    ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING
                ) as desvio_3meses,
                
                -- Features de vendas (último mês)
                COALESCE(SUM(v.valor) OVER (
                    PARTITION BY mv.vendedor_id, mv.ano, mv.mes
                ), 0) as total_vendas_mes,
                
                -- Número de vendas (último mês)
                COALESCE(COUNT(v.id) OVER (
                    PARTITION BY mv.vendedor_id, mv.ano, mv.mes
                ), 0) as num_vendas_mes,
                
                -- Features temporais
                mv.mes as mes_num,
                CASE 
                    WHEN mv.mes IN (12, 1, 2) THEN 'verao'
                    WHEN mv.mes IN (3, 4, 5) THEN 'outono'
                    WHEN mv.mes IN (6, 7, 8) THEN 'inverno'
                    ELSE 'primavera'
                END as estacao,
                
                -- Target (se bateu a meta)
                CASE 
                    WHEN mv.percentual_atingido >= 100 THEN 1
                    ELSE 0
                END as bateu_meta
                
            FROM metas_vendedor mv
            LEFT JOIN vendas v ON v.vendedor_id = mv.vendedor_id
                AND EXTRACT(YEAR FROM v.data_venda) = mv.ano
                AND EXTRACT(MONTH FROM v.data_venda) = mv.mes
            WHERE mv.ano = :ano AND mv.mes = :mes
            GROUP BY mv.id, mv.vendedor_id, mv.ano, mv.mes, 
                     mv.meta_valor, mv.realizado_valor, mv.percentual_atingido
        """)
        
        # Executa query
        with engine.connect() as conn:
            df = pd.read_sql(
                query,
                conn,
                params={"ano": ano, "mes": mes}
            )
        
        # Filtra vendedores se especificado
        if vendedor_ids:
            df = df[df["vendedor_id"].isin(vendedor_ids)]
        
        # Preenche valores faltantes
        df = df.fillna({
            "percentual_mes_anterior": 0,
            "percentual_2meses_atras": 0,
            "percentual_3meses_atras": 0,
            "media_3meses": 0,
            "desvio_3meses": 0,
            "total_vendas_mes": 0,
            "num_vendas_mes": 0,
        })
        
        logger.info(
            f"Features criadas para {len(df)} vendedores em {mes}/{ano}"
        )
        
        return df
    
    except Exception as e:
        logger.error(f"Erro ao criar features de meta: {str(e)}")
        raise


def create_meta_features_historical(
    start_ano: int,
    start_mes: int,
    end_ano: int,
    end_mes: int,
    vendedor_ids: Optional[List[int]] = None
) -> pd.DataFrame:
    """
    Cria features históricas para modelo de probabilidade de bater meta.
    
    Args:
        start_ano: Ano inicial
        start_mes: Mês inicial
        end_ano: Ano final
        end_mes: Mês final
        vendedor_ids: Lista de IDs de vendedores (None = todos)
        
    Returns:
        pd.DataFrame: DataFrame com features históricas
    """
    try:
        engine = get_db_engine()
        
        # Query para extrair features históricas
        query = text("""
            SELECT 
                mv.vendedor_id,
                mv.ano,
                mv.mes,
                mv.meta_valor,
                mv.realizado_valor,
                mv.percentual_atingido,
                
                -- Features históricas
                LAG(mv.percentual_atingido, 1) OVER (
                    PARTITION BY mv.vendedor_id 
                    ORDER BY mv.ano, mv.mes
                ) as percentual_mes_anterior,
                AVG(mv.percentual_atingido) OVER (
                    PARTITION BY mv.vendedor_id 
                    ORDER BY mv.ano, mv.mes 
                    ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING
                ) as media_3meses,
                
                -- Target
                CASE 
                    WHEN mv.percentual_atingido >= 100 THEN 1
                    ELSE 0
                END as bateu_meta
                
            FROM metas_vendedor mv
            WHERE mv.ano >= :start_ano 
                AND mv.mes >= :start_mes
                AND mv.ano <= :end_ano
                AND mv.mes <= :end_mes
            ORDER BY mv.vendedor_id, mv.ano, mv.mes
        """)
        
        # Executa query
        with engine.connect() as conn:
            df = pd.read_sql(
                query,
                conn,
                params={
                    "start_ano": start_ano,
                    "start_mes": start_mes,
                    "end_ano": end_ano,
                    "end_mes": end_mes,
                }
            )
        
        # Filtra vendedores se especificado
        if vendedor_ids:
            df = df[df["vendedor_id"].isin(vendedor_ids)]
        
        # Preenche valores faltantes
        df = df.fillna({
            "percentual_mes_anterior": 0,
            "media_3meses": 0,
        })
        
        logger.info(
            f"Features históricas criadas para {len(df)} registros"
        )
        
        return df
    
    except Exception as e:
        logger.error(f"Erro ao criar features históricas: {str(e)}")
        raise

