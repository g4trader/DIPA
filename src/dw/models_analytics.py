"""
Modelos SQLAlchemy para tabelas de Analytics.

Este módulo define tabelas agregadas pré-calculadas para acelerar consultas
e reduzir a necessidade de queries pesadas em tempo real.
"""

from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, Boolean, 
    ForeignKey, Text, Index, JSON, Numeric, UniqueConstraint
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from src.dw.connection import Base


class AnalyticsVendedorMes(Base):
    """
    Analytics agregado por Vendedor e Mês.
    
    Tabela pré-calculada com métricas mensais por vendedor,
    incluindo metas, realizados, atingimento, rankings e indicadores de churn.
    """
    __tablename__ = "analytics_vendedor_mes"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Dimensões
    vendedor_id = Column(Integer, ForeignKey("vendedores.id"), nullable=False, index=True)
    vendedor_nome = Column(String(255), nullable=False, index=True)
    supervisor_id = Column(Integer, ForeignKey("supervisores.id"), nullable=True, index=True)
    
    # Temporal
    mes_ano = Column(String(7), nullable=False, index=True)  # "2025-08"
    ano = Column(Integer, nullable=False, index=True)
    mes = Column(Integer, nullable=False, index=True)
    
    # Métricas de Meta vs Realizado
    meta_total = Column(Numeric(15, 2), nullable=False, default=0.0)
    realizado_total = Column(Numeric(15, 2), nullable=False, default=0.0)
    atingimento_pct = Column(Numeric(5, 2), nullable=True)  # Percentual de atingimento
    gap_valor = Column(Numeric(15, 2), nullable=True)  # realizado_total - meta_total
    
    # Ranking
    rank_atingimento = Column(Integer, nullable=True, index=True)  # Ranking global ou por supervisor (menor = pior)
    
    # ML Baseline - Risco de Meta
    meta_risk_score = Column(Numeric(5, 2), nullable=True, default=0.0)  # Score de risco (0-100)
    meta_risk_flag = Column(Boolean, nullable=False, default=False)  # True se vendedor em risco
    
    # Métricas de Clientes
    qtd_clientes_positivados = Column(Integer, nullable=False, default=0)  # Clientes com pelo menos 1 venda
    qtd_clientes_churn = Column(Integer, nullable=False, default=0)  # Clientes que compravam e pararam
    
    # Métricas de Produtos
    qtd_skus = Column(Integer, nullable=False, default=0)  # Diversidade de produtos vendidos
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Índices compostos para otimização
    __table_args__ = (
        UniqueConstraint('vendedor_id', 'mes_ano', name='uq_analytics_vendedor_mes'),
        Index('idx_analytics_vendedor_mes_ano', 'vendedor_id', 'mes_ano'),
        Index('idx_analytics_vendedor_rank', 'mes_ano', 'rank_atingimento'),
        Index('idx_analytics_vendedor_supervisor', 'supervisor_id', 'mes_ano'),
    )
    
    # Relacionamentos
    vendedor = relationship("Vendedor")
    supervisor = relationship("Supervisor")
    
    def __repr__(self):
        return f"<AnalyticsVendedorMes(vendedor_id={self.vendedor_id}, mes_ano='{self.mes_ano}', atingimento={self.atingimento_pct}%)>"


class AnalyticsClienteMes(Base):
    """
    Analytics agregado por Cliente e Mês.
    
    Tabela pré-calculada com métricas mensais por cliente,
    incluindo faturamento, frequência de compras e indicadores de churn.
    """
    __tablename__ = "analytics_cliente_mes"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Dimensões
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    cliente_nome = Column(String(255), nullable=False, index=True)
    vendedor_id = Column(Integer, ForeignKey("vendedores.id"), nullable=True, index=True)
    
    # Temporal
    mes_ano = Column(String(7), nullable=False, index=True)  # "2025-08"
    ano = Column(Integer, nullable=False, index=True)
    mes = Column(Integer, nullable=False, index=True)
    
    # Métricas de Faturamento
    faturamento_total = Column(Numeric(15, 2), nullable=False, default=0.0)
    qtd_compras = Column(Integer, nullable=False, default=0)  # Número de notas fiscais/pedidos
    
    # Métricas de Churn
    dias_desde_ultima_compra = Column(Integer, nullable=True)  # Dias desde a última compra no mês
    churn_score = Column(Numeric(5, 2), nullable=True, default=0.0)  # Score de churn (0-100) - ML baseline
    churn_flag = Column(Boolean, nullable=False, default=False)  # True se cliente em risco de churn
    
    # Tendências
    faturamento_media_3m = Column(Numeric(15, 2), nullable=True)  # Média de faturamento dos últimos 3 meses
    variacao_pct_vs_3m = Column(Numeric(5, 2), nullable=True)  # Variação % vs média 3 meses anteriores
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Índices compostos
    __table_args__ = (
        UniqueConstraint('cliente_id', 'mes_ano', name='uq_analytics_cliente_mes'),
        Index('idx_analytics_cliente_mes_ano', 'cliente_id', 'mes_ano'),
        Index('idx_analytics_cliente_vendedor', 'vendedor_id', 'mes_ano'),
        Index('idx_analytics_cliente_churn', 'mes_ano', 'dias_desde_ultima_compra'),
    )
    
    # Relacionamentos
    cliente = relationship("Cliente")
    vendedor = relationship("Vendedor")
    
    def __repr__(self):
        return f"<AnalyticsClienteMes(cliente_id={self.cliente_id}, mes_ano='{self.mes_ano}', faturamento={self.faturamento_total})>"


class AnalyticsProdutoMes(Base):
    """
    Analytics agregado por Produto e Mês.
    
    Tabela pré-calculada com métricas mensais por produto,
    incluindo faturamento, volume e participação.
    """
    __tablename__ = "analytics_produto_mes"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Dimensões
    codigo_produto = Column(String(50), nullable=False, index=True)
    desc_produto = Column(String(255), nullable=True)
    
    # Temporal
    mes_ano = Column(String(7), nullable=False, index=True)  # "2025-08"
    ano = Column(Integer, nullable=False, index=True)
    mes = Column(Integer, nullable=False, index=True)
    
    # Métricas de Vendas
    faturamento_total = Column(Numeric(15, 2), nullable=False, default=0.0)
    qtd_vendida = Column(Integer, nullable=False, default=0)  # Quantidade total vendida (unidades/caixas)
    qtd_clientes_ativos = Column(Integer, nullable=False, default=0)  # Clientes que compraram o produto
    
    # Métricas de Participação (opcional)
    participacao_no_faturamento = Column(Numeric(5, 2), nullable=True)  # % do faturamento total do mês
    
    # ML Baseline - Queda de Produto
    variacao_pct_vs_3m = Column(Numeric(5, 2), nullable=True)  # Variação % vs média 3 meses anteriores
    queda_score = Column(Numeric(5, 2), nullable=True, default=0.0)  # Score de queda (0-100)
    queda_flag = Column(Boolean, nullable=False, default=False)  # True se produto em queda
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Índices compostos
    __table_args__ = (
        UniqueConstraint('codigo_produto', 'mes_ano', name='uq_analytics_produto_mes'),
        Index('idx_analytics_produto_mes_ano', 'codigo_produto', 'mes_ano'),
        Index('idx_analytics_produto_faturamento', 'mes_ano', 'faturamento_total'),
    )
    
    def __repr__(self):
        return f"<AnalyticsProdutoMes(codigo='{self.codigo_produto}', mes_ano='{self.mes_ano}', faturamento={self.faturamento_total})>"


class AnalyticsAlerta(Base):
    """
    Alertas gerados a partir das análises de analytics.
    
    Tabela que armazena alertas automáticos sobre situações críticas,
    como vendedores em risco, clientes com churn alto, produtos em queda.
    """
    __tablename__ = "analytics_alertas"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Tipo de alerta
    tipo_alerta = Column(String(100), nullable=False, index=True)  # Ex.: "vendedor_meta_em_risco", "cliente_churn_alto", "produto_queda_forte"
    
    # Referência (pode ser vendedor_id, cliente_id, produto_id, conforme o tipo)
    referencia_id = Column(Integer, nullable=True, index=True)  # ID da entidade relacionada
    referencia_nome = Column(String(255), nullable=True)  # Nome da entidade para facilitar leitura
    
    # Temporal
    mes_ano = Column(String(7), nullable=False, index=True)  # "2025-08"
    ano = Column(Integer, nullable=False, index=True)
    mes = Column(Integer, nullable=False, index=True)
    
    # Descrição e detalhes
    descricao = Column(Text, nullable=False)  # Resumo executivo do alerta
    detalhes_json = Column(JSON, nullable=True)  # Payload com dados brutos para análise detalhada
    
    # Nível de criticidade
    nivel = Column(String(20), nullable=False, index=True)  # "alto", "medio", "baixo"
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Índices compostos
    __table_args__ = (
        Index('idx_analytics_alertas_tipo_mes', 'tipo_alerta', 'mes_ano'),
        Index('idx_analytics_alertas_nivel', 'nivel', 'mes_ano'),
        Index('idx_analytics_alertas_referencia', 'tipo_alerta', 'referencia_id', 'mes_ano'),
    )
    
    def __repr__(self):
        return f"<AnalyticsAlerta(tipo='{self.tipo_alerta}', nivel='{self.nivel}', mes_ano='{self.mes_ano}')>"

