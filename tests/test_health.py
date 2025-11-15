"""
Testes para o endpoint de health check.

Este módulo contém testes básicos para verificar se a API está funcionando.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_health_check():
    """
    Testa o endpoint de health check.
    
    Verifica se o endpoint retorna status 200 e contém as informações esperadas.
    """
    response = client.get("/health")
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "environment" in data
    assert "version" in data


def test_root():
    """
    Testa o endpoint raiz.
    
    Verifica se o endpoint retorna a mensagem de boas-vindas.
    """
    response = client.get("/")
    
    assert response.status_code == 200
    
    data = response.json()
    assert "message" in data
    assert "docs" in data

