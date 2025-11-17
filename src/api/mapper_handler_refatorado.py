"""
Mapper para converter resposta do handler refatorado para formato AskResponse.

Este módulo converte a resposta do novo fluxo (processar_pergunta_com_dw)
para o formato esperado pelo frontend (AskResponse).
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from src.agent.intent_spec import IntentSpec


def map_handler_refatorado_to_ask_response(
    resposta_handler: Dict[str, Any],
    pergunta: str
) -> Dict[str, Any]:
    """
    Converte resposta do handler refatorado para formato AskResponse.
    
    Args:
        resposta_handler: Resposta de processar_pergunta_com_dw
        pergunta: Pergunta original do usuário
        
    Returns:
        Dicionário no formato AskResponse
    """
    intent_spec = resposta_handler.get("intent_spec")
    
    # Mapeia intent do IntentSpec
    intent = "outros"
    intent_label = "Consulta Geral"
    confianca = 0.7
    if intent_spec:
        intent = intent_spec.tipo
        intent_label = _map_intent_to_label(intent_spec.tipo)
        confianca = getattr(intent_spec, 'confianca', 0.7)
    
    # Resumo executivo
    resumo_executivo = resposta_handler.get("resumo_executivo", "")
    
    # KPIs (extrai da tabela_principal se disponível)
    kpis = _extrair_kpis_da_resposta(resposta_handler)
    
    # Top vendedores (extrai da tabela_principal se disponível)
    top_vendedores = _extrair_top_vendedores_da_resposta(resposta_handler)
    
    # Insights
    insights = resposta_handler.get("insights", [])
    
    # Contexto
    contexto = {
        "mes_ano": _extrair_mes_ano(resposta_handler),
        "periodo_analisado": resposta_handler.get("periodo_analisado", {})
    }
    
    # Structured response (formato CopilotStructuredResponse)
    structured = _criar_structured_response(resposta_handler, pergunta, intent, intent_label)
    
    # Payload completo
    payload = {
        "intent": intent,
        "intentLabel": intent_label,
        "confidence": confianca,
        "question": pergunta,
        "resumoExecutivo": resumo_executivo,
        "structured": structured
    }
    
    # Monta AskResponse
    return {
        "question": pergunta,
        "intent": intent,
        "confidence": confianca,
        "resumoExecutivo": resumo_executivo,
        "kpis": kpis,
        "topVendedores": top_vendedores,
        "insights": insights,
        "observacoes": None,
        "contexto": contexto,
        "timestamp": datetime.utcnow().isoformat(),
        "payload": payload,
        "structured": structured
    }


def _map_intent_to_label(intent: str) -> str:
    """Mapeia intent para label legível."""
    intent_labels = {
        "meta": "Consulta de Meta",
        "vendas": "Consulta de Vendas",
        "clientes_criticos": "Clientes Críticos",
        "churn": "Análise de Churn",
        "ranking_vendedores": "Ranking de Vendedores",
        "ranking_produtos": "Ranking de Produtos",
        "analise_meta_detalhada": "Análise Detalhada de Meta",
        "metas_por_supervisor": "Metas por Supervisor",
        "vendas_por_mes": "Vendas por Mês",
        "outros": "Consulta Geral"
    }
    return intent_labels.get(intent, "Consulta Geral")


def _extrair_kpis_da_resposta(resposta: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extrai KPIs da resposta."""
    # Tenta extrair de tabela_principal
    tabela_principal = resposta.get("tabela_principal", [])
    if not tabela_principal:
        return None
    
    # Se a tabela tem dados agregados, tenta extrair KPIs
    # Por enquanto, retorna None (será preenchido pelo structured)
    return None


def _extrair_top_vendedores_da_resposta(resposta: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Extrai top vendedores da resposta."""
    tabela_principal = resposta.get("tabela_principal", [])
    if not tabela_principal:
        return None
    
    # Tenta extrair vendedores da tabela
    # Por enquanto, retorna None (será preenchido pelo structured)
    return None


def _extrair_mes_ano(resposta: Dict[str, Any]) -> Optional[str]:
    """Extrai mês/ano da resposta."""
    periodo = resposta.get("periodo_analisado", {})
    if periodo and periodo.get("inicio"):
        # Converte YYYY-MM-DD para YYYY-MM
        inicio = periodo["inicio"]
        if isinstance(inicio, str) and len(inicio) >= 7:
            return inicio[:7]
    return None


def _criar_structured_response(
    resposta: Dict[str, Any],
    pergunta: str,
    intent: str,
    intent_label: str
) -> Dict[str, Any]:
    """
    Cria structured response no formato CopilotStructuredResponse.
    """
    resumo_executivo = resposta.get("resumo_executivo", "")
    tabela_principal = resposta.get("tabela_principal", [])
    insights = resposta.get("insights", [])
    periodo_analisado = resposta.get("periodo_analisado", {})
    intent_spec = resposta.get("intent_spec")
    dados_dw = resposta.get("dados_dw", {})
    regras_aplicadas = dados_dw.get("regras_aplicadas") if isinstance(dados_dw, dict) else None
    
    # Extrai KPIs da tabela se disponível
    kpis = []
    if tabela_principal:
        # Tenta extrair KPIs agregados da primeira tabela
        primeira_tabela = tabela_principal[0] if isinstance(tabela_principal, list) else tabela_principal
        if isinstance(primeira_tabela, dict):
            colunas = primeira_tabela.get("colunas", [])
            linhas = primeira_tabela.get("linhas", [])
            
            # Se a tabela tem colunas de KPIs, extrai
            if "Meta Total" in colunas or "meta_total" in colunas:
                # Tenta encontrar valores agregados
                pass
    
    # Converte insights para formato esperado
    insights_recomendacoes = insights if isinstance(insights, list) else []
    
    # Monta structured response
    structured = {
        "resumoExecutivo": resumo_executivo,
        "kpis": kpis if kpis else None,
        "rankingVendedores": [],
        "clientesCriticos": [],
        "insightsRecomendacoes": insights_recomendacoes,
        "jsonTecnico": {
            "intent_spec": intent_spec.to_dict() if intent_spec and hasattr(intent_spec, 'to_dict') else None,
            "periodo_analisado": periodo_analisado,
            "regras_aplicadas": regras_aplicadas,
            "tem_dados": resposta.get("tem_dados", False),
            "tabela_principal": tabela_principal
        }
    }
    
    return structured

