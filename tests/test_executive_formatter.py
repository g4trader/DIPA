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
    assert "top_alvos" in output
    assert output["top_alvos"] == []  # Deve ser lista vazia quando não há dados


def test_formatter_resposta_com_dados():
    """Testa formatação quando há dados."""
    spec = IntentSpec(tipo="positivacao")
    dados = [{"cliente_id": 1}]
    output = formatar_execucao(dados, spec, {"mes": 10}, [])
    
    # Verifica que há uma mensagem sobre dados encontrados (pode variar por tipo)
    assert "Foram" in output["resumo"] or "foram" in output["resumo"].lower() or "identificados" in output["resumo"]
    assert len(output["achados"]) > 0
    assert len(output["plano"]) > 0
    assert "top_alvos" in output
    assert isinstance(output["top_alvos"], list)


def test_formatter_chaves_existentes():
    """Testa que todas as chaves obrigatórias estão presentes."""
    spec = IntentSpec(tipo="mix_nissin")
    dados = [{"cliente_id": 1}]
    output = formatar_execucao(dados, spec, {}, [])
    
    assert set(output.keys()) == {"resumo", "achados", "implicacoes", "plano", "top_alvos"}
    assert isinstance(output["top_alvos"], list)


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
    # Validações de top_alvos
    assert "top_alvos" in out
    assert isinstance(out["top_alvos"], list)
    assert len(out["top_alvos"]) >= 1  # Com 2 clientes, deve ter pelo menos 1 entrada


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
    # Validações de top_alvos
    assert "top_alvos" in out
    assert isinstance(out["top_alvos"], list)
    assert len(out["top_alvos"]) >= 1  # Com 3 clientes, deve ter pelo menos 1 entrada


def test_formatter_generico_top_alvos_nunca_quebra():
    """Testa que o fallback genérico sempre retorna top_alvos sem quebrar."""
    spec = IntentSpec(tipo="outros")
    dados = [
        {"id": 1, "nome": "Algo", "rota": "R1"},
        {"id": 2, "nome": "Outro", "rota": "R2"},
    ]
    out = formatar_execucao(dados, spec, {}, [])
    
    assert "top_alvos" in out
    assert isinstance(out["top_alvos"], list)
    # Com dados genéricos, deve gerar pelo menos algumas entradas
    assert len(out["top_alvos"]) >= 1


def test_formatter_queda_faturamento_cenario_critico():
    """Testa que queda_faturamento gera narrativa rica para cenário crítico."""
    spec = IntentSpec(tipo="queda_faturamento", filtros={"ano_base": "2024", "ano_comparado": "2025"})
    dados = [
        {"cliente_id": 1, "nome": "Cliente A", "variacao_abs": -50000, "variacao_pct": -25.5, "rota": "ROTA 01"},
        {"cliente_id": 2, "nome": "Cliente B", "variacao_abs": -30000, "variacao_pct": -20.0, "rota": "ROTA 02"},
        {"cliente_id": 3, "nome": "Cliente C", "variacao_abs": -20000, "variacao_pct": -15.0, "rota": "ROTA 01"},
    ]
    out = formatar_execucao(dados, spec, spec.filtros, [])
    
    # Valida estrutura
    assert set(out.keys()) == {"resumo", "achados", "implicacoes", "plano", "top_alvos"}
    
    # Valida conteúdo rico
    assert "clientes com queda" in out["resumo"].lower()
    assert len(out["achados"]) >= 3  # Mínimo 3 bullets
    assert len(out["implicacoes"]) >= 3
    assert len(out["plano"]) >= 3  # Mínimo 3 bullets no plano
    assert "top_alvos" in out
    assert len(out["top_alvos"]) >= 1
    
    # Valida que menciona números dos dados
    assert "3" in out["resumo"] or "três" in out["resumo"].lower()
    
    # Valida que plano é acionável (formato imperativo)
    assert any("Agendar" in p or "Priorizar" in p or "Criar" in p for p in out["plano"])


def test_formatter_meta_departamento_cenario_critico():
    """Testa que meta_departamento gera narrativa rica para cenário crítico."""
    spec = IntentSpec(tipo="meta_departamento")
    dados = [
        {"industria": "Mars", "total_vendedores": 10, "vendedores_fora_meta": 5, "percentual_fora_meta": 50.0},
        {"industria": "Nissin", "total_vendedores": 8, "vendedores_fora_meta": 2, "percentual_fora_meta": 25.0},
    ]
    out = formatar_execucao(dados, spec, {}, [])
    
    # Valida estrutura
    assert set(out.keys()) == {"resumo", "achados", "implicacoes", "plano", "top_alvos"}
    
    # Valida conteúdo rico
    assert "indústria" in out["resumo"].lower() or "vendedores" in out["resumo"].lower()
    assert len(out["achados"]) >= 3
    assert len(out["implicacoes"]) >= 3
    assert len(out["plano"]) >= 3
    assert "top_alvos" in out
    assert len(out["top_alvos"]) >= 1
    
    # Valida que menciona números dos dados
    assert "Mars" in out["resumo"] or "50" in out["resumo"] or "5" in out["resumo"]


def test_formatter_recompra_cenario_critico():
    """Testa que recompra gera narrativa rica para cenário crítico."""
    spec = IntentSpec(tipo="recompra", filtros={"sku": "Snickers Duplo Chocolate"})
    dados = [
        {"cliente_id": 1, "nome": "Cliente A", "dias_sem_recompra": 200, "rota_id": "ROTA 01", "sku": "Snickers Duplo Chocolate"},
        {"cliente_id": 2, "nome": "Cliente B", "dias_sem_recompra": 180, "rota_id": "ROTA 02", "sku": "Snickers Duplo Chocolate"},
    ]
    out = formatar_execucao(dados, spec, spec.filtros, [])
    
    # Valida estrutura
    assert set(out.keys()) == {"resumo", "achados", "implicacoes", "plano", "top_alvos"}
    
    # Valida conteúdo rico
    assert "recompra" in out["resumo"].lower()
    assert len(out["achados"]) >= 3
    assert len(out["implicacoes"]) >= 3
    assert len(out["plano"]) >= 3
    assert "top_alvos" in out
    assert len(out["top_alvos"]) >= 1


def test_formatter_clientes_sem_item_cenario_critico():
    """Testa que clientes_sem_item gera narrativa rica para cenário crítico."""
    spec = IntentSpec(tipo="clientes_sem_item", filtros={"sku": "Red Bull Zero", "industria": "Red Bull"})
    dados = [
        {"cliente_id": 1, "nome": "Cliente A", "rota_id": "ROTA 01", "sku": "Red Bull Zero"},
        {"cliente_id": 2, "nome": "Cliente B", "rota_id": "ROTA 02", "sku": "Red Bull Zero"},
    ]
    out = formatar_execucao(dados, spec, spec.filtros, [])
    
    # Valida estrutura
    assert set(out.keys()) == {"resumo", "achados", "implicacoes", "plano", "top_alvos"}
    
    # Valida conteúdo rico
    assert "não compraram" in out["resumo"].lower() or "sem" in out["resumo"].lower()
    assert len(out["achados"]) >= 3
    assert len(out["implicacoes"]) >= 3
    assert len(out["plano"]) >= 3
    assert "top_alvos" in out
    assert len(out["top_alvos"]) >= 1


def test_formatter_positivacao_cenario_critico():
    """Testa que positivacao gera narrativa rica para cenário crítico."""
    spec = IntentSpec(tipo="positivacao", filtros={"industria": "Mars", "periodo": "P12"})
    dados = [
        {"rota_id": "ROTA 01", "total_clientes_ativos": 50, "clientes_positivados": 10, "positivacao_pct": 20.0},
        {"rota_id": "ROTA 02", "total_clientes_ativos": 40, "clientes_positivados": 15, "positivacao_pct": 37.5},
    ]
    out = formatar_execucao(dados, spec, spec.filtros, [])
    
    # Valida estrutura
    assert set(out.keys()) == {"resumo", "achados", "implicacoes", "plano", "top_alvos"}
    
    # Valida conteúdo rico
    assert "positivação" in out["resumo"].lower() or "rotas" in out["resumo"].lower()
    assert len(out["achados"]) >= 3
    assert len(out["implicacoes"]) >= 3
    assert len(out["plano"]) >= 3
    assert "top_alvos" in out
    assert len(out["top_alvos"]) >= 1
    
    # Valida que menciona números dos dados
    assert "20" in out["resumo"] or "20.0" in out["resumo"] or "10" in out["resumo"]


def test_formatter_todas_secoes_presentes():
    """Testa que TODAS as seções obrigatórias estão presentes no texto final do post_processor."""
    from src.agent.post_processor import post_processar_resposta
    
    spec = IntentSpec(tipo="clientes_sem_compra", filtros={"dias": 60})
    dados = [
        {"cliente_id": 1, "nome": "Cliente A", "dias_sem_compra": 75, "rota_id": "ROTA 01"},
    ]
    
    resposta_dw = {"dados": dados, "tem_dados": True}
    resultado = post_processar_resposta(resposta_dw, spec, [], [])
    
    texto = resultado.get("texto", "")
    
    # Valida que todas as seções estão presentes
    secoes_obrigatorias = [
        "Resumo Executivo",
        "Principais Achados",
        "Implicações Comerciais",
        "Plano de Ação Imediato"
    ]
    
    for secao in secoes_obrigatorias:
        assert secao in texto, f"Seção '{secao}' não encontrada no texto final"

