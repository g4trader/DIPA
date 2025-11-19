"""
Cliente LLM genérico que suporta múltiplos provedores (OpenAI, Groq).

Este módulo fornece funções para interagir com APIs de LLM de forma unificada,
suportando OpenAI e Groq através de variáveis de ambiente.
"""

import os
import logging
from typing import Optional, Dict, Any, Literal
import requests
from requests.exceptions import RequestException, Timeout

logger = logging.getLogger(__name__)

# Tipos de provedores suportados
LLMProvider = Literal["openai", "groq"]


class LLMError(Exception):
    """Exceção personalizada para erros de APIs LLM."""
    pass


def get_llm_provider() -> LLMProvider:
    """
    Determina qual provedor LLM usar baseado em variáveis de ambiente.
    
    Prioridade:
    1. GROQ_API_KEY presente → usa Groq
    2. OPENAI_API_KEY presente → usa OpenAI
    3. Padrão: OpenAI (se nenhuma chave estiver presente, retorna erro)
    
    Returns:
        LLMProvider: "openai" ou "groq"
    """
    groq_key = os.getenv("GROQ_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if groq_key:
        return "groq"
    elif openai_key:
        return "openai"
    else:
        raise LLMError(
            "Nenhuma chave de API LLM configurada. "
            "Configure GROQ_API_KEY ou OPENAI_API_KEY."
        )


def get_llm_config(provider: Optional[LLMProvider] = None) -> Dict[str, str]:
    """
    Lê e valida configurações do LLM a partir de variáveis de ambiente.
    
    Para Groq:
    - GROQ_API_KEY: Chave de API (obrigatória)
    - GROQ_BASE_URL: URL base (opcional, padrão: https://api.groq.com/openai/v1)
    - GROQ_MODEL: Modelo (opcional, padrão: mixtral-8x7b-32768)
    
    Para OpenAI:
    - OPENAI_API_KEY: Chave de API (obrigatória)
    - OPENAI_BASE_URL: URL base (opcional, padrão: https://api.openai.com/v1)
    - OPENAI_MODEL: Modelo (opcional, padrão: gpt-4o-mini)
    
    Args:
        provider: Provedor a usar ("openai" ou "groq"). Se None, detecta automaticamente.
    
    Returns:
        dict: Dicionário com configurações do cliente
            {
                "provider": str,
                "api_key": str,
                "base_url": str,
                "model": str
            }
            
    Raises:
        LLMError: Se a chave de API não estiver configurada
    """
    if provider is None:
        provider = get_llm_provider()
    
    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise LLMError(
                "GROQ_API_KEY não encontrada. "
                "Configure a variável de ambiente GROQ_API_KEY com sua chave de API do Groq."
            )
        
        base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
        model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        
    else:  # OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise LLMError(
                "OPENAI_API_KEY não encontrada. "
                "Configure a variável de ambiente OPENAI_API_KEY com sua chave de API da OpenAI."
            )
        
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    # Remove barra final se existir
    base_url = base_url.rstrip("/")
    
    logger.info(f"Cliente LLM configurado: provider={provider}, base_url={base_url}, model={model}")
    
    return {
        "provider": provider,
        "api_key": api_key,
        "base_url": base_url,
        "model": model
    }


def call_llm(
    prompt: str,
    system_prompt: Optional[str] = None,
    provider: Optional[LLMProvider] = None,
    **kwargs
) -> str:
    """
    Faz uma chamada HTTP à API de chat/completions do LLM (OpenAI ou Groq).
    
    Envia o prompt e system_prompt para a API e retorna a resposta gerada.
    
    Args:
        prompt: Prompt do usuário
        system_prompt: Prompt do sistema (opcional)
        provider: Provedor a usar ("openai" ou "groq"). Se None, detecta automaticamente.
        **kwargs: Argumentos adicionais para a API:
            - temperature: float (padrão: 0.7)
            - max_tokens: int (padrão: 1000)
            - top_p: float (opcional)
            - frequency_penalty: float (opcional)
            - presence_penalty: float (opcional)
            
    Returns:
        str: Texto da resposta gerada pelo LLM
        
    Raises:
        LLMError: Se houver erro na chamada à API ou resposta inválida
        
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
        config = get_llm_config(provider)
        api_key = config["api_key"]
        base_url = config["base_url"]
        model = config["model"]
        provider_name = config["provider"]
        
        # Monta URL do endpoint (mesmo formato para OpenAI e Grok)
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
        
        logger.info(f"Chamando {provider_name.upper()} API: model={model}, prompt_length={len(prompt)}")
        
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
            raise LLMError(
                f"Timeout ao chamar API do {provider_name.upper()} após {timeout} segundos. "
                "Tente novamente ou aumente o timeout."
            )
        except RequestException as e:
            raise LLMError(
                f"Erro de rede ao chamar API do {provider_name.upper()}: {str(e)}"
            )
        
        # Verifica status da resposta
        if response.status_code != 200:
            error_detail = "Erro desconhecido"
            try:
                error_data = response.json()
                error_detail = error_data.get("error", {}).get("message", str(error_data))
            except:
                error_detail = response.text[:500]
            
            raise LLMError(
                f"Erro ao chamar API do {provider_name.upper()} (status {response.status_code}): {error_detail}"
            )
        
        # Extrai resposta
        try:
            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                raise LLMError(f"API do {provider_name.upper()} retornou resposta sem choices")
            
            content = choices[0].get("message", {}).get("content", "")
            if not content:
                raise LLMError(f"API do {provider_name.upper()} retornou resposta vazia")
            
            logger.info(f"Resposta do {provider_name.upper()} gerada ({len(content)} caracteres)")
            return content.strip()
            
        except (KeyError, ValueError) as e:
            raise LLMError(f"Erro ao processar resposta da API: {str(e)}")
    
    except LLMError:
        raise
    except Exception as e:
        logger.error(f"Erro inesperado ao chamar {provider_name.upper()} API: {str(e)}")
        raise LLMError(f"Erro inesperado: {str(e)}")


# Funções de compatibilidade para manter código existente funcionando
def get_openai_client() -> Dict[str, str]:
    """
    Função de compatibilidade que retorna configurações do LLM.
    Mantida para compatibilidade com código existente.
    """
    config = get_llm_config()
    return {
        "api_key": config["api_key"],
        "base_url": config["base_url"],
        "model": config["model"]
    }


# Alias para compatibilidade
OpenAIError = LLMError

