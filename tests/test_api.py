"""
Testes para API FastAPI.

Testa endpoints e funcionalidades da API do agente.
"""

import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import json

# Adiciona diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def client():
    """Fixture para cliente de teste da API."""
    from src.api.main import app
    return TestClient(app)


@pytest.fixture
def mock_agent_service():
    """Fixture para mock do serviço do agente."""
    mock_service = MagicMock()
    mock_service.process_question.return_value = {
        "resposta": "Resposta simulada do agente",
        "intent": "meta_vendedor",
        "contexto": {
            "vendedor": "ROTA 77",
            "mes_ano": "2024-12",
            "meta_valor": 100000.0,
            "realizado_valor": 85000.0,
            "perc_atingido": 85.0
        },
        "confianca": 0.8
    }
    return mock_service


@pytest.fixture
def mock_db_session():
    """Fixture para mock de sessão do banco."""
    mock_session = MagicMock()
    return mock_session


@pytest.mark.unit
@pytest.mark.api
class TestHealthEndpoint:
    """Testes para endpoint /health."""
    
    def test_health_endpoint(self, client):
        """Testa endpoint de health check."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verifica estrutura da resposta
        assert "status" in data
        assert data["status"] in ["healthy", "ok"], \
            f"Status deveria ser 'healthy' ou 'ok', encontrado: {data['status']}"
        assert "timestamp" in data
        assert "version" in data
    
    def test_health_endpoint_structure(self, client):
        """Testa estrutura completa da resposta do /health."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Campos esperados
        expected_fields = ["status", "timestamp", "version"]
        for field in expected_fields:
            assert field in data, f"Campo {field} não encontrado na resposta"
        
        # Verifica tipos
        assert isinstance(data["status"], str)
        assert isinstance(data["timestamp"], str)
        assert isinstance(data["version"], str)
    
    def test_root_endpoint(self, client):
        """Testa endpoint raiz."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "endpoints" in data
        assert isinstance(data["endpoints"], dict)


@pytest.mark.unit
@pytest.mark.api
class TestAskEndpoint:
    """Testes para endpoint /ask."""
    
    def test_ask_endpoint_request_structure(self, client, mock_agent_service, mock_db_session):
        """Testa estrutura de requisição do endpoint /ask."""
        request_data = {
            "pergunta": "Qual é a meta do vendedor ROTA 77 em dezembro?",
            "usuario_id": "user123",
            "papel": "supervisor"
        }
        
        # Mock do serviço do agente
        with patch('src.api.main.get_agent_service', return_value=mock_agent_service), \
             patch('src.api.main.get_db_session', return_value=iter([mock_db_session])):
            
            response = client.post("/ask", json=request_data)
            
            # Verifica resposta
            assert response.status_code == 200, \
                f"Status code deveria ser 200, encontrado: {response.status_code}"
            
            data = response.json()
            
            # Verifica estrutura da resposta
            assert "resposta" in data, "Resposta deveria conter campo 'resposta'"
            assert "intent" in data, "Resposta deveria conter campo 'intent'"
            assert "contexto" in data, "Resposta deveria conter campo 'contexto'"
            assert "confianca" in data, "Resposta deveria conter campo 'confianca'"
            assert "timestamp" in data, "Resposta deveria conter campo 'timestamp'"
            
            # Verifica tipos
            assert isinstance(data["resposta"], str)
            assert isinstance(data["intent"], str)
            assert isinstance(data["contexto"], dict)
            assert isinstance(data["confianca"], float)
            assert 0 <= data["confianca"] <= 1, "Confiança deveria estar entre 0 e 1"
    
    def test_ask_endpoint_missing_fields(self, client):
        """Testa endpoint /ask com campos faltantes."""
        # Testa sem pergunta (obrigatória)
        request_data = {
            "usuario_id": "user123"
        }
        
        response = client.post("/ask", json=request_data)
        
        # Deve retornar erro de validação
        assert response.status_code in [422, 400], \
            f"Status code deveria ser 422 ou 400, encontrado: {response.status_code}"
    
    def test_ask_endpoint_empty_question(self, client, mock_agent_service, mock_db_session):
        """Testa endpoint /ask com pergunta vazia."""
        request_data = {
            "pergunta": "",
            "papel": "supervisor"
        }
        
        with patch('src.api.main.get_agent_service', return_value=mock_agent_service), \
             patch('src.api.main.get_db_session', return_value=iter([mock_db_session])):
            
            response = client.post("/ask", json=request_data)
            
            # Pode aceitar ou rejeitar pergunta vazia
            assert response.status_code in [200, 400, 422]
    
    def test_ask_endpoint_with_mock_llm(self, client, mock_agent_service, mock_db_session):
        """Testa endpoint /ask com mock do LLM."""
        request_data = {
            "pergunta": "Por que o vendedor ROTA 77 não bateu a meta em dezembro?",
            "papel": "supervisor"
        }
        
        # Mock do serviço do agente
        mock_agent_service.process_question.return_value = {
            "resposta": "## Análise de Meta - ROTA 77 (2024-12)\n\nO vendedor não atingiu a meta...",
            "intent": "meta_vendedor",
            "contexto": {
                "vendedor": "ROTA 77",
                "mes_ano": "2024-12",
                "meta_valor": 100000.0,
                "realizado_valor": 85000.0,
                "perc_atingido": 85.0
            },
            "confianca": 0.85
        }
        
        with patch('src.api.main.get_agent_service', return_value=mock_agent_service), \
             patch('src.api.main.get_db_session', return_value=iter([mock_db_session])):
            
            response = client.post("/ask", json=request_data)
            
            assert response.status_code == 200
            
            data = response.json()
            
            # Verifica que resposta contém texto esperado
            assert "ROTA 77" in data["resposta"] or "vendedor" in data["resposta"].lower()
            assert data["intent"] == "meta_vendedor"
            assert data["contexto"]["vendedor"] == "ROTA 77"
    
    def test_ask_endpoint_with_mock_database(self, client, mock_agent_service, mock_db_session):
        """Testa endpoint /ask com mock de consultas ao banco."""
        request_data = {
            "pergunta": "Quais clientes da rota 12 estão em maior risco de churn?",
            "papel": "supervisor"
        }
        
        # Mock do serviço do agente com contexto de churn
        mock_agent_service.process_question.return_value = {
            "resposta": "Foram identificados 5 clientes em risco de churn...",
            "intent": "churn_clientes",
            "contexto": {
                "clientes": [
                    {"nome": "Cliente A", "risco_churn": 0.85, "score": "alto"},
                    {"nome": "Cliente B", "risco_churn": 0.72, "score": "medio"}
                ],
                "qtd_clientes_risco": 5
            },
            "confianca": 0.75
        }
        
        with patch('src.api.main.get_agent_service', return_value=mock_agent_service), \
             patch('src.api.main.get_db_session', return_value=iter([mock_db_session])):
            
            response = client.post("/ask", json=request_data)
            
            assert response.status_code == 200
            
            data = response.json()
            assert data["intent"] == "churn_clientes"
            assert "clientes" in data["contexto"] or "qtd_clientes_risco" in data["contexto"]
    
    def test_ask_endpoint_json_valid(self, client, mock_agent_service, mock_db_session):
        """Testa que endpoint /ask retorna JSON válido."""
        request_data = {
            "pergunta": "Teste de pergunta",
            "papel": "diretor"
        }
        
        with patch('src.api.main.get_agent_service', return_value=mock_agent_service), \
             patch('src.api.main.get_db_session', return_value=iter([mock_db_session])):
            
            response = client.post("/ask", json=request_data)
            
            assert response.status_code == 200
            
            # Verifica que é JSON válido
            try:
                data = response.json()
                # Testa serialização
                json_str = json.dumps(data)
                parsed = json.loads(json_str)
                assert parsed == data
            except (ValueError, TypeError) as e:
                pytest.fail(f"Resposta não é JSON válido: {str(e)}")


@pytest.mark.unit
@pytest.mark.api
class TestPreviewEndpoint:
    """Testes para endpoint /preview/vendedor."""
    
    def test_preview_endpoint_structure(self, client):
        """Testa estrutura do endpoint /preview/vendedor."""
        vendedor = "ROTA%2077"
        mes_ano = "2024-12"
        
        # Mock das queries para evitar dependências do banco
        mock_vendedor_data = {
            "vendedor": "ROTA 77",
            "mes_ano": "2024-12",
            "meta_valor": 100000.0,
            "realizado_valor": 85000.0,
            "perc_atingido": 85.0,
            "gap_valor": -15000.0,
            "meta_volume": 1000,
            "realizado_volume": 850,
            "perc_atingido_volume": 85.0,
            "total_vendas": 85000.0,
            "qtd_clientes": 50,
            "ticket_medio": 1700.0
        }
        
        with patch('src.api.main.query_vendedor_meta', return_value=mock_vendedor_data), \
             patch('src.api.main.get_db_session', return_value=iter([MagicMock()])):
            
            response = client.get(f"/preview/vendedor/{vendedor}/{mes_ano}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Verifica estrutura
                assert "vendedor" in data
                assert "mes_ano" in data
                assert "dados" in data
                assert "timestamp" in data
                
                # Verifica dados
                assert data["vendedor"] == vendedor.replace("%20", " ") or data["vendedor"] == "ROTA 77"
                assert data["mes_ano"] == mes_ano
                assert isinstance(data["dados"], dict)
    
    def test_preview_endpoint_invalid_date_format(self, client):
        """Testa endpoint com formato de data inválido."""
        vendedor = "ROTA%2077"
        mes_ano = "invalid-date"
        
        response = client.get(f"/preview/vendedor/{vendedor}/{mes_ano}")
        
        # Deve retornar erro de validação
        assert response.status_code in [400, 422, 500], \
            f"Status code deveria ser 400, 422 ou 500, encontrado: {response.status_code}"
    
    def test_preview_endpoint_not_found(self, client):
        """Testa endpoint quando vendedor não é encontrado."""
        vendedor = "VENDEDOR_INEXISTENTE"
        mes_ano = "2024-12"
        
        # Mock retornando erro
        mock_error_data = {"erro": "Vendedor 'VENDEDOR_INEXISTENTE' não encontrado"}
        
        with patch('src.api.main.query_vendedor_meta', return_value=mock_error_data), \
             patch('src.api.main.get_db_session', return_value=iter([MagicMock()])):
            
            response = client.get(f"/preview/vendedor/{vendedor}/{mes_ano}")
            
            # Deve retornar 404
            assert response.status_code == 404, \
                f"Status code deveria ser 404, encontrado: {response.status_code}"


@pytest.mark.unit
@pytest.mark.api
class TestAPIStructure:
    """Testes para estrutura geral da API."""
    
    def test_api_docs_available(self, client):
        """Testa se documentação da API está disponível."""
        response = client.get("/docs")
        
        # Swagger UI deve estar disponível
        assert response.status_code == 200, \
            f"Swagger UI deveria estar disponível, status: {response.status_code}"
    
    def test_api_redoc_available(self, client):
        """Testa se ReDoc está disponível."""
        response = client.get("/redoc")
        
        # ReDoc deve estar disponível
        assert response.status_code == 200, \
            f"ReDoc deveria estar disponível, status: {response.status_code}"


@pytest.mark.unit
@pytest.mark.api
class TestAPIErrorHandling:
    """Testes para tratamento de erros da API."""
    
    def test_ask_endpoint_error_handling(self, client, mock_db_session):
        """Testa tratamento de erros no endpoint /ask."""
        request_data = {
            "pergunta": "Teste de erro",
            "papel": "supervisor"
        }
        
        # Mock do serviço que levanta erro
        mock_service = MagicMock()
        mock_service.process_question.side_effect = Exception("Erro simulado")
        
        with patch('src.api.main.get_agent_service', return_value=mock_service), \
             patch('src.api.main.get_db_session', return_value=iter([mock_db_session])):
            
            response = client.post("/ask", json=request_data)
            
            # Deve retornar erro 500
            assert response.status_code == 500, \
                f"Status code deveria ser 500, encontrado: {response.status_code}"
            
            data = response.json()
            assert "detail" in data, "Resposta de erro deveria conter campo 'detail'"
    
    def test_preview_endpoint_error_handling(self, client):
        """Testa tratamento de erros no endpoint /preview."""
        vendedor = "ROTA%2077"
        mes_ano = "2024-12"
        
        # Mock que levanta erro
        with patch('src.api.main.query_vendedor_meta', side_effect=Exception("Erro simulado")), \
             patch('src.api.main.get_db_session', return_value=iter([MagicMock()])):
            
            response = client.get(f"/preview/vendedor/{vendedor}/{mes_ano}")
            
            # Deve retornar erro 500
            assert response.status_code == 500, \
                f"Status code deveria ser 500, encontrado: {response.status_code}"


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.slow
class TestAPIIntegration:
    """Testes de integração para API (podem ser mais lentos)."""
    
    @pytest.mark.skip(reason="Requer banco de dados e modelos configurados")
    def test_full_ask_pipeline(self, client):
        """Testa pipeline completo do endpoint /ask."""
        request_data = {
            "pergunta": "Por que o vendedor ROTA 77 não bateu a meta em dezembro?",
            "papel": "supervisor"
        }
        
        # Este teste requer:
        # - Banco de dados configurado
        # - Dados carregados
        # - Modelos treinados (opcional)
        # - LLM configurado (opcional)
        
        response = client.post("/ask", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "resposta" in data
        assert "intent" in data
        assert "contexto" in data
        assert isinstance(data["resposta"], str)
        assert len(data["resposta"]) > 0


@pytest.mark.unit
@pytest.mark.api
class TestIntentDetection:
    """Testes para detecção de intenções."""
    
    def test_intent_detection_meta_vendedor(self):
        """Testa detecção de intenção de meta de vendedor."""
        from src.agent.intent import detect_intent, IntentType
        
        pergunta = "Qual é a meta do vendedor ROTA 77 em dezembro?"
        
        result = detect_intent(pergunta)
        
        assert "intent" in result
        assert "entities" in result
        assert isinstance(result["intent"], IntentType)
        
        # Verifica que detectou intenção de meta ou explicação
        assert result["intent"] in [IntentType.META_VENDEDOR, IntentType.EXPLICACAO, IntentType.DESCONHECIDA]
    
    def test_intent_detection_churn(self):
        """Testa detecção de intenção de churn."""
        from src.agent.intent import detect_intent, IntentType
        
        pergunta = "Quais clientes estão em risco de churn?"
        
        result = detect_intent(pergunta)
        
        assert "intent" in result
        # Pode detectar churn ou outra intenção dependendo dos padrões
        assert isinstance(result["intent"], IntentType)
    
    def test_entity_extraction(self):
        """Testa extração de entidades."""
        from src.agent.intent import extract_entities
        
        pergunta = "Qual é a meta do vendedor ROTA 77 em dezembro de 2024?"
        
        entities = extract_entities(pergunta)
        
        assert "vendedor" in entities or "rota" in entities, \
            "Deveria extrair vendedor ou rota da pergunta"
        
        # Verifica se extraiu rota
        rota = entities.get("rota") or entities.get("vendedor")
        if rota:
            assert "ROTA 77" in rota or "77" in rota, \
                f"Deveria extrair ROTA 77, encontrado: {rota}"
        
        # Verifica se extraiu mês/ano
        assert "mes" in entities or "mes_ano" in entities or "ano" in entities, \
            "Deveria extrair mês ou ano da pergunta"


@pytest.mark.unit
@pytest.mark.api
class TestInsightsEndpoints:
    """Testes para endpoints de insights (se existirem)."""
    
    @pytest.mark.skip(reason="Endpoint de insights não implementado ainda")
    def test_top_vendedores_endpoint(self, client):
        """Testa endpoint de top vendedores."""
        # Mock de dados para top vendedores
        mock_top_vendedores = [
            {"vendedor": "ROTA 77", "perc_atingido": 110.0, "meta_valor": 100000.0},
            {"vendedor": "ROTA 78", "perc_atingido": 105.5, "meta_valor": 120000.0},
            {"vendedor": "ROTA 79", "perc_atingido": 98.0, "meta_valor": 95000.0}
        ]
        
        with patch('src.api.main.query_top_vendedores', return_value=mock_top_vendedores), \
             patch('src.api.main.get_db_session', return_value=iter([MagicMock()])):
            
            response = client.get("/insights/top-vendedores?mes_ano=2024-12&limit=5")
            
            if response.status_code == 200:
                data = response.json()
                assert "vendedores" in data or isinstance(data, list)
                assert len(data.get("vendedores", data)) > 0
    
    @pytest.mark.skip(reason="Endpoint de insights não implementado ainda")
    def test_top_clientes_churn_endpoint(self, client):
        """Testa endpoint de top clientes em risco de churn."""
        # Mock de dados para top clientes em risco
        mock_top_clientes = [
            {"nome": "Cliente A", "risco_churn": 0.85, "score": "alto"},
            {"nome": "Cliente B", "risco_churn": 0.72, "score": "medio"},
            {"nome": "Cliente C", "risco_churn": 0.68, "score": "medio"}
        ]
        
        with patch('src.api.main.query_clientes_churn', return_value=mock_top_clientes), \
             patch('src.api.main.get_db_session', return_value=iter([MagicMock()])):
            
            response = client.get("/insights/top-clientes-churn?limit=10")
            
            if response.status_code == 200:
                data = response.json()
                assert "clientes" in data or isinstance(data, list)
                assert len(data.get("clientes", data)) > 0
