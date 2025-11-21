"""
Cliente GROQ centralizado com "GROQ Guard" para proteção contra limites de tamanho.

Este módulo implementa:
- Limitação automática de tamanho de prompt
- Truncamento inteligente preservando início e fim
- Sempre define max_tokens
- Tratamento específico de erros GROQ (400 - "Please reduce the length")
- Logging estruturado de eventos
"""

import os
import logging
from typing import Optional, Dict, Any
import requests
from requests.exceptions import RequestException, Timeout
import json

logger = logging.getLogger(__name__)

# Configurações padrão do GROQ Guard
DEFAULT_MAX_PROMPT_CHARS = 10000  # Limite padrão de caracteres no prompt
DEFAULT_MAX_TOKENS = 512  # Max tokens padrão para resumos
DEFAULT_MAX_TOKENS_PDF = 1024  # Max tokens para PDF
DEFAULT_MAX_TOKENS_ASK = 2048  # Max tokens para /ask

# Configurações por contexto
CONTEXT_MAX_TOKENS = {
    "resumo_executivo": DEFAULT_MAX_TOKENS,
    "pdf": DEFAULT_MAX_TOKENS_PDF,
    "ask": DEFAULT_MAX_TOKENS_ASK,
    "default": DEFAULT_MAX_TOKENS,
}


class GroqContentTooLongError(Exception):
    """Exceção levantada quando o conteúdo excede o limite do GROQ."""
    pass


class GroqError(Exception):
    """Exceção genérica para erros do GROQ."""
    pass


def truncate_prompt(
    prompt: str,
    max_chars: int = DEFAULT_MAX_PROMPT_CHARS,
    preserve_start: bool = True,
    preserve_end: bool = True,
    truncation_marker: str = "[CONTEXTO TRUNCADO]"
) -> str:
    """
    Trunca um prompt preservando início e fim quando possível.
    
    Args:
        prompt: Prompt original
        max_chars: Número máximo de caracteres
        preserve_start: Se True, preserva o início do prompt
        preserve_end: Se True, preserva o fim do prompt
        truncation_marker: Marcador a inserir quando truncar
        
    Returns:
        Prompt truncado
    """
    if len(prompt) <= max_chars:
        return prompt
    
    logger.warning(
        f"Prompt truncado: {len(prompt)} -> {max_chars} caracteres",
        extra={
            "event": "groq_prompt_truncated",
            "original_length": len(prompt),
            "truncated_length": max_chars,
        }
    )
    
    if preserve_start and preserve_end:
        # Preserva início e fim, corta o meio
        # Garante que o resultado final não exceda max_chars
        marker_len = len(truncation_marker)
        available_chars = max_chars - marker_len
        start_chars = available_chars // 2
        end_chars = available_chars - start_chars  # Resto vai para o fim
        
        start_part = prompt[:start_chars]
        end_part = prompt[-end_chars:]
        
        result = f"{start_part}{truncation_marker}{end_part}"
        # Garante que não excede (pode acontecer por arredondamento)
        if len(result) > max_chars:
            result = result[:max_chars]
        return result
    elif preserve_start:
        # Preserva apenas o início
        return prompt[:max_chars - len(truncation_marker)] + truncation_marker
    else:
        # Preserva apenas o fim
        return truncation_marker + prompt[-(max_chars - len(truncation_marker)):]


def call_groq_model(
    prompt: str,
    *,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    system: Optional[str] = None,
    max_prompt_chars: Optional[int] = None,
    contexto: str = "default",
    temperature: float = 0.7,
) -> str:
    """
    Chama o modelo GROQ com proteção automática contra limites de tamanho.
    
    Aplica as seguintes regras ANTES de chamar a API:
    - Limita o tamanho do prompt em caracteres (padrão: 10000)
    - Se o prompt passar do limite, trunca preservando início e fim
    - Sempre define max_tokens (nunca deixa "solto")
    - Trata erros específicos do GROQ (400 - "Please reduce the length")
    
    Args:
        prompt: Prompt do usuário
        max_tokens: Número máximo de tokens na resposta (padrão: 512)
        system: Prompt do sistema (opcional)
        max_prompt_chars: Limite de caracteres no prompt (None = usa padrão)
        contexto: Contexto da chamada ("resumo_executivo", "pdf", "ask", "default")
        temperature: Temperatura para geração (padrão: 0.7)
        
    Returns:
        str: Resposta do GROQ
        
    Raises:
        GroqContentTooLongError: Se o conteúdo exceder o limite mesmo após truncamento
        GroqError: Para outros erros do GROQ
    """
    # Obtém configurações do GROQ
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise GroqError("GROQ_API_KEY não configurada")
    
    base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    
    # Remove barra final se existir
    base_url = base_url.rstrip("/")
    
    # Ajusta max_tokens baseado no contexto se não foi especificado explicitamente
    if max_tokens == DEFAULT_MAX_TOKENS and contexto in CONTEXT_MAX_TOKENS:
        max_tokens = CONTEXT_MAX_TOKENS[contexto]
    
    # Define limite de caracteres no prompt
    if max_prompt_chars is None:
        max_prompt_chars = DEFAULT_MAX_PROMPT_CHARS
    
    # Trunca prompt se necessário
    prompt_original_length = len(prompt)
    prompt_truncated = truncate_prompt(prompt, max_chars=max_prompt_chars)
    
    # Trunca system prompt se necessário
    system_truncated = None
    if system:
        system_original_length = len(system)
        system_truncated = truncate_prompt(system, max_chars=max_prompt_chars // 2)
        if len(system_truncated) < system_original_length:
            logger.warning(
                f"System prompt truncado: {system_original_length} -> {len(system_truncated)} caracteres",
                extra={
                    "event": "groq_system_prompt_truncated",
                    "original_length": system_original_length,
                    "truncated_length": len(system_truncated),
                }
            )
    
    # Monta mensagens
    messages = []
    if system_truncated:
        messages.append({
            "role": "system",
            "content": system_truncated
        })
    messages.append({
        "role": "user",
        "content": prompt_truncated
    })
    
    # Monta payload da requisição
    url = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Log antes da chamada
    logger.info(
        f"Chamando GROQ API: model={model}, prompt_length={len(prompt_truncated)}, "
        f"max_tokens={max_tokens}, contexto={contexto}",
        extra={
            "event": "groq_api_call",
            "model": model,
            "prompt_length": len(prompt_truncated),
            "prompt_original_length": prompt_original_length,
            "max_tokens": max_tokens,
            "contexto": contexto,
        }
    )
    
    try:
        # Faz requisição HTTP
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        # Verifica status da resposta
        if response.status_code == 400:
            # Tenta extrair mensagem de erro
            try:
                error_data = response.json()
                error_message = error_data.get("error", {}).get("message", str(error_data))
            except:
                error_message = response.text[:500]
            
            # Verifica se é erro de "too long"
            if "Please reduce the length" in error_message or "reduce the length" in error_message.lower():
                # Log estruturado do evento
                logger.error(
                    f"GROQ retornou erro 400 - conteúdo muito longo: {error_message}",
                    extra={
                        "event": "groq_too_long",
                        "length_prompt_chars": len(prompt_truncated),
                        "max_tokens": max_tokens,
                        "contexto": contexto,
                        "error_message": error_message,
                    }
                )
                
                # Levanta exceção específica
                raise GroqContentTooLongError(
                    f"Conteúdo excede limite do GROQ mesmo após truncamento. "
                    f"Prompt: {len(prompt_truncated)} chars, max_tokens: {max_tokens}, "
                    f"contexto: {contexto}. Erro: {error_message}"
                )
            else:
                # Outro erro 400
                logger.error(
                    f"GROQ retornou erro 400: {error_message}",
                    extra={
                        "event": "groq_error_400",
                        "error_message": error_message,
                        "contexto": contexto,
                    }
                )
                raise GroqError(f"Erro 400 do GROQ: {error_message}")
        
        elif response.status_code != 200:
            # Outros erros HTTP
            try:
                error_data = response.json()
                error_message = error_data.get("error", {}).get("message", str(error_data))
            except:
                error_message = response.text[:500]
            
            logger.error(
                f"GROQ retornou erro {response.status_code}: {error_message}",
                extra={
                    "event": "groq_error",
                    "status_code": response.status_code,
                    "error_message": error_message,
                    "contexto": contexto,
                }
            )
            raise GroqError(f"Erro {response.status_code} do GROQ: {error_message}")
        
        # Extrai resposta
        try:
            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                raise GroqError("GROQ retornou resposta sem choices")
            
            content = choices[0].get("message", {}).get("content", "")
            if not content:
                raise GroqError("GROQ retornou resposta vazia")
            
            logger.info(
                f"Resposta GROQ gerada: {len(content)} caracteres",
                extra={
                    "event": "groq_success",
                    "response_length": len(content),
                    "contexto": contexto,
                }
            )
            
            return content.strip()
            
        except (KeyError, ValueError) as e:
            raise GroqError(f"Erro ao processar resposta do GROQ: {str(e)}")
    
    except GroqContentTooLongError:
        raise
    except GroqError:
        raise
    except Timeout:
        logger.error(
            "Timeout ao chamar GROQ API",
            extra={
                "event": "groq_timeout",
                "contexto": contexto,
            }
        )
        raise GroqError("Timeout ao chamar GROQ API após 30 segundos")
    except RequestException as e:
        logger.error(
            f"Erro de rede ao chamar GROQ API: {str(e)}",
            extra={
                "event": "groq_network_error",
                "error": str(e),
                "contexto": contexto,
            }
        )
        raise GroqError(f"Erro de rede ao chamar GROQ API: {str(e)}")
    except Exception as e:
        logger.error(
            f"Erro inesperado ao chamar GROQ API: {str(e)}",
            extra={
                "event": "groq_unexpected_error",
                "error": str(e),
                "contexto": contexto,
            }
        )
        raise GroqError(f"Erro inesperado: {str(e)}")

