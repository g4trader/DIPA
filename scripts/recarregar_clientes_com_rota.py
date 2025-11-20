#!/usr/bin/env python3
"""
Script para recarregar clientes do CSV com o mapeamento corrigido de rota_rca.

Este script:
1. Carrega o CSV de clientes
2. Recarrega no banco usando load_clientes_to_db (que agora mapeia 'Nome RCA' -> rota_rca)
3. Verifica quantos clientes foram atualizados com rota_rca
"""

import sys
import os
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data.ingestion import load_csv
from src.load_to_db import load_clientes_to_db
from src.dw.connection import init_db, SessionLocal
from src.dw.models import Cliente
from sqlalchemy import func
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def recarregar_clientes():
    """Recarrega clientes do CSV com mapeamento corrigido."""
    logger.info("=" * 80)
    logger.info("RECARREGANDO CLIENTES COM MAPEAMENTO CORRIGIDO")
    logger.info("=" * 80)
    
    # Configura banco local
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    db_path = os.path.join(project_root, 'data', 'dipam_dw.db')
    
    if os.path.exists(db_path):
        os.environ['DB_TYPE'] = 'sqlite'
        os.environ['SQLITE_PATH'] = db_path
        if 'DIPAM_DW_GCS_URI' in os.environ:
            del os.environ['DIPAM_DW_GCS_URI']
        logger.info(f"✅ Usando banco SQLite local: {db_path}")
    else:
        logger.warning(f"⚠️  Banco SQLite não encontrado em {db_path}")
        logger.info("Tentando usar configuração padrão")
    
    init_db()
    from src.dw.connection import SessionLocal as SessionLocalUpdated
    
    if SessionLocalUpdated is None:
        logger.error("SessionLocal não foi inicializado. Verifique a configuração do banco.")
        return
    
    session = SessionLocalUpdated()
    
    try:
        # Verifica estado antes
        clientes_antes = session.query(func.count(Cliente.id)).filter(Cliente.ativo == True).scalar()
        clientes_com_rota_antes = session.query(func.count(Cliente.id)).filter(
            Cliente.ativo == True,
            Cliente.rota_rca.isnot(None),
            Cliente.rota_rca != ''
        ).scalar()
        
        logger.info(f"\nEstado ANTES do recarregamento:")
        logger.info(f"  Total de clientes ativos: {clientes_antes}")
        logger.info(f"  Clientes com rota_rca: {clientes_com_rota_antes}")
        
        # Carrega CSV
        csv_path = os.path.join(project_root, 'data_raw', 'Clientes ativos.xls - Clientes ativos.csv')
        logger.info(f"\nCarregando CSV: {csv_path}")
        
        if not os.path.exists(csv_path):
            logger.error(f"Arquivo CSV não encontrado: {csv_path}")
            return
        
        df = load_csv(csv_path)
        logger.info(f"CSV carregado: {len(df)} linhas")
        
        # Verifica se 'Nome RCA' existe
        if 'Nome RCA' not in df.columns:
            logger.warning("Coluna 'Nome RCA' não encontrada no CSV!")
            logger.info(f"Colunas disponíveis: {list(df.columns)}")
        else:
            rotas_no_csv = df['Nome RCA'].dropna().unique()
            logger.info(f"Rotas encontradas no CSV: {len(rotas_no_csv)}")
            logger.info(f"Exemplos: {rotas_no_csv[:5].tolist()}")
        
        # Recarrega clientes
        logger.info("\nRecarregando clientes no banco...")
        registros_processados = load_clientes_to_db(df, batch_size=1000)
        logger.info(f"Registros processados: {registros_processados}")
        
        # Verifica estado depois (nova query, não precisa refresh)
        clientes_depois = session.query(func.count(Cliente.id)).filter(Cliente.ativo == True).scalar()
        clientes_com_rota_depois = session.query(func.count(Cliente.id)).filter(
            Cliente.ativo == True,
            Cliente.rota_rca.isnot(None),
            Cliente.rota_rca != ''
        ).scalar()
        
        logger.info(f"\nEstado DEPOIS do recarregamento:")
        logger.info(f"  Total de clientes ativos: {clientes_depois}")
        logger.info(f"  Clientes com rota_rca: {clientes_com_rota_depois}")
        logger.info(f"  ✅ Clientes atualizados com rota_rca: {clientes_com_rota_depois - clientes_com_rota_antes}")
        
        # Exemplos de clientes com rota
        if clientes_com_rota_depois > 0:
            exemplos = session.query(Cliente.codigo, Cliente.nome, Cliente.rota_rca).filter(
                Cliente.ativo == True,
                Cliente.rota_rca.isnot(None),
                Cliente.rota_rca != ''
            ).limit(5).all()
            
            logger.info(f"\nExemplos de clientes com rota_rca:")
            for codigo, nome, rota in exemplos:
                logger.info(f"  - {codigo}: {nome} -> {rota}")
        
        logger.info("\n" + "=" * 80)
        logger.info("RECARREGAMENTO CONCLUÍDO")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Erro durante recarregamento: {str(e)}", exc_info=True)
        session.rollback()
    finally:
        session.close()


if __name__ == "__main__":
    recarregar_clientes()

