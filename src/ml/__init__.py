"""
Módulo de Machine Learning.

Contém modelos de ML para probabilidade de bater meta e risco de churn.
"""

from src.ml.meta_model import MetaModel
from src.ml.churn_model import ChurnModel

__all__ = [
    "MetaModel",
    "ChurnModel",
]



