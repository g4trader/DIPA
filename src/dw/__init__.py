"""
Módulo de Data Warehouse.

Contém funções para criar e gerenciar o data warehouse.
"""

from src.dw.connection import get_db_engine, init_db, create_tables
from src.dw.etl import load_data_to_dw

__all__ = [
    "get_db_engine",
    "init_db",
    "create_tables",
    "load_data_to_dw",
]





