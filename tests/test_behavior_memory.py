"""
Testes para Behavior Memory V1 - Regras persistentes do Diretor.

Este módulo testa:
- Aplicação de regras persistentes do banco ao IntentSpec
- Criação de regras via endpoint /feedback/behavior
- Prioridade de escopos (tipo_intent_dimensao > tipo_intent > tipo_dimensao > global)
"""

import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from src.dw.models import Base, BehaviorRule
from src.agent.intent_spec import IntentSpec
from src.agent.behavior_memory import aplicar_regras_ao_intent


@pytest.fixture
def db_session():
    """Cria um banco SQLite em memória para testes."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()


def test_behavior_excluir_filtro_tipo_intent(db_session):
    """Teste: EXCLUIR_FILTRO com escopo tipo_intent."""
    # Cria regra: excluir pasta VERDE para tipo_intent="mix_nissin"
    regra = BehaviorRule(
        criado_por="diretor",
        ativo=True,
        escopo="tipo_intent",
        tipo_intent="mix_nissin",
        dimensao_principal=None,
        tipo_regra="EXCLUIR_FILTRO",
        regra_json={
            "campo": "pasta",
            "operador": "!=",
            "valor": "VERDE"
        },
        comentario="Teste: excluir pasta verde em análises de mix Nissin"
    )
    db_session.add(regra)
    db_session.commit()
    
    # Cria IntentSpec para mix_nissin
    intent_spec = IntentSpec(
        tipo="mix_nissin",
        periodo_inicio="2025-10-01",
        periodo_fim="2025-10-31",
        dimensao_principal="cliente",
        filtros={"ano": 2025, "mes": 10}
    )
    
    # Aplica regras
    intent_spec_modificado, regras_aplicadas = aplicar_regras_ao_intent(intent_spec, db_session)
    
    # Verifica que o filtro foi aplicado
    assert "excluir_pastas" in intent_spec_modificado.filtros
    assert "VERDE" in intent_spec_modificado.filtros["excluir_pastas"]
    assert len(regras_aplicadas) == 1
    assert regras_aplicadas[0]["tipo_regra"] == "EXCLUIR_FILTRO"
    assert regras_aplicadas[0]["escopo"] == "tipo_intent"


def test_behavior_forcar_filtro_global(db_session):
    """Teste: FORÇAR_FILTRO com escopo global."""
    # Cria regra global: forçar industria="Mars"
    regra = BehaviorRule(
        criado_por="diretor",
        ativo=True,
        escopo="global",
        tipo_intent=None,
        dimensao_principal=None,
        tipo_regra="FORÇAR_FILTRO",
        regra_json={
            "campo": "industria",
            "valor": "Mars"
        },
        comentario="Teste: sempre forçar industria Mars"
    )
    db_session.add(regra)
    db_session.commit()
    
    # Cria IntentSpec genérico
    intent_spec = IntentSpec(
        tipo="positivacao",
        periodo_inicio="2025-10-01",
        periodo_fim="2025-10-31",
        dimensao_principal="rota",
        filtros={}
    )
    
    # Aplica regras
    intent_spec_modificado, regras_aplicadas = aplicar_regras_ao_intent(intent_spec, db_session)
    
    # Verifica que o filtro foi forçado
    assert intent_spec_modificado.filtros["industria"] == "Mars"
    assert len(regras_aplicadas) == 1
    assert regras_aplicadas[0]["tipo_regra"] == "FORÇAR_FILTRO"
    assert regras_aplicadas[0]["escopo"] == "global"


def test_behavior_prioridade_escopos(db_session):
    """Teste: Prioridade de escopos (tipo_intent_dimensao > tipo_intent > global)."""
    # Cria 3 regras com diferentes escopos
    regra_global = BehaviorRule(
        criado_por="diretor",
        ativo=True,
        escopo="global",
        tipo_regra="FORÇAR_FILTRO",
        regra_json={"campo": "industria", "valor": "Red Bull"}
    )
    regra_tipo = BehaviorRule(
        criado_por="diretor",
        ativo=True,
        escopo="tipo_intent",
        tipo_intent="mix_nissin",
        tipo_regra="FORÇAR_FILTRO",
        regra_json={"campo": "industria", "valor": "Mars"}
    )
    regra_tipo_dimensao = BehaviorRule(
        criado_por="diretor",
        ativo=True,
        escopo="tipo_intent_dimensao",
        tipo_intent="mix_nissin",
        dimensao_principal="cliente",
        tipo_regra="FORÇAR_FILTRO",
        regra_json={"campo": "industria", "valor": "Nissin"}
    )
    
    db_session.add_all([regra_global, regra_tipo, regra_tipo_dimensao])
    db_session.commit()
    
    # Cria IntentSpec que corresponde a todas as regras
    intent_spec = IntentSpec(
        tipo="mix_nissin",
        periodo_inicio="2025-10-01",
        periodo_fim="2025-10-31",
        dimensao_principal="cliente",
        filtros={}
    )
    
    # Aplica regras
    intent_spec_modificado, regras_aplicadas = aplicar_regras_ao_intent(intent_spec, db_session)
    
    # Verifica que a regra de maior prioridade (tipo_intent_dimensao) foi aplicada por último
    # e sobrescreveu as anteriores
    assert intent_spec_modificado.filtros["industria"] == "Nissin"
    # Todas as 3 regras devem ter sido aplicadas (mas a última sobrescreve)
    assert len(regras_aplicadas) == 3
    # Verifica que a última regra aplicada é a de maior prioridade
    assert regras_aplicadas[-1]["escopo"] == "tipo_intent_dimensao"


def test_behavior_ajustar_limiar(db_session):
    """Teste: AJUSTAR_LIMIAR."""
    # Cria regra: ajustar limite_media para 5.0
    regra = BehaviorRule(
        criado_por="diretor",
        ativo=True,
        escopo="tipo_intent",
        tipo_intent="mix",
        tipo_regra="AJUSTAR_LIMIAR",
        regra_json={
            "campo": "limite_media",
            "limiar": 5.0
        },
        comentario="Teste: ajustar limite de média para 5.0"
    )
    db_session.add(regra)
    db_session.commit()
    
    # Cria IntentSpec para mix
    intent_spec = IntentSpec(
        tipo="mix",
        periodo_inicio="2025-10-01",
        periodo_fim="2025-10-31",
        dimensao_principal="produto",
        filtros={"meses_janela": 12}
    )
    
    # Aplica regras
    intent_spec_modificado, regras_aplicadas = aplicar_regras_ao_intent(intent_spec, db_session)
    
    # Verifica que o limiar foi ajustado
    assert intent_spec_modificado.filtros["limite_media"] == 5.0
    assert len(regras_aplicadas) == 1
    assert regras_aplicadas[0]["tipo_regra"] == "AJUSTAR_LIMIAR"


def test_behavior_regra_inativa_nao_aplica(db_session):
    """Teste: Regras inativas não são aplicadas."""
    # Cria regra inativa
    regra = BehaviorRule(
        criado_por="diretor",
        ativo=False,  # Inativa
        escopo="tipo_intent",
        tipo_intent="mix_nissin",
        tipo_regra="EXCLUIR_FILTRO",
        regra_json={"campo": "pasta", "valor": "VERDE"}
    )
    db_session.add(regra)
    db_session.commit()
    
    # Cria IntentSpec
    intent_spec = IntentSpec(
        tipo="mix_nissin",
        periodo_inicio="2025-10-01",
        periodo_fim="2025-10-31",
        dimensao_principal="cliente",
        filtros={}
    )
    
    # Aplica regras
    intent_spec_modificado, regras_aplicadas = aplicar_regras_ao_intent(intent_spec, db_session)
    
    # Verifica que nenhuma regra foi aplicada
    assert "excluir_pastas" not in intent_spec_modificado.filtros
    assert len(regras_aplicadas) == 0


def test_behavior_regra_escopo_nao_compativel(db_session):
    """Teste: Regras com escopo não compatível não são aplicadas."""
    # Cria regra para tipo_intent="meta"
    regra = BehaviorRule(
        criado_por="diretor",
        ativo=True,
        escopo="tipo_intent",
        tipo_intent="meta",
        tipo_regra="EXCLUIR_FILTRO",
        regra_json={"campo": "pasta", "valor": "VERDE"}
    )
    db_session.add(regra)
    db_session.commit()
    
    # Cria IntentSpec para tipo diferente
    intent_spec = IntentSpec(
        tipo="mix_nissin",  # Tipo diferente
        periodo_inicio="2025-10-01",
        periodo_fim="2025-10-31",
        dimensao_principal="cliente",
        filtros={}
    )
    
    # Aplica regras
    intent_spec_modificado, regras_aplicadas = aplicar_regras_ao_intent(intent_spec, db_session)
    
    # Verifica que nenhuma regra foi aplicada
    assert "excluir_pastas" not in intent_spec_modificado.filtros
    assert len(regras_aplicadas) == 0
