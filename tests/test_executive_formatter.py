"""
Testes para o módulo executive_formatter.

Valida que o formatador gera narrativas executivas consistentes
tanto para casos com dados quanto sem dados.
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

