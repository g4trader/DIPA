"""
Módulo de Análise de Dados.

Contém funções para análise de produtos, vendas, metas e outros indicadores.
"""

from src.analysis.produtos import (
    get_produtos_menos_vendidos,
    get_top_produtos_para_recuperar
)
from src.analysis.metas import metas_resumo_ultimos_meses
from src.analysis.clientes import (
    clientes_positivados_sem_compra_produto,
    clientes_risco_churn,
    clientes_oportunidades_crescimento
)
from src.analysis.supervisores import desempenho_supervisores

__all__ = [
    "get_produtos_menos_vendidos",
    "get_top_produtos_para_recuperar",
    "metas_resumo_ultimos_meses",
    "clientes_positivados_sem_compra_produto",
    "clientes_risco_churn",
    "clientes_oportunidades_crescimento",
    "desempenho_supervisores",
]

