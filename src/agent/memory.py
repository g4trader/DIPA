"""
Sistema de Memória Q&A usando Embeddings da OpenAI.

Este módulo fornece funções para gerar embeddings de perguntas
e criar um índice semântico das interações para busca por similaridade.
"""

import os
import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError as SQLAlchemyOperationalError
import sqlite3
import requests
from requests.exceptions import RequestException, Timeout

from src.dw.models import InteracaoAgent, InteracaoEmbedding
from src.llm_openai_client import OpenAIError

logger = logging.getLogger(__name__)

# Modelo de embeddings padrão da OpenAI
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
# Dimensão padrão do embedding (1536 para text-embedding-3-small, 3072 para text-embedding-3-large)
EMBEDDING_DIMENSION = int(os.getenv("OPENAI_EMBEDDING_DIMENSION", "1536"))


def get_openai_config() -> dict:
    """
    Obtém configuração do cliente OpenAI.
    
    Returns:
        dict: Configuração com api_key e base_url
        
    Raises:
        OpenAIError: Se a chave de API não estiver configurada
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise OpenAIError(
            "OPENAI_API_KEY não encontrada. "
            "Configure a variável de ambiente OPENAI_API_KEY com sua chave de API da OpenAI."
        )
    
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    
    return {
        "api_key": api_key,
        "base_url": base_url,
    }


def gerar_embedding(texto: str) -> List[float]:
    """
    Gera embedding vetorial para um texto usando a API de embeddings da OpenAI.
    
    Args:
        texto: Texto para gerar embedding
        
    Returns:
        List[float]: Lista de floats representando o embedding vetorial
        
    Raises:
        OpenAIError: Se houver erro na chamada à API
    """
    if not texto or not texto.strip():
        raise ValueError("Texto não pode estar vazio")
    
    try:
        config = get_openai_config()
        
        # Endpoint de embeddings
        url = f"{config['base_url']}/embeddings"
        
        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": EMBEDDING_MODEL,
            "input": texto.strip(),
        }
        
        # Adiciona dimension se for text-embedding-3-*
        if "text-embedding-3" in EMBEDDING_MODEL:
            payload["dimensions"] = EMBEDDING_DIMENSION
        
        logger.debug(f"Gerando embedding para texto: {texto[:50]}...")
        
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            error_msg = f"Erro ao gerar embedding: {response.status_code}"
            try:
                error_data = response.json()
                error_msg += f" - {error_data.get('error', {}).get('message', 'Erro desconhecido')}"
            except:
                error_msg += f" - {response.text[:200]}"
            
            logger.error(error_msg)
            raise OpenAIError(error_msg)
        
        result = response.json()
        embedding = result["data"][0]["embedding"]
        
        logger.debug(f"Embedding gerado: {len(embedding)} dimensões")
        
        return embedding
        
    except OpenAIError:
        raise
    except Timeout:
        error_msg = "Timeout ao gerar embedding (mais de 30 segundos)"
        logger.error(error_msg)
        raise OpenAIError(error_msg)
    except RequestException as e:
        error_msg = f"Erro de rede ao gerar embedding: {str(e)}"
        logger.error(error_msg)
        raise OpenAIError(error_msg)
    except Exception as e:
        error_msg = f"Erro inesperado ao gerar embedding: {str(e)}"
        logger.error(error_msg)
        raise OpenAIError(error_msg)


def indexar_interacao(
    session: Session,
    interacao_id: int,
    pergunta: str
) -> InteracaoEmbedding:
    """
    Gera embedding para uma pergunta e salva na tabela interacoes_embedding.
    
    Se já existir um embedding para esta interação, atualiza o existente.
    
    Args:
        session: Sessão SQLAlchemy
        interacao_id: ID da interação em interacoes_agent
        pergunta: Texto da pergunta para gerar embedding
        
    Returns:
        InteracaoEmbedding: Objeto do embedding criado/atualizado
        
    Raises:
        ValueError: Se a interação não existir
        OpenAIError: Se houver erro ao gerar embedding
    """
    # Verifica se a interação existe
    interacao = session.query(InteracaoAgent).filter(
        InteracaoAgent.id == interacao_id
    ).first()
    
    if not interacao:
        raise ValueError(f"Interação com ID {interacao_id} não encontrada")
    
    # Gera embedding
    embedding_vector = gerar_embedding(pergunta)
    
    # Verifica se já existe embedding para esta interação
    embedding_existente = session.query(InteracaoEmbedding).filter(
        InteracaoEmbedding.interacao_id == interacao_id
    ).first()
    
    if embedding_existente:
        # Atualiza embedding existente
        embedding_existente.embedding = embedding_vector
        logger.info(f"Embedding atualizado para interação {interacao_id}")
        return embedding_existente
    else:
        # Cria novo embedding
        novo_embedding = InteracaoEmbedding(
            interacao_id=interacao_id,
            embedding=embedding_vector
        )
        session.add(novo_embedding)
        logger.info(f"Embedding criado para interação {interacao_id}")
        return novo_embedding


def buscar_interacoes_similares(
    session: Session,
    pergunta: str,
    limite: int = 5,
    threshold: float = 0.7
) -> List[dict]:
    """
    Busca interações similares usando similaridade de cosseno.
    
    Args:
        session: Sessão SQLAlchemy
        pergunta: Pergunta para buscar similares
        limite: Número máximo de resultados
        threshold: Limite mínimo de similaridade (0-1)
        
    Returns:
        List[dict]: Lista de dicionários com informações das interações similares
            {
                "interacao_id": int,
                "pergunta": str,
                "resposta": str,
                "similaridade": float,
                "intent": str,
                "confianca": float
            }
    """
    import numpy as np
    
    # Gera embedding da pergunta
    embedding_query = gerar_embedding(pergunta)
    
    # Busca todos os embeddings
    embeddings = session.query(InteracaoEmbedding).all()
    
    if not embeddings:
        logger.warning("Nenhum embedding encontrado no banco")
        return []
    
    # Calcula similaridade de cosseno
    resultados = []
    query_vec = np.array(embedding_query)
    
    for emb in embeddings:
        emb_vec = np.array(emb.embedding)
        
        # Similaridade de cosseno
        dot_product = np.dot(query_vec, emb_vec)
        norm_query = np.linalg.norm(query_vec)
        norm_emb = np.linalg.norm(emb_vec)
        
        if norm_query == 0 or norm_emb == 0:
            continue
        
        similaridade = dot_product / (norm_query * norm_emb)
        
        if similaridade >= threshold:
            interacao = emb.interacao
            resultados.append({
                "interacao_id": interacao.id,
                "pergunta": interacao.pergunta,
                "resposta": interacao.resposta,
                "similaridade": float(similaridade),
                "intent": interacao.intent,
                "confianca": interacao.confianca
            })
    
    # Ordena por similaridade (maior primeiro)
    resultados.sort(key=lambda x: x["similaridade"], reverse=True)
    
    # Retorna top N
    return resultados[:limite]


def buscar_interacoes_parecidas(
    session: Session,
    pergunta: str,
    limite: int = 5,
    threshold: float = 0.0
) -> List[dict]:
    """
    Busca interações parecidas ordenadas por similaridade.
    
    Gera embedding da pergunta, calcula similaridade com embeddings armazenados,
    ordena por similaridade e retorna as top N interações.
    
    Esta função é resiliente a erros de banco de dados: se a tabela não existir
    ou houver algum problema, retorna lista vazia sem interromper o fluxo.
    
    Args:
        session: Sessão SQLAlchemy
        pergunta: Pergunta para buscar similares
        limite: Número máximo de resultados
        threshold: Limite mínimo de similaridade (0-1, padrão: 0.0 para retornar todas)
        
    Returns:
        List[dict]: Lista de dicionários com informações das interações parecidas
            {
                "interacao_id": int,
                "pergunta": str,
                "resposta": str,
                "intent": str,
                "confianca": float,
                "sucesso": bool or None,
                "similaridade": float
            }
            Ordenado por similaridade (maior primeiro)
            Retorna [] (lista vazia) em caso de erro de banco ou ausência de dados
    """
    import numpy as np
    
    # Gera embedding da pergunta
    try:
        embedding_query = gerar_embedding(pergunta)
    except Exception as e:
        logger.warning(f"Erro ao gerar embedding: {str(e)}")
        return []
    
    # Busca todos os embeddings com suas interações
    # Envolto em try/except para garantir que erros de banco não derrubem o agente
    try:
        embeddings = session.query(InteracaoEmbedding).join(InteracaoAgent).all()
    except (SQLAlchemyOperationalError, sqlite3.OperationalError) as e:
        # Erro de banco: tabela não existe, migração pendente, etc.
        logger.warning(
            f"Erro ao buscar embeddings no banco (tabela pode não existir): {str(e)}. "
            f"Retornando lista vazia. O agente continuará sem usar memória."
        )
        return []
    except Exception as e:
        # Outros erros inesperados
        logger.warning(
            f"Erro inesperado ao buscar embeddings: {str(e)}. "
            f"Retornando lista vazia. O agente continuará sem usar memória."
        )
        return []
    
    if not embeddings:
        logger.debug("Nenhum embedding encontrado no banco")
        return []
    
    # Calcula similaridade de cosseno
    try:
        resultados = []
        query_vec = np.array(embedding_query)
        
        for emb in embeddings:
            emb_vec = np.array(emb.embedding)
            
            # Similaridade de cosseno
            dot_product = np.dot(query_vec, emb_vec)
            norm_query = np.linalg.norm(query_vec)
            norm_emb = np.linalg.norm(emb_vec)
            
            if norm_query == 0 or norm_emb == 0:
                continue
            
            similaridade = dot_product / (norm_query * norm_emb)
            
            if similaridade >= threshold:
                interacao = emb.interacao
                resultados.append({
                    "interacao_id": interacao.id,
                    "pergunta": interacao.pergunta,
                    "resposta": interacao.resposta,
                    "intent": interacao.intent,
                    "confianca": interacao.confianca,
                    "sucesso": interacao.sucesso,  # True, False ou None
                    "similaridade": float(similaridade)
                })
        
        # Ordena por similaridade (maior primeiro)
        resultados.sort(key=lambda x: x["similaridade"], reverse=True)
        
        # Retorna top N
        return resultados[:limite]
    
    except Exception as e:
        # Erro ao processar embeddings (ex: formato inválido, numpy error)
        logger.warning(
            f"Erro ao processar similaridade de embeddings: {str(e)}. "
            f"Retornando lista vazia."
        )
        return []

