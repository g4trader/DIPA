#!/usr/bin/env python3
"""
Script para executar o pipeline ETL.

Este script:
1. Carrega dados brutos (CSVs)
2. Limpa e padroniza dados
3. Carrega dados no data warehouse
"""

import sys
from pathlib import Path
import logging
import pandas as pd

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from src.config import config
from src.data.ingestion import load_csv, validate_data
from src.data.cleaning import (
    clean_data,
    standardize_dates,
    standardize_currency,
    standardize_numbers,
    normalize_strings
)
from src.dw.etl import (
    load_clientes,
    load_vendedores,
    load_vendas,
    load_metas_vendedor,
    update_percentual_atingido
)
from src.dw.connection import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_clientes(file_path: str):
    """
    Processa dados de clientes.
    
    Args:
        file_path: Caminho para o arquivo CSV de clientes
    """
    print(f"Processando clientes: {file_path}")
    
    # Carrega dados
    df = load_csv(file_path)
    
    # Valida dados
    validation = validate_data(df, required_columns=["codigo", "nome"])
    if not validation["valid"]:
        logger.error(f"Erros de validação: {validation['errors']}")
        return
    
    # Limpa dados
    df = clean_data(df, remove_duplicates=True)
    
    # Padroniza datas
    if "data_cadastro" in df.columns:
        df = standardize_dates(df, ["data_cadastro"])
    
    # Normaliza strings
    df = normalize_strings(df, columns=["nome", "cidade", "estado"])
    
    # Carrega no banco
    load_clientes(df)
    
    print(f"Clientes processados: {len(df)} registros")


def process_vendedores(file_path: str):
    """
    Processa dados de vendedores.
    
    Args:
        file_path: Caminho para o arquivo CSV de vendedores
    """
    print(f"Processando vendedores: {file_path}")
    
    # Carrega dados
    df = load_csv(file_path)
    
    # Valida dados
    validation = validate_data(df, required_columns=["codigo", "nome"])
    if not validation["valid"]:
        logger.error(f"Erros de validação: {validation['errors']}")
        return
    
    # Limpa dados
    df = clean_data(df, remove_duplicates=True)
    
    # Normaliza strings
    df = normalize_strings(df, columns=["nome"])
    
    # Carrega no banco
    load_vendedores(df)
    
    print(f"Vendedores processados: {len(df)} registros")


def process_vendas(file_path: str):
    """
    Processa dados de vendas.
    
    Args:
        file_path: Caminho para o arquivo CSV de vendas
    """
    print(f"Processando vendas: {file_path}")
    
    # Carrega dados
    df = load_csv(file_path)
    
    # Valida dados
    validation = validate_data(df, required_columns=["cliente_id", "vendedor_id", "data_venda", "valor"])
    if not validation["valid"]:
        logger.error(f"Erros de validação: {validation['errors']}")
        return
    
    # Limpa dados
    df = clean_data(df, remove_duplicates=True)
    
    # Padroniza datas
    if "data_venda" in df.columns:
        df = standardize_dates(df, ["data_venda"])
    
    # Padroniza valores monetários
    if "valor" in df.columns:
        df = standardize_currency(df, ["valor"])
    
    # Carrega no banco
    load_vendas(df)
    
    print(f"Vendas processadas: {len(df)} registros")


def process_metas_vendedor(file_path: str):
    """
    Processa dados de metas de vendedor.
    
    Args:
        file_path: Caminho para o arquivo CSV de metas
    """
    print(f"Processando metas de vendedor: {file_path}")
    
    # Carrega dados
    df = load_csv(file_path)
    
    # Valida dados
    validation = validate_data(df, required_columns=["vendedor_id", "ano", "mes", "meta_valor"])
    if not validation["valid"]:
        logger.error(f"Erros de validação: {validation['errors']}")
        return
    
    # Limpa dados
    df = clean_data(df, remove_duplicates=True)
    
    # Padroniza valores monetários
    if "meta_valor" in df.columns:
        df = standardize_currency(df, ["meta_valor"])
    if "realizado_valor" in df.columns:
        df = standardize_currency(df, ["realizado_valor"])
    
    # Carrega no banco
    load_metas_vendedor(df)
    
    # Atualiza percentual atingido
    update_percentual_atingido()
    
    print(f"Metas processadas: {len(df)} registros")


def main():
    """Função principal."""
    print("=" * 60)
    print("Executando pipeline ETL")
    print("=" * 60)
    print()
    
    # Inicializa banco de dados
    init_db()
    
    # Processa dados
    data_raw_dir = config.paths.data_raw_dir
    
    # Clientres
    clientes_file = data_raw_dir / "clientes.csv"
    if clientes_file.exists():
        process_clientes(clientes_file)
        print()
    
    # Vendedores
    vendedores_file = data_raw_dir / "vendedores.csv"
    if vendedores_file.exists():
        process_vendedores(vendedores_file)
        print()
    
    # Vendas
    vendas_file = data_raw_dir / "vendas.csv"
    if vendas_file.exists():
        process_vendas(vendas_file)
        print()
    
    # Metas
    metas_file = data_raw_dir / "metas_vendedor.csv"
    if metas_file.exists():
        process_metas_vendedor(metas_file)
        print()
    
    print("=" * 60)
    print("Pipeline ETL concluído!")
    print("=" * 60)


if __name__ == "__main__":
    main()




