"""
Testes unitários para agent/post_processor.py
"""

import pytest
from unittest.mock import Mock

from src.agent.post_processor import (
    processar_resposta,
    _processar_template_negativo,
    _processar_template_positivo
)


def test_processar_resposta_template_negativo():
    """Testa processar_resposta com template negativo."""
    intent_spec = {
        "tipo": "meta",
        "dimensao_principal": "mes"
    }
    
    dados_dw = {
        "atingimento_medio": 95.0,
        "gap_total": -50000.0,
        "meta_total": 1000000.0,
        "realizado_total": 950000.0
    }
    
    causas_detector = {
        "gap_total": -50000.0,
        "atingimento_medio": 95.0,
        "causas": {
            "rotas": [{"rota_nome": "Rota A", "gap_rota": -20000.0}],
            "vendedores": [{"vendedor_nome": "Vendedor A", "atingimento_vendedor": 80.0}],
            "clientes": [],
            "skus": []
        },
        "resumo_causas": ["Rota A respondeu por 40% do gap."]
    }
    
    resultado = processar_resposta(
        intent_spec=intent_spec,
        dados_dw=dados_dw,
        causas_detector=causas_detector
    )
    
    # Verifica estrutura
    assert "resumo_executivo" in resultado
    assert "diagnostico_causas" in resultado
    assert "checklist_problemas" in resultado
    assert "plano_acao_7_dias" in resultado
    assert "plano_acao_30_dias" in resultado
    assert "tendencias_previsao" in resultado
    assert "detalhes_tecnicos" in resultado


def test_processar_resposta_template_positivo():
    """Testa processar_resposta com template positivo."""
    intent_spec = {
        "tipo": "meta",
        "dimensao_principal": "mes"
    }
    
    dados_dw = {
        "atingimento_medio": 105.0,
        "gap_total": 50000.0,
        "meta_total": 1000000.0,
        "realizado_total": 1050000.0
    }
    
    resultado = processar_resposta(
        intent_spec=intent_spec,
        dados_dw=dados_dw
    )
    
    # Verifica estrutura
    assert "resumo_executivo" in resultado
    assert "oportunidades_crescimento" in resultado
    assert "detalhes_tecnicos" in resultado


def test_processar_resposta_sem_causas():
    """Testa processar_resposta quando não há causas."""
    intent_spec = {
        "tipo": "meta",
        "dimensao_principal": "mes"
    }
    
    dados_dw = {
        "atingimento_medio": 95.0,
        "gap_total": -50000.0
    }
    
    resultado = processar_resposta(
        intent_spec=intent_spec,
        dados_dw=dados_dw,
        causas_detector={}
    )
    
    # Verifica que ainda retorna estrutura completa
    assert "resumo_executivo" in resultado
    assert "diagnostico_causas" in resultado

