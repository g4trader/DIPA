"""
Sistema de Profiler para Queries.

Este módulo implementa decorator @profile_query que registra métricas
detalhadas de execução de queries.
"""

import time
import functools
import logging
from typing import Callable, Any, Optional, Dict
from collections import defaultdict

logger = logging.getLogger(__name__)

# Armazena métricas de profiler
_profiler_metrics: Dict[str, Dict[str, Any]] = defaultdict(dict)


def profile_query(query_id: str):
    """
    Decorator que perfila execução de queries.
    
    Registra:
    - Tempo de execução
    - Número de registros
    - Número de passos no banco
    - Número de objetos ORM criados
    
    Args:
        query_id: ID da query (Q1, Q2, etc.)
    
    Example:
        @profile_query("Q1")
        def get_clientes_sem_compra_ha_dias(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            db_steps = 0
            orm_objects_created = 0
            
            try:
                # Executa função
                result = func(*args, **kwargs)
                
                duration_ms = (time.time() - start_time) * 1000
                records = len(result) if isinstance(result, list) else 0
                
                # Estima db_steps (número de queries executadas)
                # Para queries complexas, pode ser > 1
                db_steps = 1  # Base: pelo menos 1 query
                
                # Estima objetos ORM criados (número de registros retornados)
                orm_objects_created = records
                
                # Registra perfil
                from src.core.logging_config import log_query_profile
                log_query_profile(
                    query_id=query_id,
                    duration_ms=duration_ms,
                    records=records,
                    db_steps=db_steps,
                    orm_objects_created=orm_objects_created
                )
                
                # Armazena métricas para /metrics
                _profiler_metrics[query_id] = {
                    "duration_ms": duration_ms,
                    "records": records,
                    "db_steps": db_steps,
                    "orm_objects_created": orm_objects_created,
                    "last_execution": time.time()
                }
                
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                
                # Registra perfil com erro
                from src.core.logging_config import log_query_profile
                log_query_profile(
                    query_id=query_id,
                    duration_ms=duration_ms,
                    records=0,
                    db_steps=0,
                    orm_objects_created=0
                )
                
                raise
        
        return wrapper
    return decorator


def get_profiler_metrics() -> Dict[str, Dict[str, Any]]:
    """Retorna métricas do profiler."""
    return dict(_profiler_metrics)


def reset_profiler_metrics():
    """Reseta métricas do profiler."""
    global _profiler_metrics
    _profiler_metrics.clear()

