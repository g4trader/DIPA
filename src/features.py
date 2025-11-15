"""
Camada de Features para Machine Learning.

Este módulo cria DataFrames prontos para modelagem a partir das tabelas
do data warehouse, com features engenheiradas para modelos de ML.
"""

import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta
from typing import Optional
import logging

from pathlib import Path
from src.config import config
from src.dw.connection import get_db_engine, get_db_session

logger = logging.getLogger(__name__)


def build_features_vendedor_mes(
    session: Optional[Session] = None,
    start_mes_ano: Optional[str] = None,
    end_mes_ano: Optional[str] = None
) -> pd.DataFrame:
    """
    Constrói features por vendedor/mês para modelo de probabilidade de bater meta.
    
    Agrega dados de metas_vendedor, vendas e clientes para criar features
    relacionadas ao desempenho do vendedor em cada mês.
    
    Features geradas:
    - mes_ano: Mês/ano de referência (YYYY-MM)
    - vendedor_id: ID do vendedor
    - vendedor_nome: Nome do vendedor
    - supervisor_nome: Nome do supervisor (se disponível)
    - valor_meta: Meta de valor do mês
    - valor_faturado: Valor faturado no mês
    - valor_total: Valor total (faturado + parado)
    - percentual_atingido_valor: Percentual de atingimento da meta de valor
    - qtd_meta: Meta de quantidade (caixas)
    - qtd_cx_faturado: Quantidade de caixas faturadas
    - qtd_cx_paradas: Quantidade de caixas paradas
    - total_caixas: Total de caixas
    - percentual_atingido_volume: Percentual de atingimento da meta de volume
    - meta_pos: Meta de positivação
    - clientes_pos: Clientes positivados
    - percentual_atingido_pos: Percentual de atingimento da meta de positivação
    - gap_valor: Diferença entre valor faturado e meta (valor_faturado - valor_meta)
    - bateu_meta: 1 se percentual_atingido_valor >= 100, senão 0
    - ticket_medio: Faturamento médio por NF no mês
    - desconto_medio: Média de desconto por NF no mês
    - num_clientes_atendidos: Número de clientes distintos atendidos no mês
    
    Args:
        session: Sessão SQLAlchemy (obrigatória)
        start_mes_ano: Mês/ano inicial (ex.: "2024-01") - None = todos
        end_mes_ano: Mês/ano final (ex.: "2024-12") - None = todos
        
    Returns:
        pd.DataFrame: DataFrame com features por vendedor/mês, pronto para ML
    """
    logger.info("Construindo features de vendedor/mês...")
    
    if session is None:
        raise ValueError("session é obrigatória para build_features_vendedor_mes")
    
    try:
        from src.dw.models import MetaVendedor, Vendedor, Supervisor, Venda, Cliente
        from sqlalchemy import func, case, and_, or_
        from sqlalchemy.orm import aliased
        
        # Query base usando SQLAlchemy ORM
        query = session.query(
            MetaVendedor.mes_ano,
            MetaVendedor.ano,
            MetaVendedor.mes,
            MetaVendedor.vendedor_id,
            Vendedor.codigo.label('vendedor'),
            Vendedor.nome.label('vendedor_nome'),
            Supervisor.nome.label('supervisor_nome'),
            MetaVendedor.valor_meta.label('meta_valor'),
            MetaVendedor.valor_faturado.label('realizado_valor'),
            MetaVendedor.valor_total,
            MetaVendedor.percentual_atingido_valor.label('perc_ating_valor'),
            MetaVendedor.qtd_meta.label('meta_volume'),
            func.coalesce(MetaVendedor.qtd_cx_faturado, 0).label('realizado_volume'),
            MetaVendedor.qtd_cx_paradas,
            MetaVendedor.total_caixas,
            MetaVendedor.percentual_atingido_volume.label('perc_ating_volume'),
            MetaVendedor.meta_pos,
            func.coalesce(MetaVendedor.clientes_pos, 0).label('clientes_pos'),
            MetaVendedor.percentual_atingido_pos.label('perc_ating_positivacao'),
        ).join(
            Vendedor, MetaVendedor.vendedor_id == Vendedor.id
        ).outerjoin(
            Supervisor, Vendedor.supervisor_id == Supervisor.id
        )
        
        # Filtros de data
        if start_mes_ano:
            query = query.filter(MetaVendedor.mes_ano >= start_mes_ano)
        if end_mes_ano:
            query = query.filter(MetaVendedor.mes_ano <= end_mes_ano)
        
        # Executa query base
        df = pd.read_sql(query.statement, session.bind)
        
        if len(df) == 0:
            logger.warning("Nenhuma meta de vendedor encontrada")
            return df
        
        logger.debug(f"Shape inicial após query de metas: {df.shape}")
        
        # Calcula gap_valor
        df['gap_valor'] = df['realizado_valor'] - df['meta_valor']
        
        # Calcula bateu_meta
        df['bateu_meta'] = (df['perc_ating_valor'] >= 100).astype(int)
        
        # Agrega estatísticas de vendas por vendedor/mês
        logger.debug("Agregando estatísticas de vendas...")
        
        # Query para agregar vendas por vendedor/mês
        vendas_query = session.query(
            Venda.vendedor_id,
            func.strftime('%Y-%m', Venda.data_venda).label('mes_ano_venda'),
            func.count(func.distinct(Venda.numero_nf)).label('num_nfs'),
            func.avg(Venda.valor_total_liquido).label('ticket_medio'),
            func.avg(Venda.valor_desconto).label('desconto_medio'),
            func.count(func.distinct(Venda.cliente_id)).label('num_clientes_atendidos'),
        ).filter(
            Venda.data_venda.isnot(None)
        ).group_by(
            Venda.vendedor_id,
            func.strftime('%Y-%m', Venda.data_venda)
        )
        
        df_vendas = pd.read_sql(vendas_query.statement, session.bind)
        
        # Merge com DataFrame principal
        df = df.merge(
            df_vendas,
            left_on=['vendedor_id', 'mes_ano'],
            right_on=['vendedor_id', 'mes_ano_venda'],
            how='left'
        )
        
        # Remove coluna auxiliar
        if 'mes_ano_venda' in df.columns:
            df = df.drop(columns=['mes_ano_venda'])
        
        # Preenche valores faltantes de vendas
        df['num_nfs'] = df['num_nfs'].fillna(0).astype(int)
        df['ticket_medio'] = df['ticket_medio'].fillna(0.0)
        df['desconto_medio'] = df['desconto_medio'].fillna(0.0)
        df['num_clientes_atendidos'] = df['num_clientes_atendidos'].fillna(0).astype(int)
        
        # Renomeia colunas para nomes esperados
        df = df.rename(columns={
            'meta_valor': 'valor_meta',
            'realizado_valor': 'valor_faturado',
            'perc_ating_valor': 'percentual_atingido_valor',
            'meta_volume': 'qtd_meta',
            'realizado_volume': 'qtd_cx_faturado',
            'perc_ating_volume': 'percentual_atingido_volume',
            'perc_ating_positivacao': 'percentual_atingido_pos',
            'num_nfs': 'qtd_nfs_mes',
        })
        
        # Preenche valores faltantes
        df = df.fillna({
            'supervisor_nome': '',
            'qtd_cx_paradas': 0,
            'total_caixas': 0,
            'meta_pos': 0,
        })
        
        # Garante tipos numéricos corretos
        numeric_cols = [
            'valor_meta', 'valor_faturado', 'valor_total', 'percentual_atingido_valor',
            'qtd_meta', 'qtd_cx_faturado', 'qtd_cx_paradas', 'total_caixas',
            'percentual_atingido_volume', 'meta_pos', 'clientes_pos', 'percentual_atingido_pos',
            'gap_valor', 'ticket_medio', 'desconto_medio', 'qtd_nfs_mes', 'num_clientes_atendidos'
        ]
        
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        
        # Ordena por vendedor e mês
        df = df.sort_values(['vendedor_id', 'ano', 'mes']).reset_index(drop=True)
        
        logger.info(f"Features de vendedor/mês construídas: {len(df)} registros, {len(df.columns)} colunas")
        logger.debug(f"Shape final: {df.shape}")
        logger.debug(f"Colunas: {list(df.columns)}")
        
        return df
    
    except Exception as e:
        logger.error(f"Erro ao construir features de vendedor/mês: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
        raise


def build_features_cliente_mes(
    session: Optional[Session] = None,
    start_mes_ano: Optional[str] = None,
    end_mes_ano: Optional[str] = None,
    dias_churn: int = 90
) -> pd.DataFrame:
    """
    Constrói features por cliente/mês para modelo de churn.
    
    Agrega dados de vendas e clientes para criar features relacionadas
    ao comportamento de compra do cliente em cada mês.
    
    Features geradas:
    - id_cliente: ID do cliente
    - codigo_cliente: Código do cliente
    - nome_cliente: Nome do cliente
    - vendedor_nome: Nome do vendedor (se disponível via join)
    - pasta: Pasta do supervisor (se disponível)
    - rota_rca: Rota do RCA (se disponível)
    - mes_ano: Mês/ano de referência (YYYY-MM)
    - valor_total_mes: Valor total de compras no mês
    - qtd_pedidos_mes: Quantidade de pedidos (NFs distintas) no mês
    - qtd_departamentos_distintos: Quantidade de departamentos distintos comprados no mês
    - qtd_dias_com_compra: Número de dias no mês com pelo menos uma compra
    - ticket_medio_mes: Ticket médio do mês (valor_total_mes / qtd_pedidos_mes)
    - dias_desde_ultima_compra: Dias desde a última compra antes deste mês
    - churn_provavel: 1 se o cliente não comprou nos próximos X dias após o mês, senão 0
    
    Args:
        session: Sessão SQLAlchemy (obrigatória)
        start_mes_ano: Mês/ano inicial (ex.: "2024-01") - None = todos
        end_mes_ano: Mês/ano final (ex.: "2024-12") - None = todos
        dias_churn: Número de dias sem compra para considerar churn (padrão: 90)
        
    Returns:
        pd.DataFrame: DataFrame com features por cliente/mês, pronto para ML
    """
    logger.info(f"Construindo features de cliente/mês (churn: {dias_churn} dias)...")
    
    if session is None:
        raise ValueError("session é obrigatória para build_features_cliente_mes")
    
    try:
        from src.dw.models import Venda, Cliente, Vendedor, Supervisor
        from sqlalchemy import func, case, and_, or_, extract
        
        # Query base: agrega vendas por cliente/mês
        query = session.query(
            func.strftime('%Y-%m', Venda.data_venda).label('mes_ano'),
            extract('year', Venda.data_venda).label('ano'),
            extract('month', Venda.data_venda).label('mes'),
            Cliente.id.label('id_cliente'),
            Cliente.codigo.label('codigo_cliente'),
            Cliente.nome.label('nome_cliente'),
            Vendedor.nome.label('vendedor_nome'),
            Supervisor.pasta.label('pasta'),
            Cliente.rota_rca.label('rota_rca'),
            func.sum(Venda.valor_total_liquido).label('valor_total_mes'),
            func.count(func.distinct(Venda.numero_nf)).label('qtd_pedidos_mes'),
            func.count(func.distinct(Venda.departamento)).label('qtd_departamentos_distintos'),
        ).join(
            Cliente, Venda.cliente_id == Cliente.id
        ).outerjoin(
            Vendedor, Venda.vendedor_id == Vendedor.id
        ).outerjoin(
            Supervisor, Venda.supervisor_id == Supervisor.id
        ).filter(
            Venda.data_venda.isnot(None),
            Cliente.ativo == True
        )
        
        # Filtros de data
        if start_mes_ano:
            query = query.filter(func.strftime('%Y-%m', Venda.data_venda) >= start_mes_ano)
        if end_mes_ano:
            query = query.filter(func.strftime('%Y-%m', Venda.data_venda) <= end_mes_ano)
        
        # Agrupa por cliente e mês
        query = query.group_by(
            func.strftime('%Y-%m', Venda.data_venda),
            extract('year', Venda.data_venda),
            extract('month', Venda.data_venda),
            Cliente.id,
            Cliente.codigo,
            Cliente.nome,
            Vendedor.nome,
            Supervisor.pasta,
            Cliente.rota_rca
        )
        
        # Executa query base
        df = pd.read_sql(query.statement, session.bind)
        
        if len(df) == 0:
            logger.warning("Nenhuma venda encontrada")
            return df
        
        logger.debug(f"Shape inicial após agregação de vendas: {df.shape}")
        
        # Calcula qtd_dias_com_compra (dias distintos com venda no mês)
        logger.debug("Calculando qtd_dias_com_compra...")
        dias_query = session.query(
            Cliente.id.label('cliente_id'),
            func.strftime('%Y-%m', Venda.data_venda).label('mes_ano_venda'),
            func.count(func.distinct(func.date(Venda.data_venda))).label('qtd_dias_com_compra')
        ).join(
            Cliente, Venda.cliente_id == Cliente.id
        ).filter(
            Venda.data_venda.isnot(None),
            Cliente.ativo == True
        )
        
        if start_mes_ano:
            dias_query = dias_query.filter(func.strftime('%Y-%m', Venda.data_venda) >= start_mes_ano)
        if end_mes_ano:
            dias_query = dias_query.filter(func.strftime('%Y-%m', Venda.data_venda) <= end_mes_ano)
        
        dias_query = dias_query.group_by(
            Cliente.id,
            func.strftime('%Y-%m', Venda.data_venda)
        )
        
        df_dias = pd.read_sql(dias_query.statement, session.bind)
        
        # Merge com DataFrame principal
        df = df.merge(
            df_dias,
            left_on=['id_cliente', 'mes_ano'],
            right_on=['cliente_id', 'mes_ano_venda'],
            how='left'
        )
        
        # Remove colunas auxiliares
        for col in ['cliente_id', 'mes_ano_venda']:
            if col in df.columns:
                df = df.drop(columns=[col])
        
        # Calcula ticket_medio_mes
        df['ticket_medio_mes'] = (df['valor_total_mes'] / df['qtd_pedidos_mes'].replace(0, np.nan)).fillna(0.0)
        
        # Calcula dias_desde_ultima_compra
        logger.debug("Calculando dias_desde_ultima_compra...")
        
        # Para cada cliente/mês, busca a última venda antes do mês
        ultima_compra_query = session.query(
            Cliente.id.label('cliente_id'),
            func.strftime('%Y-%m', Venda.data_venda).label('mes_ano_venda'),
            func.max(Venda.data_venda).label('ultima_compra_antes')
        ).join(
            Cliente, Venda.cliente_id == Cliente.id
        ).filter(
            Venda.data_venda.isnot(None)
        ).group_by(
            Cliente.id,
            func.strftime('%Y-%m', Venda.data_venda)
        )
        
        df_ultima_compra = pd.read_sql(ultima_compra_query.statement, session.bind)
        
        # Para cada linha, calcula dias desde última compra
        def calcular_dias_desde_ultima(row):
            cliente_id = row['id_cliente']
            mes_ano_str = row['mes_ano']
            ano, mes = map(int, mes_ano_str.split('-'))
            inicio_mes = datetime(ano, mes, 1)
            
            # Busca última compra antes deste mês
            compras_anteriores = df_ultima_compra[
                (df_ultima_compra['cliente_id'] == cliente_id) &
                (df_ultima_compra['mes_ano_venda'] < mes_ano_str)
            ]
            
            if len(compras_anteriores) == 0:
                return 999  # Nunca comprou antes
            
            ultima_compra = pd.to_datetime(compras_anteriores['ultima_compra_antes'].max())
            dias = (inicio_mes - ultima_compra).days
            return max(0, dias)
        
        df['dias_desde_ultima_compra'] = df.apply(calcular_dias_desde_ultima, axis=1)
        
        # Calcula churn_provavel
        logger.debug("Calculando churn_provavel...")
        
        # Carrega todas as vendas futuras
        vendas_futuras_query = session.query(
            Venda.cliente_id,
            func.strftime('%Y-%m', Venda.data_venda).label('mes_venda'),
            func.min(Venda.data_venda).label('primeira_venda_futura')
        ).filter(
            Venda.data_venda.isnot(None)
        ).group_by(
            Venda.cliente_id,
            func.strftime('%Y-%m', Venda.data_venda)
        )
        
        df_vendas_futuras = pd.read_sql(vendas_futuras_query.statement, session.bind)
        df_vendas_futuras['mes_venda'] = pd.to_datetime(df_vendas_futuras['mes_venda'] + '-01')
        
        def calcular_churn(row):
            cliente_id = row['id_cliente']
            mes_ano_str = row['mes_ano']
            ano, mes = map(int, mes_ano_str.split('-'))
            mes_atual = datetime(ano, mes, 1)
            mes_fim_periodo = mes_atual + timedelta(days=dias_churn + 30)
            
            # Busca vendas futuras do cliente
            vendas_cliente = df_vendas_futuras[
                (df_vendas_futuras['cliente_id'] == cliente_id) &
                (df_vendas_futuras['mes_venda'] > mes_atual) &
                (df_vendas_futuras['mes_venda'] <= mes_fim_periodo)
            ]
            
            # Se não há vendas no período, é churn provável
            return 1 if len(vendas_cliente) == 0 else 0
        
        df['churn_provavel'] = df.apply(calcular_churn, axis=1)
        
        # Preenche valores faltantes
        df = df.fillna({
            'valor_total_mes': 0.0,
            'qtd_pedidos_mes': 0,
            'qtd_departamentos_distintos': 0,
            'qtd_dias_com_compra': 0,
            'ticket_medio_mes': 0.0,
            'dias_desde_ultima_compra': 999,
            'vendedor_nome': '',
            'pasta': '',
            'rota_rca': '',
        })
        
        # Garante tipos numéricos corretos
        numeric_cols = [
            'valor_total_mes', 'qtd_pedidos_mes', 'qtd_departamentos_distintos',
            'qtd_dias_com_compra', 'ticket_medio_mes', 'dias_desde_ultima_compra'
        ]
        
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0 if 'valor' in col or 'ticket' in col else 0)
        
        # Ordena por cliente e mês
        df = df.sort_values(['id_cliente', 'ano', 'mes']).reset_index(drop=True)
        
        logger.info(f"Features de cliente/mês construídas: {len(df)} registros, {len(df.columns)} colunas")
        logger.debug(f"Shape final: {df.shape}")
        logger.debug(f"Colunas: {list(df.columns)}")
        
        return df
    
    except Exception as e:
        logger.error(f"Erro ao construir features de cliente/mês: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
        raise


def save_features_to_csv(
    df: pd.DataFrame,
    filename: str,
    features_dir: Optional[str] = None
):
    """
    Salva DataFrame de features em arquivo CSV.
    
    Args:
        df: DataFrame com features
        filename: Nome do arquivo (ex.: "features_vendedor_mes.csv")
        features_dir: Diretório para salvar (None = usa config.paths.features_dir)
    """
    if features_dir is None:
        features_dir = config.paths.features_dir
    
    features_dir = Path(features_dir)
    features_dir.mkdir(parents=True, exist_ok=True)
    
    filepath = features_dir / filename
    df.to_csv(filepath, index=False)
    
    logger.info(f"Features salvas em: {filepath}")


def load_features_from_csv(
    filename: str,
    features_dir: Optional[str] = None
) -> pd.DataFrame:
    """
    Carrega DataFrame de features de arquivo CSV.
    
    Args:
        filename: Nome do arquivo (ex.: "features_vendedor_mes.csv")
        features_dir: Diretório para carregar (None = usa config.paths.features_dir)
        
    Returns:
        pd.DataFrame: DataFrame com features carregadas
    """
    if features_dir is None:
        features_dir = config.paths.features_dir
    
    features_dir = Path(features_dir)
    filepath = features_dir / filename
    
    if not filepath.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {filepath}")
    
    df = pd.read_csv(filepath)
    logger.info(f"Features carregadas de: {filepath}")
    
    return df

