#!/usr/bin/env python3
"""
Script para construir features para ML.

Este script constrói features de vendedor/mês e cliente/mês
e salva em arquivos CSV para uso em modelagem.
"""

import sys
from pathlib import Path
import logging

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from src.config import config
from src.dw.connection import init_db
from src.features import (
    build_features_vendedor_mes,
    build_features_cliente_mes,
    save_features_to_csv
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Função principal."""
    print("=" * 60)
    print("Construindo Features para ML")
    print("=" * 60)
    print()
    
    # Inicializa banco de dados
    logger.info("Inicializando banco de dados...")
    init_db()
    
    # Constrói features de vendedor/mês
    print("=" * 60)
    print("Construindo Features de Vendedor/Mês")
    print("=" * 60)
    print()
    
    try:
        df_vendedor = build_features_vendedor_mes()
        
        # Salva em CSV
        save_features_to_csv(df_vendedor, "features_vendedor_mes.csv")
        
        print(f"✓ Features de vendedor/mês construídas: {len(df_vendedor)} registros")
        print(f"  Colunas: {len(df_vendedor.columns)}")
        print(f"  Target (bateu_meta): {df_vendedor['bateu_meta'].sum()} registros positivos")
        print()
        
    except Exception as e:
        logger.error(f"Erro ao construir features de vendedor/mês: {str(e)}")
        print(f"✗ Erro: {str(e)}")
        print()
    
    # Constrói features de cliente/mês
    print("=" * 60)
    print("Construindo Features de Cliente/Mês (Churn)")
    print("=" * 60)
    print()
    
    try:
        df_cliente = build_features_cliente_mes(dias_churn=90)
        
        # Salva em CSV
        save_features_to_csv(df_cliente, "features_cliente_mes.csv")
        
        print(f"✓ Features de cliente/mês construídas: {len(df_cliente)} registros")
        print(f"  Colunas: {len(df_cliente.columns)}")
        print(f"  Target (churn_provavel): {df_cliente['churn_provavel'].sum()} registros positivos")
        print()
        
    except Exception as e:
        logger.error(f"Erro ao construir features de cliente/mês: {str(e)}")
        print(f"✗ Erro: {str(e)}")
        print()
    
    print("=" * 60)
    print("Construção de features concluída!")
    print("=" * 60)
    print()
    print("Arquivos salvos em:")
    print(f"  - {config.paths.features_dir}/features_vendedor_mes.csv")
    print(f"  - {config.paths.features_dir}/features_cliente_mes.csv")
    print()


if __name__ == "__main__":
    main()





