"""
Testes para endpoint /feedback/behavior (Behavior Memory V1).

Este módulo testa a criação de regras de comportamento via endpoint REST.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from src.dw.models import Base, BehaviorRule
from src.api.main import app
from src.dw.connection import get_db_session


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


@pytest.fixture
def client(db_session):
    """Cria cliente de teste FastAPI com sessão de banco mockada."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db_session] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_feedback_endpoint_cria_regra(client, db_session):
    """Teste: POST /feedback/behavior cria regra no banco."""
    payload = {
        "tipo_regra": "EXCLUIR_FILTRO",
        "escopo": "tipo_intent",
        "tipo_intent": "mix_nissin",
        "dimensao_principal": None,
        "regra": {
            "campo": "pasta",
            "operador": "!=",
            "valor": "VERDE"
        },
        "comentario": "pedido do diretor: excluir pasta verde nesse tipo de análise",
        "fonte_feedback": "teste automatizado"
    }
    
    response = client.post("/feedback/behavior", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "behavior_rule_id" in data
    assert data["behavior_rule_id"] > 0
    
    # Verifica que a regra foi criada no banco
    regra = db_session.query(BehaviorRule).filter(
        BehaviorRule.id == data["behavior_rule_id"]
    ).first()
    
    assert regra is not None
    assert regra.tipo_regra == "EXCLUIR_FILTRO"
    assert regra.escopo == "tipo_intent"
    assert regra.tipo_intent == "mix_nissin"
    assert regra.regra_json["campo"] == "pasta"
    assert regra.regra_json["valor"] == "VERDE"
    assert regra.ativo == True
    assert regra.criado_por == "diretor"


def test_feedback_endpoint_valida_tipo_regra(client):
    """Teste: POST /feedback/behavior valida tipo_regra."""
    payload = {
        "tipo_regra": "TIPO_INVALIDO",
        "escopo": "tipo_intent",
        "tipo_intent": "mix_nissin",
        "regra": {"campo": "pasta", "valor": "VERDE"}
    }
    
    response = client.post("/feedback/behavior", json=payload)
    
    assert response.status_code == 400
    assert "tipo_regra deve ser um de" in response.json()["detail"]


def test_feedback_endpoint_valida_escopo(client):
    """Teste: POST /feedback/behavior valida escopo."""
    payload = {
        "tipo_regra": "EXCLUIR_FILTRO",
        "escopo": "escopo_invalido",
        "regra": {"campo": "pasta", "valor": "VERDE"}
    }
    
    response = client.post("/feedback/behavior", json=payload)
    
    assert response.status_code == 400
    assert "escopo deve ser um de" in response.json()["detail"]


def test_feedback_endpoint_valida_tipo_intent_obrigatorio(client):
    """Teste: POST /feedback/behavior valida que tipo_intent é obrigatório para escopo tipo_intent."""
    payload = {
        "tipo_regra": "EXCLUIR_FILTRO",
        "escopo": "tipo_intent",
        "tipo_intent": None,  # Não fornecido
        "regra": {"campo": "pasta", "valor": "VERDE"}
    }
    
    response = client.post("/feedback/behavior", json=payload)
    
    assert response.status_code == 400
    assert "tipo_intent é obrigatório" in response.json()["detail"]

