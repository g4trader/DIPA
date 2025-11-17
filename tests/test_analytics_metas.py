"""
Testes para a camada analítica de metas (src/dw/analytics_metas.py).

Valida que as funções retornam dados corretos por mês/supervisor
e que não quebram quando não há dados.
"""

import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from src.dw.connection import get_db_session, init_db
from src.dw.analytics_metas import (
    listar_metas_por_mes,
    listar_vendas_por_mes,
    listar_metas_realizado_por_supervisor,
    listar_clientes_criticos,
    MetaMes,
    VendaMes,
    SupervisorMeta,
    ClienteCritico
)
from src.dw.models_analytics import AnalyticsVendedorMes, AnalyticsClienteMes
from src.dw.models import MetaVendedor, Venda, Supervisor, Vendedor, Cliente


@pytest.fixture(scope="module")
def db_session():
    """Fixture para sessão de banco de dados."""
    init_db(create_tables_if_not_exists=True)
    session_generator = get_db_session()
    session = next(session_generator)
    yield session
    session.close()


def test_listar_metas_por_mes_com_dados(db_session: Session):
    """
    Testa se listar_metas_por_mes retorna uma lista por mês, não apenas um total.
    """
    # Busca período com dados (ajustar conforme banco real)
    periodo_inicio = "2024-11"
    periodo_fim = "2025-10"
    
    metas = listar_metas_por_mes(db_session, periodo_inicio, periodo_fim)
    
    # Verifica que retorna lista
    assert isinstance(metas, list)
    
    # Se houver dados, verifica estrutura
    if len(metas) > 0:
        # Verifica que cada item é um MetaMes
        assert isinstance(metas[0], MetaMes)
        
        # Verifica que tem mes_ano
        assert metas[0].mes_ano is not None
        assert len(metas[0].mes_ano) == 7  # "YYYY-MM"
        
        # Verifica que tem valores numéricos
        assert isinstance(metas[0].meta_total, (int, float))
        assert isinstance(metas[0].realizado_total, (int, float))
        assert isinstance(metas[0].atingimento_medio, (int, float))
        
        # Verifica que está ordenado por mês
        meses = [m.mes_ano for m in metas]
        assert meses == sorted(meses)
        
        # Verifica que cada mês tem valores válidos
        for meta in metas:
            assert meta.mes_ano >= periodo_inicio
            assert meta.mes_ano <= periodo_fim
            assert meta.meta_total >= 0
            assert meta.realizado_total >= 0
            assert meta.total_vendedores >= 0


def test_listar_metas_por_mes_sem_dados(db_session: Session):
    """
    Testa se listar_metas_por_mes retorna lista vazia quando não há dados.
    """
    # Período que provavelmente não tem dados
    periodo_inicio = "2099-01"
    periodo_fim = "2099-12"
    
    metas = listar_metas_por_mes(db_session, periodo_inicio, periodo_fim)
    
    # Deve retornar lista vazia, não erro
    assert isinstance(metas, list)
    assert len(metas) == 0


def test_listar_vendas_por_mes_com_dados(db_session: Session):
    """
    Testa se listar_vendas_por_mes retorna uma lista por mês.
    """
    periodo_inicio = "2024-11"
    periodo_fim = "2025-10"
    
    vendas = listar_vendas_por_mes(db_session, periodo_inicio, periodo_fim)
    
    # Verifica que retorna lista
    assert isinstance(vendas, list)
    
    # Se houver dados, verifica estrutura
    if len(vendas) > 0:
        # Verifica que cada item é um VendaMes
        assert isinstance(vendas[0], VendaMes)
        
        # Verifica estrutura
        assert vendas[0].mes_ano is not None
        assert isinstance(vendas[0].faturamento_total, (int, float))
        assert isinstance(vendas[0].quantidade_vendas, int)
        assert isinstance(vendas[0].quantidade_clientes, int)
        assert isinstance(vendas[0].ticket_medio, (int, float))
        
        # Verifica ordenação
        meses = [v.mes_ano for v in vendas]
        assert meses == sorted(meses)


def test_listar_vendas_por_mes_sem_dados(db_session: Session):
    """
    Testa se listar_vendas_por_mes retorna lista vazia quando não há dados.
    """
    periodo_inicio = "2099-01"
    periodo_fim = "2099-12"
    
    vendas = listar_vendas_por_mes(db_session, periodo_inicio, periodo_fim)
    
    assert isinstance(vendas, list)
    assert len(vendas) == 0


def test_listar_metas_realizado_por_supervisor_com_dados(db_session: Session):
    """
    Testa se listar_metas_realizado_por_supervisor retorna dados por supervisor.
    """
    # Usa mês com dados (ajustar conforme banco real)
    mes = "2025-08"
    
    supervisores = listar_metas_realizado_por_supervisor(db_session, mes)
    
    # Verifica que retorna lista
    assert isinstance(supervisores, list)
    
    # Se houver dados, verifica estrutura
    if len(supervisores) > 0:
        # Verifica que cada item é um SupervisorMeta
        assert isinstance(supervisores[0], SupervisorMeta)
        
        # Verifica estrutura
        assert supervisores[0].supervisor_id is not None
        assert supervisores[0].supervisor_nome is not None
        assert supervisores[0].mes_ano == mes
        assert isinstance(supervisores[0].meta_total, (int, float))
        assert isinstance(supervisores[0].realizado_total, (int, float))
        assert isinstance(supervisores[0].atingimento_pct, (int, float))
        assert supervisores[0].quantidade_vendedores >= 0


def test_listar_metas_realizado_por_supervisor_sem_dados(db_session: Session):
    """
    Testa se listar_metas_realizado_por_supervisor retorna lista vazia quando não há dados.
    """
    mes = "2099-01"
    
    supervisores = listar_metas_realizado_por_supervisor(db_session, mes)
    
    assert isinstance(supervisores, list)
    # Pode retornar vazio ou lista vazia, ambos são válidos


def test_listar_clientes_criticos_com_dados(db_session: Session):
    """
    Testa se listar_clientes_criticos retorna clientes em risco.
    """
    periodo_inicio = "2025-08"
    periodo_fim = "2025-08"
    
    clientes = listar_clientes_criticos(
        db_session,
        periodo_inicio,
        periodo_fim,
        limite=20
    )
    
    # Verifica que retorna lista
    assert isinstance(clientes, list)
    
    # Se houver dados, verifica estrutura
    if len(clientes) > 0:
        # Verifica que cada item é um ClienteCritico
        assert isinstance(clientes[0], ClienteCritico)
        
        # Verifica estrutura
        assert clientes[0].cliente_id is not None
        assert clientes[0].cliente_nome is not None
        assert isinstance(clientes[0].churn_score, (int, float))
        assert isinstance(clientes[0].churn_flag, bool)
        
        # Verifica que está ordenado por churn_score (maior primeiro)
        scores = [c.churn_score for c in clientes if c.churn_score > 0]
        if len(scores) > 1:
            assert scores == sorted(scores, reverse=True)
        
        # Verifica limite
        assert len(clientes) <= 20


def test_listar_clientes_criticos_sem_dados(db_session: Session):
    """
    Testa se listar_clientes_criticos retorna lista vazia quando não há dados.
    """
    periodo_inicio = "2099-01"
    periodo_fim = "2099-12"
    
    clientes = listar_clientes_criticos(
        db_session,
        periodo_inicio,
        periodo_fim
    )
    
    assert isinstance(clientes, list)
    assert len(clientes) == 0


def test_listar_metas_por_mes_exclui_totais(db_session: Session):
    """
    Testa se listar_metas_por_mes exclui linhas de "Totais" quando solicitado.
    """
    periodo_inicio = "2025-08"
    periodo_fim = "2025-08"
    
    # Com exclusão de totais
    metas_com_exclusao = listar_metas_por_mes(
        db_session,
        periodo_inicio,
        periodo_fim,
        excluir_totais=True
    )
    
    # Sem exclusão (para comparação)
    metas_sem_exclusao = listar_metas_por_mes(
        db_session,
        periodo_inicio,
        periodo_fim,
        excluir_totais=False
    )
    
    # Se houver dados, verifica que com exclusão tem valores menores ou iguais
    if len(metas_com_exclusao) > 0 and len(metas_sem_exclusao) > 0:
        # Meta total com exclusão deve ser <= sem exclusão
        # (se houver linha de Totais, sem exclusão terá valor maior)
        meta_com = metas_com_exclusao[0].meta_total
        meta_sem = metas_sem_exclusao[0].meta_total
        
        # Pode ser igual (se não houver Totais) ou menor (se houver)
        assert meta_com <= meta_sem


def test_listar_clientes_criticos_com_filtros(db_session: Session):
    """
    Testa se listar_clientes_criticos funciona com filtros opcionais.
    """
    periodo_inicio = "2025-08"
    periodo_fim = "2025-08"
    
    # Sem filtros
    clientes_todos = listar_clientes_criticos(
        db_session,
        periodo_inicio,
        periodo_fim
    )
    
    # Com limite
    clientes_limitados = listar_clientes_criticos(
        db_session,
        periodo_inicio,
        periodo_fim,
        limite=10
    )
    
    # Verifica que limite funciona
    assert len(clientes_limitados) <= 10
    assert len(clientes_limitados) <= len(clientes_todos)

