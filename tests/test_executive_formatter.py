"""
Testes para o módulo executive_formatter.

Valida que o formatador gera narrativas executivas consistentes
tanto para casos com dados quanto sem dados, e que cada tipo de intent
usa sua narrativa específica.
"""

from src.agent.executive_formatter import formatar_execucao
from src.agent.intent_spec import IntentSpec


def test_formatter_resposta_vazia():
    """Testa formatação quando não há dados."""
    spec = IntentSpec(tipo="clientes_sem_compra")
    output = formatar_execucao([], spec, {}, [])
    
    # Verifica que há uma mensagem sobre ausência de dados (pode variar por tipo)
    assert "Nenhum" in output["resumo"] or "nenhum" in output["resumo"].lower()
    assert len(output["achados"]) > 0
    assert len(output["plano"]) > 0


def test_formatter_resposta_com_dados():
    """Testa formatação quando há dados."""
    spec = IntentSpec(tipo="positivacao")
    dados = [{"cliente_id": 1}]
    output = formatar_execucao(dados, spec, {"mes": 10}, [])
    
    # Verifica que há uma mensagem sobre dados encontrados (pode variar por tipo)
    assert "Foram" in output["resumo"] or "foram" in output["resumo"].lower() or "identificados" in output["resumo"]
    assert len(output["achados"]) > 0
    assert len(output["plano"]) > 0


def test_formatter_chaves_existentes():
    """Testa que todas as chaves obrigatórias estão presentes."""
    spec = IntentSpec(tipo="mix_nissin")
    dados = [{"cliente_id": 1}]
    output = formatar_execucao(dados, spec, {}, [])
    
    assert set(output.keys()) == {"resumo", "achados", "implicacoes", "plano"}


def test_formatter_clientes_sem_compra_usa_narrativa_especifica():
    """Testa que clientes_sem_compra usa narrativa específica."""
    spec = IntentSpec(tipo="clientes_sem_compra", filtros={"dias": 60})
    dados = [
        {"cliente_id": 1, "nome": "Cliente A", "dias_sem_compra": 75, "rota_id": "ROTA 01"},
        {"cliente_id": 2, "nome": "Cliente B", "dias_sem_compra": 90, "rota_id": "ROTA 02"},
    ]
    out = formatar_execucao(dados, spec, spec.filtros, [])
    
    assert "clientes ativos sem compras" in out["resumo"]
    assert len(out["plano"]) >= 3
    assert "Priorizar contato" in out["plano"][0] or "priorizar" in out["plano"][0].lower()


def test_formatter_mix_nissin_usa_narrativa_especifica():
    """Testa que mix_nissin usa narrativa específica."""
    spec = IntentSpec(tipo="mix_nissin", filtros={"mes": "2025-10"})
    dados = [
        {"cliente_id": 1, "nome": "Cliente A", "rota_id": "ROTA 01"},
        {"cliente_id": 2, "nome": "Cliente B", "rota_id": "ROTA 02"},
        {"cliente_id": 3, "nome": "Cliente C", "rota_id": "ROTA 03"},
    ]
    out = formatar_execucao(dados, spec, spec.filtros, [])
    
    assert "mix mínimo de Nissin" in out["resumo"] or "mix" in out["resumo"].lower()
    assert len(out["implicacoes"]) >= 2
    assert "mix" in out["plano"][0].lower() or "Nissin" in out["plano"][0]

