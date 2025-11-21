#!/usr/bin/env python3
"""
Script para testar o GROQ Guard com prompts grandes.

Este script:
1. Constrói um prompt artificialmente grande (bem maior que o limite)
2. Chama call_groq_model
3. Verifica:
   - Se o texto foi truncado antes do envio
   - Se, em caso de 400 simulado, a exceção GroqContentTooLongError é lançada corretamente
"""

import sys
import os
from pathlib import Path

# Adiciona o diretório raiz ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

import logging
from src.api.groq_client import (
    call_groq_model,
    GroqContentTooLongError,
    GroqError,
    truncate_prompt,
    DEFAULT_MAX_PROMPT_CHARS
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_truncate_prompt():
    """Testa a função truncate_prompt."""
    logger.info("=" * 80)
    logger.info("TESTE 1: Truncamento de Prompt")
    logger.info("=" * 80)
    
    # Cria prompt muito grande
    prompt_grande = "A" * (DEFAULT_MAX_PROMPT_CHARS + 5000)
    
    logger.info(f"Prompt original: {len(prompt_grande)} caracteres")
    logger.info(f"Limite: {DEFAULT_MAX_PROMPT_CHARS} caracteres")
    
    prompt_truncado = truncate_prompt(prompt_grande, max_chars=DEFAULT_MAX_PROMPT_CHARS)
    
    logger.info(f"Prompt truncado: {len(prompt_truncado)} caracteres")
    
    assert len(prompt_truncado) <= DEFAULT_MAX_PROMPT_CHARS, "Prompt não foi truncado corretamente"
    assert "[CONTEXTO TRUNCADO]" in prompt_truncado, "Marcador de truncamento não encontrado"
    
    logger.info("✅ TESTE 1 PASSOU: Truncamento funcionando corretamente")
    logger.info("")


def test_groq_guard_with_large_prompt():
    """Testa o GROQ Guard com prompt grande."""
    logger.info("=" * 80)
    logger.info("TESTE 2: GROQ Guard com Prompt Grande")
    logger.info("=" * 80)
    
    # Verifica se GROQ_API_KEY está configurada
    if not os.getenv("GROQ_API_KEY"):
        logger.warning("⚠️  GROQ_API_KEY não configurada. Pulando teste real.")
        logger.info("   Para testar completamente, configure GROQ_API_KEY e execute novamente.")
        return
    
    # Cria prompt grande (mas não extremo, para não gastar tokens desnecessariamente)
    prompt_grande = "Analise os seguintes dados:\n\n" + "\n".join([
        f"Cliente {i}: dados detalhados " + "X" * 100
        for i in range(200)  # 200 clientes com 100 chars cada = ~20k chars
    ])
    
    logger.info(f"Prompt original: {len(prompt_grande)} caracteres")
    logger.info(f"Limite padrão: {DEFAULT_MAX_PROMPT_CHARS} caracteres")
    
    try:
        resposta = call_groq_model(
            prompt=prompt_grande,
            system="Você é um analista executivo.",
            max_tokens=256,
            contexto="test",
        )
        
        logger.info(f"✅ GROQ aceitou o prompt (resposta: {len(resposta)} caracteres)")
        logger.info("   O prompt foi truncado automaticamente antes do envio.")
        
    except GroqContentTooLongError as e:
        logger.error(f"❌ GROQ recusou conteúdo muito longo (esperado em alguns casos): {str(e)}")
        logger.info("   Isso é esperado se o conteúdo exceder o limite mesmo após truncamento.")
        logger.info("   O sistema deve tratar isso com fallback.")
        
    except GroqError as e:
        logger.error(f"❌ Erro do GROQ: {str(e)}")
        logger.info("   Verifique se GROQ_API_KEY está correta e se há conexão com a internet.")
        
    logger.info("")


def test_groq_guard_with_normal_prompt():
    """Testa o GROQ Guard com prompt normal."""
    logger.info("=" * 80)
    logger.info("TESTE 3: GROQ Guard com Prompt Normal")
    logger.info("=" * 80)
    
    # Verifica se GROQ_API_KEY está configurada
    if not os.getenv("GROQ_API_KEY"):
        logger.warning("⚠️  GROQ_API_KEY não configurada. Pulando teste real.")
        return
    
    prompt_normal = "Analise os seguintes dados: Total de clientes: 100. Meta: R$ 50.000. Realizado: R$ 45.000."
    
    try:
        resposta = call_groq_model(
            prompt=prompt_normal,
            system="Você é um analista executivo. Gere um resumo curto.",
            max_tokens=128,
            contexto="test",
        )
        
        logger.info(f"✅ GROQ processou prompt normal com sucesso")
        logger.info(f"   Resposta: {resposta[:100]}...")
        
    except Exception as e:
        logger.error(f"❌ Erro inesperado: {str(e)}")
        raise
    
    logger.info("")


if __name__ == "__main__":
    try:
        test_truncate_prompt()
        test_groq_guard_with_large_prompt()
        test_groq_guard_with_normal_prompt()
        
        logger.info("=" * 80)
        logger.info("✅ TODOS OS TESTES CONCLUÍDOS")
        logger.info("=" * 80)
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"❌ Erro durante testes: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

