"""
Mapeia resposta do agente para formato CopilotAnswerPayload estruturado.

Este módulo converte o JSON retornado pelo agente em um formato otimizado
para renderização no frontend (CopilotAnswerCard).
"""

import re
from typing import Dict, Any, Optional, List
from datetime import datetime

def map_intent_to_label(intent: str) -> str:
    """
    Mapeia intent interno para label legível em português.
    
    Args:
        intent: Intent detectado (ex.: "consulta_meta")
        
    Returns:
        Label legível (ex.: "Consulta de Meta")
    """
    intent_labels = {
        "consulta_meta": "Consulta de Meta",
        "consulta_vendedores_performance": "Consulta Vendedores Performance",
        "consulta_vendedor": "Consulta de Vendedor",
        "consulta_supervisor": "Consulta de Supervisor",
        "previsao_vendas": "Previsão de Vendas",
        "produtos_baixa_venda": "Produtos de Baixa Venda",
        "clientes_churn_produto": "Clientes Churn Produto",
    }
    return intent_labels.get(intent, "Consulta Geral")


def format_mes_ano_label(mes_ano: str) -> str:
    """
    Converte "2025-08" para "agosto de 2025".
    
    Args:
        mes_ano: Mês/ano no formato YYYY-MM
        
    Returns:
        Label formatado em português
    """
    try:
        ano, mes = mes_ano.split("-")
        meses = [
            "janeiro", "fevereiro", "março", "abril", "maio", "junho",
            "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
        ]
        mes_index = int(mes) - 1
        if 0 <= mes_index < 12:
            return f"{meses[mes_index]} de {ano}"
    except (ValueError, IndexError):
        pass
    return mes_ano


def extrair_secao_markdown(texto: str, secao: str) -> Optional[str]:
    """
    Extrai o conteúdo de uma seção markdown do texto.
    
    Args:
        texto: Texto markdown completo
        secao: Nome da seção a extrair (ex.: "Resumo executivo")
        
    Returns:
        Conteúdo da seção ou None se não encontrar
    """
    patterns = [
        rf"##\s+{re.escape(secao)}[^\n]*\n(.*?)(?=##|\Z)",
        rf"###\s+{re.escape(secao)}[^\n]*\n(.*?)(?=##|###|\Z)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, texto, re.DOTALL | re.IGNORECASE)
        if match:
            content = match.group(1).strip()
            # Remove formatação markdown excessiva
            content = re.sub(r"^\*\*|\*\*$", "", content)
            content = re.sub(r"^\*|\*$", "", content)
            return content
    
    return None


def map_agent_to_copilot_payload(agent_result: Dict[str, Any], question: str) -> Dict[str, Any]:
    """
    Mapeia resultado do agente para formato CopilotAnswerPayload.
    
    Args:
        agent_result: Resultado do processamento da pergunta pelo agente
        question: Pergunta original do usuário
        
    Returns:
        Dicionário no formato CopilotAnswerPayload
    """
    intent = agent_result.get("intent", "outros")
    confianca = agent_result.get("confianca", 0.0)
    resposta = agent_result.get("resposta", "")
    contexto = agent_result.get("contexto", {})
    
    # Monta payload base
    payload: Dict[str, Any] = {
        "intent": intent,
        "intentLabel": map_intent_to_label(intent),
        "confidence": confianca,
        "question": question,
        "respostaMarkdown": resposta,
    }
    
    # Extrai seções do markdown
    resumo_executivo = extrair_secao_markdown(resposta, "Resumo executivo")
    if resumo_executivo:
        # Pega apenas as primeiras 2-3 frases
        frases = re.split(r"[.!?]+\s+", resumo_executivo)
        resumo_curto = ". ".join(frases[:3])
        if not resumo_curto.endswith((".", "!", "?")):
            resumo_curto += "."
        payload["resumoExecutivo"] = resumo_curto.strip()
    else:
        # Fallback: primeiras 2-3 frases do texto
        frases = re.split(r"[.!?]+\s+", resposta[:500])
        resumo_fallback = ". ".join(frases[:3])
        if not resumo_fallback.endswith((".", "!", "?")):
            resumo_fallback += "."
        payload["resumoExecutivo"] = resumo_fallback.strip()
    
    # Extrai insights e observações
    insights_texto = extrair_secao_markdown(resposta, "Insights e recomendações")
    if insights_texto:
        payload["insights"] = insights_texto.strip()
    
    observacoes_texto = extrair_secao_markdown(resposta, "Observações sobre os dados")
    if observacoes_texto:
        payload["observacoes"] = observacoes_texto.strip()
    
    # Extrai KPIs do contexto (se houver dados de meta)
    mes_ano = contexto.get("mes_ano_analise") or contexto.get("mes_ano")
    if mes_ano and intent in ["consulta_meta", "consulta_vendedores_performance"]:
        # Busca lista de vendedores no contexto
        vendedores = (
            contexto.get("detalhe_vendedores_mes", {}).get("vendedores") or
            contexto.get("vendedores") or
            contexto.get("top_vendedores") or
            []
        )
        
        if vendedores and isinstance(vendedores, list):
            # Calcula vendedores que bateram (atingimento >= 100)
            # Garante que atingimento não é None e é um número antes de comparar
            vendedores_que_bateram = sum(
                1 for v in vendedores 
                if isinstance(v, dict) 
                and v.get("atingimento") is not None 
                and isinstance(v.get("atingimento"), (int, float))
                and float(v.get("atingimento", 0)) >= 100
            )
            
            # Calcula atingimento médio
            # Filtra apenas vendedores com atingimento válido (não None)
            atingimentos = [
                float(v.get("atingimento", 0))
                for v in vendedores 
                if isinstance(v, dict) and v.get("atingimento") is not None and isinstance(v.get("atingimento"), (int, float))
            ]
            
            if atingimentos:
                atingimento_medio = sum(atingimentos) / len(atingimentos)
                
                payload["kpis"] = {
                    "mesAnoLabel": format_mes_ano_label(mes_ano),
                    "vendedoresQueBateram": vendedores_que_bateram,
                    "atingimentoMedio": round(atingimento_medio, 2)
                }
    
    # Monta top vendedores (se houver dados)
    if mes_ano and intent in ["consulta_meta", "consulta_vendedores_performance"]:
        vendedores = (
            contexto.get("detalhe_vendedores_mes", {}).get("vendedores") or
            contexto.get("vendedores") or
            contexto.get("top_vendedores") or
            []
        )
        
        if vendedores and isinstance(vendedores, list):
            # Ordena por atingimento (maior primeiro) e pega top 5
            # Filtra apenas vendedores com atingimento válido (não None, e é número)
            vendedores_com_atingimento = [
                v for v in vendedores 
                if isinstance(v, dict) 
                and v.get("atingimento") is not None 
                and isinstance(v.get("atingimento"), (int, float))
            ]
            
            vendedores_ordenados = sorted(
                vendedores_com_atingimento,
                key=lambda x: float(x.get("atingimento", 0)),
                reverse=True
            )[:5]
            
            if vendedores_ordenados:
                payload["topVendedores"] = [
                    {
                        "rank": idx + 1,
                        "nome": v.get("vendedor_nome") or v.get("nome") or v.get("vendedor") or "N/A",
                        "supervisor": v.get("supervisor") or v.get("supervisor_nome"),
                        "meta": float(v.get("meta", 0) or v.get("meta_valor", 0) or 0),
                        "realizado": float(v.get("realizado", 0) or v.get("realizado_valor", 0) or v.get("faturado", 0) or 0),
                        "atingimento": float(v.get("atingimento", 0) or v.get("perc_atingido", 0) or 0)
                    }
                    for idx, v in enumerate(vendedores_ordenados)
                ]
    
    return payload

