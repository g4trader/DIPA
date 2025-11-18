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
    """Testa que clientes_sem_compra usa narrativa específica com diagnóstico numérico e risco comercial."""
    spec = IntentSpec(tipo="clientes_sem_compra", filtros={"dias": 60})
    # Cenário negativo forte: muitos clientes sem compra há muito tempo
    dados = [
        {"cliente_id": 1, "nome": "Cliente A", "dias_sem_compra": 120, "rota_id": "ROTA 01", "supervisor": "Supervisor X"},
        {"cliente_id": 2, "nome": "Cliente B", "dias_sem_compra": 150, "rota_id": "ROTA 01", "supervisor": "Supervisor X"},
        {"cliente_id": 3, "nome": "Cliente C", "dias_sem_compra": 200, "rota_id": "ROTA 02", "supervisor": "Supervisor Y"},
        {"cliente_id": 4, "nome": "Cliente D", "dias_sem_compra": 180, "rota_id": "ROTA 02", "supervisor": "Supervisor Y"},
        {"cliente_id": 5, "nome": "Cliente E", "dias_sem_compra": 160, "rota_id": "ROTA 01", "supervisor": "Supervisor X"},
    ]
    out = formatar_execucao(dados, spec, spec.filtros, [])
    
    # Valida estrutura
    assert set(out.keys()) == {"resumo", "achados", "implicacoes", "plano", "top_alvos"}
    
    # Valida diagnóstico numérico: deve mencionar número de clientes
    import re
    numeros_clientes = re.findall(r'\d+', out["resumo"])
    assert len(numeros_clientes) > 0, "Resumo deve conter números (quantidade de clientes)"
    assert "5" in out["resumo"] or "cinco" in out["resumo"].lower(), "Resumo deve mencionar 5 clientes"
    
    # Valida menção a risco comercial
    texto_completo = " ".join([out["resumo"]] + out["implicacoes"]).lower()
    termos_risco = ["perda", "risco", "queda", "share", "receita", "faturamento", "churn", "rompimento"]
    assert any(termo in texto_completo for termo in termos_risco), \
        f"Texto deve mencionar risco comercial. Termos esperados: {termos_risco}"
    
    # Valida plano acionável
    assert len(out["plano"]) >= 3, "Plano deve ter pelo menos 3 bullets"
    assert any("Priorizar" in p or "priorizar" in p.lower() or "Agendar" in p or "agendar" in p.lower() 
               for p in out["plano"]), "Plano deve conter ações imperativas"
    
    # Validações de top_alvos
    assert "top_alvos" in out
    assert isinstance(out["top_alvos"], list)
    assert len(out["top_alvos"]) >= 1  # Com 5 clientes, deve ter pelo menos 1 entrada


def test_formatter_mix_nissin_usa_narrativa_especifica():
    """Testa que mix_nissin usa narrativa específica com cenário positivo (>100 clientes)."""
    spec = IntentSpec(tipo="mix_nissin", filtros={"mes": "2025-10", "ano": "2025"})
    # Cenário positivo: mais de 100 clientes batendo o mix mínimo
    dados = [
        {"cliente_id": i, "nome": f"Cliente {i}", "rota_id": f"ROTA {(i % 5) + 1:02d}"}
        for i in range(1, 105)  # 104 clientes
    ]
    out = formatar_execucao(dados, spec, spec.filtros, [])
    
    # Valida estrutura
    assert set(out.keys()) == {"resumo", "achados", "implicacoes", "plano", "top_alvos"}
    
    # Valida diagnóstico numérico: deve mencionar número de clientes
    import re
    numeros_clientes = re.findall(r'\d+', out["resumo"])
    assert len(numeros_clientes) > 0, "Resumo deve conter números (quantidade de clientes)"
    assert "104" in out["resumo"] or "cento" in out["resumo"].lower(), "Resumo deve mencionar 104 clientes"
    
    # Valida que é cenário positivo (boa adesão)
    texto_completo = " ".join([out["resumo"]] + out["achados"]).lower()
    assert "boa" in texto_completo or "adesão" in texto_completo or "104" in out["resumo"], \
        "Narrativa deve destacar boa adesão ao mix mínimo"
    
    # Valida menção a quem "puxou" o resultado (rota/supervisor/equipe)
    assert "rota" in texto_completo or "ROTA" in out["resumo"], \
        "Narrativa deve mencionar rotas que puxaram o resultado"
    
    # Valida recomendações sobre escalar estratégia
    plano_texto = " ".join(out["plano"]).lower()
    termos_escalar = ["replicar", "escalar", "expandir", "outras rotas", "playbook", "estratégia"]
    assert any(termo in plano_texto for termo in termos_escalar), \
        f"Plano deve recomendar escalar estratégia. Termos esperados: {termos_escalar}"
    
    # Validações de top_alvos
    assert "top_alvos" in out
    assert isinstance(out["top_alvos"], list)
    assert len(out["top_alvos"]) >= 1  # Com 104 clientes, deve ter pelo menos 1 entrada


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


def test_formatter_mix_usa_narrativa_especifica():
    """Testa que mix (Q5) usa narrativa específica com diagnóstico numérico e plano acionável."""
    spec = IntentSpec(tipo="mix", filtros={"limite": 10.0, "limite_media": 10.0})
    # Simula pelo menos 3 itens com média < 10 caixas
    dados = [
        {"sku": "SKU001", "descricao": "Produto A", "media_mensal": 2.5, "industria": "Mars", "categoria": "Chocolate"},
        {"sku": "SKU002", "descricao": "Produto B", "media_mensal": 4.0, "industria": "Mars", "categoria": "Chocolate"},
        {"sku": "SKU003", "descricao": "Produto C", "media_mensal": 6.5, "industria": "Nissin", "categoria": "Macarrão"},
        {"sku": "SKU004", "descricao": "Produto D", "media_mensal": 8.0, "industria": "Mars", "categoria": "Chocolate"},
        {"sku": "SKU005", "descricao": "Produto E", "media_mensal": 9.5, "industria": "Red Bull", "categoria": "Energético"},
    ]
    out = formatar_execucao(dados, spec, spec.filtros, [])
    
    # Valida estrutura
    assert set(out.keys()) == {"resumo", "achados", "implicacoes", "plano", "top_alvos"}
    
    # Valida diagnóstico numérico: deve mencionar número de itens
    import re
    numeros_itens = re.findall(r'\d+', out["resumo"])
    assert len(numeros_itens) > 0, "Resumo deve conter números (quantidade de itens)"
    assert "5" in out["resumo"] or "cinco" in out["resumo"].lower(), "Resumo deve mencionar 5 itens"
    
    # Valida que menciona limite usado
    assert "10" in out["resumo"] or "dez" in out["resumo"].lower(), "Resumo deve mencionar limite de 10 caixas"
    
    # Valida que todas as 5 seções estão presentes no texto final (via post_processor)
    from src.agent.post_processor import post_processar_resposta
    resposta_dw = {"dados": dados, "tem_dados": True}
    resultado = post_processar_resposta(resposta_dw, spec, [], [])
    texto = resultado.get("texto", "")
    
    secoes_obrigatorias = [
        "Resumo Executivo",
        "Principais Achados",
        "Implicações Comerciais",
        "Plano de Ação Imediato",
        "Alvos Prioritários (TOP 10)"
    ]
    
    for secao in secoes_obrigatorias:
        assert secao in texto, f"Seção '{secao}' não encontrada no texto final"
    
    # Valida que "Plano de Ação Imediato" contém pelo menos 3 bullets
    if "Plano de Ação Imediato" in texto:
        bloco_plano = texto.split("Plano de Ação Imediato", 1)[1].split("Alvos Prioritários", 1)[0]
        bullets_plano = [l.strip() for l in bloco_plano.splitlines() if l.strip() and l.strip().startswith("-")]
        assert len(bullets_plano) >= 3, f"Plano deve ter pelo menos 3 bullets, encontrados: {len(bullets_plano)}"
    
    # Valida que "Alvos Prioritários (TOP 10)" aparece no texto
    assert "Alvos Prioritários (TOP 10)" in texto, "Seção 'Alvos Prioritários (TOP 10)' deve estar presente"
    
    # Validações de top_alvos
    assert "top_alvos" in out
    assert isinstance(out["top_alvos"], list)
    assert len(out["top_alvos"]) >= 1  # Com 5 itens, deve ter pelo menos 1 entrada


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

