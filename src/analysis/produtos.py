"""
Análise de Produtos.

Este módulo contém funções para analisar produtos com baixa venda
e identificar oportunidades de recuperação.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from src.dw.models import Venda

logger = logging.getLogger(__name__)


def get_produtos_menos_vendidos(
    session: Session,
    dias: int = 90,
    limite: int = 20
) -> List[Dict[str, Any]]:
    """
    Busca produtos com menor volume de vendas nos últimos X dias.
    
    Agrupa por código e descrição do produto, somando unidades, caixas
    e faturamento. Ordena pelo menor volume vendido (faturamento).
    
    Args:
        session: Sessão SQLAlchemy
        dias: Número de dias para análise (padrão: 90)
        limite: Número máximo de produtos a retornar (padrão: 20)
        
    Returns:
        List[dict]: Lista de dicionários com:
            {
                "codigo": str,
                "produto": str,
                "unidades": int,
                "caixas": float,
                "faturamento": float
            }
            Ordenado pelo menor faturamento (crescente)
    """
    logger.info(f"Buscando produtos menos vendidos dos últimos {dias} dias...")
    
    try:
        # 1. Consulta a data máxima de venda no banco (ponto de referência)
        data_base = session.query(func.max(Venda.data_venda)).scalar()
        
        if not data_base:
            logger.warning("Nenhuma venda encontrada no banco de dados")
            return []
        
        # 2. Define o intervalo correto: últimos X dias a partir da data base
        data_inicio = data_base - timedelta(days=dias)
        data_fim = data_base
        
        logger.info(f"Analisando vendas de {data_inicio} a {data_fim} (base: {data_base})")
        
        # Query para agrupar vendas por produto
        # 3. Filtra usando BETWEEN: vendas.data_venda BETWEEN data_inicio AND data_fim
        # Nota: Se codigo_produto/desc_produto estiverem NULL, usa departamento como identificador
        query = (
            session.query(
                func.coalesce(Venda.codigo_produto, Venda.departamento, 'PRODUTO_SEM_CODIGO').label('codigo_produto'),
                func.coalesce(Venda.desc_produto, Venda.departamento, Venda.secao, 'Produto sem descrição').label('desc_produto'),
                func.sum(Venda.qtd_unidades).label('total_unidades'),
                func.sum(Venda.qtd_caixas).label('total_caixas'),
                func.sum(Venda.valor_total_liquido).label('total_faturamento')
            )
            .filter(Venda.data_venda.between(data_inicio, data_fim))
            .filter(
                # Pelo menos um campo de identificação deve existir
                or_(
                    Venda.codigo_produto.isnot(None),
                    Venda.departamento.isnot(None)
                )
            )
            .group_by(
                func.coalesce(Venda.codigo_produto, Venda.departamento, 'PRODUTO_SEM_CODIGO'),
                func.coalesce(Venda.desc_produto, Venda.departamento, Venda.secao, 'Produto sem descrição')
            )
            .having(func.sum(Venda.valor_total_liquido) > 0)  # Apenas produtos com faturamento positivo
            .order_by('total_faturamento')  # Ordena pelo menor faturamento (crescente)
            .limit(limite)
        )
        
        # Executa query
        results = query.all()
        
        if not results:
            logger.warning("Nenhum produto encontrado no período especificado")
            return []
        
        # Formata resultado
        produtos = []
        for row in results:
            produtos.append({
                "codigo": str(row.codigo_produto) if row.codigo_produto else "",
                "produto": str(row.desc_produto) if row.desc_produto else "",
                "unidades": int(row.total_unidades) if row.total_unidades else 0,
                "caixas": float(row.total_caixas) if row.total_caixas else 0.0,
                "faturamento": float(row.total_faturamento) if row.total_faturamento else 0.0,
            })
        
        logger.info(f"Encontrados {len(produtos)} produtos com menor venda")
        
        return produtos
        
    except Exception as e:
        logger.error(f"Erro ao buscar produtos menos vendidos: {str(e)}")
        raise


def get_top_produtos_para_recuperar(
    session: Session,
    dias: int = 90
) -> List[Dict[str, Any]]:
    """
    Identifica os top 10 produtos que precisam de impulso baseado em giro ajustado.
    
    Calcula a métrica de giro:
        giro = faturamento / (unidades + caixas * 12)
    
    Ordena pelo menor giro ajustado (produtos com menor giro são os piores).
    
    Args:
        session: Sessão SQLAlchemy
        dias: Número de dias para análise (padrão: 90)
        
    Returns:
        List[dict]: Lista de até 10 dicionários com:
            {
                "codigo": str,
                "produto": str,
                "unidades": int,
                "caixas": float,
                "faturamento": float,
                "giro": float  # faturamento / (unidades + caixas * 12)
            }
            Ordenado pelo menor giro (crescente)
    """
    logger.info(f"Buscando top produtos para recuperar dos últimos {dias} dias...")
    
    try:
        # 1. Consulta a data máxima de venda no banco (ponto de referência)
        data_base = session.query(func.max(Venda.data_venda)).scalar()
        
        if not data_base:
            logger.warning("Nenhuma venda encontrada no banco de dados")
            return []
        
        # 2. Define o intervalo correto: últimos X dias a partir da data base
        data_inicio = data_base - timedelta(days=dias)
        data_fim = data_base
        
        logger.info(f"Analisando vendas de {data_inicio} a {data_fim} (base: {data_base})")
        
        # Query para agrupar vendas por produto
        # 3. Filtra usando BETWEEN: vendas.data_venda BETWEEN data_inicio AND data_fim
        # Nota: Se codigo_produto/desc_produto estiverem NULL, usa departamento como identificador
        query = (
            session.query(
                func.coalesce(Venda.codigo_produto, Venda.departamento, 'PRODUTO_SEM_CODIGO').label('codigo_produto'),
                func.coalesce(Venda.desc_produto, Venda.departamento, Venda.secao, 'Produto sem descrição').label('desc_produto'),
                func.sum(Venda.qtd_unidades).label('total_unidades'),
                func.sum(Venda.qtd_caixas).label('total_caixas'),
                func.sum(Venda.valor_total_liquido).label('total_faturamento')
            )
            .filter(Venda.data_venda.between(data_inicio, data_fim))
            .filter(
                # Pelo menos um campo de identificação deve existir
                or_(
                    Venda.codigo_produto.isnot(None),
                    Venda.departamento.isnot(None)
                )
            )
            .group_by(
                func.coalesce(Venda.codigo_produto, Venda.departamento, 'PRODUTO_SEM_CODIGO'),
                func.coalesce(Venda.desc_produto, Venda.departamento, Venda.secao, 'Produto sem descrição')
            )
            .having(func.sum(Venda.valor_total_liquido) > 0)
        )
        
        # Executa query
        results = query.all()
        
        if not results:
            logger.warning("Nenhum produto encontrado no período especificado")
            return []
        
        # Calcula giro para cada produto
        produtos_com_giro = []
        for row in results:
            unidades = int(row.total_unidades) if row.total_unidades else 0
            caixas = float(row.total_caixas) if row.total_caixas else 0.0
            faturamento = float(row.total_faturamento) if row.total_faturamento else 0.0
            
            # Calcula volume total (unidades + caixas convertidas para unidades)
            # Assume que cada caixa tem 12 unidades
            volume_total = unidades + (caixas * 12)
            
            # Calcula giro ajustado
            # Se volume_total for 0, giro é 0 (evita divisão por zero)
            if volume_total > 0:
                giro = faturamento / volume_total
            else:
                giro = 0.0
            
            produtos_com_giro.append({
                "codigo": str(row.codigo_produto) if row.codigo_produto else "",
                "produto": str(row.desc_produto) if row.desc_produto else "",
                "unidades": unidades,
                "caixas": caixas,
                "faturamento": faturamento,
                "giro": round(giro, 2),
            })
        
        # Ordena pelo menor giro (crescente) e pega top 10
        produtos_com_giro.sort(key=lambda x: x["giro"])
        top_produtos = produtos_com_giro[:10]
        
        logger.info(f"Encontrados {len(top_produtos)} produtos com menor giro")
        
        return top_produtos
        
    except Exception as e:
        logger.error(f"Erro ao buscar produtos para recuperar: {str(e)}")
        raise

