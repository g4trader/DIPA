"""
Configuração de Logging Estruturado em JSON para DIPAM Copilot.

Este módulo configura logs estruturados em formato JSON para facilitar
análise e monitoramento em Cloud Run e ambientes locais.
"""

import json
import logging
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from functools import wraps


class JSONFormatter(logging.Formatter):
    """Formatter que converte logs para JSON estruturado."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Formata o log record como JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Adiciona campos extras se existirem
        if hasattr(record, "event"):
            log_data["event"] = record.event
        if hasattr(record, "query_id"):
            log_data["query_id"] = record.query_id
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "records"):
            log_data["records"] = record.records
        if hasattr(record, "response_size_bytes"):
            log_data["response_size_bytes"] = record.response_size_bytes
        if hasattr(record, "user_prompt"):
            log_data["user_prompt"] = record.user_prompt
        if hasattr(record, "trace_id"):
            log_data["trace_id"] = record.trace_id
        if hasattr(record, "status"):
            log_data["status"] = record.status
        if hasattr(record, "function_name"):
            log_data["function_name"] = record.function_name
        if hasattr(record, "error"):
            log_data["error"] = str(record.error)
        
        # Adiciona exception info se houver
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


def setup_structured_logging(
    level: str = "INFO",
    use_json: bool = True,
    stream: Any = sys.stdout
) -> logging.Logger:
    """
    Configura logging estruturado em JSON.
    
    Args:
        level: Nível de log (DEBUG, INFO, WARNING, ERROR)
        use_json: Se True, usa formato JSON; caso contrário, usa formato padrão
        stream: Stream de saída (default: stdout)
    
    Returns:
        Logger configurado
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Remove handlers existentes
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Cria handler
    handler = logging.StreamHandler(stream)
    handler.setLevel(getattr(logging, level.upper()))
    
    # Configura formatter
    if use_json:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    
    return root_logger


def log_query_execution(
    query_id: str,
    duration_ms: float,
    records: int,
    response_size_bytes: Optional[int] = None,
    user_prompt: Optional[str] = None,
    status: str = "success",
    error: Optional[Exception] = None,
    function_name: Optional[str] = None
):
    """
    Registra execução de query com todos os campos estruturados.
    
    Args:
        query_id: ID da query (Q1, Q2, etc.)
        duration_ms: Tempo de execução em milissegundos
        records: Número de registros retornados
        response_size_bytes: Tamanho da resposta em bytes (opcional)
        user_prompt: Prompt do usuário (opcional)
        status: Status da execução (success, failure, timeout)
        error: Exceção se houver (opcional)
        function_name: Nome da função executada (opcional)
    """
    logger = logging.getLogger("dipam.queries")
    trace_id = str(uuid.uuid4())
    
    # Calcula tamanho da resposta se não fornecido
    if response_size_bytes is None and records > 0:
        # Estimativa: ~200 bytes por registro em média
        response_size_bytes = records * 200
    
    # Cria log record com campos extras
    extra = {
        "event": "query_execution",
        "query_id": query_id,
        "duration_ms": round(duration_ms, 2),
        "records": records,
        "response_size_bytes": response_size_bytes,
        "trace_id": trace_id,
        "status": status,
        "function_name": function_name or query_id,
    }
    
    if user_prompt:
        extra["user_prompt"] = user_prompt[:500]  # Limita tamanho
    
    if error:
        extra["error"] = str(error)
        logger.error("Query execution failed", extra=extra, exc_info=error)
    else:
        logger.info("Query execution completed", extra=extra)


def log_query_profile(
    query_id: str,
    duration_ms: float,
    records: int,
    db_steps: int,
    orm_objects_created: int
):
    """
    Registra perfil detalhado de execução de query.
    
    Args:
        query_id: ID da query (Q1, Q2, etc.)
        duration_ms: Tempo de execução em milissegundos
        records: Número de registros retornados
        db_steps: Número de passos no banco de dados
        orm_objects_created: Número de objetos ORM criados
    """
    logger = logging.getLogger("dipam.profiler")
    
    extra = {
        "event": "query_profile",
        "query": query_id,
        "duration_ms": round(duration_ms, 2),
        "records": records,
        "db_steps": db_steps,
        "orm_objects_created": orm_objects_created,
    }
    
    logger.info("Query profile", extra=extra)


# Inicializa logging estruturado ao importar o módulo
# Pode ser sobrescrito pela aplicação principal se necessário
_logging_initialized = False

def initialize_logging():
    """Inicializa logging estruturado (chamado uma vez)."""
    global _logging_initialized
    if not _logging_initialized:
        # Verifica se deve usar JSON (padrão: True em produção)
        use_json = os.getenv("LOG_FORMAT", "json").lower() == "json"
        setup_structured_logging(
            level=os.getenv("LOG_LEVEL", "INFO"),
            use_json=use_json
        )
        _logging_initialized = True

