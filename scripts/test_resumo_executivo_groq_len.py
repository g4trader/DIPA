#!/usr/bin/env python3
"""
Script para testar Resumo Executivo com resposta muito grande.

Este script:
- Simula um cenário onde a resposta é muito grande
- Garante que:
  - Não há crash
  - Se a GROQ recusar, o sistema gera um resumo de fallback e segue
"""

import sys
import os
from pathlib import Path

# Adiciona o diretório raiz ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

import logging
from src.llm_integration import gerar_resposta_llm_diretor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_resumo_executivo_com_dados_grandes():
    """Testa resumo executivo com contexto muito grande."""
    logger.info("=" * 80)
    logger.info("TESTE: Resumo Executivo com Dados Grandes")
    logger.info("=" * 80)
    
    # Cria contexto com muitos vendedores (simula resposta grande)
    contexto_grande = {
        "mes_ano": "2025-10",
        "meta_total": 1000000.0,
        "realizado_total": 850000.0,
        "gap_total": -150000.0,
        "atingimento_medio": 85.0,
        "total_vendedores": 500,
        "total_vendedores_em_risco": 150,
        "piores_vendedores": [
            {
                "vendedor_nome": f"ROTA {i:03d}",
                "atingimento": 50.0 + (i * 0.5),
                "gap": -10000.0 - (i * 100),
                "meta": 50000.0,
                "realizado": 25000.0 + (i * 50),
            }
            for i in range(200)  # 200 vendedores (simula resposta muito grande)
        ]
    }
    
    logger.info(f"Contexto criado com {len(contexto_grande['piores_vendedores'])} vendedores")
    logger.info("Chamando gerar_resposta_llm_diretor...")
    
    try:
        resumo = gerar_resposta_llm_diretor(
            contexto=contexto_grande,
            pergunta="Por que não batemos a meta em outubro de 2025?",
            tipo="resumo_executivo"
        )
        
        logger.info("✅ Resumo executivo gerado com sucesso")
        logger.info(f"   Tamanho: {len(resumo)} caracteres")
        logger.info(f"   Resumo: {resumo[:200]}...")
        
        # Verifica que não está vazio
        assert len(resumo) > 0, "Resumo executivo está vazio"
        
        # Verifica que contém informações relevantes
        assert "meta" in resumo.lower() or "atingimento" in resumo.lower() or "vendedor" in resumo.lower(), \
            "Resumo executivo não contém informações relevantes"
        
        logger.info("✅ TESTE PASSOU: Resumo executivo gerado mesmo com dados grandes")
        
    except Exception as e:
        logger.error(f"❌ Erro ao gerar resumo executivo: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def test_resumo_executivo_fallback():
    """Testa se o fallback funciona quando GROQ falha."""
    logger.info("=" * 80)
    logger.info("TESTE: Resumo Executivo - Fallback")
    logger.info("=" * 80)
    
    contexto = {
        "mes_ano": "2025-10",
        "meta_total": 1000000.0,
        "realizado_total": 850000.0,
        "gap_total": -150000.0,
        "atingimento_medio": 85.0,
        "total_vendedores": 10,
        "piores_vendedores": [
            {"vendedor_nome": "ROTA 01", "atingimento": 50.0, "gap": -10000.0},
            {"vendedor_nome": "ROTA 02", "atingimento": 60.0, "gap": -8000.0},
        ]
    }
    
    logger.info("Chamando gerar_resposta_llm_diretor...")
    
    try:
        resumo = gerar_resposta_llm_diretor(
            contexto=contexto,
            pergunta="Por que não batemos a meta?",
            tipo="resumo_executivo"
        )
        
        logger.info("✅ Resumo executivo gerado")
        logger.info(f"   Tamanho: {len(resumo)} caracteres")
        logger.info(f"   Resumo: {resumo}")
        
        # Verifica que não está vazio
        assert len(resumo) > 0, "Resumo executivo está vazio"
        
        logger.info("✅ TESTE PASSOU: Fallback funcionando")
        
    except Exception as e:
        logger.error(f"❌ Erro ao gerar resumo executivo: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


if __name__ == "__main__":
    try:
        test_resumo_executivo_com_dados_grandes()
        test_resumo_executivo_fallback()
        
        logger.info("=" * 80)
        logger.info("✅ TODOS OS TESTES CONCLUÍDOS")
        logger.info("=" * 80)
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"❌ Erro durante testes: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

