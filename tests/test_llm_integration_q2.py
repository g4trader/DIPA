"""
Testes para integração Q2: Queda de Faturamento.

Testa:
1. Detecção de intent Q2
2. Parse de período
3. Geração de IntentSpec
4. Integração com orquestrador (com mocks)
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.llm_integration_intent_q2 import (
    detectar_intent_q2,
    parse_periodo_queda_faturamento,
    gerar_intent_spec_q2,
    processar_pergunta_q2
)
from src.agent.intent_spec import IntentSpec


class TestDetectarIntentQ2:
    """Testes para detecção de intent Q2."""
    
    def test_detecta_queda_faturamento_basico(self):
        """Testa detecção de pergunta básica sobre queda de faturamento."""
        pergunta = "Quais clientes tiveram queda de faturamento de setembro para outubro?"
        assert detectar_intent_q2(pergunta) == True
    
    def test_detecta_despencaram(self):
        """Testa detecção com palavra 'despencaram'."""
        pergunta = "Me mostre os clientes que despencaram em vendas no último mês."
        assert detectar_intent_q2(pergunta) == True
    
    def test_detecta_reduziram_compras(self):
        """Testa detecção com 'reduziram as compras'."""
        pergunta = "Quais clientes reduziram as compras em outubro?"
        assert detectar_intent_q2(pergunta) == True
    
    def test_detecta_top_clientes_queda(self):
        """Testa detecção de 'top clientes com maior queda'."""
        pergunta = "Top clientes com maior queda de faturamento neste trimestre."
        assert detectar_intent_q2(pergunta) == True
    
    def test_detecta_rota_queda(self):
        """Testa detecção de pergunta sobre rota."""
        pergunta = "Qual rota mais sofreu queda de faturamento em outubro?"
        assert detectar_intent_q2(pergunta) == True
    
    def test_detecta_pararam_comprar(self):
        """Testa detecção de 'pararam de comprar'."""
        pergunta = "Quais clientes pararam de comprar ou reduziram muito as compras em out/25?"
        assert detectar_intent_q2(pergunta) == True
    
    def test_nao_detecta_pergunta_nao_relacionada(self):
        """Testa que perguntas não relacionadas não são detectadas."""
        pergunta = "Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?"
        assert detectar_intent_q2(pergunta) == False
    
    def test_nao_detecta_sem_palavra_queda(self):
        """Testa que sem palavras-chave de queda, não detecta."""
        pergunta = "Quais são os clientes mais importantes?"
        assert detectar_intent_q2(pergunta) == False


class TestParsePeriodoQuedaFaturamento:
    """Testes para parse de período."""
    
    def test_parse_de_setembro_para_outubro(self):
        """Testa parse de 'de setembro para outubro'."""
        texto = "Quais clientes tiveram queda de faturamento de setembro para outubro?"
        resultado = parse_periodo_queda_faturamento(texto)
        
        assert resultado["data_ini_mes_anterior"] == "2025-09-01"
        assert resultado["data_fim_mes_anterior"] == "2025-09-30"
        assert resultado["data_ini_mes_atual"] == "2025-10-01"
        assert resultado["data_fim_mes_atual"] == "2025-10-31"
        assert resultado["ano"] == 2025
    
    def test_parse_ultimo_mes(self):
        """Testa parse de 'último mês'."""
        texto = "Quais clientes tiveram queda no último mês?"
        resultado = parse_periodo_queda_faturamento(texto)
        
        # Deve calcular mês anterior e atual baseado na data atual
        hoje = datetime.now()
        mes_anterior = hoje.replace(day=1) - timedelta(days=1)
        mes_atual = hoje.replace(day=1)
        
        assert resultado["data_ini_mes_anterior"] is not None
        assert resultado["data_fim_mes_anterior"] is not None
        assert resultado["data_ini_mes_atual"] is not None
        assert resultado["data_fim_mes_atual"] is not None
    
    def test_parse_trimestre_atual(self):
        """Testa parse de 'trimestre atual'."""
        texto = "Quais clientes tiveram queda no trimestre atual?"
        resultado = parse_periodo_queda_faturamento(texto)
        
        # Deve calcular baseado no trimestre atual
        assert resultado["data_ini_mes_anterior"] is not None
        assert resultado["data_fim_mes_anterior"] is not None
        assert resultado["data_ini_mes_atual"] is not None
        assert resultado["data_fim_mes_atual"] is not None
    
    def test_parse_meses_especificos(self):
        """Testa parse quando menciona meses específicos."""
        texto = "Quais clientes tiveram queda de faturamento em setembro e outubro de 2025?"
        resultado = parse_periodo_queda_faturamento(texto)
        
        assert resultado["data_ini_mes_anterior"] == "2025-09-01"
        assert resultado["data_fim_mes_anterior"] == "2025-09-30"
        assert resultado["data_ini_mes_atual"] == "2025-10-01"
        assert resultado["data_fim_mes_atual"] == "2025-10-31"
        assert resultado["ano"] == 2025
    
    def test_parse_formato_mes_ano(self):
        """Testa parse de formato 'set/25' ou '09/25'."""
        texto = "Quais clientes tiveram queda de set/25 para out/25?"
        resultado = parse_periodo_queda_faturamento(texto)
        
        assert resultado["data_ini_mes_anterior"] == "2025-09-01"
        assert resultado["data_fim_mes_anterior"] == "2025-09-30"
        assert resultado["data_ini_mes_atual"] == "2025-10-01"
        assert resultado["data_fim_mes_atual"] == "2025-10-31"
        assert resultado["ano"] == 2025
    
    def test_parse_padrao_se_nao_encontrado(self):
        """Testa que usa padrão set/25 → out/25 se não encontrar período."""
        texto = "Quais clientes tiveram queda?"
        resultado = parse_periodo_queda_faturamento(texto)
        
        # Deve usar padrão de demo
        assert resultado["data_ini_mes_anterior"] == "2025-09-01"
        assert resultado["data_fim_mes_anterior"] == "2025-09-30"
        assert resultado["data_ini_mes_atual"] == "2025-10-01"
        assert resultado["data_fim_mes_atual"] == "2025-10-31"
        assert resultado["ano"] == 2025


class TestGerarIntentSpecQ2:
    """Testes para geração de IntentSpec Q2."""
    
    def test_gera_intent_spec_basico(self):
        """Testa geração básica de IntentSpec."""
        pergunta = "Quais clientes tiveram queda de faturamento de setembro para outubro?"
        intent_spec = gerar_intent_spec_q2(pergunta)
        
        assert intent_spec.tipo == "queda_faturamento"
        assert intent_spec.dimensao_principal == "cliente"
        assert intent_spec.periodo_inicio == "2025-09-01"
        assert intent_spec.periodo_fim == "2025-10-31"
        assert intent_spec.filtros["data_ini_mes_anterior"] == "2025-09-01"
        assert intent_spec.filtros["data_fim_mes_anterior"] == "2025-09-30"
        assert intent_spec.filtros["data_ini_mes_atual"] == "2025-10-01"
        assert intent_spec.filtros["data_fim_mes_atual"] == "2025-10-31"
        assert intent_spec.filtros["min_faturamento_mes_anterior"] == 500.0
        assert intent_spec.filtros["min_queda_percentual"] == 10.0
        assert intent_spec.filtros["limit"] == 100
    
    def test_gera_intent_spec_com_top_n(self):
        """Testa geração de IntentSpec com 'top N'."""
        pergunta = "Top 50 clientes com maior queda de faturamento de setembro para outubro?"
        intent_spec = gerar_intent_spec_q2(pergunta)
        
        assert intent_spec.filtros["limit"] == 50


class TestProcessarPerguntaQ2:
    """Testes para processamento completo de pergunta Q2."""
    
    def test_nao_processa_pergunta_nao_q2(self):
        """Testa que pergunta não-Q2 gera erro."""
        pergunta = "Quais clientes estão sem compra há mais de 60 dias?"
        
        with pytest.raises(ValueError, match="não é sobre queda de faturamento"):
            processar_pergunta_q2(pergunta)


class TestIntegracaoComOrquestrador:
    """Testes de integração com orquestrador (com mocks)."""
    
    def test_intent_spec_gerado_tem_estrutura_correta(self):
        """Testa que o IntentSpec gerado tem a estrutura correta para o orquestrador."""
        pergunta = "Quais clientes tiveram queda de faturamento de setembro para outubro?"
        intent_spec = gerar_intent_spec_q2(pergunta)
        
        # Verifica estrutura do IntentSpec
        assert intent_spec.tipo == "queda_faturamento"
        assert intent_spec.dimensao_principal == "cliente"
        assert intent_spec.filtros["data_ini_mes_anterior"] == "2025-09-01"
        assert intent_spec.filtros["data_fim_mes_anterior"] == "2025-09-30"
        assert intent_spec.filtros["data_ini_mes_atual"] == "2025-10-01"
        assert intent_spec.filtros["data_fim_mes_atual"] == "2025-10-31"
        assert intent_spec.filtros["min_faturamento_mes_anterior"] == 500.0
        assert intent_spec.filtros["min_queda_percentual"] == 10.0
        assert intent_spec.filtros["limit"] == 100

