"""
Testes para intent_to_spec com tipos DW oficiais (Q1-Q13).

Este módulo testa que intent_to_spec cria IntentSpec canônicos
para todos os tipos DW oficiais, sem cair em fallback "outros".
"""

import pytest
from src.agent.intent import IntentType
from src.agent.intent_to_spec import intent_to_spec


def test_intent_to_spec_clientes_sem_compra():
    """Teste: CLIENTES_SEM_COMPRA gera IntentSpec canônico."""
    entities = {
        "dias": 60,
        "data_referencia": "2025-11-17"
    }
    
    intent_spec = intent_to_spec(IntentType.CLIENTES_SEM_COMPRA, entities)
    
    assert intent_spec.tipo == "clientes_sem_compra"
    assert intent_spec.dimensao_principal == "cliente"
    assert intent_spec.filtros["dias"] == 60
    assert "dias_sem_compra" in intent_spec.metricas
    assert intent_spec.confianca == 0.8


def test_intent_to_spec_mix_nissin():
    """Teste: MIX_NISSIN gera IntentSpec canônico."""
    entities = {
        "ano": 2025,
        "mes": 10,
        "pergunta_original": "Quais clientes têm mix mínimo de Nissin em outubro?"
    }
    
    intent_spec = intent_to_spec(IntentType.MIX_NISSIN, entities)
    
    assert intent_spec.tipo == "mix_nissin"
    assert intent_spec.dimensao_principal == "cliente"  # Padrão quando não menciona rota
    assert intent_spec.filtros["ano"] == 2025
    assert intent_spec.filtros["mes"] == 10
    assert "qtd_skus_nissin" in intent_spec.metricas
    assert intent_spec.confianca == 0.8


def test_intent_to_spec_mix_nissin_rota():
    """Teste: MIX_NISSIN com dimensão rota."""
    entities = {
        "ano": 2025,
        "mes": 10,
        "rota": "ROTA 22",
        "pergunta_original": "Quais rotas têm mix mínimo de Nissin em outubro?"
    }
    
    intent_spec = intent_to_spec(IntentType.MIX_NISSIN, entities)
    
    assert intent_spec.tipo == "mix_nissin"
    assert intent_spec.dimensao_principal == "rota"  # Detecta rota na pergunta
    assert intent_spec.filtros["ano"] == 2025
    assert intent_spec.confianca == 0.8


def test_intent_to_spec_nao_cai_em_fallback():
    """Teste: Tipos DW oficiais NUNCA caem em fallback 'outros'."""
    tipos_dw = [
        IntentType.CLIENTES_SEM_COMPRA,
        IntentType.QUEDA_FATURAMENTO,
        IntentType.META_DEPARTAMENTO_DW,
        IntentType.POSITIVACAO,
        IntentType.MIX,
        IntentType.RECOMPRA,
        IntentType.CLIENTES_SEM_ITEM,
        IntentType.VENDAS_BAIXAS,
        IntentType.MIX_NISSIN
    ]
    
    entities = {}
    
    for intent_type in tipos_dw:
        intent_spec = intent_to_spec(intent_type, entities)
        assert intent_spec.tipo != "outros", f"Tipo DW {intent_type.value} caiu em fallback 'outros'"
        assert intent_spec.confianca == 0.8, f"Tipo DW {intent_type.value} não tem confiança 0.8"


def test_intent_to_spec_queda_faturamento():
    """Teste: QUEDA_FATURAMENTO gera IntentSpec canônico."""
    entities = {
        "ano_base": 2024,
        "ano_comparado": 2025,
        "top_n": 50
    }
    
    intent_spec = intent_to_spec(IntentType.QUEDA_FATURAMENTO, entities)
    
    assert intent_spec.tipo == "queda_faturamento"
    assert intent_spec.dimensao_principal == "cliente"
    assert intent_spec.filtros["ano_base"] == 2024
    assert intent_spec.filtros["ano_comparado"] == 2025
    assert intent_spec.filtros["top_n"] == 50
    assert "delta_faturamento" in intent_spec.metricas


def test_intent_to_spec_positivacao():
    """Teste: POSITIVACAO gera IntentSpec canônico."""
    entities = {
        "industria": "Mars",
        "periodo_inicio": "2025-10-01",
        "periodo_fim": "2025-10-31"
    }
    
    intent_spec = intent_to_spec(IntentType.POSITIVACAO, entities)
    
    assert intent_spec.tipo == "positivacao"
    assert intent_spec.dimensao_principal == "rota"
    assert intent_spec.filtros["industria"] == "Mars"
    assert "positivacao_pct" in intent_spec.metricas

