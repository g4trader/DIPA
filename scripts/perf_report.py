#!/usr/bin/env python3
"""
Script de Relatório de Performance para DIPAM Copilot.

Gera relatório consolidado de performance das queries Q1-Q5.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Adiciona o diretório raiz ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Define SQLITE_PATH para o caminho local se não estiver definido
if not os.getenv("SQLITE_PATH"):
    sqlite_path = Path(project_root) / "data" / "dipam_dw.db"
    os.environ["SQLITE_PATH"] = str(sqlite_path)

from src.core.cache_layer import get_cache_info, get_etl_timestamp
from src.core.metrics import get_metrics_dict
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def format_duration(seconds):
    """Formata duração em formato legível."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m{secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours:02d}h{minutes:02d}m"


def format_time_ago(timestamp):
    """Formata timestamp como "há X tempo"."""
    if not timestamp:
        return "N/A"
    
    now = time.time()
    diff = now - timestamp
    
    if diff < 60:
        return f"{int(diff)}s atrás"
    elif diff < 3600:
        return f"{int(diff // 60)}m atrás"
    elif diff < 86400:
        return f"{int(diff // 3600)}h{int((diff % 3600) // 60)}m atrás"
    else:
        days = int(diff // 86400)
        return f"{days}d atrás"


def generate_perf_report():
    """Gera relatório de performance."""
    logger.info("=" * 80)
    logger.info("DIPAM COPILOT - PERFORMANCE REPORT")
    logger.info("=" * 80)
    
    try:
        # Obtém métricas
        metrics = get_metrics_dict()
        cache_info = get_cache_info()
        
        # Queries para reportar
        queries = ["Q1", "Q2", "Q3", "Q4", "Q5"]
        
        logger.info("\n📊 QUERIES:")
        logger.info("-" * 80)
        
        for query_id in queries:
            duration_ms = metrics.get("query_duration_ms", {}).get(query_id, 0)
            records = int(metrics.get("query_records_total", {}).get(query_id, 0))
            
            # Cache stats
            cache_hits = cache_info.get("cache_stats", {}).get(query_id, {}).get("hits", 0)
            cache_misses = cache_info.get("cache_stats", {}).get(query_id, {}).get("misses", 0)
            
            # Determina status do cache
            if cache_hits > 0:
                cache_status = f"cache_hit={cache_hits}"
            elif cache_misses > 0:
                cache_status = f"cache_miss={cache_misses}"
            else:
                cache_status = "cache_n/a"
            
            logger.info(f"{query_id}: {duration_ms:.0f}ms | {records} registros | {cache_status}")
        
        # ETL info
        logger.info("\n📦 ETL:")
        logger.info("-" * 80)
        etl_timestamp = get_etl_timestamp()
        if etl_timestamp:
            etl_ago = format_time_ago(etl_timestamp)
            etl_datetime = datetime.fromtimestamp(etl_timestamp)
            logger.info(f"Executado há: {etl_ago}")
            logger.info(f"Data/hora: {etl_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            logger.info("ETL executado há: N/A (timestamp não encontrado)")
        
        # Uptime
        logger.info("\n⏱️  SISTEMA:")
        logger.info("-" * 80)
        uptime_seconds = metrics.get("uptime_seconds", 0)
        uptime_formatted = format_duration(uptime_seconds)
        logger.info(f"Uptime: {uptime_formatted}")
        
        # Cache summary
        logger.info("\n💾 CACHE:")
        logger.info("-" * 80)
        cache_size = cache_info.get("cache_size", 0)
        logger.info(f"Tamanho do cache: {cache_size} entradas")
        
        total_hits = sum(
            stats.get("hits", 0)
            for stats in cache_info.get("cache_stats", {}).values()
        )
        total_misses = sum(
            stats.get("misses", 0)
            for stats in cache_info.get("cache_stats", {}).values()
        )
        
        if total_hits + total_misses > 0:
            hit_rate = (total_hits / (total_hits + total_misses)) * 100
            logger.info(f"Taxa de acerto: {hit_rate:.1f}% ({total_hits} hits, {total_misses} misses)")
        else:
            logger.info("Taxa de acerto: N/A (nenhuma execução ainda)")
        
        logger.info("=" * 80)
        
        return True
        
    except Exception as e:
        logger.error(f"Erro ao gerar relatório: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    success = generate_perf_report()
    sys.exit(0 if success else 1)

