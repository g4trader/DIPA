#!/usr/bin/env python3
"""
Análise de Metas vs Realizado.

Módulo para análise de metas e realizados dos últimos N meses,
com diferentes níveis de agregação (empresa, departamento, vendedor).
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_

from src.dw.models import MetaVendedor, MetaDepartamento

logger = logging.getLogger(__name__)


def metas_resumo_ultimos_meses(
    session: Session,
    n_meses: int = 6,
    nivel: str = "empresa",
    supervisor_id: Optional[int] = None,
    vendedor_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Retorna resumo de metas vs realizado dos últimos N meses.
    
    Args:
        session: Sessão SQLAlchemy
        n_meses: Número de meses para analisar (padrão: 6)
        nivel: Nível de agregação ("empresa", "departamento", "vendedor")
        supervisor_id: ID do supervisor para filtrar (opcional)
        vendedor_id: ID do vendedor para filtrar (opcional)
    
    Returns:
        Dicionário com resumo dos últimos N meses:
        {
            "data_base": "YYYY-MM",
            "n_meses": N,
            "nivel": nivel,
            "meses": [
                {
                    "mes_ano": "YYYY-MM",
                    "valor_meta": float,
                    "valor_faturado": float,
                    "valor_parado": float,
                    "total_caixas": float,
                    "percentual_atingido_valor": float,
                    "percentual_atingido_volume": float,
                    # Campos adicionais conforme o nível
                },
                ...
            ]
        }
    """
    # Validação de parâmetros
    if nivel not in ["empresa", "departamento", "vendedor"]:
        raise ValueError(f"Nível inválido: {nivel}. Use 'empresa', 'departamento' ou 'vendedor'.")
    
    # 1. Calcula data_base: maior mes_ano disponível
    # Tenta metas_vendedor primeiro, se não houver dados, tenta metas_departamento
    data_base_vendedor = session.query(func.max(MetaVendedor.mes_ano)).scalar()
    data_base_departamento = session.query(func.max(MetaDepartamento.mes_ano)).scalar()
    
    # Usa a maior data entre as duas tabelas
    data_base_str = max(
        [d for d in [data_base_vendedor, data_base_departamento] if d is not None],
        default=None
    )
    
    if not data_base_str:
        logger.warning("Nenhuma meta encontrada no banco de dados")
        return {
            "data_base": None,
            "n_meses": n_meses,
            "nivel": nivel,
            "meses": []
        }
    
    # Converte data_base para datetime para calcular os meses anteriores
    try:
        data_base = datetime.strptime(data_base_str, "%Y-%m")
    except ValueError:
        logger.error(f"Erro ao converter data_base: {data_base_str}")
        return {
            "data_base": data_base_str,
            "n_meses": n_meses,
            "nivel": nivel,
            "meses": []
        }
    
    # 2. Gera lista dos últimos N meses (ordem crescente)
    meses_lista = []
    for i in range(n_meses - 1, -1, -1):  # De (n-1) até 0, decrementando
        mes = data_base - relativedelta(months=i)
        meses_lista.append(mes.strftime("%Y-%m"))
    
    logger.info(
        f"Análise de metas: data_base={data_base_str}, "
        f"n_meses={n_meses}, nivel={nivel}, "
        f"meses={meses_lista}"
    )
    
    # 3. Executa query conforme o nível
    if nivel == "empresa":
        meses_dados = _resumo_empresa(session, meses_lista)
    elif nivel == "departamento":
        meses_dados = _resumo_departamento(session, meses_lista, supervisor_id)
    elif nivel == "vendedor":
        meses_dados = _resumo_vendedor(session, meses_lista, supervisor_id, vendedor_id)
    else:
        meses_dados = []
    
    return {
        "data_base": data_base_str,
        "n_meses": n_meses,
        "nivel": nivel,
        "meses": meses_dados
    }


def _resumo_empresa(session: Session, meses_lista: List[str]) -> List[Dict[str, Any]]:
    """
    Resumo agregado por empresa (todos os departamentos/vendedores).
    """
    resultados = []
    
    # Query em metas_departamento (mais eficiente para empresa)
    query = (
        session.query(
            MetaDepartamento.mes_ano,
            func.sum(MetaDepartamento.valor_meta).label("valor_meta"),
            func.sum(MetaDepartamento.valor_faturado).label("valor_faturado"),
            func.sum(MetaDepartamento.valor_parado).label("valor_parado"),
            func.sum(MetaDepartamento.total_caixas).label("total_caixas"),
            func.sum(MetaDepartamento.qtd_meta).label("qtd_meta"),
        )
        .filter(MetaDepartamento.mes_ano.in_(meses_lista))
        .group_by(MetaDepartamento.mes_ano)
        .order_by(MetaDepartamento.mes_ano)
    )
    
    resultados_query = query.all()
    
    # Converte para dicionários e calcula percentuais
    for row in resultados_query:
        mes_ano = row.mes_ano
        valor_meta = float(row.valor_meta or 0.0)
        valor_faturado = float(row.valor_faturado or 0.0)
        valor_parado = float(row.valor_parado or 0.0)
        total_caixas = float(row.total_caixas or 0.0)
        qtd_meta = float(row.qtd_meta or 0.0)
        
        # Calcula percentuais
        perc_atingido_valor = (valor_faturado / valor_meta * 100) if valor_meta > 0 else 0.0
        perc_atingido_volume = (total_caixas / qtd_meta * 100) if qtd_meta > 0 else 0.0
        
        resultados.append({
            "mes_ano": mes_ano,
            "valor_meta": valor_meta,
            "valor_faturado": valor_faturado,
            "valor_parado": valor_parado,
            "total_caixas": total_caixas,
            "percentual_atingido_valor": round(perc_atingido_valor, 2),
            "percentual_atingido_volume": round(perc_atingido_volume, 2),
        })
    
    # Preenche meses faltantes com zeros
    meses_encontrados = {r["mes_ano"] for r in resultados}
    for mes_ano in meses_lista:
        if mes_ano not in meses_encontrados:
            resultados.append({
                "mes_ano": mes_ano,
                "valor_meta": 0.0,
                "valor_faturado": 0.0,
                "valor_parado": 0.0,
                "total_caixas": 0.0,
                "percentual_atingido_valor": 0.0,
                "percentual_atingido_volume": 0.0,
            })
    
    # Ordena por mes_ano
    resultados.sort(key=lambda x: x["mes_ano"])
    
    return resultados


def _resumo_departamento(
    session: Session,
    meses_lista: List[str],
    supervisor_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Resumo agregado por departamento (supervisor).
    """
    resultados = []
    
    query = (
        session.query(
            MetaDepartamento.mes_ano,
            MetaDepartamento.supervisor_nome,
            MetaDepartamento.departamento,
            func.sum(MetaDepartamento.valor_meta).label("valor_meta"),
            func.sum(MetaDepartamento.valor_faturado).label("valor_faturado"),
            func.sum(MetaDepartamento.valor_parado).label("valor_parado"),
            func.sum(MetaDepartamento.total_caixas).label("total_caixas"),
            func.sum(MetaDepartamento.qtd_meta).label("qtd_meta"),
        )
        .filter(MetaDepartamento.mes_ano.in_(meses_lista))
    )
    
    # Filtra por supervisor se fornecido
    if supervisor_id:
        query = query.filter(MetaDepartamento.supervisor_id == supervisor_id)
    
    query = (
        query
        .group_by(
            MetaDepartamento.mes_ano,
            MetaDepartamento.supervisor_nome,
            MetaDepartamento.departamento
        )
        .order_by(MetaDepartamento.mes_ano, MetaDepartamento.supervisor_nome)
    )
    
    resultados_query = query.all()
    
    for row in resultados_query:
        mes_ano = row.mes_ano
        supervisor_nome = row.supervisor_nome or "N/A"
        departamento = row.departamento or supervisor_nome
        
        valor_meta = float(row.valor_meta or 0.0)
        valor_faturado = float(row.valor_faturado or 0.0)
        valor_parado = float(row.valor_parado or 0.0)
        total_caixas = float(row.total_caixas or 0.0)
        qtd_meta = float(row.qtd_meta or 0.0)
        
        perc_atingido_valor = (valor_faturado / valor_meta * 100) if valor_meta > 0 else 0.0
        perc_atingido_volume = (total_caixas / qtd_meta * 100) if qtd_meta > 0 else 0.0
        
        resultados.append({
            "mes_ano": mes_ano,
            "departamento": departamento,
            "supervisor": supervisor_nome,
            "valor_meta": valor_meta,
            "valor_faturado": valor_faturado,
            "valor_parado": valor_parado,
            "total_caixas": total_caixas,
            "percentual_atingido_valor": round(perc_atingido_valor, 2),
            "percentual_atingido_volume": round(perc_atingido_volume, 2),
        })
    
    return resultados


def _resumo_vendedor(
    session: Session,
    meses_lista: List[str],
    supervisor_id: Optional[int] = None,
    vendedor_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Resumo agregado por vendedor.
    """
    resultados = []
    
    query = (
        session.query(
            MetaVendedor.mes_ano,
            MetaVendedor.vendedor_id,
            MetaVendedor.vendedor_nome,
            func.sum(MetaVendedor.valor_meta).label("valor_meta"),
            func.sum(MetaVendedor.valor_faturado).label("valor_faturado"),
            func.sum(MetaVendedor.valor_parado).label("valor_parado"),
            func.sum(MetaVendedor.total_caixas).label("total_caixas"),
            func.sum(MetaVendedor.qtd_meta).label("qtd_meta"),
        )
        .filter(MetaVendedor.mes_ano.in_(meses_lista))
    )
    
    # Filtra por vendedor se fornecido
    if vendedor_id:
        query = query.filter(MetaVendedor.vendedor_id == vendedor_id)
    
    # Filtra por supervisor se fornecido (via join com vendedores)
    if supervisor_id:
        from src.dw.models import Vendedor
        query = query.join(Vendedor, MetaVendedor.vendedor_id == Vendedor.id)
        query = query.filter(Vendedor.supervisor_id == supervisor_id)
    
    query = (
        query
        .group_by(
            MetaVendedor.mes_ano,
            MetaVendedor.vendedor_id,
            MetaVendedor.vendedor_nome
        )
        .order_by(MetaVendedor.mes_ano, MetaVendedor.vendedor_nome)
    )
    
    resultados_query = query.all()
    
    for row in resultados_query:
        mes_ano = row.mes_ano
        vendedor_id_val = row.vendedor_id
        vendedor_nome = row.vendedor_nome or f"Vendedor {vendedor_id_val}"
        
        valor_meta = float(row.valor_meta or 0.0)
        valor_faturado = float(row.valor_faturado or 0.0)
        valor_parado = float(row.valor_parado or 0.0)
        total_caixas = float(row.total_caixas or 0.0)
        qtd_meta = float(row.qtd_meta or 0.0)
        
        perc_atingido_valor = (valor_faturado / valor_meta * 100) if valor_meta > 0 else 0.0
        perc_atingido_volume = (total_caixas / qtd_meta * 100) if qtd_meta > 0 else 0.0
        
        resultados.append({
            "mes_ano": mes_ano,
            "vendedor_id": vendedor_id_val,
            "vendedor": vendedor_nome,
            "valor_meta": valor_meta,
            "valor_faturado": valor_faturado,
            "valor_parado": valor_parado,
            "total_caixas": total_caixas,
            "percentual_atingido_valor": round(perc_atingido_valor, 2),
            "percentual_atingido_volume": round(perc_atingido_volume, 2),
        })
    
    return resultados

