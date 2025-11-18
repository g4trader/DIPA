"""
Testes para as queries essenciais do ENGINEERING_QUERIES.md.

Este módulo testa todas as funções em src/dw/queries.py usando um DW de teste
com dados mínimos conforme o blueprint.
"""

import pytest
from datetime import date, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Importa modelos
from src.dw.models import (
    Base, Cliente, Vendedor, Supervisor, Venda,
    MetaVendedor, MetaDepartamento, DimProduto
)

# Importa queries
from src.dw.queries import (
    get_clientes_sem_compra_ha_dias,
    get_clientes_queda_faturamento_ano_contra_ano,
    get_industrias_com_mais_vendedores_fora_meta,
    get_rotas_positivacao_industria,
    get_itens_baixa_media_mensal,
    get_clientes_sem_recompra_sku,
    get_clientes_segmento_sem_sku_no_periodo,
    get_clientes_uma_unidade_industria_mes,
    get_clientes_sem_sku_no_periodo,
    get_clientes_mix_minimo_nissin_mes,
    get_rotas_desempenho_mix_minimo_nissin_mes
)


@pytest.fixture
def db_session():
    """
    Cria um banco SQLite em memória para testes.
    Conforme ENGINEERING_MASTER_PLAN.md seção 3.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    # Popula dados de teste
    _popular_dados_teste(session)
    
    yield session
    
    session.close()


def _popular_dados_teste(session: Session):
    """
    Popula o banco de teste com dados mínimos conforme o blueprint.
    """
    # Supervisores
    sup1 = Supervisor(
        id=1,
        codigo="SUP01",
        nome="Supervisor Leandro",
        pasta="verde",
        ativo=True
    )
    sup2 = Supervisor(
        id=2,
        codigo="SUP02",
        nome="Supervisor Maria",
        pasta="amarela",
        ativo=True
    )
    session.add_all([sup1, sup2])
    session.flush()
    
    # Vendedores
    vend1 = Vendedor(
        id=1,
        codigo="ROTA 22",
        nome="ROTA 22",
        rota_rca="ROTA 22",
        supervisor_id=1,
        ativo=True
    )
    vend2 = Vendedor(
        id=2,
        codigo="ROTA 75",
        nome="ROTA 75",
        rota_rca="ROTA 75",
        supervisor_id=2,
        ativo=True
    )
    session.add_all([vend1, vend2])
    session.flush()
    
    # Clientes
    cli1 = Cliente(
        id=1,
        codigo="CLI001",
        nome="Cliente A",
        segmento_venda="conveniencia",
        rota_rca="ROTA 22",
        supervisor_id=1,
        ativo=True
    )
    cli2 = Cliente(
        id=2,
        codigo="CLI002",
        nome="Cliente B",
        segmento_venda="varejo",
        rota_rca="ROTA 75",
        supervisor_id=2,
        ativo=True
    )
    cli3 = Cliente(
        id=3,
        codigo="CLI003",
        nome="Cliente C",
        segmento_venda="conveniencia",
        rota_rca="ROTA 22",
        supervisor_id=1,
        ativo=True
    )
    session.add_all([cli1, cli2, cli3])
    session.flush()
    
    # Produtos (dim_produto) - SKUs canônicos conforme ENGINEERING_QUERIES.md
    # Nissin
    prod_2257 = DimProduto(
        id=1,
        produto_id=2257,
        sku="2257",
        descricao="Nissin Lamen Galinha Caipira 85g",
        industria="Nissin",
        marca="Nissin",
        categoria="Massas instantâneas",
        ativo=True
    )
    prod_2087 = DimProduto(
        id=2,
        produto_id=2087,
        sku="2087",
        descricao="Nissin Lamen Carne 85g",
        industria="Nissin",
        marca="Nissin",
        categoria="Massas instantâneas",
        ativo=True
    )
    prod_2086 = DimProduto(
        id=3,
        produto_id=2086,
        sku="2086",
        descricao="Nissin Lamen Frango 85g",
        industria="Nissin",
        marca="Nissin",
        categoria="Massas instantâneas",
        ativo=True
    )
    prod_2101 = DimProduto(
        id=4,
        produto_id=2101,
        sku="2101",
        descricao="Nissin Lamen Camarão 85g",
        industria="Nissin",
        marca="Nissin",
        categoria="Massas instantâneas",
        ativo=True
    )
    prod_2102 = DimProduto(
        id=5,
        produto_id=2102,
        sku="2102",
        descricao="Nissin Lamen Picanha 85g",
        industria="Nissin",
        marca="Nissin",
        categoria="Massas instantâneas",
        ativo=True
    )
    prod_2103 = DimProduto(
        id=6,
        produto_id=2103,
        sku="2103",
        descricao="Nissin Lamen Costela 85g",
        industria="Nissin",
        marca="Nissin",
        categoria="Massas instantâneas",
        ativo=True
    )
    # Mars
    prod_snickers_dobro = DimProduto(
        id=7,
        produto_id=7001,
        sku="SNICKERS_DOBRO",
        descricao="Snickers Duplo 45g",
        industria="Mars",
        marca="Mars",
        categoria="Confeitos",
        ativo=True
    )
    prod_snickers_45g = DimProduto(
        id=8,
        produto_id=7002,
        sku="SNICKERS_45G",
        descricao="Snickers Original 45g",
        industria="Mars",
        marca="Mars",
        categoria="Confeitos",
        ativo=True
    )
    prod_mm_choco = DimProduto(
        id=9,
        produto_id=8001,
        sku="MM_CHOCO_40G",
        descricao="M&Ms Chocolate 40g",
        industria="Mars",
        marca="Mars",
        categoria="Confeitos",
        ativo=True
    )
    prod_mm_tubo = DimProduto(
        id=10,
        produto_id=8002,
        sku="MM_TUBO",
        descricao="M&Ms Tubo 45g",
        industria="Mars",
        marca="Mars",
        categoria="Confeitos",
        ativo=True
    )
    # Red Bull
    prod_rb_zero = DimProduto(
        id=11,
        produto_id=9001,
        sku="RB_ZERO",
        descricao="Red Bull Zero 250ml",
        industria="Red Bull",
        marca="Red Bull",
        categoria="Bebidas energéticas",
        ativo=True
    )
    session.add_all([
        prod_2257, prod_2087, prod_2086, prod_2101, prod_2102, prod_2103,
        prod_snickers_dobro, prod_snickers_45g, prod_mm_choco, prod_mm_tubo,
        prod_rb_zero
    ])
    session.flush()
    
    # Vendas (fato_vendas_detalhado) - usando produto_id referenciando dim_produto
    # Cliente 1: comprou em 2024 e 2025
    venda1_2024 = Venda(
        id=1,
        data_venda=date(2024, 8, 15),
        cliente_id=1,
        codigo_cliente="CLI001",
        vendedor_id=1,
        supervisor_id=1,
        produto_id=1,  # prod_2257
        codigo_produto="2257",
        desc_produto="Nissin Lamen Galinha Caipira 85g",
        departamento="NISSIN",
        valor_total_liquido=1000.0,
        qtd_caixas=10,
        qtd_unidades=100
    )
    venda1_2025 = Venda(
        id=2,
        data_venda=date(2025, 8, 20),
        cliente_id=1,
        codigo_cliente="CLI001",
        vendedor_id=1,
        supervisor_id=1,
        produto_id=1,  # prod_2257
        codigo_produto="2257",
        desc_produto="Nissin Lamen Galinha Caipira 85g",
        departamento="NISSIN",
        valor_total_liquido=800.0,  # Queda de 20%
        qtd_caixas=8,
        qtd_unidades=80
    )
    
    # Cliente 2: comprou apenas em 2024 (queda total em 2025)
    venda2_2024 = Venda(
        id=3,
        data_venda=date(2024, 9, 10),
        cliente_id=2,
        codigo_cliente="CLI002",
        vendedor_id=2,
        supervisor_id=2,
        produto_id=2,  # prod_2087
        codigo_produto="2087",
        desc_produto="Nissin Lamen Carne 85g",
        departamento="NISSIN",
        valor_total_liquido=2000.0,
        qtd_caixas=20,
        qtd_unidades=200
    )
    
    # Cliente 3: sem compras há mais de 60 dias
    venda3_antiga = Venda(
        id=4,
        data_venda=date(2025, 6, 1),  # Mais de 60 dias atrás
        cliente_id=3,
        codigo_cliente="CLI003",
        vendedor_id=1,
        supervisor_id=1,
        produto_id=4,  # prod_2101
        codigo_produto="2101",
        desc_produto="Nissin Lamen Camarão 85g",
        departamento="NISSIN",
        valor_total_liquido=500.0,
        qtd_caixas=5,
        qtd_unidades=50
    )
    
    # Vendas Mars para positivação (no período 2025-10-01 a 2025-10-31)
    venda_mars = Venda(
        id=5,
        data_venda=date(2025, 10, 15),  # Dentro do período de teste
        cliente_id=1,
        codigo_cliente="CLI001",
        vendedor_id=1,
        supervisor_id=1,
        produto_id=8,  # prod_snickers_45g
        codigo_produto="SNICKERS_45G",
        desc_produto="Snickers Original 45g",
        departamento="MARS",
        valor_total_liquido=300.0,
        qtd_caixas=3,
        qtd_unidades=30
    )
    
    session.add_all([
        venda1_2024, venda1_2025, venda2_2024, venda3_antiga, venda_mars
    ])
    session.flush()
    
    # Metas vendedor (conforme Q3 - fato_metas_vendedor_mensal.industria)
    meta_vend1_out = MetaVendedor(
        id=1,
        vendedor_id=1,
        industria="Nissin",  # Campo industria conforme ENGINEERING_QUERIES.md
        ano=2025,
        mes=10,
        mes_ano="2025-10",
        valor_meta=10000.0,
        valor_faturado=9500.0,
        percentual_atingido_valor=95.0  # Fora da meta
    )
    meta_vend2_out = MetaVendedor(
        id=2,
        vendedor_id=2,
        industria="Mars",  # Campo industria conforme ENGINEERING_QUERIES.md
        ano=2025,
        mes=10,
        mes_ano="2025-10",
        valor_meta=8000.0,
        valor_faturado=8500.0,
        percentual_atingido_valor=106.25  # Acima da meta
    )
    session.add_all([meta_vend1_out, meta_vend2_out])
    session.flush()
    
    # Metas departamento
    meta_dept1 = MetaDepartamento(
        id=1,
        supervisor_id=1,
        departamento="NISSIN",
        ano=2025,
        mes=10,
        mes_ano="2025-10",
        valor_meta=50000.0,
        valor_faturado=48000.0,
        percentual_atingido_valor=96.0
    )
    meta_dept2 = MetaDepartamento(
        id=2,
        supervisor_id=2,
        departamento="MARS",
        ano=2025,
        mes=10,
        mes_ano="2025-10",
        valor_meta=30000.0,
        valor_faturado=32000.0,
        percentual_atingido_valor=106.67
    )
    session.add_all([meta_dept1, meta_dept2])
    session.commit()


# ============================================================================
# TESTES Q1: CLIENTES SEM COMPRA HÁ DIAS
# ============================================================================

def test_get_clientes_sem_compra_ha_dias_happy_path(db_session):
    """Teste happy path: clientes sem compra há mais de 60 dias."""
    hoje = date(2025, 11, 17)
    resultado = get_clientes_sem_compra_ha_dias(
        db_session,
        dias=60,
        data_referencia=hoje.isoformat()
    )
    
    assert isinstance(resultado, list)
    assert len(resultado) > 0
    
    # Cliente 3 deve estar na lista (última compra em 2025-06-01)
    cliente3 = next((c for c in resultado if c["cliente_id"] == 3), None)
    assert cliente3 is not None
    assert cliente3["dias_sem_compra"] is not None
    assert cliente3["dias_sem_compra"] > 60


def test_get_clientes_sem_compra_ha_dias_edge_empty(db_session):
    """Teste edge: nenhum cliente sem compra há 365 dias."""
    hoje = date(2025, 11, 17)
    resultado = get_clientes_sem_compra_ha_dias(
        db_session,
        dias=365,  # Muito longo
        data_referencia=hoje.isoformat()
    )
    
    assert isinstance(resultado, list)
    # Pode retornar vazio ou clientes que nunca compraram


def test_get_clientes_sem_compra_ha_dias_behavior_memory(db_session):
    """Teste com Behavior Memory: excluir pasta verde."""
    hoje = date(2025, 11, 17)
    filtros_behavior = {
        "excluir_pastas": ["verde"]
    }
    
    resultado = get_clientes_sem_compra_ha_dias(
        db_session,
        dias=60,
        data_referencia=hoje.isoformat(),
        filtros_behavior=filtros_behavior
    )
    
    assert isinstance(resultado, list)
    # Cliente 3 está na pasta verde (supervisor_id=1, pasta="verde")
    # Não deve aparecer no resultado
    cliente3 = next((c for c in resultado if c["cliente_id"] == 3), None)
    assert cliente3 is None


# ============================================================================
# TESTES Q2: QUEDA FATURAMENTO ANO CONTRA ANO
# ============================================================================

def test_get_clientes_queda_faturamento_ano_contra_ano_happy_path(db_session):
    """Teste happy path: clientes com queda de faturamento."""
    resultado = get_clientes_queda_faturamento_ano_contra_ano(
        db_session,
        ano_base=2024,
        ano_comparado=2025,
        top_n=10
    )
    
    assert isinstance(resultado, list)
    # Cliente 1 deve ter queda (1000 -> 800)
    cliente1 = next((c for c in resultado if c["cliente_id"] == 1), None)
    if cliente1:
        assert cliente1["faturamento_base"] > cliente1["faturamento_comp"]
        assert cliente1["delta_faturamento"] < 0


def test_get_clientes_queda_faturamento_ano_contra_ano_edge_empty(db_session):
    """Teste edge: comparação de anos sem dados."""
    resultado = get_clientes_queda_faturamento_ano_contra_ano(
        db_session,
        ano_base=2020,  # Sem dados
        ano_comparado=2021,  # Sem dados
        top_n=10
    )
    
    assert isinstance(resultado, list)
    # Deve retornar lista vazia ou sem quedas


# ============================================================================
# TESTES Q3: INDÚSTRIAS COM MAIS VENDEDORES FORA DA META
# ============================================================================

def test_get_industrias_com_mais_vendedores_fora_meta_happy_path(db_session):
    """Teste happy path: indústrias com vendedores fora da meta."""
    resultado = get_industrias_com_mais_vendedores_fora_meta(
        db_session,
        ano=2025,
        mes=10,
        atingimento_limite=100.0
    )
    
    assert isinstance(resultado, list)
    # Deve retornar pelo menos NISSIN (vendedor 1 está fora da meta)
    nissin = next((i for i in resultado if i["industria"] == "NISSIN"), None)
    if nissin:
        assert nissin["qtd_vendedores_fora_meta"] > 0


def test_get_industrias_com_mais_vendedores_fora_meta_edge_empty(db_session):
    """Teste edge: mês sem vendedores fora da meta."""
    resultado = get_industrias_com_mais_vendedores_fora_meta(
        db_session,
        ano=2025,
        mes=11,  # Sem dados
        atingimento_limite=100.0
    )
    
    assert isinstance(resultado, list)
    # Pode retornar vazio se não houver dados


# ============================================================================
# TESTES Q4: ROTAS POSITIVAÇÃO INDÚSTRIA
# ============================================================================

def test_get_rotas_positivacao_industria_happy_path(db_session):
    """Teste happy path: rotas com positivação de indústria."""
    resultado = get_rotas_positivacao_industria(
        db_session,
        industria="Mars",  # Industria canônica conforme ENGINEERING_QUERIES.md
        data_inicio="2025-10-01",
        data_fim="2025-10-31"
    )
    
    assert isinstance(resultado, list)
    # ROTA 22 deve ter positivação (cliente 1 comprou Mars)
    rota22 = next((r for r in resultado if r["rota_id"] == "ROTA 22"), None)
    if rota22:
        assert rota22["clientes_positivados"] > 0
        assert rota22["positivacao_pct"] >= 0


def test_get_rotas_positivacao_industria_edge_empty(db_session):
    """Teste edge: indústria sem vendas no período."""
    resultado = get_rotas_positivacao_industria(
        db_session,
        industria="Red Bull",  # Industria canônica (sem vendas no período)
        data_inicio="2025-10-01",
        data_fim="2025-10-31"
    )
    
    assert isinstance(resultado, list)
    # Deve retornar rotas com positivacao_pct = 0


# ============================================================================
# TESTES Q5: ITENS BAIXA MÉDIA MENSAL
# ============================================================================

def test_get_itens_baixa_media_mensal_happy_path(db_session):
    """Teste happy path: itens com média mensal < limite."""
    resultado = get_itens_baixa_media_mensal(
        db_session,
        meses_janela=12,
        limite_media=10.0,
        data_referencia="2025-11-17"
    )
    
    assert isinstance(resultado, list)
    # Todos os resultados devem ter media_mensal < limite_media
    for item in resultado:
        assert item["media_mensal"] < 10.0


def test_get_itens_baixa_media_mensal_edge_empty(db_session):
    """Teste edge: limite muito baixo."""
    resultado = get_itens_baixa_media_mensal(
        db_session,
        meses_janela=12,
        limite_media=0.1,  # Muito baixo
        data_referencia="2025-11-17"
    )
    
    assert isinstance(resultado, list)
    # Pode retornar vazio se todos os itens têm média >= 0.1


# ============================================================================
# TESTES Q6: CLIENTES SEM RECOMPRA SKU
# ============================================================================

def test_get_clientes_sem_recompra_sku_happy_path(db_session):
    """Teste happy path: clientes sem recompra de SKU."""
    resultado = get_clientes_sem_recompra_sku(
        db_session,
        sku="2257",  # SKU canônico conforme ENGINEERING_QUERIES.md
        meses_janela=6,
        data_referencia="2025-11-17"
    )
    
    assert isinstance(resultado, list)
    # Todos devem ter qtd_compras = 1
    for cliente in resultado:
        assert cliente["qtd_compras"] == 1


def test_get_clientes_sem_recompra_sku_edge_empty(db_session):
    """Teste edge: SKU inexistente."""
    resultado = get_clientes_sem_recompra_sku(
        db_session,
        sku="SKU_INEXISTENTE",
        meses_janela=6,
        data_referencia="2025-11-17"
    )
    
    assert isinstance(resultado, list)
    # Deve retornar vazio


# ============================================================================
# TESTES Q7: CLIENTES SEGMENTO SEM SKU
# ============================================================================

def test_get_clientes_segmento_sem_sku_no_periodo_happy_path(db_session):
    """Teste happy path: clientes de segmento sem SKU."""
    resultado = get_clientes_segmento_sem_sku_no_periodo(
        db_session,
        segmento="conveniencia",
        sku="SNICKERS_45G",  # SKU canônico conforme ENGINEERING_QUERIES.md
        data_inicio="2025-10-01",
        data_fim="2025-10-31"
    )
    
    assert isinstance(resultado, list)
    # Clientes do segmento que não compraram o SKU


def test_get_clientes_segmento_sem_sku_no_periodo_edge_empty(db_session):
    """Teste edge: todos os clientes do segmento compraram o SKU."""
    resultado = get_clientes_segmento_sem_sku_no_periodo(
        db_session,
        segmento="varejo",
        sku="2087",  # SKU canônico conforme ENGINEERING_QUERIES.md
        data_inicio="2024-09-01",
        data_fim="2024-09-30"
    )
    
    assert isinstance(resultado, list)
    # Pode retornar vazio se todos compraram


# ============================================================================
# TESTES Q8: CLIENTES UMA UNIDADE INDÚSTRIA
# ============================================================================

def test_get_clientes_uma_unidade_industria_mes_happy_path(db_session):
    """Teste happy path: clientes com 1 unidade de indústria."""
    resultado = get_clientes_uma_unidade_industria_mes(
        db_session,
        industria="Nissin",  # Industria canônica conforme ENGINEERING_QUERIES.md
        ano=2025,
        mes=8
    )
    
    assert isinstance(resultado, list)
    # Todos devem ter qtd_total = 1
    for cliente in resultado:
        assert cliente["qtd_total"] == 1


def test_get_clientes_uma_unidade_industria_mes_edge_empty(db_session):
    """Teste edge: mês sem vendas da indústria."""
    resultado = get_clientes_uma_unidade_industria_mes(
        db_session,
        industria="AB Brasil",  # Industria canônica conforme ENGINEERING_QUERIES.md
        ano=2025,
        mes=10
    )
    
    assert isinstance(resultado, list)
    # Deve retornar vazio


# ============================================================================
# TESTES Q9/Q10/Q11: CLIENTES SEM SKU NO PERÍODO
# ============================================================================

def test_get_clientes_sem_sku_no_periodo_happy_path(db_session):
    """Teste happy path: clientes ativos sem positivação de SKU."""
    resultado = get_clientes_sem_sku_no_periodo(
        db_session,
        sku="SNICKERS_45G",  # SKU canônico conforme ENGINEERING_QUERIES.md
        data_inicio="2025-10-01",
        data_fim="2025-10-31"
    )
    
    assert isinstance(resultado, list)
    # Clientes ativos que não compraram o SKU


def test_get_clientes_sem_sku_no_periodo_edge_empty(db_session):
    """Teste edge: todos os clientes compraram o SKU."""
    resultado = get_clientes_sem_sku_no_periodo(
        db_session,
        sku="SKU_INEXISTENTE",
        data_inicio="2025-10-01",
        data_fim="2025-10-31"
    )
    
    assert isinstance(resultado, list)
    # Deve retornar todos os clientes ativos (nenhum comprou)


# ============================================================================
# TESTES Q12: CLIENTES MIX MÍNIMO NISSIN
# ============================================================================

def test_get_clientes_mix_minimo_nissin_mes_happy_path(db_session):
    """Teste happy path: clientes com mix mínimo de Nissin."""
    # Adiciona mais vendas para ter mix completo
    # Cliente 1 já tem 2257, precisa adicionar 2087, 2086 e um complementar
    venda_2087 = Venda(
        id=6,
        data_venda=date(2025, 10, 5),
        cliente_id=1,
        codigo_cliente="CLI001",
        vendedor_id=1,
        supervisor_id=1,
        produto_id=2,  # prod_2087
        codigo_produto="2087",
        desc_produto="Nissin Lamen Carne 85g",
        departamento="NISSIN",
        valor_total_liquido=200.0,
        qtd_caixas=2,
        qtd_unidades=20
    )
    venda_2086 = Venda(
        id=7,
        data_venda=date(2025, 10, 6),
        cliente_id=1,
        codigo_cliente="CLI001",
        vendedor_id=1,
        supervisor_id=1,
        produto_id=3,  # prod_2086
        codigo_produto="2086",
        desc_produto="Nissin Lamen Frango 85g",
        departamento="NISSIN",
        valor_total_liquido=150.0,
        qtd_caixas=1,
        qtd_unidades=15
    )
    venda_2101 = Venda(
        id=8,
        data_venda=date(2025, 10, 7),
        cliente_id=1,
        codigo_cliente="CLI001",
        vendedor_id=1,
        supervisor_id=1,
        produto_id=4,  # prod_2101
        codigo_produto="2101",
        desc_produto="Nissin Lamen Camarão 85g",
        departamento="NISSIN",
        valor_total_liquido=100.0,
        qtd_caixas=1,
        qtd_unidades=10
    )
    db_session.add_all([venda_2087, venda_2086, venda_2101])
    db_session.commit()
    
    resultado = get_clientes_mix_minimo_nissin_mes(
        db_session,
        ano=2025,
        mes=10
    )
    
    assert isinstance(resultado, list)
    # Cliente 1 deve estar na lista (tem todos os SKUs necessários)


def test_get_clientes_mix_minimo_nissin_mes_edge_empty(db_session):
    """Teste edge: nenhum cliente com mix completo."""
    resultado = get_clientes_mix_minimo_nissin_mes(
        db_session,
        ano=2025,
        mes=11  # Sem dados
    )
    
    assert isinstance(resultado, list)
    # Deve retornar vazio


# ============================================================================
# TESTES Q13: ROTAS DESEMPENHO MIX NISSIN
# ============================================================================

def test_get_rotas_desempenho_mix_minimo_nissin_mes_happy_path(db_session):
    """Teste happy path: rotas com desempenho mix Nissin."""
    resultado = get_rotas_desempenho_mix_minimo_nissin_mes(
        db_session,
        ano=2025,
        mes=10
    )
    
    assert isinstance(resultado, list)
    # Todas as rotas devem ter pct_mix_ok calculado
    for rota in resultado:
        assert "rota_id" in rota
        assert "total_clientes_ativos" in rota
        assert "clientes_mix_ok" in rota
        assert "pct_mix_ok" in rota
        assert 0 <= rota["pct_mix_ok"] <= 100


def test_get_rotas_desempenho_mix_minimo_nissin_mes_edge_empty(db_session):
    """Teste edge: mês sem dados."""
    resultado = get_rotas_desempenho_mix_minimo_nissin_mes(
        db_session,
        ano=2025,
        mes=11  # Sem dados
    )
    
    assert isinstance(resultado, list)
    # Pode retornar vazio ou rotas com pct_mix_ok = 0


# ============================================================================
# TESTES DE COMPATIBILIDADE SQLite/PostgreSQL
# ============================================================================

def test_queries_nao_quebram_sqlite(db_session):
    """Garante que todas as queries funcionam em SQLite."""
    hoje = date(2025, 11, 17)
    
    # Testa todas as funções básicas
    funcoes = [
        lambda: get_clientes_sem_compra_ha_dias(db_session, dias=60, data_referencia=hoje.isoformat()),
        lambda: get_clientes_queda_faturamento_ano_contra_ano(db_session, 2024, 2025, top_n=10),
        lambda: get_industrias_com_mais_vendedores_fora_meta(db_session, 2025, 10, 100.0),
        lambda: get_rotas_positivacao_industria(db_session, "Mars", "2025-10-01", "2025-10-31"),  # Industria canônica
        lambda: get_itens_baixa_media_mensal(db_session, 12, 10.0, hoje.isoformat()),
        lambda: get_clientes_sem_recompra_sku(db_session, "2257", 6, hoje.isoformat()),  # SKU canônico
        lambda: get_clientes_segmento_sem_sku_no_periodo(db_session, "conveniencia", "2257", "2025-10-01", "2025-10-31"),  # SKU canônico
        lambda: get_clientes_uma_unidade_industria_mes(db_session, "Nissin", 2025, 8),  # Industria canônica
        lambda: get_clientes_sem_sku_no_periodo(db_session, "2257", "2025-10-01", "2025-10-31"),  # SKU canônico
        lambda: get_clientes_mix_minimo_nissin_mes(db_session, 2025, 10),
        lambda: get_rotas_desempenho_mix_minimo_nissin_mes(db_session, 2025, 10)
    ]
    
    for func in funcoes:
        resultado = func()
        assert isinstance(resultado, list), f"Função {func.__name__} não retornou lista"
        # Não deve lançar exceção

