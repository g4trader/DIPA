"""
Testes unitários para agent/behavior_memory.py
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

from src.agent.behavior_memory import (
    carregar_regras,
    salvar_regras,
    registrar_feedback,
    aplicar_regras_ao_intent
)


@pytest.fixture
def temp_rules_file(tmp_path):
    """Cria um arquivo temporário para behavior_rules.json."""
    rules_file = tmp_path / "behavior_rules.json"
    rules_file.write_text(json.dumps({"regras_por_tipo_analise": {}}), encoding='utf-8')
    return rules_file


def test_carregar_regras_vazio(temp_rules_file):
    """Testa carregar_regras quando o arquivo está vazio."""
    with patch('src.agent.behavior_memory.BEHAVIOR_RULES_FILE', temp_rules_file):
        regras = carregar_regras()
        assert "regras_por_tipo_analise" in regras
        assert len(regras["regras_por_tipo_analise"]) == 0


def test_salvar_regras(temp_rules_file):
    """Testa salvar_regras."""
    with patch('src.agent.behavior_memory.BEHAVIOR_RULES_FILE', temp_rules_file):
        regras = {
            "regras_por_tipo_analise": {
                "analise_meta_mensal": {
                    "excluir_carteira": ["pasta_verde"]
                }
            }
        }
        salvar_regras(regras)
        
        # Verifica que foi salvo
        regras_carregadas = carregar_regras()
        assert "analise_meta_mensal" in regras_carregadas["regras_por_tipo_analise"]
        assert "pasta_verde" in regras_carregadas["regras_por_tipo_analise"]["analise_meta_mensal"]["excluir_carteira"]


def test_registrar_feedback(temp_rules_file):
    """Testa registrar_feedback."""
    with patch('src.agent.behavior_memory.BEHAVIOR_RULES_FILE', temp_rules_file):
        registrar_feedback(
            tipo_analise="analise_meta_mensal",
            tipo_regra="excluir_carteira",
            valor="pasta_verde",
            comentario="Regra definida pelo Diretor"
        )
        
        # Verifica que foi registrado
        regras = carregar_regras()
        assert "analise_meta_mensal" in regras["regras_por_tipo_analise"]
        assert "pasta_verde" in regras["regras_por_tipo_analise"]["analise_meta_mensal"]["excluir_carteira"]


def test_aplicar_regras_ao_intent(temp_rules_file):
    """Testa aplicar_regras_ao_intent."""
    with patch('src.agent.behavior_memory.BEHAVIOR_RULES_FILE', temp_rules_file):
        # Registra uma regra
        registrar_feedback(
            tipo_analise="analise_meta_mensal",
            tipo_regra="excluir_carteira",
            valor="pasta_verde"
        )
        
        # Cria intent
        intent = {
            "tipo": "meta",
            "filtros": {}
        }
        
        # Aplica regras
        intent_ajustado = aplicar_regras_ao_intent(intent)
        
        # Verifica que filtros foram ajustados
        assert "excluir_carteiras" in intent_ajustado["filtros"]
        assert "pasta_verde" in intent_ajustado["filtros"]["excluir_carteiras"]


def test_aplicar_regras_ao_intent_sem_regras(temp_rules_file):
    """Testa aplicar_regras_ao_intent quando não há regras."""
    with patch('src.agent.behavior_memory.BEHAVIOR_RULES_FILE', temp_rules_file):
        intent = {
            "tipo": "meta",
            "filtros": {}
        }
        
        intent_ajustado = aplicar_regras_ao_intent(intent)
        
        # Verifica que intent não foi alterado
        assert intent_ajustado == intent or len(intent_ajustado.get("filtros", {})) == 0

