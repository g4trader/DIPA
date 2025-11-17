"""
Módulo ETL para carregar dados brutos no Data Warehouse.

Este módulo contém funções para ler CSVs de data_raw/ e popular
as tabelas do DW de forma normalizada e consistente.
"""

from src.etl.load_raw_to_dw import run_full_etl

__all__ = ["run_full_etl"]

