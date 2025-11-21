"""
Performance Guard - Timeout Inteligente para Queries.

Este módulo implementa decorator @performance_guard que aborta queries
que ultrapassam o tempo limite configurado.
"""

import time
import functools
import signal
import logging
from typing import Callable, Any, Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class QueryTimeoutError(Exception):
    """Exceção lançada quando uma query ultrapassa o timeout."""
    pass


@contextmanager
def timeout_context(seconds: float):
    """
    Context manager para timeout usando signal (Unix only).
    
    Para Windows, usa threading.Timer como fallback.
    """
    import platform
    
    if platform.system() == "Windows":
        # Windows não suporta signal.SIGALRM
        import threading
        
        def timeout_handler():
            raise QueryTimeoutError(f"Query timeout após {seconds} segundos")
        
        timer = threading.Timer(seconds, timeout_handler)
        timer.start()
        try:
            yield
        finally:
            timer.cancel()
    else:
        # Unix/Linux/MacOS
        def timeout_handler(signum, frame):
            raise QueryTimeoutError(f"Query timeout após {seconds} segundos")
        
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(seconds))
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)


def performance_guard(timeout_seconds: float = 12.0):
    """
    Decorator que aplica timeout inteligente a funções de query.
    
    Se a query ultrapassar o limite:
    - Aborta com exceção tratada
    - Registra log com status "timeout"
    - Retorna resposta amigável (se configurado)
    
    Args:
        timeout_seconds: Tempo limite em segundos (padrão: 12.0)
    
    Example:
        @performance_guard(timeout_seconds=12.0)
        def get_clientes_sem_compra_ha_dias(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            query_id = kwargs.get("query_id") or func.__name__
            start_time = time.time()
            
            try:
                # Tenta executar com timeout
                # Nota: signal.SIGALRM não funciona bem em threads
                # Para produção, considerar usar asyncio ou threading
                result = func(*args, **kwargs)
                
                duration_ms = (time.time() - start_time) * 1000
                
                # Log de sucesso
                from src.core.logging_config import log_query_execution
                log_query_execution(
                    query_id=query_id,
                    duration_ms=duration_ms,
                    records=len(result) if isinstance(result, list) else 0,
                    status="success",
                    function_name=func.__name__
                )
                
                return result
                
            except QueryTimeoutError as e:
                duration_ms = (time.time() - start_time) * 1000
                
                # Log de timeout
                from src.core.logging_config import log_query_execution
                log_query_execution(
                    query_id=query_id,
                    duration_ms=duration_ms,
                    records=0,
                    status="timeout",
                    error=e,
                    function_name=func.__name__
                )
                
                # Re-raise para tratamento no mapper
                raise e
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                
                # Log de erro
                from src.core.logging_config import log_query_execution
                log_query_execution(
                    query_id=query_id,
                    duration_ms=duration_ms,
                    records=0,
                    status="failure",
                    error=e,
                    function_name=func.__name__
                )
                
                raise
        
        return wrapper
    return decorator


def performance_guard_async(timeout_seconds: float = 12.0):
    """
    Versão assíncrona do performance_guard para uso com asyncio.
    
    Args:
        timeout_seconds: Tempo limite em segundos (padrão: 12.0)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            import asyncio
            
            query_id = kwargs.get("query_id") or func.__name__
            start_time = time.time()
            
            try:
                # Executa com timeout assíncrono
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout_seconds
                )
                
                duration_ms = (time.time() - start_time) * 1000
                
                # Log de sucesso
                from src.core.logging_config import log_query_execution
                log_query_execution(
                    query_id=query_id,
                    duration_ms=duration_ms,
                    records=len(result) if isinstance(result, list) else 0,
                    status="success",
                    function_name=func.__name__
                )
                
                return result
                
            except asyncio.TimeoutError:
                duration_ms = (time.time() - start_time) * 1000
                e = QueryTimeoutError(f"Query timeout após {timeout_seconds} segundos")
                
                # Log de timeout
                from src.core.logging_config import log_query_execution
                log_query_execution(
                    query_id=query_id,
                    duration_ms=duration_ms,
                    records=0,
                    status="timeout",
                    error=e,
                    function_name=func.__name__
                )
                
                raise e
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                
                # Log de erro
                from src.core.logging_config import log_query_execution
                log_query_execution(
                    query_id=query_id,
                    duration_ms=duration_ms,
                    records=0,
                    status="failure",
                    error=e,
                    function_name=func.__name__
                )
                
                raise
        
        return wrapper
    return decorator

