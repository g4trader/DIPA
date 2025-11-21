"""
Rotas da API do Dipam AI.

Este módulo contém todas as rotas da API, organizadas por funcionalidade.
"""

from fastapi import APIRouter

# Router principal
router = APIRouter()

# Importar rotas aqui quando forem criadas
# from api.routes.health import router as health_router
# from api.routes.queries import router as queries_router

# Registrar rotas
# router.include_router(health_router, prefix="/health", tags=["health"])

__all__ = ["router"]





