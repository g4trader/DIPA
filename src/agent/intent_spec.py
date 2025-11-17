"""
Especificação de Intenção (IntentSpec) para o DIPAM COPILOT™.

Este módulo define a estrutura de dados que representa uma intenção
de negócio do usuário, traduzida em uma especificação de consulta
para a camada DW.

ARQUITETURA:
- IntentSpec é uma abstração que traduz perguntas em consultas DW
- Usa SEMPRE a camada DW (analytics_metas.py, queries_*.py)
- NUNCA faz queries diretas no SQLite
- BigQuery NÃO implementado (apenas roadmap)
"""

from dataclasses import dataclass, field
from typing import Literal, Optional, Dict, Any, List
from datetime import date


@dataclass
class IntentSpec:
    """
    Especificação de intenção de negócio traduzida em consulta DW.
    
    Representa o que o usuário quer saber, transformado em uma
    especificação estruturada que pode ser executada na camada DW.
    """
    # Tipo de intenção
    tipo: Literal[
        "meta",
        "vendas",
        "clientes_criticos",
        "churn",
        "ranking_vendedores",
        "ranking_produtos",
        "analise_meta_detalhada",
        "metas_por_supervisor",
        "vendas_por_mes",
        "outros"
    ]
    
    # Período de análise
    periodo_inicio: Optional[str] = None  # "YYYY-MM" ou None
    periodo_fim: Optional[str] = None  # "YYYY-MM" ou None
    
    # Dimensão principal da análise
    dimensao_principal: Literal[
        "mes",
        "vendedor",
        "supervisor",
        "rota",
        "cliente",
        "marca",
        "categoria",
        "sku",
        "nenhuma"
    ] = "nenhuma"
    
    # Filtros opcionais
    filtros: Dict[str, Any] = field(default_factory=dict)
    # Exemplos de filtros:
    # - supervisor_id: int
    # - vendedor_id: int
    # - rota: str (ex.: "ROTA 22")
    # - cliente_id: int
    # - departamento: str
    # - marca: str
    # - categoria: str
    
    # Métricas solicitadas
    metricas: List[str] = field(default_factory=list)
    # Exemplos de métricas:
    # - "meta_total"
    # - "realizado_total"
    # - "atingimento_medio"
    # - "gap_total"
    # - "faturamento_total"
    # - "churn_score"
    # - "quantidade_vendas"
    
    # Metadados adicionais
    confianca: float = 0.5  # Confiança na detecção da intenção (0-1)
    entidades_extraidas: Dict[str, Any] = field(default_factory=dict)
    # Exemplos de entidades:
    # - mes_ano: "2025-08"
    # - vendedor_nome: "ROTA 22"
    # - supervisor_nome: "Supervisor Leandro"
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte IntentSpec para dicionário."""
        return {
            "tipo": self.tipo,
            "periodo_inicio": self.periodo_inicio,
            "periodo_fim": self.periodo_fim,
            "dimensao_principal": self.dimensao_principal,
            "filtros": self.filtros,
            "metricas": self.metricas,
            "confianca": self.confianca,
            "entidades_extraidas": self.entidades_extraidas
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IntentSpec":
        """Cria IntentSpec a partir de dicionário."""
        return cls(
            tipo=data.get("tipo", "outros"),
            periodo_inicio=data.get("periodo_inicio"),
            periodo_fim=data.get("periodo_fim"),
            dimensao_principal=data.get("dimensao_principal", "nenhuma"),
            filtros=data.get("filtros", {}),
            metricas=data.get("metricas", []),
            confianca=data.get("confianca", 0.5),
            entidades_extraidas=data.get("entidades_extraidas", {})
        )


def criar_intent_spec_meta(
    periodo_inicio: Optional[str] = None,
    periodo_fim: Optional[str] = None,
    supervisor_id: Optional[int] = None,
    vendedor_id: Optional[int] = None,
    rota: Optional[str] = None,
    confianca: float = 0.8
) -> IntentSpec:
    """
    Cria IntentSpec para consulta de meta.
    
    Args:
        periodo_inicio: Mês inicial "YYYY-MM"
        periodo_fim: Mês final "YYYY-MM"
        supervisor_id: Filtrar por supervisor
        vendedor_id: Filtrar por vendedor
        rota: Filtrar por rota (ex.: "ROTA 22")
        confianca: Confiança na detecção
        
    Returns:
        IntentSpec configurado para consulta de meta
    """
    filtros = {}
    if supervisor_id:
        filtros["supervisor_id"] = supervisor_id
    if vendedor_id:
        filtros["vendedor_id"] = vendedor_id
    if rota:
        filtros["rota"] = rota
    
    dimensao = "nenhuma"
    if periodo_inicio and periodo_fim and periodo_inicio != periodo_fim:
        dimensao = "mes"
    elif supervisor_id:
        dimensao = "supervisor"
    elif vendedor_id or rota:
        dimensao = "vendedor"
    
    return IntentSpec(
        tipo="meta",
        periodo_inicio=periodo_inicio,
        periodo_fim=periodo_fim,
        dimensao_principal=dimensao,
        filtros=filtros,
        metricas=["meta_total", "realizado_total", "atingimento_medio", "gap_total"],
        confianca=confianca
    )


def criar_intent_spec_clientes_criticos(
    periodo_inicio: Optional[str] = None,
    periodo_fim: Optional[str] = None,
    supervisor_id: Optional[int] = None,
    rota_id: Optional[int] = None,
    limite: int = 50,
    confianca: float = 0.8
) -> IntentSpec:
    """
    Cria IntentSpec para consulta de clientes críticos (churn).
    
    Args:
        periodo_inicio: Mês inicial "YYYY-MM"
        periodo_fim: Mês final "YYYY-MM"
        supervisor_id: Filtrar por supervisor
        rota_id: Filtrar por rota/vendedor
        limite: Número máximo de clientes
        confianca: Confiança na detecção
        
    Returns:
        IntentSpec configurado para consulta de clientes críticos
    """
    filtros = {}
    if supervisor_id:
        filtros["supervisor_id"] = supervisor_id
    if rota_id:
        filtros["rota_id"] = rota_id
    filtros["limite"] = limite
    
    return IntentSpec(
        tipo="clientes_criticos",
        periodo_inicio=periodo_inicio,
        periodo_fim=periodo_fim,
        dimensao_principal="cliente",
        filtros=filtros,
        metricas=["churn_score", "dias_sem_compra", "faturamento_total"],
        confianca=confianca
    )


def criar_intent_spec_vendas(
    periodo_inicio: Optional[str] = None,
    periodo_fim: Optional[str] = None,
    dimensao: Literal["mes", "vendedor", "supervisor", "cliente", "produto"] = "mes",
    confianca: float = 0.8
) -> IntentSpec:
    """
    Cria IntentSpec para consulta de vendas.
    
    Args:
        periodo_inicio: Mês inicial "YYYY-MM"
        periodo_fim: Mês final "YYYY-MM"
        dimensao: Dimensão principal da análise
        confianca: Confiança na detecção
        
    Returns:
        IntentSpec configurado para consulta de vendas
    """
    return IntentSpec(
        tipo="vendas",
        periodo_inicio=periodo_inicio,
        periodo_fim=periodo_fim,
        dimensao_principal=dimensao,
        filtros={},
        metricas=["faturamento_total", "quantidade_vendas", "quantidade_clientes", "ticket_medio"],
        confianca=confianca
    )


def criar_intent_spec_ranking_vendedores(
    mes: str,
    ordenacao: Literal["gap", "atingimento", "faturamento"] = "gap",
    limite: int = 10,
    confianca: float = 0.8
) -> IntentSpec:
    """
    Cria IntentSpec para ranking de vendedores.
    
    Args:
        mes: Mês no formato "YYYY-MM"
        ordenacao: Critério de ordenação
        limite: Número máximo de vendedores
        confianca: Confiança na detecção
        
    Returns:
        IntentSpec configurado para ranking de vendedores
    """
    return IntentSpec(
        tipo="ranking_vendedores",
        periodo_inicio=mes,
        periodo_fim=mes,
        dimensao_principal="vendedor",
        filtros={"ordenacao": ordenacao, "limite": limite},
        metricas=["meta_total", "realizado_total", "atingimento_pct", "gap_valor"],
        confianca=confianca
    )

