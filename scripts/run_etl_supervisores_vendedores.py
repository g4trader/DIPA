#!/usr/bin/env python3
"""
Script para executar o ETL de supervisores, vendedores e enriquecimento de clientes.

Uso:
    python scripts/run_etl_supervisores_vendedores.py
"""

import sys
import os
from pathlib import Path

# Adiciona o diretório raiz ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Define SQLITE_PATH para o caminho local se não estiver definido
if not os.getenv("SQLITE_PATH"):
    sqlite_path = Path(project_root) / "data" / "dipam_dw.db"
    os.environ["SQLITE_PATH"] = str(sqlite_path)

from src.dw.etl import process_supervisores_vendedores_clientes
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Executa o ETL."""
    logger.info("=" * 80)
    logger.info("EXECUTANDO ETL: SUPERVISORES, VENDEDORES E CLIENTES")
    logger.info("=" * 80)
    
    try:
        process_supervisores_vendedores_clientes()
        logger.info("\n✅ ETL executado com sucesso!")
        logger.info("\nExecute o script de validação para verificar os resultados:")
        logger.info("  python scripts/diagnostico_pos_etl.py")
    except Exception as e:
        logger.error(f"\n❌ Erro ao executar ETL: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()

