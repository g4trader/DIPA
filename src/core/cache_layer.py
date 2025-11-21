"""
Cache Inteligente para Queries Q1-Q5.

Este módulo implementa cache em memória com TTL e invalidação automática
quando ETL é executado.
"""

import functools
import hashlib
import json
import os
import time
import logging
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# Cache em memória global
_cache: Dict[str, Dict[str, Any]] = {}
_cache_stats: Dict[str, Dict[str, int]] = {}


def get_etl_timestamp_path() -> Path:
    """Retorna caminho do arquivo de timestamp do ETL."""
    project_root = Path(__file__).parent.parent.parent
    return project_root / ".etl_timestamp"


def get_etl_timestamp() -> Optional[float]:
    """
    Lê timestamp da última execução de ETL.
    
    Returns:
        Timestamp Unix ou None se não existir
    """
    timestamp_path = get_etl_timestamp_path()
    if timestamp_path.exists():
        try:
            with open(timestamp_path, "r") as f:
                return float(f.read().strip())
        except Exception as e:
            logger.warning(f"Erro ao ler timestamp do ETL: {e}")
    return None


def update_etl_timestamp():
    """Atualiza timestamp da última execução de ETL."""
    timestamp_path = get_etl_timestamp_path()
    timestamp = time.time()
    
    try:
        timestamp_path.parent.mkdir(parents=True, exist_ok=True)
        with open(timestamp_path, "w") as f:
            f.write(str(timestamp))
        
        # Invalida cache quando ETL é executado
        invalidate_cache()
        
        # Atualiza métricas
        from src.core.metrics import update_etl_timestamp as update_metrics_etl
        update_metrics_etl(timestamp)
        
        logger.info(f"ETL timestamp atualizado: {timestamp}")
    except Exception as e:
        logger.error(f"Erro ao atualizar timestamp do ETL: {e}")


def invalidate_cache():
    """Invalida todo o cache."""
    global _cache, _cache_stats
    _cache.clear()
    _cache_stats.clear()
    logger.info("Cache invalidado")


def _make_cache_key(query_name: str, *args, **kwargs) -> str:
    """
    Cria chave de cache baseada no nome da query e argumentos.
    
    Args:
        query_name: Nome da query (Q1, Q2, etc.)
        *args: Argumentos posicionais
        **kwargs: Argumentos nomeados
    
    Returns:
        Chave de cache (hash)
    """
    # Remove argumentos que não afetam o resultado (session, etc.)
    cacheable_kwargs = {
        k: v for k, v in kwargs.items()
        if k not in ["session", "filtros_behavior"]  # session muda, filtros_behavior pode ser complexo
    }
    
    # Cria hash dos argumentos
    key_data = {
        "query": query_name,
        "args": str(args),
        "kwargs": json.dumps(cacheable_kwargs, sort_keys=True, default=str)
    }
    
    key_str = json.dumps(key_data, sort_keys=True)
    key_hash = hashlib.md5(key_str.encode()).hexdigest()
    
    return f"{query_name}:{key_hash}"


def query_cache(ttl_seconds: int = 300, query_id: Optional[str] = None):
    """
    Decorator para cache inteligente de queries.
    
    Cache com chave = (nome_da_query, hash_argumentos)
    TTL de 5 minutos (padrão)
    Invalida automaticamente quando ETL é executado
    
    Args:
        ttl_seconds: Tempo de vida do cache em segundos (padrão: 300 = 5 min)
        query_id: ID da query para estatísticas (Q1, Q2, etc.)
    
    Example:
        @query_cache(ttl_seconds=300, query_id="Q1")
        def get_clientes_sem_compra_ha_dias(...):
            ...
    
    Nota: Se kwargs contiver 'bypass_cache=True', o cache é ignorado.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            global _cache, _cache_stats
            
            # ✅ CORREÇÃO: Verifica se deve bypassar cache
            bypass_cache = kwargs.pop("bypass_cache", False)
            if bypass_cache:
                logger.info(f"[cache] Bypass cache ativado para {query_id or func.__name__}")
                # Remove bypass_cache dos kwargs antes de chamar a função
                return func(*args, **kwargs)
            
            # Identifica query
            query_name = query_id or func.__name__
            
            # Verifica se ETL foi executado recentemente
            etl_timestamp = get_etl_timestamp()
            if etl_timestamp:
                # Se ETL foi executado após o cache, invalida
                for cache_key, cache_entry in list(_cache.items()):
                    if cache_entry.get("created_at", 0) < etl_timestamp:
                        del _cache[cache_key]
                        logger.debug(f"Cache invalidado por ETL: {cache_key}")
            
            # Cria chave de cache
            cache_key = _make_cache_key(query_name, *args, **kwargs)
            
            # Inicializa estatísticas se necessário
            if query_name not in _cache_stats:
                _cache_stats[query_name] = {"hits": 0, "misses": 0}
            
            # Verifica cache
            if cache_key in _cache:
                cache_entry = _cache[cache_key]
                cache_age = time.time() - cache_entry["created_at"]
                
                if cache_age < ttl_seconds:
                    # Cache hit
                    _cache_stats[query_name]["hits"] += 1
                    logger.debug(f"Cache HIT: {cache_key} (idade: {cache_age:.1f}s)")
                    return cache_entry["result"]
                else:
                    # Cache expirado
                    del _cache[cache_key]
                    logger.debug(f"Cache expirado: {cache_key}")
            
            # Cache miss - executa função
            _cache_stats[query_name]["misses"] += 1
            from src.core.metrics import record_cache_miss
            record_cache_miss(query_name)
            logger.debug(f"Cache MISS: {cache_key}")
            
            result = func(*args, **kwargs)
            
            # Armazena no cache
            _cache[cache_key] = {
                "result": result,
                "created_at": time.time(),
                "query_name": query_name
            }
            
            return result
        
        return wrapper
    return decorator


def get_cache_stats() -> Dict[str, Dict[str, int]]:
    """Retorna estatísticas do cache."""
    return _cache_stats.copy()


def get_cache_info() -> Dict[str, Any]:
    """Retorna informações sobre o cache."""
    etl_timestamp = get_etl_timestamp()
    etl_datetime = datetime.fromtimestamp(etl_timestamp) if etl_timestamp else None
    
    return {
        "cache_size": len(_cache),
        "cache_stats": get_cache_stats(),
        "last_etl": etl_datetime.isoformat() if etl_datetime else None,
        "last_etl_timestamp": etl_timestamp
    }

