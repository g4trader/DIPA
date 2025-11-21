#!/usr/bin/env python3
"""
Script para testar conexão com o banco de dados.

Este script verifica se as configurações de banco de dados estão corretas
e se é possível conectar ao banco configurado.
"""

import sys
import os
from pathlib import Path

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from config.settings import settings
from db.connection import init_db, get_database_url
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_connection():
    """
    Testa a conexão com o banco de dados.
    """
    logger.info("Testando configuração de banco de dados...")
    
    try:
        # Verifica configurações
        logger.info(f"Tipo de banco: {settings.database_type}")
        
        if settings.database_type == "bigquery":
            logger.info(f"Projeto BigQuery: {settings.bigquery_project_id}")
            logger.info(f"Dataset: {settings.bigquery_dataset}")
            
            if not settings.bigquery_project_id or not settings.bigquery_dataset:
                logger.error("BIGQUERY_PROJECT_ID e BIGQUERY_DATASET devem ser configurados")
                return False
        
        elif settings.database_type == "postgresql":
            logger.info(f"Host PostgreSQL: {settings.postgres_host}")
            logger.info(f"Database: {settings.postgres_db}")
            
            if not all([settings.postgres_user, settings.postgres_password, 
                       settings.postgres_host, settings.postgres_db]):
                logger.error("Credenciais PostgreSQL devem ser configuradas")
                return False
        
        # Gera URL de conexão
        database_url = get_database_url()
        logger.info(f"URL de conexão gerada: {database_url[:50]}...")
        
        # Tenta inicializar conexão
        logger.info("Inicializando conexão...")
        init_db()
        logger.info("✅ Conexão inicializada com sucesso!")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Erro ao conectar: {str(e)}")
        return False


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)





