"""
Main entry point for Cloud Run buildpack.

Este arquivo expõe o app FastAPI na raiz do projeto para que o Cloud Run
buildpack (Gunicorn) possa encontrar o módulo main:app.

Cloud Run espera: gunicorn main:app
"""

# Importa o app do módulo src.api.main
from src.api.main import app

# Expõe app para o Gunicorn/Cloud Run
__all__ = ["app"]

