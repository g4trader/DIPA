"""
Testes de integração para o Orquestrador DW.

Testa:
- Validação de IntentSpec
- Mapeamento IntentSpec → função DW
- Execução de função DW
- Normalização de resultado
- Envelopamento de resposta
"""

import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from src.agent.intent_spec import IntentSpec
from src.agent.orquestrador_dw import (
    executar_intent_spec,
    _validar_intent_spec,
    _aplicar_periodo_padrao,
    _normalizar_periodo_para_mes_ano
)
from src.dw.connection import get_db_session


def test_validar_intent_spec_valido():
    """Testa validação de IntentSpec válido."""
    intent = IntentSpec(
        tipo="meta",
        periodo_inicio="2025-08-01",
        periodo_fim="2025-08-31",
        dimensao_principal="mes"
    )
    
    valido, mensagem = _validar_intent_spec(intent)
    assert valido is True
    assert mensagem is None


def test_validar_intent_spec_tipo_invalido():
    """Testa validação de IntentSpec com tipo inválido."""
    intent = IntentSpec(
        tipo="tipo_inexistente",
        periodo_inicio="2025-08-01",
        periodo_fim="2025-08-31",
        dimensao_principal="mes"
    )
    
    valido, mensagem = _validar_intent_spec(intent)
    assert valido is False
    assert "não é suportado" in mensagem


def test_validar_intent_spec_periodo_invalido():
    """Testa validação de IntentSpec com período inválido."""
    intent = IntentSpec(
        tipo="meta",
        periodo_inicio="2025-13-01",  # Mês inválido
        periodo_fim="2025-08-31",
        dimensao_principal="mes"
    )
    
    valido, mensagem = _validar_intent_spec(intent)
    assert valido is False
    assert "data válida" in mensagem


def test_validar_intent_spec_periodo_fim_menor_que_inicio():
    """Testa validação de IntentSpec com periodo_fim < periodo_inicio."""
    intent = IntentSpec(
        tipo="meta",
        periodo_inicio="2025-08-31",
        periodo_fim="2025-08-01",  # Fim antes do início
        dimensao_principal="mes"
    )
    
    valido, mensagem = _validar_intent_spec(intent)
    assert valido is False
    assert "deve ser >=" in mensagem


def test_aplicar_periodo_padrao():
    """Testa aplicação de período padrão quando null."""
    intent = IntentSpec(
        tipo="meta",
        periodo_inicio=None,
        periodo_fim=None,
        dimensao_principal="mes"
    )
    
    intent_com_periodo = _aplicar_periodo_padrao(intent)
    
    assert intent_com_periodo.periodo_inicio is not None
    assert intent_com_periodo.periodo_fim is not None
    assert len(intent_com_periodo.periodo_inicio) == 10  # YYYY-MM-DD
    assert len(intent_com_periodo.periodo_fim) == 10


def test_normalizar_periodo_para_mes_ano():
    """Testa normalização de período YYYY-MM-DD para YYYY-MM."""
    # YYYY-MM-DD
    assert _normalizar_periodo_para_mes_ano("2025-08-15") == "2025-08"
    # YYYY-MM
    assert _normalizar_periodo_para_mes_ano("2025-08") == "2025-08"
    # None
    assert _normalizar_periodo_para_mes_ano(None) is None


@pytest.mark.integration
def test_executar_intent_spec_meta_por_mes():
    """Testa execução de IntentSpec para meta por mês."""
    with get_db_session() as session:
        intent = IntentSpec(
            tipo="meta",
            periodo_inicio="2025-08-01",
            periodo_fim="2025-08-31",
            dimensao_principal="mes"
        )
        
        resposta = executar_intent_spec(session, intent)
        
        assert resposta["status"] in ["ok", "sem_dados"]
        assert "mensagem" in resposta
        assert "intent" in resposta
        assert "periodo_analisado" in resposta
        assert "dados" in resposta
        assert isinstance(resposta["dados"], list)


@pytest.mark.integration
def test_executar_intent_spec_meta_vendedor():
    """Testa execução de IntentSpec para ranking de vendedores."""
    with get_db_session() as session:
        intent = IntentSpec(
            tipo="ranking_vendedores",
            periodo_inicio="2025-08-01",
            periodo_fim="2025-08-31",
            dimensao_principal="vendedor",
            filtros={"top_n": 5}
        )
        
        resposta = executar_intent_spec(session, intent)
        
        assert resposta["status"] in ["ok", "sem_dados", "erro_validacao", "erro_interno"]
        assert "dados" in resposta
        assert isinstance(resposta["dados"], list)


@pytest.mark.integration
def test_executar_intent_spec_clientes_criticos():
    """Testa execução de IntentSpec para clientes críticos."""
    with get_db_session() as session:
        intent = IntentSpec(
            tipo="clientes_criticos",
            periodo_inicio="2025-08-01",
            periodo_fim="2025-08-31",
            dimensao_principal="cliente",
            filtros={"limite": 10}
        )
        
        resposta = executar_intent_spec(session, intent)
        
        assert resposta["status"] in ["ok", "sem_dados", "erro_validacao", "erro_interno"]
        assert "dados" in resposta
        assert isinstance(resposta["dados"], list)


@pytest.mark.integration
def test_executar_intent_spec_tipo_nao_suportado():
    """Testa execução de IntentSpec com tipo não suportado."""
    with get_db_session() as session:
        intent = IntentSpec(
            tipo="tipo_inexistente",
            periodo_inicio="2025-08-01",
            periodo_fim="2025-08-31",
            dimensao_principal="mes"
        )
        
        resposta = executar_intent_spec(session, intent)
        
        assert resposta["status"] == "erro_validacao"
        assert "não é suportado" in resposta["mensagem"]


@pytest.mark.integration
def test_executar_intent_spec_combinacao_nao_suportada():
    """Testa execução de IntentSpec com combinação tipo+dimensão não suportada."""
    with get_db_session() as session:
        intent = IntentSpec(
            tipo="meta",
            periodo_inicio="2025-08-01",
            periodo_fim="2025-08-31",
            dimensao_principal="sku"  # Combinação não mapeada
        )
        
        resposta = executar_intent_spec(session, intent)
        
        # Pode retornar erro_validacao ou tentar fallback genérico
        assert resposta["status"] in ["erro_validacao", "sem_dados", "ok"]


@pytest.mark.integration
def test_resposta_estrutura_padrao():
    """Testa que a resposta sempre segue a estrutura padrão."""
    with get_db_session() as session:
        intent = IntentSpec(
            tipo="meta",
            periodo_inicio="2025-08-01",
            periodo_fim="2025-08-31",
            dimensao_principal="mes"
        )
        
        resposta = executar_intent_spec(session, intent)
        
        # Estrutura obrigatória
        assert "status" in resposta
        assert resposta["status"] in ["ok", "sem_dados", "erro_validacao", "erro_interno"]
        assert "mensagem" in resposta
        assert isinstance(resposta["mensagem"], str)
        assert "intent" in resposta
        assert isinstance(resposta["intent"], dict)
        assert "periodo_analisado" in resposta
        assert isinstance(resposta["periodo_analisado"], dict)
        assert "inicio" in resposta["periodo_analisado"]
        assert "fim" in resposta["periodo_analisado"]
        assert "dados" in resposta
        assert isinstance(resposta["dados"], list)

