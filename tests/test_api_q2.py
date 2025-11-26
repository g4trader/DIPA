"""
Testes para endpoint Q2 (queda de faturamento).

Testa o endpoint /api/copilot/q2 e a integração com o endpoint /ask.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json

# Importa app FastAPI
from src.api.main import app

client = TestClient(app)


class TestQ2Endpoint:
    """Testes para endpoint /api/copilot/q2."""
    
    @patch('src.api.q2_endpoint.executar_q2_via_orquestrador')
    @patch('src.api.q2_endpoint.detectar_intent_q2')
    def test_endpoint_q2_com_pergunta_valida(self, mock_detectar, mock_executar):
        """Testa endpoint Q2 com pergunta válida."""
        # Mock da detecção
        mock_detectar.return_value = True
        
        # Mock do resultado do orquestrador
        mock_resultado = {
            "tipo": "Q2_QUEDA_FATURAMENTO",
            "dados_dw": {
                "dados": [
                    {
                        "cliente_id": 3318,
                        "cliente_nome": "ATACADAO DISTR COM IND LTDA LJ2",
                        "faturamento_mes_anterior": 3681404.58,
                        "faturamento_mes_atual": 2838392.46,
                        "queda_absoluta": 843012.12,
                        "queda_percentual": 22.90,
                        "rota": "ROTA 113",
                        "vendedor_nome": "ROTA 113",
                        "supervisor_nome": "Supervisor A"
                    },
                    {
                        "cliente_id": 2366,
                        "cliente_nome": "VIEZZER & CIA LTDA",
                        "faturamento_mes_anterior": 722858.49,
                        "faturamento_mes_atual": 194257.20,
                        "queda_absoluta": 528601.29,
                        "queda_percentual": 73.13,
                        "rota": "ROTA 21",
                        "vendedor_nome": "ROTA 21",
                        "supervisor_nome": "Supervisor B"
                    }
                ],
                "metrics": {
                    "total_clientes_queda": 2326,
                    "queda_media_absoluta": 95374.42,
                    "queda_media_percentual": 71.48,
                    "queda_maxima_absoluta": 843012.12,
                    "queda_maxima_percentual": 184.32
                },
                "total_com_faturamento_mes_anterior": 4061
            },
            "periodo": {
                "data_ini_mes_anterior": "2025-09-01",
                "data_fim_mes_anterior": "2025-09-30",
                "data_ini_mes_atual": "2025-10-01",
                "data_fim_mes_atual": "2025-10-31"
            },
            "texto_executivo": "Análise de Queda de Faturamento - set/25 x out/25\n\nForam identificados 2326 clientes com queda...",
            "periodo_descricao": "set/25 x out/25"
        }
        mock_executar.return_value = mock_resultado
        
        # Faz requisição
        response = client.post(
            "/api/copilot/q2",
            json={
                "pergunta": "Quais clientes tiveram queda de faturamento de setembro para outubro?"
            }
        )
        
        # Validações
        assert response.status_code == 200
        
        data = response.json()
        assert data["tipo"] == "Q2_QUEDA_FATURAMENTO"
        assert "texto_executivo" in data
        assert len(data["texto_executivo"]) > 0
        assert "periodo" in data
        assert data["periodo"]["descricao"] == "set/25 x out/25"
        assert "resumo" in data
        assert data["resumo"]["total_clientes_queda"] == 2326
        assert data["resumo"]["percentual_clientes_queda"] is not None
        assert data["resumo"]["queda_media_absoluta"] == 95374.42
        assert data["resumo"]["queda_media_percentual"] == 71.48
        assert "top_clientes" in data
        assert len(data["top_clientes"]) > 0
        assert data["top_clientes"][0]["nome"] == "ATACADAO DISTR COM IND LTDA LJ2"
        assert data["top_clientes"][0]["queda_absoluta"] == 843012.12
        assert "rotas" in data
        assert len(data["rotas"]) > 0
        assert "dados_brutos" in data
    
    @patch('src.api.q2_endpoint.detectar_intent_q2')
    def test_endpoint_q2_com_pergunta_invalida(self, mock_detectar):
        """Testa endpoint Q2 com pergunta que não é sobre Q2."""
        # Mock da detecção retorna False
        mock_detectar.return_value = False
        
        # Faz requisição
        response = client.post(
            "/api/copilot/q2",
            json={
                "pergunta": "Quais clientes estão sem compra há mais de 60 dias?"
            }
        )
        
        # Deve retornar 400
        assert response.status_code == 400
        assert "não é sobre queda de faturamento" in response.json()["detail"].lower()
    
    def test_endpoint_q2_sem_pergunta(self):
        """Testa endpoint Q2 sem campo pergunta."""
        response = client.post(
            "/api/copilot/q2",
            json={}
        )
        
        # Deve retornar erro de validação
        assert response.status_code == 422
    
    @patch('src.api.q2_endpoint.executar_q2_via_orquestrador')
    @patch('src.api.q2_endpoint.detectar_intent_q2')
    def test_endpoint_q2_com_periodo_nao_reconhecido(self, mock_detectar, mock_executar):
        """Testa endpoint Q2 com período não reconhecido (usa padrão)."""
        # Mock da detecção
        mock_detectar.return_value = True
        
        # Mock do resultado (usa período padrão)
        mock_resultado = {
            "tipo": "Q2_QUEDA_FATURAMENTO",
            "dados_dw": {
                "dados": [],
                "metrics": {
                    "total_clientes_queda": 0,
                    "queda_media_absoluta": 0.0,
                    "queda_media_percentual": 0.0,
                    "queda_maxima_absoluta": 0.0,
                    "queda_maxima_percentual": 0.0
                }
            },
            "periodo": {
                "data_ini_mes_anterior": "2025-09-01",
                "data_fim_mes_anterior": "2025-09-30",
                "data_ini_mes_atual": "2025-10-01",
                "data_fim_mes_atual": "2025-10-31"
            },
            "texto_executivo": "Análise de Queda de Faturamento - set/25 x out/25\n\nNão foram identificados clientes...",
            "periodo_descricao": "set/25 x out/25"
        }
        mock_executar.return_value = mock_resultado
        
        # Faz requisição
        response = client.post(
            "/api/copilot/q2",
            json={
                "pergunta": "Quais clientes tiveram queda?"
            }
        )
        
        # Deve retornar 200 mesmo sem período específico (usa padrão)
        assert response.status_code == 200
        data = response.json()
        assert data["tipo"] == "Q2_QUEDA_FATURAMENTO"
        assert data["resumo"]["total_clientes_queda"] == 0


class TestQ2IntegrationWithAsk:
    """Testes para integração Q2 com endpoint /ask."""
    
    @patch('src.llm_integration_intent_q2.detectar_intent_q2')
    def test_ask_endpoint_detecta_q2_e_redireciona(self, mock_detectar):
        """Testa que /ask detecta Q2 e redireciona."""
        # Mock da detecção
        mock_detectar.return_value = True
        
        # Mock do processamento Q2
        with patch('src.api.main.processar_q2_endpoint') as mock_processar:
            mock_processar.return_value = MagicMock(
                texto_executivo="Texto executivo Q2",
                resumo=MagicMock(
                    total_clientes_queda=2326,
                    dict=lambda: {"total_clientes_queda": 2326}
                ),
                top_clientes=[],
                rotas=[],
                periodo=MagicMock(descricao="set/25 x out/25")
            )
            
            # Faz requisição
            response = client.post(
                "/ask",
                json={
                    "pergunta": "Quais clientes tiveram queda de faturamento de setembro para outubro?"
                }
            )
            
            # Deve processar via Q2
            # Nota: A resposta pode ser AskResponse convertida, mas o conteúdo deve ser Q2
            assert response.status_code == 200
            # Verifica que o mock foi chamado
            mock_processar.assert_called_once()


class TestQ2ResponseStructure:
    """Testes para estrutura da resposta Q2."""
    
    @patch('src.api.q2_endpoint.executar_q2_via_orquestrador')
    @patch('src.api.q2_endpoint.detectar_intent_q2')
    def test_resposta_contem_todos_os_campos_obrigatorios(self, mock_detectar, mock_executar):
        """Testa que a resposta contém todos os campos obrigatórios."""
        mock_detectar.return_value = True
        
        mock_resultado = {
            "tipo": "Q2_QUEDA_FATURAMENTO",
            "dados_dw": {
                "dados": [
                    {
                        "cliente_id": 3318,
                        "cliente_nome": "ATACADAO DISTR COM IND LTDA LJ2",
                        "queda_absoluta": 843012.12,
                        "queda_percentual": 22.90,
                        "rota": "ROTA 113"
                    }
                ],
                "metrics": {
                    "total_clientes_queda": 2326,
                    "queda_media_absoluta": 95374.42,
                    "queda_media_percentual": 71.48,
                    "queda_maxima_absoluta": 843012.12,
                    "queda_maxima_percentual": 184.32
                },
                "total_com_faturamento_mes_anterior": 4061
            },
            "periodo": {
                "data_ini_mes_anterior": "2025-09-01",
                "data_fim_mes_anterior": "2025-09-30",
                "data_ini_mes_atual": "2025-10-01",
                "data_fim_mes_atual": "2025-10-31"
            },
            "texto_executivo": "Texto executivo...",
            "periodo_descricao": "set/25 x out/25"
        }
        mock_executar.return_value = mock_resultado
        
        response = client.post(
            "/api/copilot/q2",
            json={
                "pergunta": "Quais clientes tiveram queda de faturamento?"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Campos obrigatórios
        assert "tipo" in data
        assert "periodo" in data
        assert "texto_executivo" in data
        assert "resumo" in data
        assert "top_clientes" in data
        assert "rotas" in data
        
        # Estrutura do resumo
        resumo = data["resumo"]
        assert "total_clientes_queda" in resumo
        assert "queda_media_absoluta" in resumo
        assert "queda_media_percentual" in resumo
        assert "queda_maxima_absoluta" in resumo
        assert "queda_maxima_percentual" in resumo
        
        # Estrutura do período
        periodo = data["periodo"]
        assert "descricao" in periodo
        
        # Estrutura de top clientes
        if len(data["top_clientes"]) > 0:
            cliente = data["top_clientes"][0]
            assert "nome" in cliente
            assert "queda_absoluta" in cliente
            assert "queda_percentual" in cliente
        
        # Estrutura de rotas
        if len(data["rotas"]) > 0:
            rota = data["rotas"][0]
            assert "rota" in rota
            assert "qtd_clientes_queda" in rota
            assert "queda_total" in rota

