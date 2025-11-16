"""
API FastAPI do Agente de IA Comercial - Dipam AI.

Este módulo expõe endpoints REST para o agente conversacional,
permitindo interação em linguagem natural com os dados da empresa.
"""

from fastapi import FastAPI, HTTPException, Depends, Query, Path
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
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
origins = [
    "https://dipam.smartiasolutions.com.br",
    "https://www.dipam.smartiasolutions.com.br",
    # Frontend Cloud Run (URL principal e alternativa)
    "https://dipam-copilot-frontend-6arhlm3mha-uc.a.run.app",
    "https://dipam-copilot-frontend-642830139828.us-central1.run.app",
    # Local development
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Em desenvolvimento, adicionar localhost:8000 para testes locais
if config.environment == "development":
    origins.extend([
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    
    # 1. Validação de OpenAI (não crítica para o servidor subir)
    logger.info("Verificando configuração OpenAI...")
    try:
        from src.llm_openai_client import get_openai_client
        client = get_openai_client()
        if client:
            app.state.openai_available = True
            logger.info("✅ OPENAI_API_KEY validada com sucesso")
        else:
            logger.warning("⚠️  OpenAI client retornou None")
            app.state.startup_errors.append("OPENAI_API_KEY: client retornou None")
    except Exception as e:
        error_msg = f"OPENAI_API_KEY não configurada ou inválida: {str(e)}"
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
        
        # Verifica arquivo SQLite se estiver usando SQLite
        if config.database.db_type == "sqlite":
            sqlite_path = config.database.sqlite_path  # Isso já cria o diretório se necessário
            logger.info(f"Usando SQLite - Caminho: {sqlite_path}")
            
            # Verifica se o arquivo existe (após garantir que o diretório existe)
            if os.path.exists(sqlite_path):
                file_size = os.path.getsize(sqlite_path)
                logger.info(f"✅ Arquivo SQLite encontrado - Tamanho: {file_size / (1024*1024):.2f} MB")
            else:
                # Arquivo não existe, mas o diretório foi criado pelo sqlite_path property
                # Isso é OK - o SQLite criará o arquivo na primeira conexão
                logger.info(f"📝 Arquivo SQLite não existe ainda - será criado na primeira conexão: {sqlite_path}")
                logger.info(f"   Diretório pai existe? {os.path.exists(os.path.dirname(sqlite_path))}")
        
        # Inicializa conexão com banco de dados
        init_db()
        logger.info("Conexão com banco de dados inicializada")
        
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
                app.state.agent_service_available = True
                logger.info("✅ Modelos de ML carregados com sucesso")
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
        from src.llm_openai_client import get_openai_client, call_llm
        
        # Valida configuração
        client_config = get_openai_client()
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
        "timestamp": datetime.utcnow().isoformat()
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
        logger.info(f"Pergunta recebida: {request.pergunta[:100]}...")
        
        # Verifica se agent service está disponível (modelos ML podem estar carregando)
        if not app.state.agent_service_available:
            logger.warning("⚠️  AgentService ainda não está disponível (modelos ML carregando em background)")
            return JSONResponse(
                status_code=503,
                content={
                    "error": "Serviço temporariamente indisponível",
                    "message": "Os modelos de ML ainda estão carregando. Por favor, aguarde alguns segundos e tente novamente.",
                    "detail": "AgentService está carregando em background. Isso geralmente leva 20-30 segundos após o startup.",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
        
        # Obtém serviço do agente
        agent_service = get_agent_service()
        
        # Processa pergunta
        result = agent_service.process_question(
            pergunta=request.pergunta,
            usuario_id=request.usuario_id,
            papel=request.papel,
            session=session
        )
        
        # Mapeia resultado do agente para formato CopilotAnswerPayload
        from src.api.copilot_mapper import map_agent_to_copilot_payload
        
        # Passa o contexto completo para o mapper (precisa dos dados de vendedores)
        copilot_payload = map_agent_to_copilot_payload(result, request.pergunta)
        
        # Prepara resposta com dados estruturados
        # Monta AskResponse com o payload estruturado
        dados_estruturados = _extrair_dados_estruturados(result, request.pergunta)
        dados_estruturados["payload"] = copilot_payload  # Adiciona payload estruturado
        
        response = AskResponse(**dados_estruturados)
        
        # Salva interação no banco de dados (não bloqueia se falhar)
        try:
            # Cria um contexto resumido com apenas números chave (não o contexto completo)
            contexto_resumido = _resumir_contexto(result.get("contexto", {}))
            
            interacao = InteracaoAgent(
                usuario_id=request.usuario_id,
                papel=request.papel,
                pergunta=request.pergunta,
                resposta=result["resposta"],
                intent=result["intent"],
                confianca=result["confianca"],
                contexto_resumido=contexto_resumido,
                sucesso=None  # Será preenchido depois pelo feedback do usuário
            )
            
            session.add(interacao)
            session.commit()
            
            logger.info(f"Interação salva com sucesso (ID: {interacao.id})")
        
        except Exception as e:
            # Não bloqueia a resposta se o insert falhar
            logger.error(f"Erro ao salvar interação no banco: {str(e)}")
            session.rollback()
            # Continua normalmente
        
        return response
    
    except Exception as e:
        # IMPORTANTE: Captura TODAS as exceções para garantir que sempre retornamos uma resposta com CORS
        # JSONResponse garante que o middleware CORS adicione os headers mesmo em erros
        # Isso evita que o worker morra e o Google Frontend retorne 503 sem headers CORS
        logger.error(f"❌ Erro ao processar pergunta: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Retorna erro estruturado COM headers CORS (via JSONResponse)
        return JSONResponse(
            status_code=500,
            content={
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


@app.post("/feedback/{interacao_id}", response_model=FeedbackResponse)
async def feedback_interacao(
    interacao_id: int = Path(..., description="ID da interação a receber feedback", gt=0),
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

