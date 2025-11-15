"""
Módulo de Logging de Interações.

Registra todas as interações do agente para aprendizado contínuo:
- Pergunta, intent, entidades, SQL executado, resposta
- Embedding da pergunta para agrupamento posterior
- Flag de sucesso/fracasso (baseado em se a resposta usou dados reais)
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from src.dw.models import InteracaoAgent, InteracaoEmbedding
from src.llm_openai_client import get_openai_client
import requests
import json

logger = logging.getLogger(__name__)


def gerar_embedding_pergunta(pergunta: str) -> Optional[list]:
    """
    Gera embedding da pergunta usando OpenAI embeddings API.
    
    Args:
        pergunta: Pergunta do usuário
        
    Returns:
        list: Embedding vetorial (1536 dimensões para text-embedding-ada-002) ou None em caso de erro
    """
    try:
        config = get_openai_client()
        api_key = config["api_key"]
        base_url = config["base_url"]
        
        # URL do endpoint de embeddings
        url = f"{base_url}/embeddings"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "text-embedding-ada-002",
            "input": pergunta
        }
        
        response = requests.post(url, json=data, headers=headers, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            embedding = result.get("data", [{}])[0].get("embedding")
            return embedding
        else:
            logger.warning(f"Erro ao gerar embedding: status {response.status_code}")
            return None
    
    except Exception as e:
        logger.warning(f"Erro ao gerar embedding da pergunta: {str(e)}")
        return None


def detectar_sucesso_resposta(contexto: Dict[str, Any], resposta: str) -> bool:
    """
    Detecta se a resposta foi baseada em dados reais (sucesso=True) ou caiu em fallback (sucesso=False).
    
    Critérios para sucesso=True:
    - Tem dados no contexto (tabelas, listas não vazias)
    - Resposta não contém mensagens de "não encontrei dados"
    - SQL foi executado (sql_executado não é None)
    
    Args:
        contexto: Contexto usado para gerar a resposta
        resposta: Resposta gerada
        
    Returns:
        bool: True se resposta foi baseada em dados reais, False caso contrário
    """
    # Verifica se há SQL executado
    if contexto.get("sql_executado"):
        return True
    
    # Verifica se há dados no contexto
    if contexto.get("tem_dados_suficientes") is False:
        return False
    
    # Verifica se há mensagem de dados insuficientes
    mensagem_insuficiente = contexto.get("mensagem_dados_insuficientes", "")
    if mensagem_insuficiente:
        return False
    
    # Verifica se resposta contém palavras-chave de fallback
    resposta_lower = resposta.lower()
    palavras_fallback = [
        "não encontrei dados",
        "não há dados",
        "sem dados",
        "dados insuficientes",
        "não foi possível",
        "erro ao processar"
    ]
    
    for palavra in palavras_fallback:
        if palavra in resposta_lower:
            return False
    
    # Verifica se há dados estruturados no contexto
    if contexto.get("dados") or contexto.get("clientes") or contexto.get("vendedores") or contexto.get("produtos"):
        return True
    
    # Se chegou aqui, assume sucesso (resposta foi gerada)
    return True


def registrar_interacao(
    session: Session,
    pergunta: str,
    resposta: str,
    intent: str,
    entities: Dict[str, Any],
    contexto: Dict[str, Any],
    confianca: float,
    usuario_id: Optional[str] = None,
    papel: Optional[str] = None,
    sql_executado: Optional[str] = None
) -> Optional[int]:
    """
    Registra uma interação do agente no banco de dados.
    
    Args:
        session: Sessão SQLAlchemy
        pergunta: Pergunta do usuário
        resposta: Resposta gerada pelo agente
        intent: Intent detectada
        entities: Entidades extraídas da pergunta
        contexto: Contexto usado para gerar a resposta
        confianca: Nível de confiança da resposta (0-1)
        usuario_id: ID do usuário (opcional)
        papel: Papel do usuário (diretor, supervisor, vendedor) (opcional)
        sql_executado: SQL executado se teve query (opcional)
        
    Returns:
        int: ID da interação registrada ou None em caso de erro
    """
    try:
        # Detecta sucesso da resposta
        sucesso = detectar_sucesso_resposta(contexto, resposta)
        
        # Prepara campos para salvar
        intent_prevista = intent  # Compatibilidade com campo específico
        
        # Serializa entidades para JSON
        entities_json = entities
        
        # Resumo curto da resposta (primeiros 200 caracteres)
        resposta_resumida = resposta[:200] + "..." if len(resposta) > 200 else resposta
        
        # Cria registro de interação
        interacao = InteracaoAgent(
            pergunta=pergunta,
            resposta=resposta,
            intent=intent,
            intent_prevista=intent_prevista,
            confianca=confianca,
            entities_json=entities_json,
            sql_executado=sql_executado,
            resposta_resumida=resposta_resumida,
            sucesso=sucesso,
            usuario_id=usuario_id,
            papel=papel,
            contexto_resumido={
                "intent": intent,
                "confianca": confianca,
                "sucesso": sucesso
            }
        )
        
        session.add(interacao)
        session.flush()  # Para obter o ID
        
        # Gera e salva embedding da pergunta
        embedding_data = gerar_embedding_pergunta(pergunta)
        if embedding_data:
            interacao_embedding = InteracaoEmbedding(
                interacao_id=interacao.id,
                embedding=embedding_data
            )
            session.add(interacao_embedding)
        
        session.commit()
        
        logger.info(
            f"Interação registrada: ID={interacao.id}, intent={intent}, "
            f"sucesso={sucesso}, confianca={confianca:.2f}"
        )
        
        return interacao.id
    
    except Exception as e:
        logger.error(f"Erro ao registrar interação: {str(e)}")
        session.rollback()
        return None

