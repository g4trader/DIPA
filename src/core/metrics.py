"""
Sistema de Métricas para DIPAM Copilot.

Este módulo mantém métricas internas para exportação via /metrics
em formato Prometheus-compatible.
"""

import time
from typing import Dict, Any, Optional
from datetime import datetime
from collections import defaultdict

# Métricas globais
_metrics: Dict[str, Any] = {
    "query_duration": defaultdict(list),  # query_id -> [durations_ms]
    "query_records": defaultdict(list),  # query_id -> [record_counts]
    "cache_hits": defaultdict(int),  # query_id -> count
    "cache_misses": defaultdict(int),  # query_id -> count
    "etl_timestamp": None,  # timestamp da última execução de ETL
    "startup_time": time.time(),  # timestamp do startup
}


def record_query_metric(query_id: str, duration_ms: float, records: int):
    """
    Registra métrica de execução de query.
    
    Args:
        query_id: ID da query (Q1, Q2, etc.)
        duration_ms: Tempo de execução em milissegundos
        records: Número de registros retornados
    """
    _metrics["query_duration"][query_id].append(duration_ms)
    _metrics["query_records"][query_id].append(records)
    
    # Mantém apenas últimas 100 execuções por query
    if len(_metrics["query_duration"][query_id]) > 100:
        _metrics["query_duration"][query_id] = _metrics["query_duration"][query_id][-100:]
    if len(_metrics["query_records"][query_id]) > 100:
        _metrics["query_records"][query_id] = _metrics["query_records"][query_id][-100:]


def record_cache_hit(query_id: str):
    """Registra cache hit."""
    _metrics["cache_hits"][query_id] += 1


def record_cache_miss(query_id: str):
    """Registra cache miss."""
    _metrics["cache_misses"][query_id] += 1


def update_etl_timestamp(timestamp: Optional[float] = None):
    """
    Atualiza timestamp da última execução de ETL.
    
    Args:
        timestamp: Timestamp Unix (se None, usa time.time())
    """
    _metrics["etl_timestamp"] = timestamp or time.time()


def get_metrics_prometheus_format() -> str:
    """
    Retorna métricas em formato Prometheus-compatible.
    
    Returns:
        String com métricas no formato Prometheus
    """
    lines = []
    
    # Query duration (média das últimas execuções)
    for query_id, durations in _metrics["query_duration"].items():
        if durations:
            avg_duration = sum(durations) / len(durations)
            lines.append(f'dipam_query_duration_ms{{query="{query_id}"}} {avg_duration:.2f}')
    
    # Query records (média das últimas execuções)
    for query_id, records_list in _metrics["query_records"].items():
        if records_list:
            avg_records = sum(records_list) / len(records_list)
            lines.append(f'dipam_query_records_total{{query="{query_id}"}} {int(avg_records)}')
    
    # Cache hits
    for query_id, hits in _metrics["cache_hits"].items():
        lines.append(f'dipam_cache_hits{{query="{query_id}"}} {hits}')
    
    # Cache misses
    for query_id, misses in _metrics["cache_misses"].items():
        lines.append(f'dipam_cache_misses{{query="{query_id}"}} {misses}')
    
    # ETL timestamp
    if _metrics["etl_timestamp"]:
        lines.append(f'dipam_etl_timestamp {int(_metrics["etl_timestamp"])}')
    
    # Uptime
    uptime_seconds = time.time() - _metrics["startup_time"]
    lines.append(f'dipam_api_uptime_seconds {int(uptime_seconds)}')
    
    return "\n".join(lines)


def get_metrics_dict() -> Dict[str, Any]:
    """
    Retorna métricas como dicionário.
    
    Returns:
        Dict com todas as métricas
    """
    # Calcula médias
    query_duration_avg = {
        query_id: sum(durations) / len(durations) if durations else 0
        for query_id, durations in _metrics["query_duration"].items()
    }
    
    query_records_avg = {
        query_id: sum(records) / len(records) if records else 0
        for query_id, records in _metrics["query_records"].items()
    }
    
    return {
        "query_duration_ms": query_duration_avg,
        "query_records_total": query_records_avg,
        "cache_hits": dict(_metrics["cache_hits"]),
        "cache_misses": dict(_metrics["cache_misses"]),
        "etl_timestamp": _metrics["etl_timestamp"],
        "uptime_seconds": int(time.time() - _metrics["startup_time"])
    }

