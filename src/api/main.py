"""
API FastAPI do Agente de IA Comercial - Dipam AI.

Este módulo expõe endpoints REST para o agente conversacional,
permitindo interação em linguagem natural com os dados da empresa.
"""

from fastapi import FastAPI, HTTPException, Depends, Query, Path as FastAPIPath, Request
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path
import logging
import os
import re

from src.config import config
from src.dw.connection import init_db, get_db_session, get_db_engine
from src.agent.service import get_agent_service
from src.agent.queries import query_vendedor_meta
from src.dw.models import InteracaoAgent
from sqlalchemy.orm import Session
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializa aplicação FastAPI
app = FastAPI(
    title="Dipam AI - Agente Comercial",
    description="API do agente de IA comercial para análise de vendas, metas e churn",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware (para permitir chamadas de frontend)
# IMPORTANTE: Em produção, especificar origens permitidas explicitamente
# Isso evita problemas de CORS e melhora a segurança
# REGRA CRÍTICA: NÃO colocar barra no final das origens (ex.: NUNCA usar "https://dipam.smartiasolutions.com.br/")
allowed_origins = [
    # Produção
    "https://dipam.smartiasolutions.com.br",  # URL correta
    "https://dipam-copilot-frontend-6arhlm3mha-uc.a.run.app",
    # Local development
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

# Em desenvolvimento, adicionar localhost:8000 e localhost:8080 para testes locais
if config.environment == "development":
    allowed_origins.extend([
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ])

# CORSMiddleware padrão (primeira camada)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Middleware CORS manual por cima de TUDO (segunda camada - garante CORS mesmo em erros)
# IMPORTANTE: Este middleware NÃO interfere com requisições OPTIONS (preflight)
# porque os handlers OPTIONS já adicionam os headers corretos
@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    """
    Middleware HTTP que SEMPRE adiciona headers CORS, mesmo em erros.
    Esta é uma camada extra de segurança para garantir que TODAS as respostas
    (200, 4xx, 5xx, 503) incluam headers CORS corretos.
    
    IMPORTANTE: Requisições OPTIONS (preflight) são tratadas pelos handlers específicos
    e não passam por este middleware para adicionar headers duplicados.
    """
    # Se for requisição OPTIONS, deixa os handlers específicos tratarem
    # (mas ainda processa para garantir que erros também tenham CORS)
    try:
        response = await call_next(request)
    except Exception as exc:
        # Se der erro dentro da aplicação, ainda assim queremos CORS
        logger.error(f"Erro capturado no middleware CORS: {str(exc)}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Cria resposta de erro com CORS
        response = Response(
            content='{"detail": "Internal server error"}',
            status_code=500,
            media_type="application/json",
        )
    
    # IMPORTANTE: Se a resposta já tem Access-Control-Allow-Origin (vindo de handler OPTIONS),
    # não sobrescreve para evitar conflitos
    if "Access-Control-Allow-Origin" in response.headers:
        # Headers CORS já foram adicionados pelo handler OPTIONS ou CORSMiddleware
        return response
    
    # Adiciona headers CORS se a origem for permitida (para respostas que não são OPTIONS)
    origin = request.headers.get("origin")
    if origin:
        if origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            
            # Garante que caches respeitem origem
            vary = response.headers.get("Vary")
            if vary:
                if "Origin" not in vary:
                    response.headers["Vary"] = vary + ", Origin"
            else:
                response.headers["Vary"] = "Origin"
        else:
            logger.warning(f"[CORS middleware] Origem não permitida: {origin} (permitidas: {allowed_origins})")
    else:
        # Se não há origin header, pode ser uma requisição same-origin ou sem CORS
        # Não adiciona headers CORS neste caso
        pass
    
    return response

# Handler OPTIONS específico para /ask (DEVE vir ANTES do handler genérico)
# IMPORTANTE: Handlers específicos têm prioridade sobre genéricos no FastAPI
@app.options("/ask")
async def options_ask(request: Request):
    """
    Handler OPTIONS específico para /ask - garante que preflight funcione corretamente.
    Este handler tem prioridade sobre o handler genérico.
    """
    origin = request.headers.get("origin")
    request_method = request.headers.get("Access-Control-Request-Method", "POST")
    request_headers = request.headers.get("Access-Control-Request-Headers", "Content-Type")
    
    logger.info(f"[CORS OPTIONS /ask] origin={origin}, method={request_method}, headers={request_headers}")
    
    response = Response(status_code=200)
    
    # IMPORTANTE: Sempre adiciona headers CORS se a origem estiver na lista
    if origin and origin in allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS, GET"
        response.headers["Access-Control-Allow-Headers"] = request_headers or "Content-Type, Authorization"
        response.headers["Access-Control-Max-Age"] = "600"
        response.headers["Vary"] = "Origin"
        logger.info(f"[CORS OPTIONS /ask] ✅ Headers CORS adicionados para origem: {origin}")
    else:
        logger.warning(f"[CORS OPTIONS /ask] ❌ Origem não permitida: {origin} (permitidas: {allowed_origins})")
        # Mesmo assim, adiciona headers básicos (mas sem Access-Control-Allow-Origin para manter segurança)
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS, GET"
        response.headers["Access-Control-Allow-Headers"] = request_headers or "Content-Type, Authorization"
        response.headers["Vary"] = "Origin"
    
    return response

# Handler global para OPTIONS (preflight) - funciona para QUALQUER rota
# IMPORTANTE: Este handler genérico é usado apenas se não houver handler específico
@app.options("/{path:path}")
async def options_cors_handler(path: str, request: Request):
    """
    Handler genérico de preflight CORS para qualquer rota.
    Este endpoint captura TODAS as requisições OPTIONS que não têm handler específico.
    """
    origin = request.headers.get("origin")
    request_method = request.headers.get("Access-Control-Request-Method", "POST")
    request_headers = request.headers.get("Access-Control-Request-Headers", "Content-Type")
    
    # Log para debug
    logger.info(f"[CORS OPTIONS genérico] path={path}, origin={origin}, method={request_method}")
    
    response = Response(status_code=200)
    
    # IMPORTANTE: Sempre adiciona headers CORS se a origem estiver na lista
    if origin and origin in allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = request_method or "POST, GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = request_headers or "Content-Type, Authorization"
        response.headers["Access-Control-Max-Age"] = "600"
        response.headers["Vary"] = "Origin"
        logger.info(f"[CORS OPTIONS genérico] ✅ Headers CORS adicionados para origem: {origin}")
    else:
        logger.warning(f"[CORS OPTIONS genérico] ❌ Origem não permitida: {origin} (permitidas: {allowed_origins})")
        # Mesmo assim, adiciona headers básicos para evitar erro completo
        # (mas sem Access-Control-Allow-Origin para manter segurança)
        response.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = request_headers or "Content-Type, Authorization"
        response.headers["Vary"] = "Origin"
    
    return response


# Inicializa flags de estado da aplicação (para health checks)
# IMPORTANTE: Essas flags são setadas no startup_event e usadas pelos endpoints de health
# O servidor SEMPRE sobe, mesmo que DB ou OpenAI falhem - os health endpoints reportam o status
app.state.db_available = False
app.state.openai_available = False
app.state.agent_service_available = False
app.state.startup_errors = []

# Eventos de startup/shutdown
@app.on_event("startup")
async def startup_event():
    """
    Evento de startup da aplicação.
    
    IMPORTANTE: Este evento NUNCA deve fazer raise ou derrubar o container.
    Em vez disso, seta flags em app.state que são usadas pelos health endpoints.
    Isso garante que o servidor sempre sobe e os health checks podem reportar problemas.
    """
    logger.info("Iniciando aplicação Dipam AI Agent...")
    
    # Limpa erros anteriores (se houver restart)
    app.state.startup_errors = []
    
    # 1. Validação de LLM (OpenAI ou Groq) - não crítica para o servidor subir
    logger.info("Verificando configuração LLM (OpenAI/Groq)...")
    try:
        from src.llm_client import get_llm_config, get_llm_provider
        provider = get_llm_provider()
        llm_config = get_llm_config(provider)  # Renomeado para não sobrescrever config global
        if llm_config:
            app.state.openai_available = True  # Mantém nome para compatibilidade
            app.state.llm_provider = provider
            logger.info(f"✅ LLM configurado: {provider.upper()} (model={llm_config['model']})")
        else:
            logger.warning("⚠️  LLM client retornou None")
            app.state.startup_errors.append("LLM: client retornou None")
    except Exception as e:
        error_msg = f"LLM não configurado (GROQ_API_KEY ou OPENAI_API_KEY): {str(e)}"
        logger.error(f"❌ {error_msg}")
        app.state.startup_errors.append(error_msg)
        logger.warning("⚠️  Servidor continuará funcionando, mas funcionalidades de LLM podem não estar disponíveis")
        # NÃO faz raise - apenas registra o erro
    
    # 2. Validação e inicialização do banco de dados (não crítica para o servidor subir)
    logger.info("Verificando configuração de banco de dados...")
    try:
        db_connection_string = config.database.connection_string
        if not db_connection_string:
            raise ValueError("DATABASE_URL ou configuração de banco não encontrada")
        logger.info(f"✅ Configuração de banco de dados validada: {config.database.db_type}")
        
        # Garante que o SQLite está disponível (baixa do GCS se necessário)
        # Isso deve ser feito ANTES de inicializar a conexão
        if config.database.db_type == "sqlite":
            try:
                from src.dw.bootstrap_dw import ensure_sqlite_dw_available
                ensure_sqlite_dw_available()
            except Exception as e:
                error_msg = f"Erro ao garantir SQLite disponível: {str(e)}"
                logger.error(f"❌ {error_msg}")
                app.state.startup_errors.append(error_msg)
                # Não bloqueia o startup, mas registra o erro
        
        # Verifica arquivo SQLite se estiver usando SQLite (após possível download)
        if config.database.db_type == "sqlite":
            sqlite_path = config.database.sqlite_path  # Isso já cria o diretório se necessário
            logger.info(f"Usando SQLite - Caminho: {sqlite_path}")
            
            # Verifica se o arquivo existe (após possível download do GCS)
            if os.path.exists(sqlite_path):
                file_size = os.path.getsize(sqlite_path)
                logger.info(f"✅ Arquivo SQLite encontrado - Tamanho: {file_size / (1024*1024):.2f} MB")
            else:
                logger.warning(f"⚠️  Arquivo SQLite não encontrado: {sqlite_path}")
                logger.info(f"   Diretório pai existe? {os.path.exists(os.path.dirname(sqlite_path))}")
        
        # Inicializa conexão com banco de dados
        init_db()
        logger.info("Conexão com banco de dados inicializada")
        
        # Garante que estruturas de aplicação existam (behavior_rules, intent_prevista)
        # Isso deve ser feito APÓS init_db() para ter o engine disponível
        try:
            from src.dw.bootstrap_schema import ensure_application_schema
            from src.dw.connection import get_db_engine
            
            engine = get_db_engine()
            ensure_application_schema(engine)
            logger.info("✅ Schema de aplicação verificado/criado")
        except Exception as e:
            error_msg = f"Erro ao garantir schema de aplicação: {str(e)}"
            logger.warning(f"⚠️  {error_msg}")
            app.state.startup_errors.append(error_msg)
            # Não bloqueia o startup, apenas registra o erro
        
        # Marca banco como disponível se init_db não deu erro
        # IMPORTANTE: NÃO faz teste de conexão síncrono aqui para não bloquear startup
        # O teste de conexão será feito no primeiro request ou no endpoint /health/db
        app.state.db_available = True
        logger.info("✅ Banco de dados configurado (teste de conexão será feito sob demanda)")
        
    except Exception as e:
        error_msg = f"Erro ao inicializar banco de dados: {str(e)}"
        logger.error(f"❌ {error_msg}")
        import traceback
        logger.error(traceback.format_exc())
        app.state.startup_errors.append(error_msg)
        logger.warning("⚠️  Servidor continuará funcionando, mas consultas ao banco podem falhar")
        # NÃO faz raise - apenas registra o erro
    
    # 3. Carrega modelos de ML (não crítico para o servidor subir)
    # IMPORTANTE: Modelos ML podem demorar para carregar (~20s para arquivos grandes)
    # Em vez de bloquear o startup, carregamos de forma assíncrona após o servidor subir
    # O servidor sobe imediatamente e os modelos são carregados em background
    # Isso evita timeouts do Cloud Run (container precisa responder rápido no startup)
    logger.info("Carregando modelos de ML em background...")
    from threading import Thread
    
    def load_models_async():
        """Carrega modelos ML em thread separada para não bloquear startup"""
        try:
            logger.info("📦 Iniciando carregamento de modelos ML em background...")
            agent_service = get_agent_service()
            if agent_service:
                # Aguarda um pouco para garantir que a inicialização terminou
                import time
                max_wait = 60  # 60 segundos máximo
                wait_interval = 1  # Verifica a cada 1 segundo
                waited = 0
                
                while not agent_service.is_ready() and waited < max_wait:
                    time.sleep(wait_interval)
                    waited += wait_interval
                    if waited % 5 == 0:  # Log a cada 5 segundos
                        logger.info(f"⏳ Aguardando AgentService ficar pronto... ({waited}s/{max_wait}s)")
                
                if agent_service.is_ready():
                    app.state.agent_service_available = True
                    logger.info("✅ Modelos de ML carregados com sucesso - AgentService está pronto")
                else:
                    last_error = agent_service.get_last_error()
                    error_msg = f"AgentService não ficou pronto após {max_wait}s"
                    if last_error:
                        error_msg += f" - Último erro: {last_error}"
                    logger.warning(f"⚠️  {error_msg}")
                    app.state.startup_errors.append(error_msg)
                    # Mesmo assim, marca como disponível se o serviço existe (pode funcionar parcialmente)
                    # O endpoint /ask fará lazy loading se necessário
                    app.state.agent_service_available = True
                    logger.warning("⚠️  AgentService marcado como disponível (lazy loading será tentado no /ask se necessário)")
            else:
                logger.warning("⚠️  AgentService retornou None")
                app.state.startup_errors.append("AgentService: retornou None")
        except Exception as e:
            error_msg = f"Erro ao carregar modelos de ML: {str(e)}"
            logger.error(f"❌ {error_msg}")
            import traceback
            logger.error(traceback.format_exc())
            app.state.startup_errors.append(error_msg)
            logger.warning("⚠️  Modelos ML não carregados, mas servidor continua funcionando")
    
    # Inicia carregamento em thread separada (daemon=True para não bloquear shutdown)
    thread = Thread(target=load_models_async, daemon=True, name="LoadModelsThread")
    thread.start()
    logger.info("🚀 Servidor pronto - modelos ML carregando em background (não bloqueia requests)")
    
    # Resumo final do startup
    if app.state.startup_errors:
        logger.warning(f"⚠️  Startup concluído com {len(app.state.startup_errors)} erro(s) (servidor funcionando):")
        for error in app.state.startup_errors:
            logger.warning(f"   - {error}")
    else:
        logger.info("✅ Startup concluído com sucesso - todos os componentes disponíveis")


@app.on_event("shutdown")
async def shutdown_event():
    """Evento de shutdown da aplicação."""
    logger.info("Encerrando aplicação Dipam AI Agent...")


# Modelos Pydantic para requisições/respostas
class AskRequest(BaseModel):
    """Modelo de requisição para endpoint /ask."""
    pergunta: str = Field(..., description="Pergunta do usuário em linguagem natural")
    usuario_id: Optional[str] = Field(None, description="ID do usuário")
    papel: Optional[str] = Field(None, description="Papel do usuário ('diretor', 'supervisor', 'vendedor')")
    
    class Config:
        schema_extra = {
            "example": {
                "pergunta": "Por que a equipe do Supervisor X não bateu a meta em janeiro?",
                "usuario_id": "user123",
                "papel": "diretor"
            }
        }


class KpisData(BaseModel):
    """Dados de KPIs para resposta estruturada."""
    mesAnoLabel: str = Field(..., description="Label do mês/ano (ex.: 'agosto de 2025')")
    vendedoresQueBateram: int = Field(..., description="Número de vendedores que bateram a meta")
    atingimentoMedio: float = Field(..., description="Atingimento médio percentual")


class TopVendedor(BaseModel):
    """Dados de um vendedor no ranking."""
    rank: int = Field(..., description="Posição no ranking")
    nome: str = Field(..., description="Nome do vendedor (ex.: 'ROTA 77')")
    rota: Optional[str] = Field(None, description="Rota do vendedor (opcional)")
    supervisor: Optional[str] = Field(None, description="Supervisor (opcional)")
    meta: float = Field(..., description="Meta do vendedor")
    realizado: float = Field(..., description="Realizado do vendedor")
    atingimento: float = Field(..., description="Atingimento percentual")


class CopilotAnswerPayloadModel(BaseModel):
    """Modelo Pydantic para CopilotAnswerPayload."""
    intent: str
    intentLabel: str
    confidence: float
    question: str
    resumoExecutivo: Optional[str] = None
    insights: Optional[str] = None
    observacoes: Optional[str] = None
    kpis: Optional[KpisData] = None
    topVendedores: Optional[List[TopVendedor]] = None
    respostaMarkdown: Optional[str] = None


class AskResponse(BaseModel):
    """Modelo de resposta do endpoint /ask."""
    question: str = Field(..., description="Pergunta original do usuário")
    intent: str = Field(..., description="Intenção detectada")
    confidence: float = Field(..., description="Confiança da resposta (0-1)")
    resumoExecutivo: str = Field(..., description="Resumo executivo extraído da resposta")
    kpis: Optional[KpisData] = Field(None, description="KPIs estruturados (opcional)")
    topVendedores: Optional[List[TopVendedor]] = Field(None, description="Top vendedores (opcional)")
    insights: Optional[List[str]] = Field(None, description="Lista de insights/recomendações (opcional)")
    observacoes: Optional[List[str]] = Field(None, description="Lista de observações sobre os dados (opcional)")
    contexto: Dict[str, Any] = Field(default_factory=dict, description="Contexto de dados usado")
    timestamp: str = Field(..., description="Timestamp da resposta")
    # Payload estruturado para o CopilotAnswerCard
    payload: Optional[Dict[str, Any]] = Field(None, description="Payload estruturado CopilotAnswerPayload")
    # NOVO FASE 3: Resposta estruturada completa (CopilotStructuredResponse)
    structured: Optional[Dict[str, Any]] = Field(None, description="Resposta estruturada completa com secoes, detalhe_tabela, contexto_debug")
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "Como estão as metas de agosto 2025?",
                "intent": "consulta_meta",
                "confidence": 0.9,
                "resumoExecutivo": "As metas de agosto de 2025 apresentaram um atingimento médio de 116.33%...",
                "kpis": {
                    "mesAnoLabel": "agosto de 2025",
                    "vendedoresQueBateram": 24,
                    "atingimentoMedio": 116.33
                },
                "topVendedores": [
                    {
                        "rank": 1,
                        "nome": "ROTA 77",
                        "meta": 278679.57,
                        "realizado": 469962.21,
                        "atingimento": 168.64
                    }
                ],
                "insights": [
                    "Revisar mix de produtos para vendedores abaixo da meta",
                    "Ajustar rota para otimizar visitas"
                ],
                "observacoes": [
                    "Dados disponíveis apenas para os últimos 6 meses"
                ]
            }
        }


class PreviewVendedorResponse(BaseModel):
    """Modelo de resposta do endpoint /preview/vendedor."""
    vendedor: str
    mes_ano: str
    dados: Dict[str, Any]
    timestamp: str


class FeedbackRequest(BaseModel):
    """Modelo de requisição para endpoint /feedback/{interacao_id}."""
    sucesso: bool = Field(..., description="True se a resposta foi útil, False caso contrário")
    comentario: Optional[str] = Field(None, description="Comentário opcional do usuário sobre a resposta")
    
    class Config:
        schema_extra = {
            "example": {
                "sucesso": True,
                "comentario": "Resposta muito clara e útil para entender a situação da meta."
            }
        }


class FeedbackRequestFase4(BaseModel):
    """Modelo de requisição para endpoint /feedback (FASE 4 - novo formato)."""
    interacao_id: int = Field(..., description="ID da interação a receber feedback", gt=0)
    feedback_qualidade: int = Field(..., description="Qualidade da resposta em escala 1-5", ge=1, le=5)
    feedback_comentario: Optional[str] = Field(None, description="Comentário opcional do Diretor (máx. 2000 caracteres)", max_length=2000)
    
    class Config:
        schema_extra = {
            "example": {
                "interacao_id": 123,
                "feedback_qualidade": 4,
                "feedback_comentario": "Resposta boa, mas poderia detalhar mais os clientes em risco."
            }
        }


class FeedbackResponse(BaseModel):
    """Modelo de resposta do endpoint /feedback/{interacao_id}."""
    mensagem: str
    interacao_id: int
    sucesso: bool


# Endpoints
@app.get("/health")
async def health_check():
    """
    Endpoint de health check básico.
    
    Retorna status da API, informações básicas do sistema e status dos componentes.
    IMPORTANTE: Este endpoint SEMPRE retorna 200 se o servidor estiver rodando,
    mesmo que componentes individuais (DB, OpenAI) estejam com problemas.
    """
    try:
        environment = getattr(config, 'environment', 'development')
        
        # Calcula status geral baseado nos componentes
        status = "healthy"
        if not app.state.db_available or not app.state.openai_available:
            status = "degraded"  # Funciona, mas com limitações
        
        health_data = {
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "environment": environment,
            "version": "1.0.0",
            "database": config.database.db_type,
            "components": {
                "database": "available" if app.state.db_available else "unavailable",
                "openai": "available" if app.state.openai_available else "unavailable",
                "agent_service": "available" if app.state.agent_service_available else "unavailable"
            }
        }
        
        # Adiciona erros se houver
        if app.state.startup_errors:
            health_data["startup_errors"] = app.state.startup_errors
            health_data["warnings"] = f"{len(app.state.startup_errors)} componente(s) com problemas"
        
        # Retorna 200 mesmo com problemas - o status indica "degraded"
        return JSONResponse(content=health_data)
    except Exception as e:
        logger.error(f"Erro ao verificar saúde da aplicação: {str(e)}")
        # Retorna 503 apenas se houver erro no próprio endpoint
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@app.get("/health/dw")
async def health_dw():
    """
    Endpoint de health check específico do Data Warehouse SQLite.
    
    Verifica se o arquivo SQLite existe e se é possível executar uma query simples.
    Retorna 200 se OK, 500 se houver erro.
    """
    db_type = os.getenv("DB_TYPE", config.database.db_type)
    
    if db_type != "sqlite":
        return JSONResponse(
            status_code=200,
            content={
                "status": "ok",
                "message": "DB_TYPE != sqlite, DW healthcheck ignorado",
                "db_type": db_type
            }
        )
    
    sqlite_path_str = os.getenv("SQLITE_PATH", config.database.sqlite_path)
    sqlite_path = Path(sqlite_path_str) if sqlite_path_str else None
    
    try:
        # Verifica se o arquivo existe
        if not sqlite_path or not sqlite_path.exists():
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": "DW SQLite não acessível",
                    "detail": f"Arquivo não encontrado: {sqlite_path}",
                    "path": str(sqlite_path) if sqlite_path else None
                }
            )
        
        # Tenta abrir uma conexão e executar uma query simples
        from src.dw.connection import get_db_session
        from sqlalchemy import text
        
        session = next(get_db_session())
        try:
            # Executa query simples para verificar se o banco está acessível
            # Tenta várias tabelas possíveis (dim_cliente, clientes, dim_tempo)
            query_executed = False
            for table_name in ["dim_cliente", "clientes", "dim_tempo", "vendedores"]:
                try:
                    result = session.execute(text(f"SELECT 1 FROM {table_name} LIMIT 1"))
                    result.fetchone()
                    query_executed = True
                    break
                except Exception:
                    continue
            
            if not query_executed:
                raise RuntimeError("Nenhuma tabela conhecida encontrada no banco")
            
            return JSONResponse(
                status_code=200,
                content={
                    "status": "ok",
                    "message": "DW SQLite acessível",
                    "path": str(sqlite_path),
                    "size_mb": round(sqlite_path.stat().st_size / (1024 * 1024), 2)
                }
            )
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"[health/dw] Erro ao verificar DW: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "DW SQLite não acessível",
                "detail": str(e),
                "path": str(sqlite_path) if sqlite_path else None
            }
        )


@app.get("/health/db")
async def health_check_db():
    """
    Endpoint de health check do banco de dados.
    
    Testa a conexão com o banco de dados executando uma query simples.
    IMPORTANTE: Retorna 503 se o banco não estiver disponível, mas o servidor continua rodando.
    """
    # Verifica flag do startup primeiro
    if not app.state.db_available:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": config.database.db_type,
                "connected": False,
                "error": "Database não disponível (verifique logs do startup)",
                "startup_errors": [e for e in app.state.startup_errors if "banco" in e.lower() or "database" in e.lower() or "sqlite" in e.lower()],
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
    
    try:
        from sqlalchemy import text
        engine = get_db_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.scalar()
        
        # Tenta contar registros em uma tabela chave
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM metas_vendedor LIMIT 1"))
                count = result.scalar()
                return JSONResponse(
                    content={
                        "status": "healthy",
                        "database": config.database.db_type,
                        "connected": True,
                        "test_query": "success",
                        "metas_vendedor_count": count,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
        except Exception as e:
            logger.warning(f"Erro ao contar registros em metas_vendedor: {str(e)}")
            # Atualiza flag se conexão falhar durante runtime
            app.state.db_available = False
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "database": config.database.db_type,
                    "connected": False,
                    "error": f"Não foi possível contar registros: {str(e)}",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
    except Exception as e:
        logger.error(f"Erro ao verificar saúde do banco de dados: {str(e)}")
        # Atualiza flag se conexão falhar durante runtime
        app.state.db_available = False
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": config.database.db_type,
                "connected": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )


@app.get("/health/agent")
async def health_agent():
    """
    Health check específico do AgentService.
    
    Retorna o status de readiness do agente de IA, incluindo:
    - Se está pronto para processar perguntas
    - Último erro ocorrido (se houver)
    - Timestamp da verificação
    
    Returns:
        JSON com status do AgentService
    """
    try:
        agent_service = get_agent_service()
        
        if agent_service is None:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not_ready",
                    "ready": False,
                    "last_error": "AgentService não pôde ser criado",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
        
        is_ready = agent_service.is_ready()
        last_error = agent_service.get_last_error()
        
        status_code = 200 if is_ready else 503
        
        return JSONResponse(
            status_code=status_code,
            content={
                "status": "ready" if is_ready else "not_ready",
                "ready": is_ready,
                "last_error": last_error,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
    except Exception as e:
        logger.error(f"Erro ao verificar health do agent: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "ready": False,
                "last_error": f"Erro ao verificar status: {str(e)}",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )


@app.get("/health/openai")
async def health_check_openai():
    """
    Endpoint de health check da OpenAI.
    
    Testa a conexão com a API da OpenAI fazendo uma chamada mínima.
    IMPORTANTE: Retorna 503 se OpenAI não estiver disponível, mas o servidor continua rodando.
    """
    # Verifica flag do startup primeiro
    if not app.state.openai_available:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "openai_configured": False,
                "openai_connected": False,
                "error": "OpenAI não disponível (verifique logs do startup)",
                "startup_errors": [e for e in app.state.startup_errors if "openai" in e.lower() or "api_key" in e.lower()],
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
    
    try:
        from src.llm_client import get_llm_config, get_llm_provider
        
        # Valida configuração (detecta automaticamente Groq ou OpenAI)
        try:
            provider = get_llm_provider()
            client_config = get_llm_config(provider)
        except Exception as e:
            logger.error(f"Erro ao obter configuração LLM: {str(e)}")
            app.state.openai_available = False
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unavailable",
                    "message": f"LLM não configurado: {str(e)}",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
        
        if not client_config:
            app.state.openai_available = False
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "openai_configured": False,
                    "openai_connected": False,
                    "error": "OpenAI client retornou None",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
        
        # Faz uma chamada mínima de teste (apenas validação, sem gerar resposta completa)
        try:
            # Testa apenas se a chave é válida fazendo uma chamada muito simples
            test_response = call_llm(
                prompt="Responda apenas: OK",
                system_prompt="Você é um assistente de teste. Responda apenas 'OK'.",
                max_tokens=5,
                temperature=0
            )
            
            if test_response:
                return JSONResponse(
                    content={
                        "status": "healthy",
                        "openai_configured": True,
                        "openai_connected": True,
                        "test_response_length": len(test_response),
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
            else:
                app.state.openai_available = False
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "unhealthy",
                        "openai_configured": True,
                        "openai_connected": False,
                        "error": "Chamada de teste retornou None",
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
        except Exception as e:
            logger.error(f"Erro ao testar chamada OpenAI: {str(e)}")
            app.state.openai_available = False
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "openai_configured": True,
                    "openai_connected": False,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
    except Exception as e:
        logger.error(f"Erro ao verificar saúde da OpenAI: {str(e)}")
        app.state.openai_available = False
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "openai_configured": False,
                "openai_connected": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )


@app.get("/")
async def root():
    """
    Endpoint raiz da API.
    
    Returns:
        dict: Mensagem de boas-vindas e informações da API
    """
    return {
        "message": "Bem-vindo à API do Agente Comercial Dipam AI",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "/ask": "Pergunte ao agente em linguagem natural",
            "/preview/vendedor/{vendedor}/{mes_ano}": "Visualize dados de um vendedor/mês",
        }
    }


def _extrair_secao_markdown(texto: str, secao: str) -> Optional[str]:
    """
    Extrai o conteúdo de uma seção markdown do texto.
    
    Args:
        texto: Texto markdown completo
        secao: Nome da seção a extrair (ex.: "Resumo executivo", "Insights e recomendações")
        
    Returns:
        Conteúdo da seção ou None se não encontrar
    """
    # Padrões possíveis para o cabeçalho da seção
    patterns = [
        rf"##\s+{re.escape(secao)}[^\n]*\n(.*?)(?=##|\Z)",
        rf"###\s+{re.escape(secao)}[^\n]*\n(.*?)(?=##|###|\Z)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, texto, re.DOTALL | re.IGNORECASE)
        if match:
            content = match.group(1).strip()
            # Remove formatação markdown excessiva
            content = re.sub(r"^\*\*|\*\*$", "", content)  # Remove bold
            content = re.sub(r"^\*|\*$", "", content)  # Remove itálico
            return content
    
    return None


def _extrair_lista_markdown(texto: str, secao: str) -> List[str]:
    """
    Extrai uma lista de bullet points de uma seção markdown.
    
    Args:
        texto: Texto markdown completo
        secao: Nome da seção a extrair
        
    Returns:
        Lista de itens extraídos
    """
    secao_texto = _extrair_secao_markdown(texto, secao)
    if not secao_texto:
        return []
    
    itens = []
    linhas = secao_texto.split("\n")
    
    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue
        
        # Remove bullets (•, -, *, etc.) e listas numeradas
        item = re.sub(r"^[•\-\*]\s+", "", linha)
        item = re.sub(r"^\d+\.\s+", "", item)
        item = item.strip()
        
        if item and len(item) > 10:  # Só adiciona se for uma frase completa
            itens.append(item)
    
    return itens


def _extrair_resumo_executivo(texto: str) -> str:
    """
    Extrai o resumo executivo do texto markdown.
    
    Tenta encontrar a seção "Resumo executivo" ou usa as primeiras 2-3 frases.
    
    Args:
        texto: Texto markdown completo
        
    Returns:
        Resumo executivo extraído
    """
    # Tenta encontrar seção "Resumo executivo"
    resumo = _extrair_secao_markdown(texto, "Resumo executivo")
    if resumo:
        # Pega apenas as primeiras 2-3 frases
        frases = re.split(r"[.!?]+\s+", resumo)
        resumo_curto = ". ".join(frases[:3])
        if not resumo_curto.endswith((".", "!", "?")):
            resumo_curto += "."
        return resumo_curto.strip()
    
    # Fallback: primeiras 2-3 frases do texto
    frases = re.split(r"[.!?]+\s+", texto[:500])
    resumo_fallback = ". ".join(frases[:3])
    if not resumo_fallback.endswith((".", "!", "?")):
        resumo_fallback += "."
    return resumo_fallback.strip()


def _extrair_kpis_do_contexto(contexto: Dict[str, Any]) -> Optional[KpisData]:
    """
    Extrai KPIs estruturados do contexto.
    
    Args:
        contexto: Contexto com dados estruturados
        
    Returns:
        Dados de KPIs ou None se não houver dados suficientes
    """
    # Verifica se temos dados de metas
    mes_ano = contexto.get("mes_ano_analise") or contexto.get("mes_ano") or contexto.get("mesAno")
    if not mes_ano:
        return None
    
    # Formata label do mês/ano (ex.: "2025-08" -> "agosto de 2025")
    try:
        ano, mes = mes_ano.split("-")
        meses = [
            "janeiro", "fevereiro", "março", "abril", "maio", "junho",
            "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
        ]
        mes_label = meses[int(mes) - 1] if 1 <= int(mes) <= 12 else mes
        mes_ano_label = f"{mes_label} de {ano}"
    except Exception:
        mes_ano_label = mes_ano
    
    # Tenta extrair vendedores que bateram a meta
    vendedores_que_bateram = 0
    atingimento_medio = 0.0
    
    # Opção 1: Temos lista de vendedores com atingimento
    vendedores = contexto.get("detalhe_vendedores_mes", {}).get("vendedores") or contexto.get("vendedores") or []
    if vendedores and isinstance(vendedores, list):
        # Filtra apenas vendedores com atingimento válido (não None, e é número) antes de comparar
        vendedores_que_bateram = sum(
            1 for v in vendedores 
            if isinstance(v, dict) 
            and v.get("atingimento") is not None 
            and isinstance(v.get("atingimento"), (int, float))
            and float(v.get("atingimento", 0)) >= 100
        )
        # Extrai atingimentos válidos (não None, e é número)
        atingimentos = [
            float(v.get("atingimento", 0)) 
            for v in vendedores 
            if isinstance(v, dict) 
            and v.get("atingimento") is not None 
            and isinstance(v.get("atingimento"), (int, float))
        ]
        if atingimentos:
            atingimento_medio = sum(atingimentos) / len(atingimentos)
    
    # Opção 2: Temos dados agregados
    if atingimento_medio == 0:
        atingimento_medio = contexto.get("atingimento_medio") or contexto.get("perc_atingido_geral") or 0.0
    
    # Só retorna KPIs se tiver dados válidos
    if vendedores_que_bateram == 0 and atingimento_medio == 0:
        return None
    
    return KpisData(
        mesAnoLabel=mes_ano_label,
        vendedoresQueBateram=vendedores_que_bateram,
        atingimentoMedio=round(atingimento_medio, 2)
    )


def _extrair_top_vendedores_do_contexto(contexto: Dict[str, Any], limite: int = 10) -> Optional[List[TopVendedor]]:
    """
    Extrai top vendedores do contexto.
    
    Args:
        contexto: Contexto com dados estruturados
        limite: Número máximo de vendedores a retornar
        
    Returns:
        Lista de top vendedores ou None se não houver dados
    """
    # Tenta encontrar lista de vendedores
    vendedores = contexto.get("detalhe_vendedores_mes", {}).get("vendedores") or contexto.get("vendedores") or contexto.get("top_vendedores") or []
    
    if not vendedores or not isinstance(vendedores, list) or len(vendedores) == 0:
        return None
    
    # Ordena por atingimento (maior primeiro) e pega top N
    # Filtra apenas vendedores com atingimento válido (não None, e é número)
    vendedores_com_atingimento = [
        v for v in vendedores 
        if isinstance(v, dict) 
        and v.get("atingimento") is not None 
        and isinstance(v.get("atingimento"), (int, float))
    ]
    
    vendedores_ordenados = sorted(
        vendedores_com_atingimento,
        key=lambda x: float(x.get("atingimento", 0)),
        reverse=True
    )[:limite]
    
    if not vendedores_ordenados:
        return None
    
    # Converte para formato TopVendedor
    top_vendedores = []
    for idx, v in enumerate(vendedores_ordenados, start=1):
        top_vendedores.append(
            TopVendedor(
                rank=idx,
                nome=v.get("vendedor_nome") or v.get("nome") or v.get("vendedor") or "N/A",
                rota=v.get("rota"),
                supervisor=v.get("supervisor"),
                meta=float(v.get("meta", 0) or v.get("meta_valor", 0) or 0),
                realizado=float(v.get("realizado", 0) or v.get("realizado_valor", 0) or v.get("faturado", 0) or 0),
                atingimento=float(v.get("atingimento", 0) or v.get("perc_atingido", 0) or 0)
            )
        )
    
    return top_vendedores if top_vendedores else None


def _extrair_dados_estruturados(result: Dict[str, Any], pergunta: str) -> Dict[str, Any]:
    """
    Extrai dados estruturados do resultado do agente.
    
    Args:
        result: Resultado do processamento da pergunta
        pergunta: Pergunta original do usuário
        
    Returns:
        Dicionário com dados estruturados prontos para AskResponse
    """
    resposta_texto = result.get("resposta", "")
    contexto = result.get("contexto", {})
    
    # Extrai resumo executivo
    resumo_executivo = _extrair_resumo_executivo(resposta_texto)
    
    # Extrai KPIs (se houver dados de meta)
    kpis = None
    if result.get("intent") in ["consulta_meta", "consulta_vendedores_performance"]:
        kpis = _extrair_kpis_do_contexto(contexto)
    
    # Extrai top vendedores (se houver dados de meta/vendedores)
    top_vendedores = None
    if result.get("intent") in ["consulta_meta", "consulta_vendedores_performance"]:
        top_vendedores = _extrair_top_vendedores_do_contexto(contexto, limite=15)
    
    # Extrai insights da seção "Insights e recomendações"
    insights = _extrair_lista_markdown(resposta_texto, "Insights e recomendações")
    
    # Extrai observações da seção "Observações sobre os dados"
    observacoes = _extrair_lista_markdown(resposta_texto, "Observações sobre os dados")
    
    # NOVO FASE 3: Verifica se há resposta estruturada (CopilotStructuredResponse)
    # IMPORTANTE: Prioriza structured do contexto (vem de _handle_meta_query_diretor_analytics)
    structured = None
    if "structured" in contexto:
        structured = contexto["structured"]
    elif "structured" in result:
        structured = result["structured"]
    
    # Se encontrou structured válido no formato novo (snake_case), preserva ele
    # O copilot_mapper já vai tratar e passar adiante corretamente
    return {
        "question": pergunta,
        "intent": result.get("intent", "outros"),
        "confidence": result.get("confianca", 0.5),
        "resumoExecutivo": resumo_executivo,
        "kpis": kpis.dict() if kpis else None,
        "topVendedores": [v.dict() for v in top_vendedores] if top_vendedores else None,
        "insights": insights if insights else None,
        "observacoes": observacoes if observacoes else None,
        "contexto": _resumir_contexto(contexto),
        "timestamp": datetime.utcnow().isoformat(),
        "structured": structured  # NOVO: formato estruturado FASE 3 (pode ser snake_case ou camelCase)
    }


def _resumir_contexto(contexto: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resume o contexto mantendo apenas números chave.
    
    Remove listas extensas e mantém apenas sumários/metadados importantes.
    Para consulta_vendedores_performance, preserva piores_meta e menores_venda.
    
    Args:
        contexto: Contexto completo da resposta
        
    Returns:
        dict: Contexto resumido com apenas números chave
    """
    resumo = {}
    
    # Copia campos importantes diretamente
    campos_diretos = [
        "tipo", "mes_ano", "mes_ano_analise", "mes_ano_solicitado",
        "periodo_dias", "criterio",
        "faturamento_previsto", "intervalo_inferior", "intervalo_superior",
        "observacoes", "erro", "tem_dados"
    ]
    
    for campo in campos_diretos:
        if campo in contexto:
            resumo[campo] = contexto[campo]
    
    # Para consulta_vendedores_performance, preserva listas de vendedores
    # (mas limita tamanho para não sobrecarregar)
    if "piores_meta" in contexto:
        piores = contexto["piores_meta"]
        resumo["piores_meta"] = piores[:10] if isinstance(piores, list) else piores
        resumo["total_piores_meta"] = len(piores) if isinstance(piores, list) else 0
    
    if "menores_venda" in contexto:
        menores = contexto["menores_venda"]
        resumo["menores_venda"] = menores[:10] if isinstance(menores, list) else menores
        resumo["total_menores_venda"] = len(menores) if isinstance(menores, list) else 0
    
    # Para consulta_meta, preserva KPIs e top vendedores
    if "kpis" in contexto:
        resumo["kpis"] = contexto["kpis"]
    
    if "pioresVendedores" in contexto:
        piores = contexto["pioresVendedores"]
        resumo["pioresVendedores"] = piores[:10] if isinstance(piores, list) else piores
    
    if "melhoresVendedores" in contexto:
        melhores = contexto["melhoresVendedores"]
        resumo["melhoresVendedores"] = melhores[:10] if isinstance(melhores, list) else melhores
    
    # Resume listas grandes
    if "resumo" in contexto:
        resumo["resumo"] = contexto["resumo"]
    
    # Resumo de produtos: apenas contagem e totais
    if "produtos" in contexto and isinstance(contexto["produtos"], list):
        produtos = contexto["produtos"]
        resumo["produtos"] = {
            "total": len(produtos),
            "total_faturamento": sum(p.get("faturamento", 0) for p in produtos[:10]),
            "top_5_codigos": [p.get("codigo") for p in produtos[:5]]
        }
    
    # Resumo de vendedores: apenas contagem e totais
    if "top_vendedores" in contexto and isinstance(contexto["top_vendedores"], list):
        vendedores = contexto["top_vendedores"]
        resumo["vendedores"] = {
            "total_top": len(vendedores),
            "total_meta": sum(v.get("meta", 0) for v in vendedores),
            "total_realizado": sum(v.get("realizado", 0) for v in vendedores)
        }
    
    # Resumo de departamentos: apenas contagem
    if "departamentos" in contexto and isinstance(contexto["departamentos"], list):
        resumo["departamentos"] = {
            "total": len(contexto["departamentos"])
        }
    
    return resumo


@app.post("/ask", response_model=AskResponse)
async def ask_question(
    request: AskRequest,
    session: Session = Depends(get_db_session)
):
    """
    Endpoint principal do agente: recebe perguntas e retorna respostas.
    
    Pipeline:
    1. Detecta intenção da pergunta
    2. Busca dados relevantes no banco
    3. Usa modelos de ML quando apropriado
    4. Gera resposta natural com LLM
    
    Args:
        request: Requisição com pergunta do usuário
        session: Sessão de banco de dados (injetada)
        
    Returns:
        AskResponse: Resposta do agente com dados estruturados
        
    Example:
        POST /ask
        {
            "pergunta": "Por que o vendedor ROTA 77 não bateu a meta em dezembro?",
            "papel": "supervisor"
        }
    """
    try:
        import time
        start_time = time.perf_counter()
        
        logger.info(f"Pergunta recebida: {request.pergunta[:100]}...")
        
        # NOVO FLUXO: Usa handler refatorado (IntentSpec + Orquestrador + Regras)
        from src.agent.handler_dw_refatorado import processar_pergunta_com_dw
        from src.api.mapper_handler_refatorado import map_handler_refatorado_to_ask_response
        
        # Processa pergunta usando novo fluxo
        resposta_handler = processar_pergunta_com_dw(
            pergunta=request.pergunta,
            session=session,
            papel=request.papel
        )
        
        # Converte para formato AskResponse
        dados_estruturados = map_handler_refatorado_to_ask_response(
            resposta_handler=resposta_handler,
            pergunta=request.pergunta
        )
        
        response = AskResponse(**dados_estruturados)
        
        # Prepara resultado para registro de interação (formato compatível)
        intent_spec = resposta_handler.get("intent_spec")
        result = {
            "intent": dados_estruturados.get("intent", "outros"),
            "confianca": dados_estruturados.get("confidence", 0.7),
            "resposta": dados_estruturados.get("resumoExecutivo", ""),
            "contexto": dados_estruturados.get("contexto", {}),
            "structured": dados_estruturados.get("structured"),
            "entities": intent_spec.to_dict() if intent_spec and hasattr(intent_spec, 'to_dict') else {}
        }
        
        # Copilot payload para compatibilidade
        copilot_payload = dados_estruturados.get("payload", {})
        
        # Calcula tempo de processamento
        tempo_processamento_ms = int((time.perf_counter() - start_time) * 1000)
        
        # FASE 4: Registra interação com todos os metadados necessários
        try:
            from src.agent.interaction_registry import registrar_interacao_agent
            
            # Extrai entidades do resultado
            intent_spec = resposta_handler.get("intent_spec")
            entidades = intent_spec.to_dict() if intent_spec and hasattr(intent_spec, 'to_dict') else {}
            
            # Determina se a resposta foi bem-sucedida (tem dados reais)
            tem_dados = resposta_handler.get("tem_dados", False)
            tabela_principal = resposta_handler.get("tabela_principal", [])
            sucesso_resposta = tem_dados and len(tabela_principal) > 0
            
            # Determina fonte de dados principal
            fonte_dados_principal = None
            contexto_debug = None
            if copilot_payload.get("structured"):
                json_tecnico = copilot_payload["structured"].get("jsonTecnico", {})
                if isinstance(json_tecnico, dict):
                    contexto_debug = json_tecnico
                    # Fonte de dados baseada no tipo de intent
                    if intent_spec:
                        fonte_dados_principal = f"dw_analytics_{intent_spec.tipo}"
            
            # Conta número de registros usados
            num_registros_usados = None
            dados_dw = resposta_handler.get("dados_dw", {})
            if isinstance(dados_dw, dict):
                dados = dados_dw.get("dados", [])
                if isinstance(dados, list):
                    num_registros_usados = len(dados)
            
            # Se não encontrou em dados_dw, tenta na tabela_principal
            if num_registros_usados is None and tabela_principal:
                for tabela in tabela_principal:
                    if isinstance(tabela, dict):
                        linhas = tabela.get("linhas", [])
                        if isinstance(linhas, list):
                            num_registros_usados = (num_registros_usados or 0) + len(linhas)
            
            # Prepara resposta completa para registro
            resposta_completa = {
                "structured": copilot_payload.get("structured"),
                "resposta": resposta_handler.get("resumo_executivo", ""),
                "confianca": intent_spec.confianca if intent_spec else 0.7,
                "contexto_debug": contexto_debug,
                "resumoExecutivo": resposta_handler.get("resumo_executivo", ""),
                "intent_spec": intent_spec.to_dict() if intent_spec else None,
                "regras_aplicadas": dados_dw.get("regras_aplicadas") if isinstance(dados_dw, dict) else None
            }
            
            # Registra interação
            interacao_id = registrar_interacao_agent(
                session=session,
                papel_usuario=request.papel,
                pergunta=request.pergunta,
                intent=intent_spec.tipo if intent_spec else "outros",
                entidades=entidades,
                resposta=resposta_completa,
                sucesso_resposta=sucesso_resposta,
                fonte_dados_principal=fonte_dados_principal,
                num_registros_usados=num_registros_usados,
                tempo_processamento_ms=tempo_processamento_ms
            )
            
            if interacao_id:
                logger.info(f"✅ Interação registrada (ID: {interacao_id}, tempo: {tempo_processamento_ms}ms)")
        
        except Exception as e:
            # NÃO bloqueia a resposta se falhar
            logger.warning(f"⚠️  Erro ao registrar interação (não bloqueia resposta): {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
        
        return response
    
    except HTTPException:
        # Re-lança HTTPException para manter status code e passar pelo CORS corretamente
        raise
    except Exception as e:
        # IMPORTANTE: Captura TODAS as exceções para garantir que sempre retornamos uma resposta com CORS
        # Usa HTTPException ao invés de JSONResponse para garantir que passa pelo CORSMiddleware
        # HTTPException sempre passa pelo pipeline do FastAPI, incluindo middlewares de CORS
        logger.error(f"❌ Erro ao processar pergunta: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Levanta HTTPException ao invés de retornar JSONResponse diretamente
        # Isso garante que o CORSMiddleware adicione os headers CORS corretamente
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Erro interno do servidor",
                "message": "Ocorreu um erro ao processar sua pergunta. Por favor, tente novamente.",
                "detail": str(e) if config.environment == "development" else "Erro interno do servidor",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )


@app.get("/preview/vendedor/{vendedor}/{mes_ano}", response_model=PreviewVendedorResponse)
async def preview_vendedor(
    vendedor: str,
    mes_ano: str,
    session: Session = Depends(get_db_session)
):
    """
    Endpoint auxiliar: retorna dados numéricos de um vendedor/mês.
    
    Útil para visualizações e dashboards que precisam apenas dos dados brutos,
    sem processamento pelo LLM.
    
    Args:
        vendedor: Nome ou código do vendedor (ex.: "ROTA 77")
        mes_ano: Mês/ano no formato "YYYY-MM" (ex.: "2024-12")
        session: Sessão de banco de dados (injetada)
        
    Returns:
        PreviewVendedorResponse: Dados numéricos do vendedor/mês
        
    Example:
        GET /preview/vendedor/ROTA%2077/2024-12
    """
    try:
        logger.info(f"Buscando dados de {vendedor} para {mes_ano}...")
        
        # Valida formato de mes_ano
        try:
            datetime.strptime(mes_ano, "%Y-%m")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Formato de mes_ano inválido. Use YYYY-MM (ex.: 2024-12)"
            )
        
        # Busca dados
        dados = query_vendedor_meta(session, vendedor, mes_ano)
        
        if "erro" in dados:
            raise HTTPException(status_code=404, detail=dados["erro"])
        
        return PreviewVendedorResponse(
            vendedor=vendedor,
            mes_ano=mes_ano,
            dados=dados,
            timestamp=datetime.utcnow().isoformat()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar dados: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao buscar dados: {str(e)}")


@app.post("/admin/migrate/vendedor-id")
async def migrate_vendedor_id():
    """
    Endpoint para executar migração: adicionar coluna vendedor_id e popular vendedores.
    
    Este endpoint:
    1. Adiciona coluna vendedor_id na tabela clientes (se não existir)
    2. Cria vendedores a partir das rotas dos clientes
    3. Popula vendedor_id nos clientes baseado em rota_rca
    
    IMPORTANTE: Este endpoint deve ser protegido em produção.
    """
    try:
        from sqlalchemy import text, distinct
        from sqlalchemy.exc import OperationalError, ProgrammingError
        from src.dw.models import Cliente, Vendedor
        from src.dw.connection import SessionLocal
        from src.load_to_db import get_or_create_vendedor
        
        engine = get_db_engine()
        # ✅ CORREÇÃO: SessionLocal() retorna sessão diretamente, não generator
        if SessionLocal is None:
            init_db()
        session = SessionLocal()
        
        results = {
            "coluna_criada": False,
            "vendedores_criados": 0,
            "clientes_atualizados": 0,
            "erros": []
        }
        
        try:
            # 1. Verifica se coluna existe
            session.query(Cliente.vendedor_id).limit(1).all()
            logger.info("Coluna vendedor_id já existe")
        except (OperationalError, ProgrammingError, AttributeError) as e:
            # Cria coluna
            db_url = str(engine.url)
            try:
                if 'sqlite' in db_url:
                    with engine.connect() as conn:
                        conn.execute(text("ALTER TABLE clientes ADD COLUMN vendedor_id INTEGER"))
                        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_clientes_vendedor_id ON clientes(vendedor_id)"))
                        conn.commit()
                else:
                    with engine.connect() as conn:
                        conn.execute(text("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS vendedor_id INTEGER"))
                        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_clientes_vendedor_id ON clientes(vendedor_id)"))
                        try:
                            conn.execute(text("ALTER TABLE clientes ADD CONSTRAINT fk_clientes_vendedor_id FOREIGN KEY (vendedor_id) REFERENCES vendedores(id)"))
                        except:
                            pass  # Constraint pode já existir
                        conn.commit()
                
                results["coluna_criada"] = True
                logger.info("Coluna vendedor_id criada")
            except Exception as create_error:
                logger.warning(f"Erro ao criar coluna (pode já existir): {str(create_error)}")
                # Tenta novamente verificar se existe
                try:
                    session.query(Cliente.vendedor_id).limit(1).all()
                    logger.info("Coluna vendedor_id existe após tentativa de criação")
                except:
                    raise create_error
        
        # 2. Cria vendedores a partir das rotas dos clientes
        # ✅ CORREÇÃO: Usar distinct() corretamente
        from sqlalchemy import distinct
        rotas_distintas = session.query(distinct(Cliente.rota_rca)).filter(
            Cliente.ativo == True,
            Cliente.rota_rca.isnot(None),
            Cliente.rota_rca != ''
        ).all()
        
        logger.info(f"Encontradas {len(rotas_distintas)} rotas distintas")
        
        # Log de exemplo de rotas
        if rotas_distintas:
            logger.info(f"Exemplo de rotas: {[r[0] for r in rotas_distintas[:5]]}")
        
        for (rota,) in rotas_distintas:
            if not rota or str(rota).strip() == '':
                continue
            
            rota = str(rota).strip()
            
            # Verifica se já existe vendedor com esse código
            vendedor = session.query(Vendedor).filter(Vendedor.codigo == rota).first()
            
            if not vendedor:
                # Busca informações do primeiro cliente com essa rota
                cliente_exemplo = session.query(Cliente).filter(
                    Cliente.rota_rca == rota,
                    Cliente.ativo == True
                ).first()
                
                if cliente_exemplo:
                    nome_vendedor = cliente_exemplo.nome_rca if cliente_exemplo.nome_rca else rota
                    supervisor_id = cliente_exemplo.supervisor_id
                    
                    # ✅ CORREÇÃO: Cria vendedor usando rota como código
                    vendedor = get_or_create_vendedor(
                        session,
                        nome=nome_vendedor,
                        codigo=rota,  # ✅ Usa rota como código (chave de JOIN)
                        supervisor_id=supervisor_id
                    )
                    results["vendedores_criados"] += 1
                    logger.info(f"Vendedor criado: codigo={rota}, nome={nome_vendedor}")
                else:
                    logger.warning(f"Cliente não encontrado para rota: {rota}")
            else:
                # Atualiza vendedor existente se necessário
                updated = False
                if not vendedor.nome:
                    cliente_exemplo = session.query(Cliente).filter(
                        Cliente.rota_rca == rota,
                        Cliente.ativo == True,
                        Cliente.nome_rca.isnot(None),
                        Cliente.nome_rca != ''
                    ).first()
                    if cliente_exemplo and cliente_exemplo.nome_rca:
                        vendedor.nome = cliente_exemplo.nome_rca
                        updated = True
                
                if not vendedor.supervisor_id:
                    cliente_exemplo = session.query(Cliente).filter(
                        Cliente.rota_rca == rota,
                        Cliente.ativo == True,
                        Cliente.supervisor_id.isnot(None)
                    ).first()
                    if cliente_exemplo and cliente_exemplo.supervisor_id:
                        vendedor.supervisor_id = cliente_exemplo.supervisor_id
                        updated = True
                
                if updated:
                    session.flush()
                    logger.info(f"Vendedor atualizado: codigo={rota}")
        
        session.commit()
        
        # 3. Popula vendedor_id
        clientes_sem_vendedor = session.query(Cliente).filter(
            Cliente.ativo == True,
            Cliente.rota_rca.isnot(None),
            Cliente.rota_rca != '',
            Cliente.vendedor_id.is_(None)
        ).all()
        
        for cliente in clientes_sem_vendedor:
            if cliente.rota_rca:
                vendedor = session.query(Vendedor).filter(Vendedor.codigo == cliente.rota_rca).first()
                if vendedor:
                    cliente.vendedor_id = vendedor.id
                    results["clientes_atualizados"] += 1
        
        session.commit()
        
        return {
            "sucesso": True,
            "mensagem": "Migração executada com sucesso",
            "resultados": results
        }
        
    except Exception as e:
        session.rollback()
        logger.error(f"Erro na migração: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro na migração: {str(e)}")
    finally:
        session.close()


@app.get("/ml/status", response_model=Dict[str, Any])
async def ml_status():
    """
    Endpoint de status dos modelos ML (FASE 5).
    
    Retorna informações sobre quais modelos estão treinados e disponíveis.
    
    Returns:
        Dict com status de cada modelo (churn, meta_risk, oportunidades)
    """
    try:
        from src.ml.model_registry import list_models
        
        registry = list_models()
        
        modelos_status = {}
        tipos_modelos = ["churn", "meta_risk", "oportunidades"]
        
        for tipo in tipos_modelos:
            if tipo in registry and registry[tipo].get("treinado"):
                modelos_status[tipo] = {
                    "treinado": True,
                    "trained_at": registry[tipo].get("trained_at"),
                    "mes_inicio": registry[tipo].get("mes_inicio"),
                    "mes_fim": registry[tipo].get("mes_fim"),
                    "mes_referencia": registry[tipo].get("mes_referencia"),  # Para oportunidades
                    "n_samples": registry[tipo].get("n_samples"),
                    "accuracy": registry[tipo].get("accuracy"),
                    "roc_auc": registry[tipo].get("roc_auc")
                }
            else:
                modelos_status[tipo] = {
                    "treinado": False
                }
        
        return {
            "status": "ok",
            "modelos": modelos_status
        }
    
    except Exception as e:
        logger.error(f"Erro ao obter status dos modelos ML: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "modelos": {
                "churn": {"treinado": False},
                "meta_risk": {"treinado": False},
                "oportunidades": {"treinado": False}
            }
        }


class BehaviorRuleRequest(BaseModel):
    """Modelo de requisição para endpoint /feedback/behavior (Behavior Memory V1)."""
    tipo_regra: str = Field(..., description="Tipo de regra: EXCLUIR_FILTRO, FORÇAR_FILTRO, AJUSTAR_LIMIAR")
    escopo: str = Field(..., description="Escopo: global, tipo_intent, tipo_dimensao, tipo_intent_dimensao")
    tipo_intent: Optional[str] = Field(None, description="Tipo de intent (ex.: 'mix_nissin', 'meta')")
    dimensao_principal: Optional[str] = Field(None, description="Dimensão principal (ex.: 'cliente', 'rota')")
    regra: Dict[str, Any] = Field(..., description="Regra em JSON (campo, operador, valor, limiar, etc.)")
    comentario: Optional[str] = Field(None, description="Comentário explicando a regra")
    fonte_feedback: Optional[str] = Field(None, description="Payload original ou resumo")
    criado_por: Optional[str] = Field("diretor", description="Quem criou a regra (diretor, supervisor, sistema)")
    
    class Config:
        schema_extra = {
            "example": {
                "tipo_regra": "EXCLUIR_FILTRO",
                "escopo": "tipo_intent",
                "tipo_intent": "mix_nissin",
                "dimensao_principal": None,
                "regra": {
                    "campo": "pasta",
                    "operador": "!=",
                    "valor": "VERDE"
                },
                "comentario": "pedido do diretor: excluir pasta verde nesse tipo de análise",
                "fonte_feedback": "texto original ou contexto opcional"
            }
        }


@app.post("/feedback/behavior", response_model=Dict[str, Any])
async def feedback_behavior_rule(
    request: BehaviorRuleRequest,
    session: Session = Depends(get_db_session)
):
    """
    Endpoint para registrar regras de comportamento persistentes (Behavior Memory V1).
    
    Cria uma nova BehaviorRule que será aplicada automaticamente em consultas futuras
    compatíveis com o escopo especificado.
    
    Args:
        request: Requisição com dados da regra
        session: Sessão de banco de dados (injetada)
        
    Returns:
        Dict com status, behavior_rule_id e mensagem
        
    Example:
        POST /feedback/behavior
        {
            "tipo_regra": "EXCLUIR_FILTRO",
            "escopo": "tipo_intent",
            "tipo_intent": "mix_nissin",
            "regra": {
                "campo": "pasta",
                "operador": "!=",
                "valor": "VERDE"
            },
            "comentario": "pedido do diretor: excluir pasta verde nesse tipo de análise"
        }
    """
    try:
        # Valida tipo_regra
        tipos_validos = ["EXCLUIR_FILTRO", "FORÇAR_FILTRO", "AJUSTAR_LIMIAR"]
        if request.tipo_regra not in tipos_validos:
            raise HTTPException(
                status_code=400,
                detail=f"tipo_regra deve ser um de: {tipos_validos}"
            )
        
        # Valida escopo
        escopos_validos = ["global", "tipo_intent", "tipo_dimensao", "tipo_intent_dimensao"]
        if request.escopo not in escopos_validos:
            raise HTTPException(
                status_code=400,
                detail=f"escopo deve ser um de: {escopos_validos}"
            )
        
        # Valida que tipo_intent e dimensao_principal são fornecidos quando necessário
        if request.escopo in ["tipo_intent", "tipo_intent_dimensao"] and not request.tipo_intent:
            raise HTTPException(
                status_code=400,
                detail=f"tipo_intent é obrigatório para escopo '{request.escopo}'"
            )
        
        if request.escopo in ["tipo_dimensao", "tipo_intent_dimensao"] and not request.dimensao_principal:
            raise HTTPException(
                status_code=400,
                detail=f"dimensao_principal é obrigatória para escopo '{request.escopo}'"
            )
        
        # Cria BehaviorRule
        from src.dw.models import BehaviorRule
        
        behavior_rule = BehaviorRule(
            criado_por=request.criado_por or "diretor",
            ativo=True,
            escopo=request.escopo,
            tipo_intent=request.tipo_intent,
            dimensao_principal=request.dimensao_principal,
            tipo_regra=request.tipo_regra,
            regra_json=request.regra,
            comentario=request.comentario,
            fonte_feedback=request.fonte_feedback
        )
        
        session.add(behavior_rule)
        session.commit()
        session.refresh(behavior_rule)
        
        logger.info(
            f"[feedback/behavior] Regra criada: id={behavior_rule.id}, "
            f"escopo={request.escopo}, tipo_regra={request.tipo_regra}"
        )
        
        return {
            "status": "ok",
            "behavior_rule_id": behavior_rule.id,
            "mensagem": "Regra de comportamento registrada com sucesso e será aplicada nas próximas consultas compatíveis."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[feedback/behavior] Erro ao criar regra: {e}")
        session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao registrar regra de comportamento: {str(e)}"
        )


@app.post("/feedback", response_model=Dict[str, Any])
async def feedback_interacao_fase4(
    feedback: FeedbackRequestFase4 = ...,
    session: Session = Depends(get_db_session)
):
    """
    Endpoint de feedback sobre uma interação do agente (FASE 4).
    
    Permite que o Diretor avalie a qualidade da resposta em escala 1-5
    e forneça comentários para melhorar o sistema.
    
    Args:
        feedback: Dados do feedback (interacao_id, feedback_qualidade, feedback_comentario)
        session: Sessão de banco de dados (injetada)
        
    Returns:
        Dict com status e mensagem
        
    Raises:
        HTTPException 404: Se a interação não for encontrada
        HTTPException 500: Em caso de erro ao atualizar
        
    Example:
        POST /feedback
        {
            "interacao_id": 123,
            "feedback_qualidade": 4,
            "feedback_comentario": "Resposta boa, mas poderia detalhar mais os clientes em risco."
        }
    """
    try:
        logger.info(f"Recebendo feedback FASE 4 para interação {feedback.interacao_id}: qualidade={feedback.feedback_qualidade}")
        
        # Busca a interação no banco
        interacao = session.query(InteracaoAgent).filter(
            InteracaoAgent.id == feedback.interacao_id
        ).first()
        
        if not interacao:
            logger.warning(f"Interação {feedback.interacao_id} não encontrada")
            raise HTTPException(
                status_code=404,
                detail=f"Interação com ID {feedback.interacao_id} não encontrada"
            )
        
        # Atualiza os campos de feedback
        interacao.feedback_qualidade = feedback.feedback_qualidade
        if feedback.feedback_comentario:
            interacao.feedback_comentario = feedback.feedback_comentario
            interacao.comentario = feedback.feedback_comentario  # Mantém compatibilidade
        
        session.commit()
        
        logger.info(f"✅ Feedback FASE 4 salvo com sucesso para interação {feedback.interacao_id}")
        
        return {
            "status": "ok",
            "message": "Feedback registrado com sucesso",
            "interacao_id": interacao.id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao salvar feedback FASE 4 para interação {feedback.interacao_id}: {str(e)}")
        session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao salvar feedback: {str(e)}"
        )


@app.post("/feedback/{interacao_id}", response_model=FeedbackResponse)
async def feedback_interacao(
    interacao_id: int = FastAPIPath(..., description="ID da interação a receber feedback", gt=0),
    feedback: FeedbackRequest = ...,
    session: Session = Depends(get_db_session)
):
    """
    Endpoint de feedback sobre uma interação do agente.
    
    Permite que o usuário avalie se a resposta foi útil ou não,
    fornecendo feedback para melhorar o sistema.
    
    Args:
        interacao_id: ID da interação a receber feedback
        feedback: Dados do feedback (sucesso e comentário opcional)
        session: Sessão de banco de dados (injetada)
        
    Returns:
        FeedbackResponse: Confirmação de atualização
        
    Raises:
        HTTPException 404: Se a interação não for encontrada
        HTTPException 500: Em caso de erro ao atualizar
        
    Example:
        POST /feedback/123
        {
            "sucesso": true,
            "comentario": "Resposta muito clara e útil."
        }
    """
    try:
        logger.info(f"Recebendo feedback para interação {interacao_id}: sucesso={feedback.sucesso}")
        
        # Busca a interação no banco
        interacao = session.query(InteracaoAgent).filter(
            InteracaoAgent.id == interacao_id
        ).first()
        
        if not interacao:
            logger.warning(f"Interação {interacao_id} não encontrada")
            raise HTTPException(
                status_code=404,
                detail=f"Interação com ID {interacao_id} não encontrada"
            )
        
        # Atualiza os campos de feedback
        interacao.sucesso = feedback.sucesso
        if feedback.comentario:
            interacao.comentario = feedback.comentario
        
        # Atualiza timestamp de atualização será feito automaticamente pelo onupdate
        
        session.commit()
        
        logger.info(f"Feedback salvo com sucesso para interação {interacao_id}")
        
        return FeedbackResponse(
            mensagem="Feedback registrado com sucesso",
            interacao_id=interacao.id,
            sucesso=interacao.sucesso
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions (404, etc.)
        raise
    except Exception as e:
        logger.error(f"Erro ao salvar feedback para interação {interacao_id}: {str(e)}")
        session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao salvar feedback: {str(e)}"
        )


# Configuração para Cloud Run
# IMPORTANTE: Este bloco é executado quando rodamos: python -m src.api.main
# Cloud Run espera que o servidor escute em 0.0.0.0:PORT (onde PORT=8080)
if __name__ == "__main__":
    import uvicorn
    import os
    
    # Cloud Run define PORT=8080 via env var
    # Fallback para 8080 (padrão Cloud Run) em vez de 8000 (dev local)
    port = int(os.getenv("PORT", 8080))
    
    # IMPORTANTE: reload SEMPRE False em produção (Cloud Run)
    # reload=True só em desenvolvimento local com DEBUG=True
    is_production = os.getenv("ENVIRONMENT", "development") == "production"
    reload_mode = False if is_production else getattr(config, "debug", False)
    
    logger.info(f"🚀 Iniciando servidor FastAPI na porta {port} (PORT env: {os.getenv('PORT', 'não definido')})")
    logger.info(f"   Ambiente: {os.getenv('ENVIRONMENT', 'development')}, Reload: {reload_mode}")
    
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",  # IMPORTANTE: 0.0.0.0 para Cloud Run (não localhost/127.0.0.1)
        port=port,
        reload=reload_mode,  # reload=False em produção (Cloud Run)
        log_level=getattr(config, "log_level", "info").lower(),
    )

