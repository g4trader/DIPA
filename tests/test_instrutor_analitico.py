"""
Testes para o Instrutor Analítico.

Testa:
- Geração de plano de raciocínio interno
- Estrutura do plano retornado
- Validação de campos obrigatórios
"""

import pytest
from unittest.mock import patch, MagicMock

from src.agent.intent_spec import IntentSpec
from src.agent.instrutor_analitico import gerar_plano_raciocinio_interno


def test_estrutura_plano_raciocinio():
    """Testa que o plano retornado tem a estrutura correta."""
    pergunta = "Quais são os 5 vendedores com maior risco de não bater a meta em agosto de 2025?"
    intent_spec = IntentSpec(
        tipo="ranking_vendedores",
        periodo_inicio="2025-08-01",
        periodo_fim="2025-08-31",
        dimensao_principal="vendedor",
        filtros={"top_n": 5}
    )
    dados_dw = {
        "status": "ok",
        "dados": [
            {
                "vendedor_id": 1,
                "vendedor_nome": "João Silva",
                "meta": 100000.0,
                "realizado": 85000.0,
                "gap": -15000.0,
                "atingimento_pct": 85.0
            }
        ]
    }
    
    # Mock da chamada LLM
    with patch('src.agent.instrutor_analitico.call_openai_llm') as mock_llm:
        mock_llm.return_value = """{
  "foco_analitico": [
    "Analisar top 5 vendedores com maior gap negativo",
    "Comparar atingimento vs meta para identificar risco"
  ],
  "achados_relevantes": [
    "João Silva tem gap de R$ 15.000,00 (15% abaixo da meta)"
  ],
  "prioridades_de_comunicacao": [
    "Destacar no resumo: 5 vendedores em risco crítico",
    "Tabela deve mostrar ranking completo com gap e atingimento"
  ],
  "alertas": [
    "ALERTA: João Silva está 15% abaixo da meta"
  ]
}"""
        
        plano = gerar_plano_raciocinio_interno(pergunta, intent_spec, dados_dw)
        
        # Valida estrutura
        assert "foco_analitico" in plano
        assert isinstance(plano["foco_analitico"], list)
        assert "achados_relevantes" in plano
        assert isinstance(plano["achados_relevantes"], list)
        assert "prioridades_de_comunicacao" in plano
        assert isinstance(plano["prioridades_de_comunicacao"], list)
        assert "alertas" in plano
        assert isinstance(plano["alertas"], list)


def test_plano_com_dados_vazios():
    """Testa geração de plano quando não há dados."""
    pergunta = "Liste as metas por mês"
    intent_spec = IntentSpec(
        tipo="meta",
        periodo_inicio="2025-08-01",
        periodo_fim="2025-08-31",
        dimensao_principal="mes"
    )
    dados_dw = {
        "status": "sem_dados",
        "dados": []
    }
    
    # Mock da chamada LLM
    with patch('src.agent.instrutor_analitico.call_openai_llm') as mock_llm:
        mock_llm.return_value = """{
  "foco_analitico": [
    "Informar claramente que não há dados disponíveis"
  ],
  "achados_relevantes": [],
  "prioridades_de_comunicacao": [
    "Mencionar no resumo que não há dados para o período solicitado"
  ],
  "alertas": []
}"""
        
        plano = gerar_plano_raciocinio_interno(pergunta, intent_spec, dados_dw)
        
        # Valida que plano foi gerado mesmo sem dados
        assert "foco_analitico" in plano
        assert len(plano["foco_analitico"]) > 0


def test_plano_fallback_em_erro():
    """Testa que retorna estrutura básica em caso de erro."""
    pergunta = "Teste"
    intent_spec = IntentSpec(
        tipo="meta",
        periodo_inicio="2025-08-01",
        periodo_fim="2025-08-31",
        dimensao_principal="mes"
    )
    dados_dw = {"status": "ok", "dados": []}
    
    # Mock da chamada LLM retornando JSON inválido
    with patch('src.agent.instrutor_analitico.call_openai_llm') as mock_llm:
        mock_llm.return_value = "JSON inválido {"
        
        plano = gerar_plano_raciocinio_interno(pergunta, intent_spec, dados_dw)
        
        # Valida que retorna estrutura básica mesmo com erro
        assert "foco_analitico" in plano
        assert "achados_relevantes" in plano
        assert "prioridades_de_comunicacao" in plano
        assert "alertas" in plano
        assert isinstance(plano["foco_analitico"], list)
        assert isinstance(plano["achados_relevantes"], list)
        assert isinstance(plano["prioridades_de_comunicacao"], list)
        assert isinstance(plano["alertas"], list)


def test_plano_com_papel_supervisor():
    """Testa geração de plano considerando papel do usuário."""
    pergunta = "Quais são os vendedores com maior risco?"
    intent_spec = IntentSpec(
        tipo="ranking_vendedores",
        periodo_inicio="2025-08-01",
        periodo_fim="2025-08-31",
        dimensao_principal="vendedor"
    )
    dados_dw = {"status": "ok", "dados": []}
    
    # Mock da chamada LLM
    with patch('src.agent.instrutor_analitico.call_openai_llm') as mock_llm:
        mock_llm.return_value = """{
  "foco_analitico": ["Analisar vendedores em risco"],
  "achados_relevantes": [],
  "prioridades_de_comunicacao": ["Destacar vendedores críticos"],
  "alertas": []
}"""
        
        plano = gerar_plano_raciocinio_interno(
            pergunta, intent_spec, dados_dw, papel="supervisor"
        )
        
        # Valida que plano foi gerado
        assert "foco_analitico" in plano
        # Verifica que o prompt incluiu o contexto do supervisor
        assert "supervisor" in mock_llm.call_args[0][0].lower() or "supervisor" in mock_llm.call_args[1].get("system_prompt", "").lower()

