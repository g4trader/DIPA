"""
Aplicação principal FastAPI do Dipam AI.

Este módulo inicializa a aplicação FastAPI e configura as rotas principais.
A aplicação está preparada para deploy no Cloud Run.
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from datetime import datetime
import os
import logging

from config.settings import settings
from db.connection import init_db

# Configuração de logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Inicializa a aplicação FastAPI
app = FastAPI(
    title="Dipam AI API",
    description="API do assistente comercial com GenAI",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


@app.on_event("startup")
async def startup_event():
    """
    Evento de startup da aplicação.
    
    Inicializa conexões com banco de dados e outros serviços.
    """
    logger.info("Iniciando aplicação Dipam AI...")
    
    try:
        # Inicializa conexão com banco de dados
        init_db()
        logger.info("Conexão com banco de dados inicializada")
    except Exception as e:
        logger.error(f"Erro ao inicializar banco de dados: {str(e)}")
        # Em produção, você pode querer falhar rápido aqui
        # raise


@app.on_event("shutdown")
async def shutdown_event():
    """
    Evento de shutdown da aplicação.
    
    Limpa recursos e fecha conexões.
    """
    logger.info("Encerrando aplicação Dipam AI...")
    # Adicionar limpeza de recursos aqui se necessário


@app.get("/health")
async def health_check():
    """
    Endpoint de health check.
    
    Retorna o status da API e informações básicas do sistema.
    Útil para monitoramento e verificação de deploy.
    
    Returns:
        dict: Status da API com timestamp e informações do ambiente
    """
    return JSONResponse(
        content={
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "environment": settings.environment,
            "version": "1.0.0"
        }
    )


@app.get("/")
async def root():
    """
    Endpoint raiz da API.
    
    Returns:
        dict: Mensagem de boas-vindas
    """
    return {
        "message": "Welcome to Dipam AI API",
        "docs": "/docs",
        "health": "/health"
    }


# Configuração para Cloud Run
# O Cloud Run espera que a aplicação escute na porta definida pela variável PORT
if __name__ == "__main__":
    import uvicorn
    
    # Usa a porta do ambiente (Cloud Run) ou a porta configurada
    port = int(os.getenv("PORT", settings.api_port))
    
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )

