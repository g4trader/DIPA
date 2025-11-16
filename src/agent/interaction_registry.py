"""
Registro de interações do agente para aprendizado contínuo (FASE 4).

Este módulo contém funções helper para registrar interações do agente
na tabela interacoes_agent com todos os metadados necessários.
"""

import time
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from src.dw.models import InteracaoAgent

logger = logging.getLogger(__name__)


def registrar_interacao_agent(
    session: Session,
    papel_usuario: Optional[str],
    pergunta: str,
    intent: str,
    entidades: Dict[str, Any],
    resposta: Dict[str, Any],
    sucesso_resposta: bool,
    fonte_dados_principal: Optional[str] = None,
    num_registros_usados: Optional[int] = None,
    tempo_processamento_ms: Optional[int] = None
) -> Optional[int]:
    """
    Registra uma interação do agente na tabela interacoes_agent.
    
    Args:
        session: Sessão SQLAlchemy
        papel_usuario: Papel do usuário (ex.: "diretor", "supervisor", "vendedor")
        pergunta: Pergunta completa enviada para /ask
        intent: Intent detectado (ex.: "consulta_meta", "consulta_vendedores_performance")
        entidades: Dicionário com entidades extraídas (mes_ano, vendedor, etc.)
        resposta: Dicionário com a resposta completa (deve conter resumo_executivo, contexto_debug, etc.)
        sucesso_resposta: True se o backend conseguiu responder com dados reais
        fonte_dados_principal: Fonte principal dos dados (ex.: "analytics_vendedor_mes")
        num_registros_usados: Quantidade de linhas de analytics consultadas
        tempo_processamento_ms: Tempo de processamento em milissegundos
        
    Returns:
        ID da interação registrada ou None se falhar
    """
    try:
        # Extrai resumo executivo da resposta estruturada
        resumo_executivo = None
        if isinstance(resposta, dict):
            # Tenta pegar de structured.resumo_executivo primeiro
            structured = resposta.get("structured", {})
            if isinstance(structured, dict):
                resumo_executivo = structured.get("resumo_executivo")
            
            # Fallback para resumoExecutivo (formato antigo)
            if not resumo_executivo:
                resumo_executivo = resposta.get("resumoExecutivo")
            
            # Fallback para resumo do contexto
            if not resumo_executivo:
                contexto = resposta.get("contexto", {})
                if isinstance(contexto, dict):
                    resumo_executivo = contexto.get("resumo_executivo")
        
        # Extrai contexto de debug
        debug_payload = None
        if isinstance(resposta, dict):
            structured = resposta.get("structured", {})
            if isinstance(structured, dict):
                debug_payload = structured.get("contexto_debug")
            
            # Fallback para contexto_debug direto
            if not debug_payload:
                debug_payload = resposta.get("contexto_debug")
        
        # Cria registro de interação
        interacao = InteracaoAgent(
            papel=papel_usuario,
            pergunta=pergunta,
            intent=intent,
            entities_json=entidades,
            resumo_executivo=resumo_executivo,
            sucesso=sucesso_resposta,
            sucesso_resposta=sucesso_resposta,  # Alias para compatibilidade
            fonte_dados_principal=fonte_dados_principal,
            num_registros_usados=num_registros_usados,
            tempo_processamento_ms=tempo_processamento_ms,
            debug_payload=debug_payload,
            # Resposta completa (texto) - pega do resultado original se disponível
            resposta=resposta.get("resposta", "") if isinstance(resposta, dict) else str(resposta),
            # Confiança (se disponível)
            confianca=resposta.get("confianca", 0.0) if isinstance(resposta, dict) else 0.0
        )
        
        session.add(interacao)
        session.commit()
        
        logger.info(f"✅ Interação registrada com sucesso (ID: {interacao.id}, intent: {intent})")
        return interacao.id
    
    except Exception as e:
        # NÃO bloqueia a resposta se falhar
        logger.warning(f"⚠️  Erro ao registrar interação (não bloqueia resposta): {str(e)}")
        session.rollback()
        return None

