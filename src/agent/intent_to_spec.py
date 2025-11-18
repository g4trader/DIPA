"""
Conversor de Intenção para IntentSpec - DIPAM COPILOT™.

Este módulo converte a intenção detectada (IntentType) e entidades
extraídas em uma IntentSpec estruturada para execução na camada DW.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from src.agent.intent import IntentType
from src.agent.intent_spec import (
    IntentSpec,
    criar_intent_spec_meta,
    criar_intent_spec_clientes_criticos,
    criar_intent_spec_vendas,
    criar_intent_spec_ranking_vendedores
)

logger = logging.getLogger(__name__)


def calcular_periodo_ultimos_meses(n_meses: int) -> tuple[Optional[str], Optional[str]]:
    """
    Calcula período inicial e final para "últimos N meses".
    
    Args:
        n_meses: Número de meses (ex.: 6 para "últimos 6 meses")
        
    Returns:
        tuple: (periodo_inicio, periodo_fim) no formato "YYYY-MM"
    """
    hoje = datetime.now()
    # Calcula mês inicial (N meses atrás)
    mes_inicio = hoje - timedelta(days=30 * n_meses)
    periodo_inicio = mes_inicio.strftime("%Y-%m")
    periodo_fim = hoje.strftime("%Y-%m")
    
    return periodo_inicio, periodo_fim


def intent_to_spec(
    intent: IntentType,
    entities: Dict[str, Any]
) -> IntentSpec:
    """
    Converte intenção detectada e entidades em IntentSpec.
    
    Args:
        intent: Tipo de intenção detectada
        entities: Entidades extraídas da pergunta
        
    Returns:
        IntentSpec configurada para execução na camada DW
    """
    mes_ano = entities.get("mes_ano")
    n_meses = entities.get("n_meses") or entities.get("janela_meses")
    
    # Calcula período
    periodo_inicio = mes_ano
    periodo_fim = mes_ano
    
    # Se tem "últimos N meses", calcula período
    if n_meses:
        periodo_inicio, periodo_fim = calcular_periodo_ultimos_meses(n_meses)
    
    # Se não tem período, usa mês atual como padrão
    if not periodo_inicio:
        hoje = datetime.now()
        periodo_inicio = hoje.strftime("%Y-%m")
        periodo_fim = periodo_inicio
    
    # Extrai filtros
    supervisor_id = entities.get("supervisor_id")  # Se já foi resolvido
    vendedor_id = entities.get("vendedor_id")  # Se já foi resolvido
    rota = entities.get("rota")
    
    # Mapeia intenção para tipo de IntentSpec
    if intent == IntentType.CONSULTA_META or intent == IntentType.MOTIVO_NAO_BATEU_META:
        return criar_intent_spec_meta(
            periodo_inicio=periodo_inicio,
            periodo_fim=periodo_fim,
            supervisor_id=supervisor_id,
            vendedor_id=vendedor_id,
            rota=rota,
            confianca=0.8
        )
    
    elif intent == IntentType.CLIENTES_RISCO_CHURN or intent == IntentType.CHURN_CLIENTES:
        return criar_intent_spec_clientes_criticos(
            periodo_inicio=periodo_inicio,
            periodo_fim=periodo_fim,
            supervisor_id=supervisor_id,
            rota_id=vendedor_id,
            limite=50,
            confianca=0.8
        )
    
    elif intent == IntentType.VENDAS_ANALISE:
        dimensao = "mes"  # Padrão
        if entities.get("vendedor") or entities.get("rota"):
            dimensao = "vendedor"
        elif entities.get("supervisor"):
            dimensao = "supervisor"
        
        return criar_intent_spec_vendas(
            periodo_inicio=periodo_inicio,
            periodo_fim=periodo_fim,
            dimensao=dimensao,
            confianca=0.8
        )
    
    elif intent == IntentType.CONSULTA_VENDEDORES_PERFORMANCE:
        # Ranking de vendedores
        mes = periodo_inicio
        ordenacao = "gap"  # Padrão: ordena por gap negativo
        if "atingimento" in entities.get("pergunta_original", "").lower():
            ordenacao = "atingimento"
        elif "faturamento" in entities.get("pergunta_original", "").lower():
            ordenacao = "faturamento"
        
        return criar_intent_spec_ranking_vendedores(
            mes=mes,
            ordenacao=ordenacao,
            limite=10,
            confianca=0.8
        )
    
    # ========================================================================
    # TIPOS DW OFICIAIS (Q1-Q13 do ENGINEERING_QUERIES.md) - FIRST-CLASS
    # ========================================================================
    
    elif intent == IntentType.CLIENTES_SEM_COMPRA:
        # Q1: Clientes ativos sem compras há N dias
        filtros = {
            "dias": entities.get("dias") or entities.get("dias_sem_compra") or 60,
            "data_referencia": entities.get("data_referencia")
        }
        return IntentSpec(
            tipo="clientes_sem_compra",
            periodo_inicio=periodo_inicio,
            periodo_fim=periodo_fim,
            dimensao_principal="cliente",
            filtros=filtros,
            metricas=["dias_sem_compra", "ultima_compra"],
            confianca=0.8,
            entidades_extraidas=entities
        )
    
    elif intent == IntentType.QUEDA_FATURAMENTO:
        # Q2: Queda de faturamento ano contra ano
        filtros = {
            "ano_base": entities.get("ano_base") or 2024,
            "ano_comparado": entities.get("ano_comparado") or 2025,
            "top_n": entities.get("top_n") or entities.get("limite") or 50
        }
        return IntentSpec(
            tipo="queda_faturamento",
            periodo_inicio=periodo_inicio,
            periodo_fim=periodo_fim,
            dimensao_principal="cliente",
            filtros=filtros,
            metricas=["faturamento_base", "faturamento_comparado", "delta_faturamento", "delta_percentual"],
            confianca=0.8,
            entidades_extraidas=entities
        )
    
    elif intent == IntentType.META_DEPARTAMENTO_DW:
        # Q3: Indústrias com mais vendedores fora da meta
        # Extrai ano/mês do período ou entities
        ano = entities.get("ano")
        mes = entities.get("mes")
        if periodo_inicio and not ano:
            try:
                ano = int(periodo_inicio.split("-")[0])
                mes = int(periodo_inicio.split("-")[1])
            except (ValueError, IndexError):
                pass
        
        filtros = {
            "ano": ano,
            "mes": mes,
            "atingimento_limite": entities.get("atingimento_limite") or 100.0
        }
        return IntentSpec(
            tipo="meta_departamento",
            periodo_inicio=periodo_inicio,
            periodo_fim=periodo_fim,
            dimensao_principal="nenhuma",
            filtros=filtros,
            metricas=["qtd_vendedores_fora_meta"],
            confianca=0.8,
            entidades_extraidas=entities
        )
    
    elif intent == IntentType.POSITIVACAO:
        # Q4: Rotas com melhor/pior positivação de indústria
        filtros = {
            "industria": entities.get("industria") or entities.get("marca") or "",
            "data_inicio": periodo_inicio or "",
            "data_fim": periodo_fim or ""
        }
        return IntentSpec(
            tipo="positivacao",
            periodo_inicio=periodo_inicio,
            periodo_fim=periodo_fim,
            dimensao_principal="rota",
            filtros=filtros,
            metricas=["clientes_positivados", "total_clientes_ativos", "positivacao_pct"],
            confianca=0.8,
            entidades_extraidas=entities
        )
    
    elif intent == IntentType.MIX:
        # Q5: Itens com baixa média mensal
        filtros = {
            "meses_janela": entities.get("meses_janela") or entities.get("janela_meses") or 12,
            "limite_media": entities.get("limite_media") or entities.get("limite") or 10.0,
            "data_referencia": entities.get("data_referencia") or periodo_fim or periodo_inicio
        }
        return IntentSpec(
            tipo="mix",
            periodo_inicio=periodo_inicio,
            periodo_fim=periodo_fim,
            dimensao_principal="produto",
            filtros=filtros,
            metricas=["media_mensal", "qtd_total", "meses_com_venda"],
            confianca=0.8,
            entidades_extraidas=entities
        )
    
    elif intent == IntentType.RECOMPRA:
        # Q6: Clientes sem recompra de SKU
        filtros = {
            "sku": entities.get("sku") or entities.get("produto") or "",
            "meses_janela": entities.get("meses_janela") or entities.get("janela_meses") or 6,
            "data_referencia": entities.get("data_referencia") or periodo_fim or periodo_inicio
        }
        return IntentSpec(
            tipo="recompra",
            periodo_inicio=periodo_inicio,
            periodo_fim=periodo_fim,
            dimensao_principal="cliente",
            filtros=filtros,
            metricas=["qtd_compras", "primeira_compra", "ultima_compra"],
            confianca=0.8,
            entidades_extraidas=entities
        )
    
    elif intent == IntentType.CLIENTES_SEM_ITEM:
        # Q7/Q9/Q10/Q11: Clientes sem positivação de SKU no período
        filtros = {
            "sku": entities.get("sku") or entities.get("produto") or "",
            "segmento": entities.get("segmento"),
            "data_inicio": periodo_inicio or "",
            "data_fim": periodo_fim or ""
        }
        return IntentSpec(
            tipo="clientes_sem_item",
            periodo_inicio=periodo_inicio,
            periodo_fim=periodo_fim,
            dimensao_principal="cliente",
            filtros=filtros,
            metricas=[],
            confianca=0.8,
            entidades_extraidas=entities
        )
    
    elif intent == IntentType.VENDAS_BAIXAS:
        # Q8: Clientes com apenas 1 unidade de indústria no mês
        # Extrai ano/mês do período ou entities
        ano = entities.get("ano")
        mes = entities.get("mes")
        if periodo_inicio and not ano:
            try:
                ano = int(periodo_inicio.split("-")[0])
                mes = int(periodo_inicio.split("-")[1])
            except (ValueError, IndexError):
                pass
        
        filtros = {
            "industria": entities.get("industria") or entities.get("marca") or "",
            "ano": ano,
            "mes": mes
        }
        return IntentSpec(
            tipo="vendas_baixas",
            periodo_inicio=periodo_inicio,
            periodo_fim=periodo_fim,
            dimensao_principal="cliente",
            filtros=filtros,
            metricas=["qtd_total"],
            confianca=0.8,
            entidades_extraidas=entities
        )
    
    elif intent == IntentType.MIX_NISSIN:
        # Q12/Q13: Mix mínimo de Nissin
        # Extrai ano/mês do período ou entities
        ano = entities.get("ano")
        mes = entities.get("mes")
        if periodo_inicio and not ano:
            try:
                ano = int(periodo_inicio.split("-")[0])
                mes = int(periodo_inicio.split("-")[1])
            except (ValueError, IndexError):
                pass
        
        # Dimensão pode ser "cliente" ou "rota" dependendo da pergunta
        dimensao = entities.get("dimensao") or "cliente"
        if "rota" in entities.get("pergunta_original", "").lower() or "rota" in str(entities.get("rota", "")).lower():
            dimensao = "rota"
        
        filtros = {
            "ano": ano,
            "mes": mes
        }
        return IntentSpec(
            tipo="mix_nissin",
            periodo_inicio=periodo_inicio,
            periodo_fim=periodo_fim,
            dimensao_principal=dimensao,
            filtros=filtros,
            metricas=["qtd_skus_nissin", "mix_completo"],
            confianca=0.8,
            entidades_extraidas=entities
        )
    
    else:
        # Fallback: intent genérica (APENAS para tipos realmente não mapeados)
        # NUNCA usar para tipos DW oficiais (Q1-Q13)
        logger.warning(f"[intent_to_spec] Intent não mapeada: {intent.value}, usando fallback")
        return IntentSpec(
            tipo="outros",
            periodo_inicio=periodo_inicio,
            periodo_fim=periodo_fim,
            dimensao_principal="nenhuma",
            filtros={},
            metricas=[],
            confianca=0.5,
            entidades_extraidas=entities
        )

