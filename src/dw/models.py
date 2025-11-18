"""
Modelos SQLAlchemy para o Data Warehouse da Dipam.

Este módulo define os modelos de dados do data warehouse,
baseados na estrutura real dos CSVs fornecidos.
"""

from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, Boolean, 
    ForeignKey, Text, Index, JSON
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from src.dw.connection import Base


class DimTempo(Base):
    """
    Dimensão de Tempo.
    
    Tabela de dimensão temporal para facilitar análises e agregações.
    """
    __tablename__ = "dim_tempo"
    
    id = Column(Integer, primary_key=True, index=True)
    data = Column(Date, unique=True, nullable=False, index=True)
    ano = Column(Integer, nullable=False, index=True)
    mes = Column(Integer, nullable=False, index=True)
    dia = Column(Integer, nullable=False)
    trimestre = Column(Integer, nullable=False)
    semestre = Column(Integer, nullable=False)
    dia_semana = Column(Integer, nullable=False)  # 1=Segunda, 7=Domingo
    nome_dia_semana = Column(String(20), nullable=False)
    nome_mes = Column(String(20), nullable=False)
    mes_ano = Column(String(7), nullable=False, index=True)  # "2024-12"
    bimestre = Column(Integer, nullable=False)  # 1-6
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<DimTempo(id={self.id}, data={self.data}, mes_ano='{self.mes_ano}')>"


class Supervisor(Base):
    """
    Modelo de Supervisor.
    
    Representa os supervisores/pastas da empresa.
    Extraído dos CSVs de vendas e metas.
    """
    __tablename__ = "supervisores"
    
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True, nullable=False, index=True)
    nome = Column(String(255), nullable=False)
    pasta = Column(String(100), nullable=True, index=True)
    gerente = Column(String(255), nullable=True)  # Gerente relacionado
    ativo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    vendedores = relationship("Vendedor", back_populates="supervisor")
    metas_departamento = relationship("MetaDepartamento", back_populates="supervisor")
    clientes = relationship("Cliente", back_populates="supervisor")
    
    def __repr__(self):
        return f"<Supervisor(id={self.id}, codigo='{self.codigo}', nome='{self.nome}')>"


class Vendedor(Base):
    """
    Modelo de Vendedor.
    
    Representa os vendedores da empresa (ex.: "ROTA 77", "ROTA 02").
    Extraído dos CSVs de vendas e metas.
    """
    __tablename__ = "vendedores"
    
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True, nullable=False, index=True)  # Ex.: "ROTA 77"
    nome = Column(String(255), nullable=False)
    nome_rca = Column(String(255), nullable=True)  # Nome do RCA
    rota_rca = Column(String(100), nullable=True)  # Rota do RCA
    supervisor_id = Column(Integer, ForeignKey("supervisores.id"), nullable=True, index=True)
    ativo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Índice composto
    __table_args__ = (
        Index('idx_vendedor_supervisor', 'supervisor_id', 'ativo'),
    )
    
    # Relacionamentos
    vendas = relationship("Venda", back_populates="vendedor")
    metas_vendedor = relationship("MetaVendedor", back_populates="vendedor")
    meta_predictions = relationship("MetaPrediction", back_populates="vendedor")
    supervisor = relationship("Supervisor", back_populates="vendedores")
    
    def __repr__(self):
        return f"<Vendedor(id={self.id}, codigo='{self.codigo}', nome='{self.nome}')>"


class Cliente(Base):
    """
    Modelo de Cliente.
    
    Representa os clientes da empresa.
    Baseado no CSV "Clientes ativos".
    """
    __tablename__ = "clientes"
    
    id = Column(Integer, primary_key=True, index=True)
    cnpj_cpf = Column(String(18), nullable=True, index=True)  # CNPJ/CPF
    codigo = Column(String(50), unique=True, nullable=False, index=True)
    fantasia = Column(String(255), nullable=True)
    nome = Column(String(255), nullable=False)  # Campo "Cliente"
    estado = Column(String(2), nullable=True, index=True)
    municipio = Column(String(100), nullable=True, index=True)
    regiao_administrativa = Column(String(100), nullable=True)
    local_venda = Column(String(100), nullable=True)
    segmento_venda = Column(String(100), nullable=True)
    grupo_economico = Column(String(100), nullable=True)
    supervisor_id = Column(Integer, ForeignKey("supervisores.id"), nullable=True, index=True)
    supervisor_responsavel = Column(String(255), nullable=True)
    nome_rca = Column(String(255), nullable=True)
    rota_rca = Column(String(100), nullable=True)
    pasta = Column(String(100), nullable=True)
    consumidor_final = Column(Boolean, default=False, nullable=False)
    bloqueado = Column(Boolean, default=False, nullable=False)
    motivo_bloqueio = Column(Text, nullable=True)
    observacoes = Column(Text, nullable=True)
    ativo = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Índices compostos
    __table_args__ = (
        Index('idx_cliente_estado_municipio', 'estado', 'municipio'),
        Index('idx_cliente_supervisor_ativo', 'supervisor_id', 'ativo'),
    )
    
    # Relacionamentos
    vendas = relationship("Venda", back_populates="cliente")
    churn_risk = relationship("ChurnRisk", back_populates="cliente", uselist=False)
    supervisor = relationship("Supervisor", back_populates="clientes")
    
    def __repr__(self):
        return f"<Cliente(id={self.id}, codigo='{self.codigo}', nome='{self.nome}')>"


class DimProduto(Base):
    """
    Dimensão de Produto.
    
    Representa os produtos do catálogo da DIPAM.
    Baseado em ENGINEERING_MASTER_PLAN.md e ENGINEERING_QUERIES.md.
    """
    __tablename__ = "dim_produto"
    
    id = Column(Integer, primary_key=True, index=True)
    produto_id = Column(Integer, unique=True, nullable=False, index=True)  # ID canônico
    sku = Column(String(50), unique=True, nullable=False, index=True)  # Código SKU
    descricao = Column(String(255), nullable=False)
    industria = Column(String(100), nullable=True, index=True)  # Mars, Nissin, Red Bull, AB Brasil
    marca = Column(String(100), nullable=True)
    categoria = Column(String(100), nullable=True)
    ativo = Column(Boolean, default=True, nullable=False, index=True)
    
    # Metadados
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Índices compostos
    __table_args__ = (
        Index('idx_produto_industria_sku', 'industria', 'sku'),
        Index('idx_produto_industria_ativo', 'industria', 'ativo'),
    )
    
    # Relacionamentos
    vendas = relationship("Venda", back_populates="produto")
    
    def __repr__(self):
        return f"<DimProduto(id={self.id}, sku='{self.sku}', industria='{self.industria}')>"


class Venda(Base):
    """
    Modelo de Venda.
    
    Representa as vendas realizadas.
    Baseado no CSV "Detalhes de vendas" (bimestral).
    """
    __tablename__ = "vendas"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Dimensões temporais
    data_venda = Column(Date, nullable=False, index=True)
    tempo_id = Column(Integer, ForeignKey("dim_tempo.id"), nullable=True, index=True)
    
    # Dimensões organizacionais
    gerente = Column(String(255), nullable=True)
    supervisor_id = Column(Integer, ForeignKey("supervisores.id"), nullable=True, index=True)
    supervisor_nome = Column(String(255), nullable=True)  # Para manter histórico
    vendedor_id = Column(Integer, ForeignKey("vendedores.id"), nullable=False, index=True)
    vendedor_nome = Column(String(255), nullable=True)  # Para manter histórico
    
    # Nota fiscal
    numero_nf = Column(String(50), nullable=True, index=True)
    
    # Cliente
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    codigo_cliente = Column(String(50), nullable=False, index=True)  # Para manter histórico
    nome_cliente = Column(String(255), nullable=True)
    cgc_cpf_cliente = Column(String(18), nullable=True)
    ramo_atividade = Column(String(255), nullable=True)
    cidade_cliente = Column(String(100), nullable=True)
    
    # Produto (FK para dim_produto)
    produto_id = Column(Integer, ForeignKey("dim_produto.id"), nullable=True, index=True)
    # Campos legados mantidos para compatibilidade durante migração
    codigo_produto = Column(String(50), nullable=True, index=True)
    desc_produto = Column(String(255), nullable=True)
    departamento = Column(String(100), nullable=True, index=True)  # DEPRECATED: usar dim_produto.industria
    secao = Column(String(100), nullable=True)
    
    # Valores e quantidades
    valor_total_liquido = Column(Float, nullable=False)
    valor_desconto = Column(Float, nullable=True, default=0.0)
    qtd_caixas = Column(Integer, nullable=True)
    qtd_unidades = Column(Integer, nullable=True)
    qtd_unidades_bonificacao = Column(Integer, nullable=True, default=0)
    qtd_un_venda_liquida = Column(Integer, nullable=True)
    
    # Metadados
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Índices compostos para otimização de queries
    __table_args__ = (
        Index('idx_venda_data_cliente', 'data_venda', 'cliente_id'),
        Index('idx_venda_data_vendedor', 'data_venda', 'vendedor_id'),
        Index('idx_venda_mes_ano_vendedor', 'data_venda', 'vendedor_id'),
        Index('idx_venda_departamento_data', 'departamento', 'data_venda'),
    )
    
    # Relacionamentos
    cliente = relationship("Cliente", back_populates="vendas")
    vendedor = relationship("Vendedor", back_populates="vendas")
    supervisor = relationship("Supervisor")
    tempo = relationship("DimTempo")
    produto = relationship("DimProduto", back_populates="vendas")
    
    def __repr__(self):
        return f"<Venda(id={self.id}, data={self.data_venda}, valor={self.valor_total_liquido})>"


class MetaVendedor(Base):
    """
    Modelo de Meta por Vendedor.
    
    Representa as metas de vendas por vendedor e mês.
    Baseado no CSV "Metas X Realizado Vendedor" (mensal).
    """
    __tablename__ = "metas_vendedor"
    
    id = Column(Integer, primary_key=True, index=True)
    vendedor_id = Column(Integer, ForeignKey("vendedores.id"), nullable=False, index=True)
    vendedor_nome = Column(String(255), nullable=True)  # Para manter histórico
    ano = Column(Integer, nullable=False, index=True)
    mes = Column(Integer, nullable=False, index=True)
    mes_ano = Column(String(7), nullable=False, index=True)  # "2024-01" para facilitar queries
    
    # Indústria (conforme ENGINEERING_QUERIES.md - fato_metas_vendedor_mensal.industria)
    industria = Column(String(100), nullable=True, index=True)  # Mars, Nissin, Red Bull, AB Brasil
    
    # Metas de valor
    valor_meta = Column(Float, nullable=False)
    valor_faturado = Column(Float, nullable=True, default=0.0)
    valor_parado = Column(Float, nullable=True, default=0.0)
    valor_total = Column(Float, nullable=True)  # Vl. Faturado + Vl. Parado
    percentual_atingido_valor = Column(Float, nullable=True)  # % Ating
    
    # Metas de quantidade
    qtd_meta = Column(Integer, nullable=True)
    qtd_cx_faturado = Column(Integer, nullable=True, default=0)
    qtd_cx_paradas = Column(Integer, nullable=True, default=0)
    total_caixas = Column(Integer, nullable=True)  # Total Caixas
    percentual_atingido_volume = Column(Float, nullable=True)  # % Vol Ating
    
    # Posicionamento
    meta_pos = Column(Integer, nullable=True)
    clientes_pos = Column(Integer, nullable=True)  # Cl. Pos.
    percentual_atingido_pos = Column(Float, nullable=True)  # % Ating.1
    
    # Metadados
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Índices compostos
    __table_args__ = (
        Index('idx_meta_vendedor_mes_ano', 'mes_ano', 'vendedor_id'),
        Index('idx_meta_vendedor_ano_mes', 'ano', 'mes', 'vendedor_id'),
        Index('idx_meta_vendedor_percentual', 'percentual_atingido_valor', 'ano', 'mes'),
    )
    
    # Relacionamentos
    vendedor = relationship("Vendedor", back_populates="metas_vendedor")
    
    def __repr__(self):
        return f"<MetaVendedor(id={self.id}, vendedor_id={self.vendedor_id}, mes_ano='{self.mes_ano}')>"


class MetaDepartamento(Base):
    """
    Modelo de Meta por Departamento.
    
    Representa as metas de vendas por departamento/supervisor e mês.
    Baseado no CSV "Metas X Realizado Departamento" (mensal).
    """
    __tablename__ = "metas_departamento"
    
    id = Column(Integer, primary_key=True, index=True)
    supervisor_id = Column(Integer, ForeignKey("supervisores.id"), nullable=False, index=True)
    supervisor_nome = Column(String(255), nullable=True)  # Para manter histórico
    departamento = Column(String(100), nullable=True, index=True)
    ano = Column(Integer, nullable=False, index=True)
    mes = Column(Integer, nullable=False, index=True)
    mes_ano = Column(String(7), nullable=False, index=True)  # "2024-01"
    
    # Metas de valor
    valor_meta = Column(Float, nullable=False)
    valor_faturado = Column(Float, nullable=True, default=0.0)
    valor_parado = Column(Float, nullable=True, default=0.0)
    valor_total = Column(Float, nullable=True)
    percentual_atingido_valor = Column(Float, nullable=True)
    
    # Metas de quantidade
    qtd_meta = Column(Integer, nullable=True)
    qtd_cx_faturado = Column(Integer, nullable=True, default=0)
    qtd_cx_paradas = Column(Integer, nullable=True, default=0)
    total_caixas = Column(Integer, nullable=True)
    percentual_atingido_volume = Column(Float, nullable=True)
    
    # Posicionamento
    meta_pos = Column(Integer, nullable=True)
    clientes_pos = Column(Integer, nullable=True)
    percentual_atingido_pos = Column(Float, nullable=True)
    
    # Metadados
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Índices compostos
    __table_args__ = (
        Index('idx_meta_departamento_mes_ano', 'mes_ano', 'supervisor_id'),
        Index('idx_meta_departamento_ano_mes', 'ano', 'mes', 'supervisor_id'),
        Index('idx_meta_departamento_percentual', 'percentual_atingido_valor', 'ano', 'mes'),
    )
    
    # Relacionamentos
    supervisor = relationship("Supervisor", back_populates="metas_departamento")
    
    def __repr__(self):
        return f"<MetaDepartamento(id={self.id}, supervisor_id={self.supervisor_id}, mes_ano='{self.mes_ano}')>"


class MetaPrediction(Base):
    """
    Modelo de Predição de Meta.
    
    Armazena as predições de probabilidade de bater meta por vendedor/mês.
    Gerado pelo modelo de ML.
    """
    __tablename__ = "meta_predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    vendedor_id = Column(Integer, ForeignKey("vendedores.id"), nullable=False, index=True)
    ano = Column(Integer, nullable=False, index=True)
    mes = Column(Integer, nullable=False, index=True)
    mes_ano = Column(String(7), nullable=False, index=True)
    probabilidade_atingir = Column(Float, nullable=False)  # 0-1
    modelo_version = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Índice composto
    __table_args__ = (
        Index('idx_meta_prediction_mes_ano_vendedor', 'mes_ano', 'vendedor_id'),
    )
    
    # Relacionamentos
    vendedor = relationship("Vendedor", back_populates="meta_predictions")
    
    def __repr__(self):
        return f"<MetaPrediction(id={self.id}, vendedor_id={self.vendedor_id}, probabilidade={self.probabilidade_atingir})>"


class ChurnRisk(Base):
    """
    Modelo de Risco de Churn.
    
    Armazena as predições de risco de churn por cliente.
    Gerado pelo modelo de ML.
    """
    __tablename__ = "churn_risk"
    
    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), unique=True, nullable=False, index=True)
    risco_churn = Column(Float, nullable=False)  # 0-1, probabilidade de churn
    score = Column(String(20), nullable=True)  # 'baixo', 'medio', 'alto'
    modelo_version = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    cliente = relationship("Cliente", back_populates="churn_risk")
    
    def __repr__(self):
        return f"<ChurnRisk(id={self.id}, cliente_id={self.cliente_id}, risco={self.risco_churn})>"


class InteracaoAgent(Base):
    """
    Modelo de Interação do Agente.
    
    Armazena todas as interações do agente Dipam AI para análise
    e aprendizado com perguntas e respostas.
    """
    __tablename__ = "interacoes_agent"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Informações do usuário
    usuario_id = Column(String(100), nullable=True, index=True)
    papel = Column(String(50), nullable=True, index=True)  # diretor, supervisor, vendedor
    
    # Pergunta e resposta
    pergunta = Column(Text, nullable=False)
    resposta = Column(Text, nullable=False)
    
    # Metadados da resposta
    intent = Column(String(100), nullable=False, index=True)  # intenção detectada (usado como intent_prevista)
    intent_prevista = Column(String(100), nullable=True, index=True)  # Compatibilidade com novo campo
    confianca = Column(Float, nullable=False)  # 0-1
    
    # Entidades extraídas e SQL executado (para aprendizado contínuo)
    entities_json = Column(JSON, nullable=True)  # Entidades extraídas da pergunta
    sql_executado = Column(Text, nullable=True)  # SQL executado se teve query
    
    # Resumo da resposta (para aprendizado)
    resposta_resumida = Column(Text, nullable=True)  # Resumo curto da resposta
    resumo_executivo = Column(Text, nullable=True)  # Resumo executivo extraído da resposta estruturada (FASE 4)
    
    # Contexto resumido (apenas números chave, não o contexto completo)
    # Usa JSON para flexibilidade, ou Text como fallback para SQLite
    contexto_resumido = Column(JSON, nullable=True)
    debug_payload = Column(JSON, nullable=True)  # Contexto de debug completo (FASE 4)
    
    # Fonte de dados e métricas de processamento (FASE 4)
    fonte_dados_principal = Column(String(100), nullable=True)  # Ex.: "analytics_vendedor_mes", "analytics_cliente_mes"
    num_registros_usados = Column(Integer, nullable=True)  # Quantidade de linhas de analytics consultadas
    tempo_processamento_ms = Column(Integer, nullable=True)  # Latência total da pergunta em milissegundos
    
    # Feedback do usuário e sucesso (para aprendizado contínuo)
    sucesso = Column(Boolean, nullable=True, index=True)  # True = resposta baseada em dados reais, False = fallback
    sucesso_resposta = Column(Boolean, nullable=True, index=True)  # Alias para sucesso (FASE 4 - compatibilidade)
    feedback_usuario = Column(String(20), nullable=True)  # 👍/👎 (opcional, futuro)
    feedback_qualidade = Column(Integer, nullable=True, index=True)  # Escala 1-5 (FASE 4)
    comentario = Column(Text, nullable=True)  # Comentário do usuário sobre a resposta
    feedback_comentario = Column(Text, nullable=True)  # Alias para comentario (FASE 4 - compatibilidade)
    
    # Tags opcionais para categorização
    tags = Column(Text, nullable=True)
    
    # Metadados
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Índices compostos
    __table_args__ = (
        Index('idx_interacao_usuario_papel', 'usuario_id', 'papel'),
        Index('idx_interacao_intent_confianca', 'intent', 'confianca'),
        Index('idx_interacao_timestamp_intent', 'timestamp', 'intent'),
        Index('idx_interacao_sucesso_intent', 'sucesso', 'intent'),
        Index('idx_interacao_intent_prevista', 'intent_prevista'),
    )
    
    def __repr__(self):
        return f"<InteracaoAgent(id={self.id}, intent='{self.intent}', confianca={self.confianca:.2f})>"
    
    # Relacionamento com embeddings
    embedding = relationship("InteracaoEmbedding", back_populates="interacao", uselist=False)


class InteracaoEmbedding(Base):
    """
    Modelo de Embedding de Interação.
    
    Armazena os embeddings vetoriais das perguntas das interações
    para busca semântica e memória de Q&A.
    """
    __tablename__ = "interacoes_embedding"
    
    id = Column(Integer, primary_key=True, index=True)
    interacao_id = Column(Integer, ForeignKey("interacoes_agent.id"), unique=True, nullable=False, index=True)
    
    # Embedding: armazenado como JSON/Text para compatibilidade com SQLite e PostgreSQL
    # Para PostgreSQL com pgvector, pode ser migrado para tipo vector no futuro
    # Por enquanto, usamos JSON serializado
    embedding = Column(JSON, nullable=False)  # Lista de floats (1536 para text-embedding-ada-002)
    
    # Metadados
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relacionamento
    interacao = relationship("InteracaoAgent", back_populates="embedding")
    
    def __repr__(self):
        return f"<InteracaoEmbedding(id={self.id}, interacao_id={self.interacao_id})>"


class Skill(Base):
    """
    Modelo de Skill Analítica.
    
    Uma skill é um template SQL reutilizável que representa uma análise específica.
    Quando o agente detecta uma pergunta compatível com uma skill, ele usa o template
    SQL parametrizado para executar a query e gerar a resposta.
    
    Skills são criadas manualmente ou automaticamente pelo job de aprendizado contínuo.
    """
    __tablename__ = "skills"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Identificação da skill
    nome = Column(String(255), nullable=False, unique=True, index=True)  # Ex.: "clientes_positivados_por_rota_produto"
    descricao = Column(Text, nullable=False)  # Descrição detalhada do que a skill faz
    
    # Intent alvo (qual intent essa skill atende)
    intent_alvo = Column(String(100), nullable=False, index=True)  # Ex.: "clientes_churn_produto"
    
    # Schema de entrada (parâmetros esperados)
    schema_entrada = Column(JSON, nullable=False)  # Ex.: {"produto": "string", "mes_ano": "string (opcional)"}
    
    # Template SQL parametrizado
    sql_template = Column(Text, nullable=False)  # SQL com placeholders :produto, :data_inicio, etc.
    
    # Tipo de saída
    tipo_saida = Column(String(100), nullable=False)  # Ex.: "ranking_vendedores", "tabela_clientes", "lista_produtos"
    
    # Flag de ativação
    ativo = Column(Boolean, default=True, nullable=False, index=True)
    
    # Metadados
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Índices compostos
    __table_args__ = (
        Index('idx_skill_intent_ativo', 'intent_alvo', 'ativo'),
    )
    
    def __repr__(self):
        return f"<Skill(id={self.id}, nome='{self.nome}', intent='{self.intent_alvo}')>"


class SkillSugestao(Base):
    """
    Modelo de Sugestão de Skill.
    
    Armazena sugestões de novas skills geradas pelo job de aprendizado contínuo.
    Essas sugestões precisam ser aprovadas manualmente antes de serem adicionadas
    ao catálogo de skills ativas.
    """
    __tablename__ = "skills_sugestoes"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Interação original que gerou a sugestão
    interacao_id_orig = Column(Integer, ForeignKey("interacoes_agent.id"), nullable=True, index=True)
    
    # Pergunta que gerou a sugestão (duplicada para facilitar consultas)
    pergunta = Column(Text, nullable=False)
    
    # Intent sugerida para essa skill
    intent_sugerida = Column(String(100), nullable=False, index=True)
    
    # JSON completo da skill proposta (inclui nome, descrição, schema, sql_template, tipo_saida)
    skill_json_proposta = Column(JSON, nullable=False)
    
    # Status da sugestão
    status = Column(String(20), nullable=False, default="pending", index=True)  # pending, approved, rejected
    
    # Comentário do revisor (quem aprovou/rejeitou)
    comentario_revisor = Column(Text, nullable=True)
    
    # Metadados
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Índices compostos
    __table_args__ = (
        Index('idx_skill_sugestao_status_created', 'status', 'created_at'),
        Index('idx_skill_sugestao_intent_status', 'intent_sugerida', 'status'),
    )
    
    def __repr__(self):
        return f"<SkillSugestao(id={self.id}, intent='{self.intent_sugerida}', status='{self.status}')>"
