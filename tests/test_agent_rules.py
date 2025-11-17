"""
Testes para a camada de regras do agente DIPAM COPILOT™.

Testa:
- Criação e listagem de regras
- Aplicação de regras aos filtros
- Detecção de override explícito
- Caso específico: exclusão de pasta verde
"""

import pytest
from sqlalchemy.orm import Session

from src.dw.connection import get_db_session, init_db, get_db_engine
from src.dw.models_agent import AgentFeedbackRule, Base
from src.agent.intent_spec import IntentSpec
from src.agent.rules import (
    listar_regras_ativas,
    salvar_regra_feedback,
    aplicar_regras,
    detectar_override_explicito
)


@pytest.fixture
def setup_db():
    """Cria a tabela agent_feedback_rules antes dos testes."""
    init_db(create_tables_if_not_exists=False)
    engine = get_db_engine()
    AgentFeedbackRule.__table__.create(bind=engine, checkfirst=True)
    yield
    # Limpa após os testes (opcional)
    # AgentFeedbackRule.__table__.drop(bind=engine, checkfirst=True)


def test_criar_regra_pasta_verde(setup_db):
    """Testa criação de regra para excluir pasta verde."""
    with get_db_session() as session:
        regra = salvar_regra_feedback(
            session=session,
            owner_role="diretor",
            rule_scope="meta",
            condition_json={"carteira": "pasta_verde"},
            action_json={"excluir_dos_filtros": True, "excluir_carteira": ["pasta_verde"]},
            description="Excluir pasta verde de análises de meta"
        )
        
        assert regra.id is not None
        assert regra.owner_role == "diretor"
        assert regra.rule_scope == "meta"
        assert regra.active == 1


def test_listar_regras_ativas(setup_db):
    """Testa listagem de regras ativas."""
    with get_db_session() as session:
        # Cria regra
        salvar_regra_feedback(
            session=session,
            owner_role="diretor",
            rule_scope="meta",
            condition_json={"carteira": "pasta_verde"},
            action_json={"excluir_dos_filtros": True},
            description="Teste"
        )
        
        # Lista regras
        regras = listar_regras_ativas(session, "diretor", "meta")
        
        assert len(regras) > 0
        assert regras[0].rule_scope == "meta"
        assert regras[0].owner_role == "diretor"


def test_aplicar_regras_sem_regra(setup_db):
    """Testa aplicação de regras quando não há regras ativas."""
    with get_db_session() as session:
        intent_spec = IntentSpec(
            tipo="meta",
            periodo_inicio="2025-08-01",
            periodo_fim="2025-08-31",
            dimensao_principal="mes"
        )
        
        filtros_sql = {}
        contexto_usuario = {"role": "diretor"}
        
        resultado = aplicar_regras(intent_spec, filtros_sql, contexto_usuario, session)
        
        assert resultado["filtros_ajustados"] == filtros_sql
        assert len(resultado["regras_usadas"]) == 0


def test_aplicar_regras_com_pasta_verde(setup_db):
    """Testa aplicação de regra para excluir pasta verde."""
    with get_db_session() as session:
        # Cria regra
        salvar_regra_feedback(
            session=session,
            owner_role="diretor",
            rule_scope="meta",
            condition_json={"carteira": "pasta_verde"},
            action_json={"excluir_dos_filtros": True, "excluir_carteira": ["pasta_verde"]},
            description="Excluir pasta verde"
        )
        
        intent_spec = IntentSpec(
            tipo="meta",
            periodo_inicio="2025-08-01",
            periodo_fim="2025-08-31",
            dimensao_principal="mes"
        )
        
        filtros_sql = {}
        contexto_usuario = {"role": "diretor"}
        
        resultado = aplicar_regras(intent_spec, filtros_sql, contexto_usuario, session)
        
        # Verifica que regra foi aplicada
        assert len(resultado["regras_usadas"]) > 0
        assert "excluir_carteira" in resultado["regras_aplicadas"]
        assert "pasta_verde" in resultado["regras_aplicadas"]["excluir_carteira"]


def test_aplicar_regras_com_override(setup_db):
    """Testa que override explícito ignora regras."""
    with get_db_session() as session:
        # Cria regra
        salvar_regra_feedback(
            session=session,
            owner_role="diretor",
            rule_scope="meta",
            condition_json={"carteira": "pasta_verde"},
            action_json={"excluir_dos_filtros": True},
            description="Excluir pasta verde"
        )
        
        intent_spec = IntentSpec(
            tipo="meta",
            periodo_inicio="2025-08-01",
            periodo_fim="2025-08-31",
            dimensao_principal="mes"
        )
        
        filtros_sql = {}
        contexto_usuario = {"role": "diretor", "override_regras": True}
        
        resultado = aplicar_regras(intent_spec, filtros_sql, contexto_usuario, session)
        
        # Verifica que nenhuma regra foi aplicada
        assert len(resultado["regras_usadas"]) == 0
        assert resultado["filtros_ajustados"] == filtros_sql


def test_detectar_override_explicito():
    """Testa detecção de override explícito na pergunta."""
    # Casos com override
    assert detectar_override_explicito("incluindo pasta verde") is True
    assert detectar_override_explicito("dessa vez considere também a pasta verde") is True
    assert detectar_override_explicito("ignore a regra de excluir a pasta verde") is True
    
    # Casos sem override
    assert detectar_override_explicito("quais são as metas de agosto") is False
    assert detectar_override_explicito("mostre os vendedores com maior risco") is False


@pytest.mark.integration
def test_fluxo_completo_consulta_com_regra(setup_db):
    """Testa fluxo completo: consulta de meta SEM regra → inclui pasta verde normalmente."""
    with get_db_session() as session:
        # Primeiro, consulta sem regra
        intent_spec = IntentSpec(
            tipo="meta",
            periodo_inicio="2025-08-01",
            periodo_fim="2025-08-31",
            dimensao_principal="mes"
        )
        
        contexto_usuario = {"role": "diretor"}
        
        # Aplica regras (não deve ter nenhuma)
        resultado = aplicar_regras(intent_spec, {}, contexto_usuario, session)
        assert len(resultado["regras_usadas"]) == 0
        
        # Agora cria regra
        salvar_regra_feedback(
            session=session,
            owner_role="diretor",
            rule_scope="meta",
            condition_json={"carteira": "pasta_verde"},
            action_json={"excluir_dos_filtros": True, "excluir_carteira": ["pasta_verde"]},
            description="Excluir pasta verde"
        )
        
        # Consulta novamente (deve aplicar regra)
        resultado = aplicar_regras(intent_spec, {}, contexto_usuario, session)
        assert len(resultado["regras_usadas"]) > 0
        assert "excluir_carteira" in resultado["regras_aplicadas"]


@pytest.mark.integration
def test_fluxo_completo_override_explicito(setup_db):
    """Testa fluxo completo: pergunta com override explícito → pasta verde volta a ser considerada."""
    with get_db_session() as session:
        # Cria regra
        salvar_regra_feedback(
            session=session,
            owner_role="diretor",
            rule_scope="meta",
            condition_json={"carteira": "pasta_verde"},
            action_json={"excluir_dos_filtros": True},
            description="Excluir pasta verde"
        )
        
        intent_spec = IntentSpec(
            tipo="meta",
            periodo_inicio="2025-08-01",
            periodo_fim="2025-08-31",
            dimensao_principal="mes"
        )
        
        # Pergunta com override
        pergunta = "Quais são as metas de agosto incluindo pasta verde"
        override = detectar_override_explicito(pergunta)
        assert override is True
        
        contexto_usuario = {"role": "diretor", "override_regras": override}
        
        # Aplica regras (deve ignorar devido ao override)
        resultado = aplicar_regras(intent_spec, {}, contexto_usuario, session)
        assert len(resultado["regras_usadas"]) == 0

