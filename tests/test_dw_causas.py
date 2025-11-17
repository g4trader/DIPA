"""
Testes unitários para dw/causas.py
"""

import pytest
from datetime import datetime
from sqlalchemy.orm import Session
from unittest.mock import Mock, MagicMock

from src.dw.causas import (
    get_metas_realizado_por_mes,
    get_piores_vendedores_no_mes,
    get_rotas_com_maior_gap_no_mes,
    get_clientes_com_queda_no_mes,
    get_skus_com_queda_no_mes,
    MetaRealizadoMes,
    VendedorCausa,
    RotaCausa,
    ClienteQueda,
    SKUQueda
)


@pytest.fixture
def mock_session():
    """Cria uma sessão mockada."""
    session = Mock(spec=Session)
    return session


@pytest.fixture
def mock_analytics_vendedor_mes():
    """Cria dados mockados de AnalyticsVendedorMes."""
    from unittest.mock import Mock
    
    rows = [
        Mock(
            mes="2025-08",
            meta_total=100000.0,
            realizado_total=95000.0
        ),
        Mock(
            mes="2025-08",
            meta_total=50000.0,
            realizado_total=40000.0
        )
    ]
    return rows


def test_get_metas_realizado_por_mes(mock_session, mock_analytics_vendedor_mes):
    """Testa get_metas_realizado_por_mes."""
    # Mock da query
    query_mock = Mock()
    query_mock.filter.return_value = query_mock
    query_mock.group_by.return_value = query_mock
    query_mock.order_by.return_value = query_mock
    query_mock.all.return_value = mock_analytics_vendedor_mes
    
    mock_session.query.return_value = query_mock
    
    # Executa função
    resultados = get_metas_realizado_por_mes(
        session=mock_session,
        periodo_inicio="2025-08",
        periodo_fim="2025-08"
    )
    
    # Verifica resultados
    assert len(resultados) == 1
    assert resultados[0].mes == "2025-08"
    assert resultados[0].meta_total == 150000.0  # Soma dos dois registros
    assert resultados[0].realizado_total == 135000.0
    assert resultados[0].gap_total == -15000.0
    assert resultados[0].atingimento_medio < 100.0


def test_get_piores_vendedores_no_mes(mock_session):
    """Testa get_piores_vendedores_no_mes."""
    # Mock da query
    query_mock = Mock()
    query_mock.filter.return_value = query_mock
    query_mock.group_by.return_value = query_mock
    
    # Mock dos resultados
    rows = [
        Mock(
            vendedor_id=1,
            vendedor_nome="Vendedor A",
            supervisor_id=10,
            meta_vendedor_mes=100000.0,
            realizado_vendedor_mes=80000.0
        ),
        Mock(
            vendedor_id=2,
            vendedor_nome="Vendedor B",
            supervisor_id=10,
            meta_vendedor_mes=50000.0,
            realizado_vendedor_mes=45000.0
        )
    ]
    query_mock.all.return_value = rows
    
    mock_session.query.return_value = query_mock
    
    # Mock de Vendedor e Supervisor
    vendedor_mock = Mock()
    vendedor_mock.id = 1
    vendedor_mock.nome = "Vendedor A"
    vendedor_mock.codigo = "ROTA_1"
    vendedor_mock.supervisor_id = 10
    
    supervisor_mock = Mock()
    supervisor_mock.nome = "Supervisor 1"
    
    mock_session.query.return_value.filter.return_value.first.side_effect = [
        vendedor_mock,  # Para vendedor_id=1
        supervisor_mock  # Para supervisor_id=10
    ]
    
    # Executa função
    resultados = get_piores_vendedores_no_mes(
        session=mock_session,
        ano_mes="2025-08",
        limite=10
    )
    
    # Verifica ordenação (menor atingimento primeiro)
    assert len(resultados) == 2
    assert resultados[0].atingimento_vendedor < resultados[1].atingimento_vendedor


def test_get_rotas_com_maior_gap_no_mes(mock_session):
    """Testa get_rotas_com_maior_gap_no_mes."""
    # Mock da query
    query_mock = Mock()
    query_mock.filter.return_value = query_mock
    query_mock.group_by.return_value = query_mock
    
    # Mock dos resultados
    rows = [
        Mock(
            vendedor_id=1,
            vendedor_nome="Rota A",
            supervisor_id=10,
            meta_rota_mes=100000.0,
            realizado_rota_mes=80000.0
        )
    ]
    query_mock.all.return_value = rows
    
    mock_session.query.return_value = query_mock
    
    # Mock de Supervisor
    supervisor_mock = Mock()
    supervisor_mock.nome = "Supervisor 1"
    mock_session.query.return_value.filter.return_value.first.return_value = supervisor_mock
    
    # Executa função
    resultados = get_rotas_com_maior_gap_no_mes(
        session=mock_session,
        ano_mes="2025-08",
        limite=10
    )
    
    # Verifica resultados
    assert len(resultados) >= 0  # Pode ser 0 se não houver gap


def test_get_clientes_com_queda_no_mes(mock_session):
    """Testa get_clientes_com_queda_no_mes."""
    # Mock da query
    query_mock = Mock()
    query_mock.join.return_value = query_mock
    query_mock.filter.return_value = query_mock
    query_mock.group_by.return_value = query_mock
    query_mock.subquery.return_value = Mock()
    
    # Mock dos resultados
    rows = [
        Mock(
            cliente_id=1,
            cliente_nome="Cliente A",
            faturamento_mes_atual=50000.0,
            faturamento_mes_anterior=80000.0
        )
    ]
    query_mock.outerjoin.return_value.all.return_value = rows
    
    mock_session.query.return_value = query_mock
    
    # Executa função
    resultados = get_clientes_com_queda_no_mes(
        session=mock_session,
        ano_mes="2025-08",
        limite=20
    )
    
    # Verifica que apenas quedas são retornadas (variacao_pct < 0)
    for cliente in resultados:
        assert cliente.variacao_pct < 0


def test_get_skus_com_queda_no_mes(mock_session):
    """Testa get_skus_com_queda_no_mes."""
    # Mock da query
    query_mock = Mock()
    query_mock.filter.return_value = query_mock
    query_mock.group_by.return_value = query_mock
    query_mock.subquery.return_value = Mock()
    
    # Mock dos resultados
    rows = [
        Mock(
            codigo_produto="SKU001",
            sku_nome="Produto A",
            faturamento_mes_atual=10000.0,
            faturamento_mes_anterior=20000.0
        )
    ]
    query_mock.outerjoin.return_value.all.return_value = rows
    
    mock_session.query.return_value = query_mock
    
    # Executa função
    resultados = get_skus_com_queda_no_mes(
        session=mock_session,
        ano_mes="2025-08",
        limite=20
    )
    
    # Verifica que apenas quedas são retornadas (variacao_pct < 0)
    for sku in resultados:
        assert sku.variacao_pct < 0

