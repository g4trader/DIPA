"""
Cliente OpenAI para integração com API de chat/completions.

Este módulo fornece funções para interagir com a API da OpenAI de forma segura,
usando variáveis de ambiente para configuração.
"""

import os
import logging
from typing import Optional, Dict, Any
import requests
from requests.exceptions import RequestException, Timeout

logger = logging.getLogger(__name__)


class OpenAIError(Exception):
    """Exceção personalizada para erros da API OpenAI."""
    pass


def get_openai_client() -> Dict[str, str]:
    """
    Lê e valida configurações do OpenAI a partir de variáveis de ambiente.
    
    Lê as seguintes variáveis:
    - OPENAI_API_KEY: Chave de API (obrigatória)
    - OPENAI_BASE_URL: URL base da API (opcional, padrão: https://api.openai.com/v1)
    - OPENAI_MODEL: Modelo a ser usado (opcional, padrão: gpt-4o-mini)
    
    Returns:
        dict: Dicionário com configurações do cliente
            {
                "api_key": str,
                "base_url": str,
                "model": str
            }
            
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
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    # Remove barra final se existir
    base_url = base_url.rstrip("/")
    
    logger.info(f"Cliente OpenAI configurado: base_url={base_url}, model={model}")
    
    return {
        "api_key": api_key,
        "base_url": base_url,
        "model": model
    }


def call_llm(
    prompt: str,
    system_prompt: Optional[str] = None,
    **kwargs
) -> str:
    """
    Faz uma chamada HTTP à API de chat/completions da OpenAI.
    
    Envia o prompt e system_prompt para a API e retorna a resposta gerada.
    
    Args:
        prompt: Prompt do usuário
        system_prompt: Prompt do sistema (opcional)
        **kwargs: Argumentos adicionais para a API:
            - temperature: float (padrão: 0.7)
            - max_tokens: int (padrão: 1000)
            - top_p: float (opcional)
            - frequency_penalty: float (opcional)
            - presence_penalty: float (opcional)
            
    Returns:
        str: Texto da resposta gerada pelo LLM
        
    Raises:
        OpenAIError: Se houver erro na chamada à API ou resposta inválida
        
    Example:
        resposta = call_llm(
            prompt="Qual a meta do vendedor X?",
            system_prompt="Você é um assistente comercial.",
            temperature=0.7,
            max_tokens=500
        )
    """
    try:
        # Obtém configurações do cliente
        config = get_openai_client()
        api_key = config["api_key"]
        base_url = config["base_url"]
        model = config["model"]
        
        # Monta URL do endpoint
        url = f"{base_url}/chat/completions"
        
        # Prepara mensagens
        messages = []
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        # Prepara parâmetros da requisição
        params = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1000),
        }
        
        # Adiciona parâmetros opcionais se fornecidos
        if "top_p" in kwargs:
            params["top_p"] = kwargs["top_p"]
        if "frequency_penalty" in kwargs:
            params["frequency_penalty"] = kwargs["frequency_penalty"]
        if "presence_penalty" in kwargs:
            params["presence_penalty"] = kwargs["presence_penalty"]
        
        logger.info(f"Chamando OpenAI API: model={model}, prompt_length={len(prompt)}")
        
        # Faz requisição HTTP
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        timeout = kwargs.get("timeout", 30)  # Timeout padrão de 30 segundos
        
        try:
            response = requests.post(
                url,
                json=params,
                headers=headers,
                timeout=timeout
            )
        except Timeout:
            raise OpenAIError(
                f"Timeout ao chamar API da OpenAI após {timeout} segundos. "
                "Tente novamente ou aumente o timeout."
            )
        except RequestException as e:
            raise OpenAIError(
                f"Erro de rede ao chamar API da OpenAI: {str(e)}"
            )
        
        # Verifica status da resposta
        if response.status_code != 200:
            error_detail = "Erro desconhecido"
            try:
                error_data = response.json()
                error_detail = error_data.get("error", {}).get("message", str(error_data))
            except:
                error_detail = response.text[:500]
            
            raise OpenAIError(
                f"Erro ao chamar API da OpenAI (status {response.status_code}): {error_detail}"
            )
        
        # Extrai resposta
        try:
            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                raise OpenAIError("API retornou resposta sem choices")
            
            content = choices[0].get("message", {}).get("content", "")
            if not content:
                raise OpenAIError("API retornou resposta vazia")
            
            logger.info(f"Resposta do OpenAI gerada ({len(content)} caracteres)")
            return content.strip()
            
        except (KeyError, ValueError) as e:
            raise OpenAIError(f"Erro ao processar resposta da API: {str(e)}")
    
    except OpenAIError:
        raise
    except Exception as e:
        logger.error(f"Erro inesperado ao chamar OpenAI API: {str(e)}")
        raise OpenAIError(f"Erro inesperado: {str(e)}")



