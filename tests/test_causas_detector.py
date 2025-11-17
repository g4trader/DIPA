"""
Testes unitários para agent/causas_detector.py
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy.orm import Session

from src.agent.causas_detector import detectar_causas_para_mes


@pytest.fixture
def mock_session():
    """Cria uma sessão mockada."""
    return Mock(spec=Session)


@pytest.fixture
def mock_metas_mes():
    """Cria dados mockados de metas por mês."""
    from src.dw.causas import MetaRealizadoMes
    return [
        MetaRealizadoMes(
            mes="2025-08",
            meta_total=1000000.0,
            realizado_total=950000.0,
            gap_total=-50000.0,
            atingimento_medio=95.0
        )
    ]


@pytest.fixture
def mock_vendedores():
    """Cria dados mockados de vendedores."""
    from src.dw.causas import VendedorCausa
    return [
        VendedorCausa(
            vendedor_id=1,
            vendedor_nome="Vendedor A",
            supervisor_id=10,
            supervisor_nome="Supervisor 1",
            rota_id=1,
            rota_nome="Rota A",
            meta_vendedor_mes=100000.0,
            realizado_vendedor_mes=80000.0,
            gap_vendedor=-20000.0,
            atingimento_vendedor=80.0
        )
    ]


@pytest.fixture
def mock_rotas():
    """Cria dados mockados de rotas."""
    from src.dw.causas import RotaCausa
    return [
        RotaCausa(
            rota_id=1,
            rota_nome="Rota A",
            supervisor_id=10,
            supervisor_nome="Supervisor 1",
            meta_rota_mes=100000.0,
            realizado_rota_mes=80000.0,
            gap_rota=-20000.0,
            percent_gap_do_total=40.0
        )
    ]


@patch('src.agent.causas_detector.get_metas_realizado_por_mes')
@patch('src.agent.causas_detector.get_piores_vendedores_no_mes')
@patch('src.agent.causas_detector.get_rotas_com_maior_gap_no_mes')
@patch('src.agent.causas_detector.get_clientes_com_queda_no_mes')
@patch('src.agent.causas_detector.get_skus_com_queda_no_mes')
def test_detectar_causas_para_mes_com_gap(
    mock_get_skus,
    mock_get_clientes,
    mock_get_rotas,
    mock_get_vendedores,
    mock_get_metas,
    mock_session,
    mock_metas_mes,
    mock_vendedores,
    mock_rotas
):
    """Testa detectar_causas_para_mes quando há gap."""
    # Configura mocks
    mock_get_metas.return_value = mock_metas_mes
    mock_get_vendedores.return_value = mock_vendedores
    mock_get_rotas.return_value = mock_rotas
    mock_get_clientes.return_value = []
    mock_get_skus.return_value = []
    
    # Executa função
    resultado = detectar_causas_para_mes(
        session=mock_session,
        ano_mes="2025-08"
    )
    
    # Verifica estrutura
    assert "gap_total" in resultado
    assert "atingimento_medio" in resultado
    assert "causas" in resultado
    assert "resumo_causas" in resultado
    
    # Verifica que gap_total < 0
    assert resultado["gap_total"] < 0
    
    # Verifica que há causas detectadas
    assert len(resultado["causas"]["vendedores"]) > 0 or len(resultado["causas"]["rotas"]) > 0


@patch('src.agent.causas_detector.get_metas_realizado_por_mes')
def test_detectar_causas_para_mes_sem_gap(
    mock_get_metas,
    mock_session
):
    """Testa detectar_causas_para_mes quando não há gap (meta batida)."""
    from src.dw.causas import MetaRealizadoMes
    
    # Mock com meta batida
    mock_get_metas.return_value = [
        MetaRealizadoMes(
            mes="2025-08",
            meta_total=1000000.0,
            realizado_total=1050000.0,
            gap_total=50000.0,  # Gap positivo = meta superada
            atingimento_medio=105.0
        )
    ]
    
    # Executa função
    resultado = detectar_causas_para_mes(
        session=mock_session,
        ano_mes="2025-08"
    )
    
    # Verifica que não há causas negativas
    assert resultado["gap_total"] >= 0
    assert len(resultado["causas"]["vendedores"]) == 0
    assert len(resultado["causas"]["rotas"]) == 0
    assert "Meta foi batida" in resultado["resumo_causas"][0] or "não há causas negativas" in resultado["resumo_causas"][0]


@patch('src.agent.causas_detector.get_metas_realizado_por_mes')
def test_detectar_causas_para_mes_sem_dados(
    mock_get_metas,
    mock_session
):
    """Testa detectar_causas_para_mes quando não há dados."""
    # Mock sem dados
    mock_get_metas.return_value = []
    
    # Executa função
    resultado = detectar_causas_para_mes(
        session=mock_session,
        ano_mes="2025-08"
    )
    
    # Verifica estrutura vazia
    assert resultado["gap_total"] == 0.0
    assert len(resultado["causas"]["vendedores"]) == 0
    assert len(resultado["causas"]["rotas"]) == 0

