"""
ETL para Data Warehouse.

Este módulo contém funções para carregar dados processados no data warehouse.
"""

import pandas as pd
from sqlalchemy import text
from typing import Optional, Dict, List
import logging

from src.config import config
from src.dw.connection import get_db_engine, init_db
from src.dw.models import (
    Cliente, Vendedor, Supervisor, Venda,
    MetaVendedor, MetaDepartamento
)

logger = logging.getLogger(__name__)


def load_data_to_dw(
    table_name: str,
    df: pd.DataFrame,
    if_exists: str = "replace",
    index: bool = False
):
    """
    Carrega dados de um DataFrame no data warehouse.
    
    Args:
        table_name: Nome da tabela de destino
        df: DataFrame com os dados
        if_exists: Comportamento se a tabela já existir ('replace', 'append', 'fail')
        index: Se True, inclui o index do DataFrame
    """
    try:
        engine = get_db_engine()
        
        logger.info(f"Carregando {len(df)} linhas na tabela {table_name}")
        
        df.to_sql(
            table_name,
            engine,
            if_exists=if_exists,
            index=index,
            method="multi",
            chunksize=1000
        )
        
        logger.info(f"Dados carregados com sucesso na tabela {table_name}")
    
    except Exception as e:
        logger.error(f"Erro ao carregar dados na tabela {table_name}: {str(e)}")
        raise


def load_clientes(df: pd.DataFrame):
    """
    Carrega dados de clientes no data warehouse.
    
    Args:
        df: DataFrame com dados de clientes
    """
    # Mapeia colunas do DataFrame para o modelo
    # Ajuste conforme necessário baseado na estrutura dos seus dados
    clientes_data = []
    
    for _, row in df.iterrows():
        cliente = {
            "codigo": str(row.get("codigo", row.get("id", ""))),
            "nome": str(row.get("nome", "")),
            "email": row.get("email"),
            "telefone": row.get("telefone"),
            "cidade": row.get("cidade"),
            "estado": row.get("estado"),
            "ativo": row.get("ativo", True),
            "data_cadastro": row.get("data_cadastro"),
        }
        clientes_data.append(cliente)
    
    df_clientes = pd.DataFrame(clientes_data)
    load_data_to_dw("clientes", df_clientes, if_exists="replace")


def load_vendedores(df: pd.DataFrame):
    """
    Carrega dados de vendedores no data warehouse.
    
    Args:
        df: DataFrame com dados de vendedores
    """
    vendedores_data = []
    
    for _, row in df.iterrows():
        vendedor = {
            "codigo": str(row.get("codigo", row.get("id", ""))),
            "nome": str(row.get("nome", "")),
            "email": row.get("email"),
            "supervisor_id": row.get("supervisor_id"),
            "ativo": row.get("ativo", True),
        }
        vendedores_data.append(vendedor)
    
    df_vendedores = pd.DataFrame(vendedores_data)
    load_data_to_dw("vendedores", df_vendedores, if_exists="replace")


def load_vendas(df: pd.DataFrame):
    """
    Carrega dados de vendas no data warehouse.
    
    Args:
        df: DataFrame com dados de vendas
    """
    vendas_data = []
    
    for _, row in df.iterrows():
        venda = {
            "cliente_id": row.get("cliente_id"),
            "vendedor_id": row.get("vendedor_id"),
            "data_venda": row.get("data_venda"),
            "valor": float(row.get("valor", 0)),
            "quantidade": row.get("quantidade"),
            "produto": row.get("produto"),
        }
        vendas_data.append(venda)
    
    df_vendas = pd.DataFrame(vendas_data)
    load_data_to_dw("vendas", df_vendas, if_exists="replace")


def load_metas_vendedor(df: pd.DataFrame):
    """
    Carrega dados de metas de vendedor no data warehouse.
    
    Args:
        df: DataFrame com dados de metas de vendedor
    """
    metas_data = []
    
    for _, row in df.iterrows():
        meta = {
            "vendedor_id": row.get("vendedor_id"),
            "ano": int(row.get("ano", 2024)),
            "mes": int(row.get("mes", 1)),
            "meta_valor": float(row.get("meta_valor", 0)),
            "realizado_valor": float(row.get("realizado_valor", 0)),
            "percentual_atingido": row.get("percentual_atingido"),
        }
        metas_data.append(meta)
    
    df_metas = pd.DataFrame(metas_data)
    load_data_to_dw("metas_vendedor", df_metas, if_exists="replace")


def update_percentual_atingido():
    """
    Atualiza o percentual de meta atingida para todos os registros.
    """
    try:
        engine = get_db_engine()
        
        # Atualiza metas de vendedor
        query = text("""
            UPDATE metas_vendedor
            SET percentual_atingido = 
                CASE 
                    WHEN meta_valor > 0 THEN (realizado_valor / meta_valor) * 100
                    ELSE 0
                END
        """)
        
        with engine.connect() as conn:
            conn.execute(query)
            conn.commit()
        
        logger.info("Percentual de meta atingida atualizado")
    
    except Exception as e:
        logger.error(f"Erro ao atualizar percentual de meta: {str(e)}")
        raise




