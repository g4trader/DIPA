"""
Queries de Dados para o Agente.

Este módulo contém funções para buscar dados do banco de dados
baseado nas intenções do usuário.
"""

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text, func, and_, or_, extract
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date
import logging

# Importações dos modelos SQLAlchemy
# Nota: Os modelos são Venda (singular) e MetaVendedor (singular), não Vendas ou MetasVendedor
from src.dw.models import (
    Vendedor, Supervisor, Cliente, Venda, MetaVendedor, MetaDepartamento
)

logger = logging.getLogger(__name__)


def analisar_meta_mensal(session: Session, ano: int, mes: int) -> Dict[str, Any]:
    """
    Análise profunda de meta mensal com KPIs, piores/melhores vendedores, clientes críticos e limites de dados.
    
    Args:
        session: Sessão SQLAlchemy
        ano: Ano (ex.: 2025)
        mes: Mês (1-12)
        
    Returns:
        dict: Dicionário com análise completa:
            - kpis: KPIs gerais do mês
            - pioresVendedores: Top 10 piores vendedores (maior impacto negativo)
            - melhoresVendedores: Top 10 melhores vendedores
            - clientesCriticos: Top 10 clientes com maior queda
            - limitesDados: Primeira e última data disponível
            - semDados: True se não houver dados para o período
    """
    mes_ano = f"{ano}-{mes:02d}"
    logger.info(f"Analisando meta mensal para {mes_ano}...")
    
    resultado = {
        "kpis": {},
        "pioresVendedores": [],
        "melhoresVendedores": [],
        "clientesCriticos": [],
        "limitesDados": {},
        "semDados": False
    }
    
    # 1) Calcula limites de dados disponíveis
    try:
        primeira_meta = session.query(func.min(MetaVendedor.mes_ano)).scalar()
        ultima_meta = session.query(func.max(MetaVendedor.mes_ano)).scalar()
        primeira_venda = None
        ultima_venda = None
        
        # Tenta buscar limites de vendas (pode falhar se não houver campo mes_ano em Venda)
        try:
            # Para SQLite, usa strftime
            primeira_venda = session.query(
                func.min(func.strftime("%Y-%m", Venda.data_venda))
            ).scalar()
            ultima_venda = session.query(
                func.max(func.strftime("%Y-%m", Venda.data_venda))
            ).scalar()
        except Exception:
            # Se falhar, tenta com extract (PostgreSQL) - usando cast do SQLAlchemy
            try:
                from sqlalchemy import cast, String
                primeira_venda = session.query(
                    func.min(
                        func.concat(
                            cast(func.extract('year', Venda.data_venda), String),
                            '-',
                            func.lpad(cast(func.extract('month', Venda.data_venda), String), 2, '0')
                        )
                    )
                ).scalar()
                ultima_venda = session.query(
                    func.max(
                        func.concat(
                            cast(func.extract('year', Venda.data_venda), String),
                            '-',
                            func.lpad(cast(func.extract('month', Venda.data_venda), String), 2, '0')
                        )
                    )
                ).scalar()
            except Exception:
                pass
        
        resultado["limitesDados"] = {
            "primeiroMesAno": primeira_meta or primeira_venda or "N/A",
            "ultimoMesAno": ultima_meta or ultima_venda or "N/A"
        }
    except Exception as e:
        logger.warning(f"Erro ao calcular limites de dados: {str(e)}")
        resultado["limitesDados"] = {
            "primeiroMesAno": "N/A",
            "ultimoMesAno": "N/A"
        }
    
    # 2) Busca dados de metas do mês
    metas_vendedor = (
        session.query(
            MetaVendedor.vendedor_id,
            MetaVendedor.vendedor_nome,
            MetaVendedor.supervisor_nome,
            func.sum(MetaVendedor.valor_meta).label("meta_total"),
            func.sum(MetaVendedor.valor_faturado).label("realizado_total"),
        )
        .filter(
            MetaVendedor.ano == ano,
            MetaVendedor.mes == mes
        )
        .group_by(
            MetaVendedor.vendedor_id,
            MetaVendedor.vendedor_nome,
            MetaVendedor.supervisor_nome
        )
        .all()
    )
    
    if not metas_vendedor:
        resultado["semDados"] = True
        return resultado
    
    # 3) Calcula KPIs gerais
    total_meta = sum(float(row.meta_total or 0) for row in metas_vendedor)
    total_realizado = sum(float(row.realizado_total or 0) for row in metas_vendedor)
    atingimento_medio = (total_realizado / total_meta * 100.0) if total_meta > 0 else 0.0
    
    # Lista de vendedores com dados calculados
    vendedores_dados = []
    for row in metas_vendedor:
        meta = float(row.meta_total or 0)
        realizado = float(row.realizado_total or 0)
        atingimento = (realizado / meta * 100.0) if meta > 0 else 0.0
        gap = realizado - meta
        
        vendedores_dados.append({
            "vendedor_id": row.vendedor_id,
            "vendedor_nome": row.vendedor_nome or "N/A",
            "supervisor_nome": row.supervisor_nome,
            "meta": meta,
            "realizado": realizado,
            "atingimento": atingimento,
            "gap": gap
        })
    
    # Conta vendedores por faixa de atingimento
    qtd_bateram = sum(1 for v in vendedores_dados if v["atingimento"] >= 100.0)
    qtd_entre_90_100 = sum(1 for v in vendedores_dados if 90.0 <= v["atingimento"] < 100.0)
    qtd_abaixo_90 = sum(1 for v in vendedores_dados if v["atingimento"] < 90.0)
    
    resultado["kpis"] = {
        "metaTotal": total_meta,
        "realizadoTotal": total_realizado,
        "atingimentoMedio": round(atingimento_medio, 2),
        "qtdVendedoresBateram": qtd_bateram,
        "qtdVendedoresEntre90e100": qtd_entre_90_100,
        "qtdVendedoresAbaixo90": qtd_abaixo_90
    }
    
    # 4) Top piores vendedores (maior impacto negativo)
    # Ordena por gap (mais negativo primeiro), depois por atingimento (menor primeiro)
    piores = sorted(
        vendedores_dados,
        key=lambda x: (x["gap"], -x["atingimento"]),  # Gap negativo primeiro, depois menor atingimento
        reverse=False  # Gap negativo vem primeiro
    )[:10]
    
    resultado["pioresVendedores"] = [
        {
            "vendedor_id": v["vendedor_id"],
            "vendedor_nome": v["vendedor_nome"],
            "supervisor_nome": v["supervisor_nome"],
            "meta": v["meta"],
            "realizado": v["realizado"],
            "atingimento": round(v["atingimento"], 2),
            "gap": round(v["gap"], 2)
        }
        for v in piores
    ]
    
    # 5) Top melhores vendedores (maior impacto positivo)
    melhores = sorted(
        vendedores_dados,
        key=lambda x: (x["gap"], -x["atingimento"]),  # Gap positivo primeiro, depois maior atingimento
        reverse=True  # Gap positivo vem primeiro
    )[:10]
    
    resultado["melhoresVendedores"] = [
        {
            "vendedor_id": v["vendedor_id"],
            "vendedor_nome": v["vendedor_nome"],
            "supervisor_nome": v["supervisor_nome"],
            "meta": v["meta"],
            "realizado": v["realizado"],
            "atingimento": round(v["atingimento"], 2),
            "gap": round(v["gap"], 2)
        }
        for v in melhores
    ]
    
    # 6) Clientes críticos (maior queda vs média dos últimos 3 meses)
    try:
        # Busca vendas do mês atual
        vendas_mes = (
            session.query(
                Venda.cliente_id,
                Cliente.nome.label("nome_cliente"),
                Venda.vendedor_id,
                Vendedor.nome.label("vendedor_nome"),
                func.sum(Venda.valor_total).label("faturamento_mes")
            )
            .join(Cliente, Venda.cliente_id == Cliente.id)
            .join(Vendedor, Venda.vendedor_id == Vendedor.id)
            .filter(
                extract('year', Venda.data_venda) == ano,
                extract('month', Venda.data_venda) == mes
            )
            .group_by(
                Venda.cliente_id,
                Cliente.nome,
                Venda.vendedor_id,
                Vendedor.nome
            )
            .all()
        )
        
        # Para cada cliente, calcula média dos últimos 3 meses (se disponível)
        clientes_com_variacao = []
        for venda_mes in vendas_mes:
            cliente_id = venda_mes.cliente_id
            faturamento_mes = float(venda_mes.faturamento_mes or 0)
            
            # Calcula média dos últimos 3 meses (excluindo o mês atual)
            meses_anteriores = []
            for i in range(1, 4):  # 1, 2, 3 meses atrás
                mes_anterior = mes - i
                ano_anterior = ano
                if mes_anterior <= 0:
                    mes_anterior += 12
                    ano_anterior -= 1
                
                try:
                    faturamento_anterior = (
                        session.query(func.sum(Venda.valor_total))
                        .filter(
                            Venda.cliente_id == cliente_id,
                            extract('year', Venda.data_venda) == ano_anterior,
                            extract('month', Venda.data_venda) == mes_anterior
                        )
                        .scalar()
                    )
                    if faturamento_anterior:
                        meses_anteriores.append(float(faturamento_anterior))
                except Exception:
                    pass
            
            if meses_anteriores:
                faturamento_media_3m = sum(meses_anteriores) / len(meses_anteriores)
                variacao_percentual = ((faturamento_mes - faturamento_media_3m) / faturamento_media_3m * 100.0) if faturamento_media_3m > 0 else 0.0
                
                clientes_com_variacao.append({
                    "cliente_id": cliente_id,
                    "nome_cliente": venda_mes.nome_cliente or "N/A",
                    "vendedor_nome": venda_mes.vendedor_nome or "N/A",
                    "faturamento_mes": faturamento_mes,
                    "faturamento_media_3m": round(faturamento_media_3m, 2),
                    "variacao_percentual": round(variacao_percentual, 2)
                })
        
        # Ordena por maior queda (variacao_percentual mais negativo)
        clientes_criticos = sorted(
            clientes_com_variacao,
            key=lambda x: x["variacao_percentual"]
        )[:10]  # Top 10 com maior queda
        
        resultado["clientesCriticos"] = clientes_criticos
        
    except Exception as e:
        logger.warning(f"Erro ao calcular clientes críticos: {str(e)}")
        # Continua sem clientes críticos, mas não falha a análise completa
        resultado["clientesCriticos"] = []
    
    return resultado


# ============================================================================
# FUNÇÕES DE FALLBACK (necessárias para compatibilidade com service.py)
# ============================================================================

def query_meta_realizado_por_mes(session: Session, meses_retroativos: int = 6) -> List[Dict[str, Any]]:
    """
    Retorna meta x realizado agregados por mês (em valor), usando MetaDepartamento como fonte.
    
    Args:
        session: Sessão SQLAlchemy
        meses_retroativos: Número de meses retroativos para buscar
        
    Returns:
        List[Dict]: Lista de dicionários com mes_ano, meta, realizado e atingimento
    """
    logger.info(f"Buscando meta x realizado por mês (últimos {meses_retroativos} meses)...")
    
    # Descobrir os meses disponíveis ordenados
    try:
        subq = (
            session.query(
                MetaDepartamento.ano,
                MetaDepartamento.mes
            )
            .distinct()
            .order_by(MetaDepartamento.ano.desc(), MetaDepartamento.mes.desc())
        ).all()
        
        if not subq:
            return []
        
        # Limita à janela
        meses = subq[:meses_retroativos]
        resultados = []
        
        for ano, mes in meses:
            rows = (
                session.query(
                    MetaDepartamento.mes_ano,
                    func.sum(MetaDepartamento.valor_meta).label("meta_total"),
                    func.sum(MetaDepartamento.valor_faturado).label("realizado_total"),
                )
                .filter(MetaDepartamento.ano == ano, MetaDepartamento.mes == mes)
                .group_by(MetaDepartamento.mes_ano)
                .all()
            )
            
            for row in rows:
                meta = float(row.meta_total or 0)
                realizado = float(row.realizado_total or 0)
                atingimento = (realizado / meta * 100.0) if meta > 0 else None
                
                resultados.append({
                    "mes_ano": row.mes_ano,
                    "meta": meta,
                    "realizado": realizado,
                    "atingimento": atingimento,
                })
        
        # Ordena cronologicamente
        resultados.sort(key=lambda x: x["mes_ano"])
        return resultados
        
    except Exception as e:
        logger.error(f"Erro ao buscar meta x realizado por mês: {str(e)}")
        return []


def query_meta_realizado_por_vendedor(session: Session, mes_ano: str) -> List[Dict[str, Any]]:
    """
    Para um determinado mês (YYYY-MM), retorna meta x realizado por vendedor.
    
    Args:
        session: Sessão SQLAlchemy
        mes_ano: Mês/ano no formato YYYY-MM
        
    Returns:
        List[Dict]: Lista de vendedores com meta, realizado e atingimento
    """
    logger.info(f"Buscando meta x realizado por vendedor para {mes_ano}...")
    
    try:
        rows = (
            session.query(
                MetaVendedor.vendedor_id,
                MetaVendedor.vendedor_nome,
                func.sum(MetaVendedor.valor_meta).label("meta_total"),
                func.sum(MetaVendedor.valor_faturado).label("realizado_total"),
            )
            .filter(MetaVendedor.mes_ano == mes_ano)
            .group_by(MetaVendedor.vendedor_id, MetaVendedor.vendedor_nome)
            .all()
        )
        
        resultados = []
        for row in rows:
            meta = float(row.meta_total or 0)
            realizado = float(row.realizado_total or 0)
            atingimento = (realizado / meta * 100.0) if meta > 0 else None
            
            resultados.append({
                "vendedor_id": row.vendedor_id,
                "vendedor_nome": row.vendedor_nome,
                "meta": meta,
                "realizado": realizado,
                "atingimento": atingimento,
            })
        
        # Ordena por atingimento crescente (quem está pior vem primeiro)
        resultados.sort(key=lambda x: (x["atingimento"] if x["atingimento"] is not None else 9999))
        
        logger.info(f"Encontrados {len(resultados)} vendedores para {mes_ano}")
        return resultados
        
    except Exception as e:
        logger.error(f"Erro ao buscar meta x realizado por vendedor: {str(e)}")
        return []


def query_meses_disponiveis_metas(session: Session) -> List[str]:
    """
    Retorna lista de meses disponíveis (YYYY-MM) ordenados cronologicamente.
    
    Args:
        session: Sessão SQLAlchemy
        
    Returns:
        List[str]: Lista de mes_ano (ex.: ["2024-11", "2024-12", "2025-01"])
    """
    logger.info("Buscando meses disponíveis de metas...")
    
    try:
        # Busca de MetaVendedor
        meses_vendedor = (
            session.query(MetaVendedor.mes_ano)
            .distinct()
            .all()
        )
        
        # Busca de MetaDepartamento
        meses_departamento = (
            session.query(MetaDepartamento.mes_ano)
            .distinct()
            .all()
        )
        
        # Combina e remove duplicatas
        todos_meses = set()
        for row in meses_vendedor:
            if row.mes_ano:
                todos_meses.add(row.mes_ano)
        for row in meses_departamento:
            if row.mes_ano:
                todos_meses.add(row.mes_ano)
        
        # Ordena cronologicamente
        meses_ordenados = sorted(list(todos_meses))
        
        logger.info(f"Encontrados {len(meses_ordenados)} meses disponíveis")
        return meses_ordenados
        
    except Exception as e:
        logger.error(f"Erro ao buscar meses disponíveis: {str(e)}")
        return []


# Funções stub para evitar erros de importação (implementações básicas)
def query_vendedor_meta(session: Session, vendedor_nome: str, mes_ano: str) -> Dict[str, Any]:
    """Stub function - implementação básica"""
    logger.warning(f"query_vendedor_meta chamada mas não implementada completamente")
    return {"erro": "Função não implementada"}


def query_clientes_churn(session: Session, **kwargs) -> Dict[str, Any]:
    """Stub function"""
    return {}


def query_vendas_analise(session: Session, **kwargs) -> Dict[str, Any]:
    """Stub function"""
    return {}


def query_supervisor_meta(session: Session, supervisor: str, mes_ano: str) -> Dict[str, Any]:
    """Stub function"""
    return {"erro": "Função não implementada"}


def query_metas_departamento_agregadas(session: Session, mes_ano: str) -> Dict[str, Any]:
    """Stub function"""
    return {}


def query_vendedores_que_bateram_meta(session: Session, mes_ano: str) -> List[Dict[str, Any]]:
    """Stub function"""
    return []


def query_metas_vendedor_multiplos_meses(session: Session, meses_ano: List[str]) -> Dict[str, Any]:
    """Stub function"""
    return {}


def query_vendedores_pior_performance(session: Session, mes_ano: str, top_n: int = 15) -> List[Dict[str, Any]]:
    """Stub function"""
    return []


def query_piores_vendedores_por_meta(session: Session, mes_ano: str, limite: int = 10, top_n: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Retorna os vendedores com pior desempenho (não bateram meta).
    
    Args:
        session: Sessão SQLAlchemy
        mes_ano: Mês/ano no formato YYYY-MM
        limite: Número de vendedores a retornar (compatibilidade)
        top_n: Número de vendedores a retornar (prioridade sobre limite)
        
    Returns:
        List[Dict]: Lista de vendedores com pior desempenho
    """
    # Usa top_n se fornecido, senão usa limite
    n = top_n if top_n is not None else limite
    
    try:
        ano, mes = mes_ano.split("-")
        analise = analisar_meta_mensal(session, int(ano), int(mes))
        piores = analise.get("pioresVendedores", [])
        
        # Filtra apenas vendedores que NÃO bateram meta (atingimento < 100)
        piores_que_nao_bateram = [
            v for v in piores 
            if v.get("atingimento", 0) < 100.0
        ]
        
        # Limita ao número solicitado
        return piores_que_nao_bateram[:n]
    except Exception as e:
        logger.warning(f"Erro ao buscar piores vendedores: {str(e)}")
        return []


def query_vendedores_menor_venda(session: Session, mes_ano: str, limite: int = 10) -> List[Dict[str, Any]]:
    """Stub function"""
    return []
