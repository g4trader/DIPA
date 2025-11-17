"""
Testes de Aceitação - 40 Perguntas do DIPAM COPILOT™.

Este módulo contém testes de aceitação para validar:
1. Geração correta de IntentSpec
2. Estrutura da resposta executiva
3. Conteúdo esperado em cada resposta

Organizado por tema:
- 3.1. Metas por período (7 testes)
- 3.2. Ranking de vendedores e supervisores (8 testes)
- 3.3. Clientes críticos, churn e recuperação (10 testes)
- 3.4. Produtos, marcas, categorias (7 testes)
- 3.5. Consultas executivas complexas (8 testes)
"""

import pytest
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from src.agent.intent_spec import IntentSpec
from src.agent.handler_dw_refatorado import processar_pergunta_com_dw
from src.dw.connection import get_db_session


# ============================================================================
# HELPERS DE VALIDAÇÃO
# ============================================================================

def validar_estrutura_resposta(resposta: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Valida estrutura básica da resposta.
    
    Returns:
        (valido, lista_erros)
    """
    erros = []
    
    # Campos obrigatórios
    campos_obrigatorios = [
        "resumo_executivo",
        "periodo_analisado",
        "tabela_principal",
        "insights"
    ]
    
    for campo in campos_obrigatorios:
        if campo not in resposta:
            erros.append(f"Campo obrigatório '{campo}' ausente")
    
    # Valida tipos
    if "resumo_executivo" in resposta:
        if not isinstance(resposta["resumo_executivo"], str):
            erros.append("'resumo_executivo' deve ser string")
        elif len(resposta["resumo_executivo"]) < 10:
            erros.append("'resumo_executivo' muito curto (mínimo 10 caracteres)")
    
    if "periodo_analisado" in resposta:
        if not isinstance(resposta["periodo_analisado"], dict):
            erros.append("'periodo_analisado' deve ser dict")
        else:
            if "inicio" not in resposta["periodo_analisado"]:
                erros.append("'periodo_analisado.inicio' ausente")
            if "fim" not in resposta["periodo_analisado"]:
                erros.append("'periodo_analisado.fim' ausente")
    
    if "tabela_principal" in resposta:
        if not isinstance(resposta["tabela_principal"], list):
            erros.append("'tabela_principal' deve ser list")
    
    if "insights" in resposta:
        if not isinstance(resposta["insights"], list):
            erros.append("'insights' deve ser list")
        elif len(resposta["insights"]) == 0:
            erros.append("'insights' não pode estar vazio")
    
    return len(erros) == 0, erros


def validar_intent_spec_esperado(
    intent_spec: IntentSpec,
    tipo_esperado: str,
    dimensao_esperada: str = None,
    periodo_inicio_esperado: str = None,
    periodo_fim_esperado: str = None
) -> tuple[bool, List[str]]:
    """
    Valida se IntentSpec corresponde ao esperado.
    
    Returns:
        (valido, lista_erros)
    """
    erros = []
    
    if intent_spec.tipo != tipo_esperado:
        erros.append(f"Tipo esperado '{tipo_esperado}', recebido '{intent_spec.tipo}'")
    
    if dimensao_esperada and intent_spec.dimensao_principal != dimensao_esperada:
        erros.append(
            f"Dimensão esperada '{dimensao_esperada}', "
            f"recebida '{intent_spec.dimensao_principal}'"
        )
    
    if periodo_inicio_esperado:
        if intent_spec.periodo_inicio != periodo_inicio_esperado:
            erros.append(
                f"Período início esperado '{periodo_inicio_esperado}', "
                f"recebido '{intent_spec.periodo_inicio}'"
            )
    
    if periodo_fim_esperado:
        if intent_spec.periodo_fim != periodo_fim_esperado:
            erros.append(
                f"Período fim esperado '{periodo_fim_esperado}', "
                f"recebido '{intent_spec.periodo_fim}'"
            )
    
    return len(erros) == 0, erros


def validar_conteudo_resposta(
    resposta: Dict[str, Any],
    deve_ter_tabela: bool = True,
    deve_ter_insights: bool = True,
    palavras_chave_resumo: List[str] = None
) -> tuple[bool, List[str]]:
    """
    Valida conteúdo esperado na resposta.
    
    Returns:
        (valido, lista_erros)
    """
    erros = []
    
    if deve_ter_tabela:
        if not resposta.get("tabela_principal") or len(resposta["tabela_principal"]) == 0:
            erros.append("Resposta deve conter tabela_principal com dados")
    
    if deve_ter_insights:
        if not resposta.get("insights") or len(resposta["insights"]) == 0:
            erros.append("Resposta deve conter insights")
    
    if palavras_chave_resumo:
        resumo_lower = resposta.get("resumo_executivo", "").lower()
        for palavra in palavras_chave_resumo:
            if palavra.lower() not in resumo_lower:
                erros.append(f"Resumo executivo deve mencionar '{palavra}'")
    
    return len(erros) == 0, erros


# ============================================================================
# 3.1. METAS POR PERÍODO (7 testes)
# ============================================================================

@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_01_liste_metas_por_mes_periodo_completo():
    """Teste 3.1.1: Liste as metas por mês de todo o período que você tem."""
    pergunta = "Liste as metas por mês de todo o período que você tem."
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"
        
        # Valida IntentSpec
        intent_spec = resposta.get("intent_spec")
        assert intent_spec is not None, "IntentSpec deve estar presente"
        valido, erros = validar_intent_spec_esperado(
            intent_spec,
            tipo_esperado="meta",
            dimensao_esperada="mes"
        )
        assert valido, f"Erros no IntentSpec: {erros}"
        
        # Valida conteúdo
        valido, erros = validar_conteudo_resposta(
            resposta,
            deve_ter_tabela=True,
            palavras_chave_resumo=["mês", "meta"]  # Deve mencionar meses
        )
        assert valido, f"Erros no conteúdo: {erros}"


@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_02_meta_total_realizado_agosto_2025():
    """Teste 3.1.2: Qual a meta total e o realizado total de agosto de 2025?"""
    pergunta = "Qual a meta total e o realizado total de agosto de 2025?"
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"
        
        # Valida IntentSpec
        intent_spec = resposta.get("intent_spec")
        assert intent_spec is not None
        valido, erros = validar_intent_spec_esperado(
            intent_spec,
            tipo_esperado="meta",
            dimensao_esperada="nenhuma",
            periodo_inicio_esperado="2025-08-01"
        )
        assert valido, f"Erros no IntentSpec: {erros}"
        
        # Valida conteúdo
        valido, erros = validar_conteudo_resposta(
            resposta,
            palavras_chave_resumo=["agosto", "2025", "meta", "realizado"]
        )
        assert valido, f"Erros no conteúdo: {erros}"


@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_03_evolucao_meta_nov_2024_out_2025():
    """Teste 3.1.3: Como foi a evolução da meta realizada de novembro/2024 até outubro/2025?"""
    pergunta = "Como foi a evolução da meta realizada de novembro/2024 até outubro/2025?"
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"
        
        # Valida IntentSpec
        intent_spec = resposta.get("intent_spec")
        assert intent_spec is not None
        valido, erros = validar_intent_spec_esperado(
            intent_spec,
            tipo_esperado="meta",
            dimensao_esperada="mes",
            periodo_inicio_esperado="2024-11-01",
            periodo_fim_esperado="2025-10-31"
        )
        assert valido, f"Erros no IntentSpec: {erros}"
        
        # Valida conteúdo
        valido, erros = validar_conteudo_resposta(
            resposta,
            deve_ter_tabela=True,
            palavras_chave_resumo=["evolução", "tendência"]  # Deve mencionar evolução
        )
        assert valido, f"Erros no conteúdo: {erros}"


@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_04_mes_pior_atingimento():
    """Teste 3.1.4: Qual foi o mês com pior atingimento de meta no período disponível?"""
    pergunta = "Qual foi o mês com pior atingimento de meta no período disponível?"
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"
        
        # Valida conteúdo
        valido, erros = validar_conteudo_resposta(
            resposta,
            palavras_chave_resumo=["pior", "atingimento"]  # Deve mencionar pior mês
        )
        assert valido, f"Erros no conteúdo: {erros}"


@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_05_meses_atingimento_abaixo_95():
    """Teste 3.1.5: Em quais meses o atingimento ficou abaixo de 95%?"""
    pergunta = "Em quais meses o atingimento ficou abaixo de 95%?"
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"
        
        # Valida conteúdo
        valido, erros = validar_conteudo_resposta(
            resposta,
            palavras_chave_resumo=["95%", "abaixo"]  # Deve mencionar meses críticos
        )
        assert valido, f"Erros no conteúdo: {erros}"


@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_06_vendedores_bateram_meta_agosto():
    """Teste 3.1.6: Quantos vendedores bateram a meta em agosto de 2025?"""
    pergunta = "Quantos vendedores bateram a meta em agosto de 2025?"
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"
        
        # Valida IntentSpec
        intent_spec = resposta.get("intent_spec")
        assert intent_spec is not None
        valido, erros = validar_intent_spec_esperado(
            intent_spec,
            tipo_esperado="meta",
            dimensao_esperada="vendedor",
            periodo_inicio_esperado="2025-08-01"
        )
        assert valido, f"Erros no IntentSpec: {erros}"
        
        # Valida conteúdo
        valido, erros = validar_conteudo_resposta(
            resposta,
            palavras_chave_resumo=["vendedor", "agosto", "2025"]
        )
        assert valido, f"Erros no conteúdo: {erros}"


@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_07_soma_metas_periodo_inteiro():
    """Teste 3.1.7: Quero a soma das metas do período inteiro, independente de mês."""
    pergunta = "Quero a soma das metas do período inteiro, independente de mês."
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"
        
        # Valida conteúdo
        valido, erros = validar_conteudo_resposta(
            resposta,
            palavras_chave_resumo=["soma", "total", "período"]
        )
        assert valido, f"Erros no conteúdo: {erros}"


# ============================================================================
# 3.2. RANKING DE VENDEDORES E SUPERVISORES (8 testes)
# ============================================================================

@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_08_top_5_vendedores_risco_agosto():
    """Teste 3.2.1: Quais são os 5 vendedores com maior risco de não bater a meta em agosto de 2025?"""
    pergunta = "Quais são os 5 vendedores com maior risco de não bater a meta em agosto de 2025?"
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"
        
        # Valida IntentSpec
        intent_spec = resposta.get("intent_spec")
        assert intent_spec is not None
        valido, erros = validar_intent_spec_esperado(
            intent_spec,
            tipo_esperado="ranking_vendedores",
            dimensao_esperada="vendedor",
            periodo_inicio_esperado="2025-08-01"
        )
        assert valido, f"Erros no IntentSpec: {erros}"
        
        # Valida que filtro top_n=5 está presente
        assert intent_spec.filtros.get("top_n") == 5 or intent_spec.filtros.get("limite") == 5, \
            "Filtro top_n=5 deve estar presente"
        
        # Valida conteúdo
        valido, erros = validar_conteudo_resposta(
            resposta,
            deve_ter_tabela=True,
            palavras_chave_resumo=["vendedor", "risco", "agosto"]
        )
        assert valido, f"Erros no conteúdo: {erros}"


@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_09_top_5_vendedores_melhor_performance():
    """Teste 3.2.2: Quais são os 5 vendedores com melhor performance no período de junho a agosto de 2025?"""
    pergunta = "Quais são os 5 vendedores com melhor performance no período de junho a agosto de 2025?"
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"
        
        # Valida IntentSpec
        intent_spec = resposta.get("intent_spec")
        assert intent_spec is not None
        valido, erros = validar_intent_spec_esperado(
            intent_spec,
            tipo_esperado="ranking_vendedores",
            dimensao_esperada="vendedor",
            periodo_inicio_esperado="2025-06-01",
            periodo_fim_esperado="2025-08-31"
        )
        assert valido, f"Erros no IntentSpec: {erros}"


@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_10_supervisor_mais_distante_meta():
    """Teste 3.2.3: Qual supervisor ficou mais distante da meta em agosto de 2025?"""
    pergunta = "Qual supervisor ficou mais distante da meta em agosto de 2025?"
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"
        
        # Valida IntentSpec
        intent_spec = resposta.get("intent_spec")
        assert intent_spec is not None
        valido, erros = validar_intent_spec_esperado(
            intent_spec,
            tipo_esperado="meta",
            dimensao_esperada="supervisor",
            periodo_inicio_esperado="2025-08-01"
        )
        assert valido, f"Erros no IntentSpec: {erros}"


@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_11_ranking_completo_vendedores_agosto():
    """Teste 3.2.4: Traga o ranking completo de vendedores por atingimento de meta em agosto de 2025."""
    pergunta = "Traga o ranking completo de vendedores por atingimento de meta em agosto de 2025."
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"
        
        # Valida conteúdo
        valido, erros = validar_conteudo_resposta(
            resposta,
            deve_ter_tabela=True,
            palavras_chave_resumo=["ranking", "vendedor", "atingimento"]
        )
        assert valido, f"Erros no conteúdo: {erros}"


@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_12_percentual_medio_atingimento_equipe():
    """Teste 3.2.5: Qual é o percentual médio de atingimento da equipe em agosto de 2025?"""
    pergunta = "Qual é o percentual médio de atingimento da equipe em agosto de 2025?"
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"
        
        # Valida conteúdo
        valido, erros = validar_conteudo_resposta(
            resposta,
            palavras_chave_resumo=["percentual", "médio", "atingimento", "agosto"]
        )
        assert valido, f"Erros no conteúdo: {erros}"


@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_13_vendedores_abaixo_80_meta():
    """Teste 3.2.6: Mostre a lista de vendedores que estão abaixo de 80% da meta em agosto de 2025."""
    pergunta = "Mostre a lista de vendedores que estão abaixo de 80% da meta em agosto de 2025."
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"
        
        # Valida conteúdo
        valido, erros = validar_conteudo_resposta(
            resposta,
            deve_ter_tabela=True,
            palavras_chave_resumo=["80%", "abaixo", "vendedor"]
        )
        assert valido, f"Erros no conteúdo: {erros}"


@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_14_comparar_supervisores_norte_sul():
    """Teste 3.2.7: Comparar a performance dos supervisores da região Norte e Sul em agosto de 2025."""
    pergunta = "Comparar a performance dos supervisores da região Norte e Sul em agosto de 2025."
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"
        
        # Valida conteúdo
        valido, erros = validar_conteudo_resposta(
            resposta,
            palavras_chave_resumo=["supervisor", "região", "comparar"]
        )
        assert valido, f"Erros no conteúdo: {erros}"


@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_15_vendedores_melhoraram_julho_agosto():
    """Teste 3.2.8: Quais vendedores melhoraram mais o atingimento entre julho e agosto de 2025?"""
    pergunta = "Quais vendedores melhoraram mais o atingimento entre julho e agosto de 2025?"
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"
        
        # Valida conteúdo
        valido, erros = validar_conteudo_resposta(
            resposta,
            deve_ter_tabela=True,
            palavras_chave_resumo=["melhoraram", "atingimento", "julho", "agosto"]
        )
        assert valido, f"Erros no conteúdo: {erros}"


# ============================================================================
# 3.3. CLIENTES CRÍTICOS, CHURN E RECUPERAÇÃO (10 testes)
# ============================================================================

@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_16_clientes_criticos_60_dias_por_supervisor():
    """Teste 3.3.1: Liste os clientes críticos (60 dias sem compra) por supervisor."""
    pergunta = "Liste os clientes críticos (60 dias sem compra) por supervisor."
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"
        
        # Valida IntentSpec
        intent_spec = resposta.get("intent_spec")
        assert intent_spec is not None
        valido, erros = validar_intent_spec_esperado(
            intent_spec,
            tipo_esperado="clientes_criticos",
            dimensao_esperada="cliente"
        )
        assert valido, f"Erros no IntentSpec: {erros}"


@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_17_clientes_churn_90_dias_agosto():
    """Teste 3.3.2: Quais clientes deixaram de comprar há mais de 90 dias (churn) em agosto de 2025?"""
    pergunta = "Quais clientes deixaram de comprar há mais de 90 dias (churn) em agosto de 2025?"
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"
        
        # Valida conteúdo
        valido, erros = validar_conteudo_resposta(
            resposta,
            deve_ter_tabela=True,
            palavras_chave_resumo=["churn", "90", "dias", "agosto"]
        )
        assert valido, f"Erros no conteúdo: {erros}"


@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_18_top_10_clientes_maior_queda_faturamento():
    """Teste 3.3.3: Quais são os 10 clientes com maior queda de faturamento vs média dos 3 meses anteriores?"""
    pergunta = "Quais são os 10 clientes com maior queda de faturamento vs média dos 3 meses anteriores?"
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"


@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_19_clientes_recuperados_ultimos_3_meses():
    """Teste 3.3.4: Mostre os clientes que voltaram a comprar após estarem críticos nos últimos 3 meses."""
    pergunta = "Mostre os clientes que voltaram a comprar após estarem críticos nos últimos 3 meses."
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"


@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_20_clientes_criticos_rota_75():
    """Teste 3.3.5: Quais clientes críticos estão concentrados na ROTA 75 VD?"""
    pergunta = "Quais clientes críticos estão concentrados na ROTA 75 VD?"
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"


@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_21_clientes_nissin_risco_churn():
    """Teste 3.3.6: Quais são os clientes da marca Nissin com risco de churn em agosto de 2025?"""
    pergunta = "Quais são os clientes da marca Nissin com risco de churn em agosto de 2025?"
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"


@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_22_impacto_financeiro_recuperar_50_clientes():
    """Teste 3.3.7: Mostre o impacto financeiro estimado se recuperarmos apenas 50% dos clientes críticos atuais."""
    pergunta = "Mostre o impacto financeiro estimado se recuperarmos apenas 50% dos clientes críticos atuais."
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"


@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_23_clientes_queda_50_6_meses():
    """Teste 3.3.8: Liste clientes com queda acima de 50% em relação à média dos últimos 6 meses."""
    pergunta = "Liste clientes com queda acima de 50% em relação à média dos últimos 6 meses."
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"


@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_24_clientes_criticos_supervisor_x():
    """Teste 3.3.9: Quais clientes críticos pertencem ao supervisor X?"""
    pergunta = "Quais clientes críticos pertencem ao supervisor X?"
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"


@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_25_clientes_reativados_outubro():
    """Teste 3.3.10: Quais clientes passaram de churn para ativos em outubro de 2025?"""
    pergunta = "Quais clientes passaram de churn para ativos em outubro de 2025?"
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"


# ============================================================================
# 3.4. PRODUTOS, MARCAS, CATEGORIAS (7 testes)
# ============================================================================

@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_26_produtos_maior_queda_agosto_vs_julho():
    """Teste 3.4.1: Quais são os produtos com maior queda de vendas em agosto de 2025 vs julho de 2025?"""
    pergunta = "Quais são os produtos com maior queda de vendas em agosto de 2025 vs julho de 2025?"
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"


@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_27_top_5_marcas_crescimento_trimestre():
    """Teste 3.4.2: Mostre as 5 marcas com melhor crescimento no trimestre de jun–ago/2025."""
    pergunta = "Mostre as 5 marcas com melhor crescimento no trimestre de jun–ago/2025."
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"


@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_28_participacao_nissin_faturamento_agosto():
    """Teste 3.4.3: Qual é a participação de Nissin no faturamento total de agosto de 2025?"""
    pergunta = "Qual é a participação de Nissin no faturamento total de agosto de 2025?"
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"


@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_29_categorias_puxaram_resultado_outubro():
    """Teste 3.4.4: Quais categorias puxaram o resultado positivo em outubro de 2025?"""
    pergunta = "Quais categorias puxaram o resultado positivo em outubro de 2025?"
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"


@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_30_skus_ticket_medio_alto_maio_julho():
    """Teste 3.4.5: Liste os SKUs com ticket médio mais alto no período de maio a julho de 2025."""
    pergunta = "Liste os SKUs com ticket médio mais alto no período de maio a julho de 2025."
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"


@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_31_produtos_ruptura_2_meses_voltaram():
    """Teste 3.4.6: Quais produtos tiveram ruptura de compras (ficaram 2 meses sem ser vendidos) e depois voltaram?"""
    pergunta = "Quais produtos tiveram ruptura de compras (ficaram 2 meses sem ser vendidos) e depois voltaram?"
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"


@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_32_produtos_sazonalidade_nov_fev():
    """Teste 3.4.7: Quais produtos são mais sensíveis à sazonalidade entre novembro e fevereiro?"""
    pergunta = "Quais produtos são mais sensíveis à sazonalidade entre novembro e fevereiro?"
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"


# ============================================================================
# 3.5. CONSULTAS EXECUTIVAS COMPLEXAS (8 testes)
# ============================================================================

@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_33_diretor_analise_detalhada_agosto():
    """Teste 3.5.1: Sou o Diretor e quero entender detalhadamente por que não batemos a meta em agosto de 2025. Quero explicação por vendedor, por produto e por cliente."""
    pergunta = "Sou o Diretor e quero entender detalhadamente por que não batemos a meta em agosto de 2025. Quero explicação por vendedor, por produto e por cliente."
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"
        
        # Valida IntentSpec
        intent_spec = resposta.get("intent_spec")
        assert intent_spec is not None
        valido, erros = validar_intent_spec_esperado(
            intent_spec,
            tipo_esperado="analise_meta_detalhada",
            dimensao_esperada="vendedor",
            periodo_inicio_esperado="2025-08-01"
        )
        assert valido, f"Erros no IntentSpec: {erros}"
        
        # Valida conteúdo
        valido, erros = validar_conteudo_resposta(
            resposta,
            deve_ter_tabela=True,
            palavras_chave_resumo=["agosto", "2025", "meta", "vendedor"]
        )
        assert valido, f"Erros no conteúdo: {erros}"


@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_34_regioes_venderam_abaixo_esperado():
    """Teste 3.5.2: Quais regiões venderam abaixo do esperado em agosto de 2025 e qual foi o impacto financeiro?"""
    pergunta = "Quais regiões venderam abaixo do esperado em agosto de 2025 e qual foi o impacto financeiro?"
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"


@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_35_rota_mais_clientes_nissin():
    """Teste 3.5.3: Qual rota tem mais clientes positivados em produtos Nissin no mês de agosto de 2025?"""
    pergunta = "Qual rota tem mais clientes positivados em produtos Nissin no mês de agosto de 2025?"
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"


@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_36_vendedores_carteira_concentrada():
    """Teste 3.5.4: Quais vendedores têm carteira mais concentrada em poucos clientes (risco de concentração)?"""
    pergunta = "Quais vendedores têm carteira mais concentrada em poucos clientes (risco de concentração)?"
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"


@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_37_projecao_fechamento_agosto():
    """Teste 3.5.5: Se mantivermos o ritmo médio diário de agosto de 2025, qual a projeção de fechamento do mês?"""
    pergunta = "Se mantivermos o ritmo médio diário de agosto de 2025, qual a projeção de fechamento do mês?"
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"


@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_38_relacao_visitas_faturamento_vendedor():
    """Teste 3.5.6: Mostre a relação entre visitas (pedidos) e faturamento por vendedor em agosto de 2025."""
    pergunta = "Mostre a relação entre visitas (pedidos) e faturamento por vendedor em agosto de 2025."
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"


@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_39_supervisores_mais_clientes_criticos():
    """Teste 3.5.7: Quais supervisores têm maior número de clientes críticos na carteira?"""
    pergunta = "Quais supervisores têm maior número de clientes críticos na carteira?"
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"


@pytest.mark.aceitacao
@pytest.mark.integration
def test_aceitacao_40_resumo_executivo_geral_periodo():
    """Teste 3.5.8: Mostre um resumo executivo geral do período nov/2024 a out/2025: melhores meses, piores meses, marcas que cresceram e principais riscos."""
    pergunta = "Mostre um resumo executivo geral do período nov/2024 a out/2025: melhores meses, piores meses, marcas que cresceram e principais riscos."
    
    with get_db_session() as session:
        resposta = processar_pergunta_com_dw(pergunta, session, papel="diretor")
        
        # Valida estrutura
        valido, erros = validar_estrutura_resposta(resposta)
        assert valido, f"Erros na estrutura: {erros}"
        
        # Valida conteúdo
        valido, erros = validar_conteudo_resposta(
            resposta,
            deve_ter_tabela=True,
            palavras_chave_resumo=["resumo", "período", "meses", "marcas"]
        )
        assert valido, f"Erros no conteúdo: {erros}"

