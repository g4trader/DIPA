"""
Builder para respostas estruturadas do DIPAM COPILOT™.

Este módulo contém funções helper para construir respostas estruturadas
no formato CopilotStructuredResponse a partir de dados das tabelas analytics_*.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import time
import logging

from src.agent.schemas_structured import (
    CopilotStructuredResponse, SecaoResposta, DetalheTabela, ContextoDebug
)
from src.dw.models_analytics import AnalyticsVendedorMes, AnalyticsClienteMes, AnalyticsProdutoMes

logger = logging.getLogger(__name__)


def construir_secao_vendedores(
    vendedores: List[AnalyticsVendedorMes],
    titulo: str = "Principais responsáveis pelo não atingimento da meta"
) -> SecaoResposta:
    """
    Constrói seção de lista de vendedores a partir de AnalyticsVendedorMes.
    
    Args:
        vendedores: Lista de objetos AnalyticsVendedorMes
        titulo: Título da seção
        
    Returns:
        SecaoResposta com dados formatados
    """
    dados = []
    for v in vendedores:
        dados.append({
            "vendedor_id": v.vendedor_id,
            "vendedor_nome": v.vendedor_nome,
            "supervisor_id": v.supervisor_id,
            "supervisor_nome": getattr(v.supervisor, 'nome', None) if hasattr(v, 'supervisor') and v.supervisor else None,
            "mes_ano": v.mes_ano,
            "meta_total": float(v.meta_total),
            "realizado_total": float(v.realizado_total),
            "atingimento_pct": float(v.atingimento_pct) if v.atingimento_pct else None,
            "gap_valor": float(v.gap_valor) if v.gap_valor else None,
            "rank_atingimento": v.rank_atingimento,
            "meta_risk_score": float(v.meta_risk_score) if v.meta_risk_score else None,
            "meta_risk_flag": v.meta_risk_flag,
            "qtd_clientes_positivados": v.qtd_clientes_positivados,
            "qtd_clientes_churn": v.qtd_clientes_churn,
            "qtd_skus": v.qtd_skus,
        })
    
    return SecaoResposta(
        titulo=titulo,
        tipo="lista_vendedores",
        dados=dados
    )


def construir_secao_clientes(
    clientes: List[AnalyticsClienteMes],
    titulo: str = "Clientes em risco (churn elevado)"
) -> SecaoResposta:
    """
    Constrói seção de lista de clientes a partir de AnalyticsClienteMes.
    
    Args:
        clientes: Lista de objetos AnalyticsClienteMes
        titulo: Título da seção
        
    Returns:
        SecaoResposta com dados formatados
    """
    dados = []
    for c in clientes:
        dados.append({
            "cliente_id": c.cliente_id,
            "cliente_nome": c.cliente_nome,
            "vendedor_id": c.vendedor_id,
            "vendedor_nome": getattr(c.vendedor, 'nome', None) if hasattr(c, 'vendedor') and c.vendedor else None,
            "mes_ano": c.mes_ano,
            "faturamento_total": float(c.faturamento_total),
            "faturamento_media_3m": float(c.faturamento_media_3m) if c.faturamento_media_3m else None,
            "variacao_pct_vs_3m": float(c.variacao_pct_vs_3m) if c.variacao_pct_vs_3m else None,
            "qtd_compras": c.qtd_compras,
            "dias_desde_ultima_compra": c.dias_desde_ultima_compra,
            "churn_score": float(c.churn_score) if c.churn_score else None,
            "churn_flag": c.churn_flag,
        })
    
    return SecaoResposta(
        titulo=titulo,
        tipo="lista_clientes",
        dados=dados
    )


def construir_secao_produtos(
    produtos: List[AnalyticsProdutoMes],
    titulo: str = "Produtos com queda forte de vendas"
) -> SecaoResposta:
    """
    Constrói seção de lista de produtos a partir de AnalyticsProdutoMes.
    
    Args:
        produtos: Lista de objetos AnalyticsProdutoMes
        titulo: Título da seção
        
    Returns:
        SecaoResposta com dados formatados
    """
    dados = []
    for p in produtos:
        dados.append({
            "codigo_produto": p.codigo_produto,
            "desc_produto": p.desc_produto,
            "mes_ano": p.mes_ano,
            "faturamento_total": float(p.faturamento_total),
            "qtd_vendida": p.qtd_vendida,
            "qtd_clientes_ativos": p.qtd_clientes_ativos,
            "variacao_pct_vs_3m": float(p.variacao_pct_vs_3m) if p.variacao_pct_vs_3m else None,
            "queda_score": float(p.queda_score) if p.queda_score else None,
            "queda_flag": p.queda_flag,
            "participacao_no_faturamento": float(p.participacao_no_faturamento) if p.participacao_no_faturamento else None,
        })
    
    return SecaoResposta(
        titulo=titulo,
        tipo="lista_produtos",
        dados=dados
    )


def construir_secao_recomendacoes(
    recomendacoes: List[Dict[str, Any]],
    titulo: str = "Ações recomendadas para o Diretor"
) -> SecaoResposta:
    """
    Constrói seção de recomendações.
    
    Args:
        recomendacoes: Lista de dicionários com {"descricao": str, "prioridade": str, ...}
        titulo: Título da seção
        
    Returns:
        SecaoResposta com dados formatados
    """
    return SecaoResposta(
        titulo=titulo,
        tipo="lista_recomendacoes",
        dados=recomendacoes
    )


def construir_detalhe_tabela_vendedores(
    vendedores: List[AnalyticsVendedorMes],
    titulo: Optional[str] = None
) -> DetalheTabela:
    """
    Constrói tabela detalhada de vendedores.
    
    Args:
        vendedores: Lista de objetos AnalyticsVendedorMes
        titulo: Título opcional da tabela
        
    Returns:
        DetalheTabela formatado
    """
    colunas = [
        "vendedor_nome",
        "mes_ano",
        "meta_total",
        "realizado_total",
        "atingimento_pct",
        "gap_valor",
        "meta_risk_score"
    ]
    
    linhas = []
    for v in vendedores:
        linhas.append([
            v.vendedor_nome,
            v.mes_ano,
            float(v.meta_total),
            float(v.realizado_total),
            float(v.atingimento_pct) if v.atingimento_pct else None,
            float(v.gap_valor) if v.gap_valor else None,
            float(v.meta_risk_score) if v.meta_risk_score else None,
        ])
    
    return DetalheTabela(
        colunas=colunas,
        linhas=linhas,
        titulo=titulo or "Detalhamento de Vendedores"
    )


def construir_contexto_debug(
    intent: str,
    entities: Dict[str, Any],
    mes_ano: Optional[str] = None,
    fonte_dados: str = "analytics_*",
    total_registros: Optional[int] = None,
    tempo_processamento_ms: Optional[float] = None
) -> ContextoDebug:
    """
    Constrói contexto de debug para a resposta.
    
    Args:
        intent: Intent detectada
        entities: Entidades extraídas
        mes_ano: Mês/ano resolvido
        fonte_dados: Fonte dos dados usados
        total_registros: Total de registros processados
        tempo_processamento_ms: Tempo de processamento em milissegundos
        
    Returns:
        ContextoDebug formatado
    """
    return ContextoDebug(
        intent=intent,
        entidades=entities,
        fonte_dados=fonte_dados,
        mes_ano_resolvido=mes_ano,
        total_registros=total_registros,
        tempo_processamento_ms=tempo_processamento_ms
    )


def construir_resposta_estruturada(
    resumo_executivo: str,
    secoes: List[SecaoResposta],
    detalhe_tabela: Optional[DetalheTabela] = None,
    contexto_debug: Optional[ContextoDebug] = None
) -> CopilotStructuredResponse:
    """
    Constrói resposta estruturada completa.
    
    Args:
        resumo_executivo: Texto do resumo executivo
        secoes: Lista de seções
        detalhe_tabela: Tabela detalhada (opcional)
        contexto_debug: Contexto de debug (opcional)
        
    Returns:
        CopilotStructuredResponse completo
    """
    return CopilotStructuredResponse(
        resumo_executivo=resumo_executivo,
        secoes=secoes,
        detalhe_tabela=detalhe_tabela,
        contexto_debug=contexto_debug
    )

