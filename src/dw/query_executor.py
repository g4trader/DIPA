"""
Query Executor - Execução de Queries DW com Timeout e Logging.

Este módulo encapsula a execução de queries DW com:
- Timeout interno de 20s
- Logging completo [PERF_STEP]
- Tratamento de erros estruturado
- Preparação para futura execução assíncrona
"""

import time
import logging
from typing import Dict, Any, Optional, Callable, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import StatementError, OperationalError, TimeoutError as SQLTimeoutError
from sqlalchemy import text

from src.core.performance_guard import QueryTimeoutError

logger = logging.getLogger(__name__)

# Timeout padrão para queries DW (20 segundos)
DW_QUERY_TIMEOUT_SECONDS = 20


def run_dw_query_q1(
    session: Session,
    params: Dict[str, Any],
    query_func: Callable
) -> Dict[str, Any]:
    """
    Executa query Q1 com timeout interno e logging [PERF_STEP].
    
    Esta função encapsula a execução da query Q1, garantindo:
    - Timeout de 20s
    - Logging completo (START_DW_QUERY, END_DW_QUERY)
    - Tratamento de erros estruturado
    - Retorno consistente mesmo em caso de timeout/erro
    
    FUTURO: Esta função pode ser substituída por enfileiramento de job assíncrono
    (Cloud Tasks / PubSub) sem alterar a interface do handler.
    
    Args:
        session: Sessão SQLAlchemy
        params: Parâmetros da query (dias, data_referencia, filtros_behavior, etc.)
        query_func: Função de query a ser executada (ex.: get_clientes_sem_compra_ha_dias)
        
    Returns:
        dict com estrutura:
        {
            "status": "ok" | "timeout" | "error",
            "data": List[Dict] ou None,
            "error": str ou None,
            "duration_ms": int
        }
    """
    query_id = params.get("query_id", "Q1")
    start_time = time.perf_counter()
    
    logger.info(
        f"[PERF_STEP] START_DW_QUERY - query_id={query_id}, "
        f"dias={params.get('dias', 'N/A')}, "
        f"data_referencia={params.get('data_referencia', 'N/A')}"
    )
    
    try:
        # ✅ TIMEOUT: Configura timeout na sessão SQLAlchemy
        # Para SQLite, usa timeout via PRAGMA
        # Para PostgreSQL, usa statement_timeout
        db_type = session.bind.dialect.name if session.bind else "sqlite"
        
        if db_type == "sqlite":
            # SQLite: configura timeout de conexão (não query individual)
            # Para timeout de query, precisamos usar threading ou asyncio
            # Por enquanto, confiamos no performance_guard
            pass
        elif db_type == "postgresql":
            # PostgreSQL: configura statement_timeout na sessão
            try:
                session.execute(text(f"SET statement_timeout = {DW_QUERY_TIMEOUT_SECONDS * 1000}"))
                session.commit()
            except Exception as e:
                logger.warning(f"[run_dw_query_q1] Não foi possível configurar statement_timeout: {e}")
        
        # Executa query com timeout usando threading (fallback para signal.SIGALRM)
        import threading
        from queue import Queue
        
        result_queue = Queue()
        error_queue = Queue()
        
        def execute_query():
            try:
                result = query_func(session=session, **params)
                result_queue.put(("success", result))
            except Exception as e:
                error_queue.put(e)
        
        # Inicia thread para executar query
        query_thread = threading.Thread(target=execute_query, daemon=True)
        query_thread.start()
        query_thread.join(timeout=DW_QUERY_TIMEOUT_SECONDS)
        
        # Verifica se thread terminou
        if query_thread.is_alive():
            # Thread ainda está rodando = timeout
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"[PERF_STEP] END_DW_QUERY - status=timeout, "
                f"query_id={query_id}, duration={duration_ms:.2f}ms"
            )
            
            return {
                "status": "timeout",
                "data": None,
                "error": "A consulta de dados demorou mais do que o tempo máximo configurado (20s).",
                "error_type": "DW_TIMEOUT",
                "hint": "Sugira no front ao usuário ajustar o período ou refazer a pergunta.",
                "duration_ms": int(duration_ms)
            }
        
        # Verifica se houve erro
        if not error_queue.empty():
            error = error_queue.get()
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"[PERF_STEP] END_DW_QUERY - status=error, "
                f"query_id={query_id}, duration={duration_ms:.2f}ms, error={str(error)}"
            )
            
            return {
                "status": "error",
                "data": None,
                "error": str(error),
                "error_type": "DW_ERROR",
                "duration_ms": int(duration_ms)
            }
        
        # Verifica se houve resultado
        if not result_queue.empty():
            status, result = result_queue.get()
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                f"[PERF_STEP] END_DW_QUERY - status=ok, "
                f"query_id={query_id}, duration={duration_ms:.2f}ms, "
                f"records={len(result) if isinstance(result, list) else 0}"
            )
            
            return {
                "status": "ok",
                "data": result,
                "error": None,
                "duration_ms": int(duration_ms)
            }
        
        # Caso inesperado: thread terminou mas não há resultado nem erro
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.error(
            f"[PERF_STEP] END_DW_QUERY - status=unknown, "
            f"query_id={query_id}, duration={duration_ms:.2f}ms"
        )
        
        return {
            "status": "error",
            "data": None,
            "error": "Erro inesperado na execução da query.",
            "error_type": "DW_UNKNOWN_ERROR",
            "duration_ms": int(duration_ms)
        }
        
    except QueryTimeoutError as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.error(
            f"[PERF_STEP] END_DW_QUERY - status=timeout, "
            f"query_id={query_id}, duration={duration_ms:.2f}ms"
        )
        
        return {
            "status": "timeout",
            "data": None,
            "error": "A consulta de dados demorou mais do que o tempo máximo configurado (20s).",
            "error_type": "DW_TIMEOUT",
            "hint": "Sugira no front ao usuário ajustar o período ou refazer a pergunta.",
            "duration_ms": int(duration_ms)
        }
        
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.error(
            f"[PERF_STEP] END_DW_QUERY - status=error, "
            f"query_id={query_id}, duration={duration_ms:.2f}ms, error={str(e)}"
        )
        import traceback
        logger.error(traceback.format_exc())
        
        return {
            "status": "error",
            "data": None,
            "error": str(e),
            "error_type": "DW_ERROR",
            "duration_ms": int(duration_ms)
        }

