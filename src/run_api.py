#!/usr/bin/env python3
"""
Script CLI para iniciar a API FastAPI do Agente Comercial.

Este script inicializa e executa a API FastAPI que expõe
endpoints para interação com o agente de IA comercial.

Uso:
    python -m src.run_api
"""

import sys
import os
from pathlib import Path
import uvicorn

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from src.api.main import app
from src.config import config


def main():
    """Função principal."""
    # Configuração do servidor
    host = os.getenv("API_HOST", getattr(config, 'api_agent_host', '0.0.0.0'))
    port = int(os.getenv("PORT", os.getenv("API_PORT", getattr(config, 'api_agent_port', 8000))))
    
    # Reload em desenvolvimento
    reload = getattr(config, 'debug', False)
    
    # Log level
    log_level = getattr(config, 'log_level', 'info').lower()
    
    print("=" * 60)
    print("Dipam AI - API do Agente Comercial")
    print("=" * 60)
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Reload: {reload}")
    print(f"Log Level: {log_level}")
    print()
    print("Documentação:")
    print(f"  Swagger UI: http://{host}:{port}/docs")
    print(f"  ReDoc: http://{host}:{port}/redoc")
    print()
    print("Endpoints principais:")
    print(f"  POST http://{host}:{port}/ask")
    print(f"  GET  http://{host}:{port}/health")
    print(f"  GET  http://{host}:{port}/preview/vendedor/{{vendedor}}/{{mes_ano}}")
    print()
    print("=" * 60)
    print("Iniciando servidor...")
    print("=" * 60)
    print()
    
    # Inicia servidor
    if reload:
        # Para reload, precisa passar como string de import
        uvicorn.run(
            "src.api.main:app",
            host=host,
            port=port,
            reload=reload,
            log_level=log_level
        )
    else:
        # Para produção, pode passar o app diretamente
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=False,
            log_level=log_level
        )


if __name__ == "__main__":
    main()

