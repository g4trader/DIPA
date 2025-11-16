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
    
    # Debug: verificar se contexto tem dados
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[copilot_mapper] Intent: {intent}")
    logger.info(f"[copilot_mapper] Contexto keys: {list(contexto.keys()) if contexto else 'VAZIO'}")
    if contexto and "piores_meta" in contexto:
        logger.info(f"[copilot_mapper] piores_meta: {len(contexto['piores_meta'])} registros")
    if contexto and "menores_venda" in contexto:
        logger.info(f"[copilot_mapper] menores_venda: {len(contexto['menores_venda'])} registros")
    
    # NOVO: Se houver resposta estruturada, usa ela diretamente
    # Verifica tanto no nível superior quanto dentro de contexto
    structured = agent_result.get("structured") or (contexto.get("structured") if contexto else None)
    if structured and isinstance(structured, dict):
        # Resposta estruturada já está pronta - passa diretamente
        payload: Dict[str, Any] = {
            "intent": intent,
            "intentLabel": map_intent_to_label(intent),
            "confidence": confianca,
            "question": question,
            "structured": structured,  # Resposta estruturada no formato dashboard
            "respostaMarkdown": resposta,  # Mantém texto para fallback
        }
        logger.info(f"[copilot_mapper] Resposta estruturada detectada: {len(str(structured))} caracteres")
        return payload
    
    # FALLBACK: Mapeia dados antigos para formato estruturado (compatibilidade)
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
        # Para consulta_vendedores_performance, os dados estão em piores_meta
        # Para consulta_meta, pode estar em detalhe_vendedores_mes ou outros campos
        vendedores = []
        
        if intent == "consulta_vendedores_performance":
            # Para performance, usamos piores_meta (todos os vendedores com dados)
            piores_meta = contexto.get("piores_meta", [])
            menores_venda = contexto.get("menores_venda", [])
            # Combina ambas as listas, mas prioriza piores_meta
            vendedores = piores_meta if piores_meta else menores_venda
        else:
            # Para consulta_meta, busca em vários lugares
            vendedores = (
                contexto.get("detalhe_vendedores_mes", {}).get("vendedores") or
                contexto.get("vendedores") or
                contexto.get("top_vendedores") or
                contexto.get("pioresVendedores") or
                contexto.get("melhoresVendedores") or
                []
            )
        
        if vendedores and isinstance(vendedores, list) and len(vendedores) > 0:
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
        vendedores = []
        
        if intent == "consulta_vendedores_performance":
            # Para performance, para mostrar os "melhores" (que não estão nos piores),
            # precisamos buscar todos os vendedores do mês ou usar os melhoresVendedores do contexto
            # Por enquanto, vamos mostrar os que bateram (atingimento >= 100) dos piores_meta
            piores_meta = contexto.get("piores_meta", [])
            # Filtra apenas os que bateram (atingimento >= 100) para mostrar como "top performers"
            vendedores_com_dados = [v for v in piores_meta if isinstance(v, dict) and v.get("atingimento") is not None]
            # Pega os 5 melhores (maior atingimento) entre todos os vendedores com dados
            vendedores = sorted(
                vendedores_com_dados,
                key=lambda x: float(x.get("atingimento", 0)),
                reverse=True
            )[:5]
        else:
            # Para consulta_meta, busca em vários lugares
            vendedores_raw = (
                contexto.get("detalhe_vendedores_mes", {}).get("vendedores") or
                contexto.get("vendedores") or
                contexto.get("top_vendedores") or
                contexto.get("melhoresVendedores") or
                []
            )
            
            if vendedores_raw and isinstance(vendedores_raw, list):
                # Ordena por atingimento (maior primeiro) e pega top 5
                # Filtra apenas vendedores com atingimento válido (não None, e é número)
                vendedores_com_atingimento = [
                    v for v in vendedores_raw 
                    if isinstance(v, dict) 
                    and v.get("atingimento") is not None 
                    and isinstance(v.get("atingimento"), (int, float))
                ]
                
                vendedores = sorted(
                    vendedores_com_atingimento,
                    key=lambda x: float(x.get("atingimento", 0)),
                    reverse=True
                )[:5]
        
        if vendedores and isinstance(vendedores, list) and len(vendedores) > 0:
            payload["topVendedores"] = []
            for idx, v in enumerate(vendedores):
                if not isinstance(v, dict):
                    continue
                    
                # Extrai nome do vendedor (múltiplos possíveis campos)
                nome = (
                    v.get("vendedor_nome") or 
                    v.get("nome") or 
                    v.get("vendedor") or 
                    v.get("vendedor") or
                    "N/A"
                )
                
                # Extrai supervisor (múltiplos possíveis campos)
                supervisor = (
                    v.get("supervisor") or 
                    v.get("supervisor_nome") or 
                    v.get("supervisor") or
                    None
                )
                
                # Extrai meta (múltiplos possíveis campos)
                meta = float(
                    v.get("meta", 0) or 
                    v.get("meta_valor", 0) or 
                    v.get("meta_total", 0) or 
                    v.get("valor_meta", 0) or
                    0
                )
                
                # Extrai realizado (múltiplos possíveis campos)
                realizado = float(
                    v.get("realizado", 0) or 
                    v.get("realizado_valor", 0) or 
                    v.get("realizado_total", 0) or 
                    v.get("faturado", 0) or
                    v.get("valor_faturado", 0) or
                    0
                )
                
                # Extrai atingimento (múltiplos possíveis campos)
                atingimento_val = v.get("atingimento") or v.get("perc_atingido") or v.get("perc_atingimento") or 0
                atingimento = float(atingimento_val) if atingimento_val is not None else 0.0
                
                # Só adiciona se tiver dados válidos
                if nome != "N/A" or meta > 0 or realizado > 0:
                    payload["topVendedores"].append({
                        "rank": idx + 1,
                        "nome": nome,
                        "supervisor": supervisor,
                        "meta": meta,
                        "realizado": realizado,
                        "atingimento": atingimento
                    })
    
    # Monta clientes problemáticos/críticos (se houver dados)
    # IMPORTANTE: Extrai clientesCriticos ou clientesProblema do contexto
    clientes_criticos = (
        contexto.get("clientesCriticos") or
        contexto.get("clientesProblema") or
        contexto.get("clientes_criticos") or
        []
    )
    
    if clientes_criticos and isinstance(clientes_criticos, list) and len(clientes_criticos) > 0:
        payload["clientesProblema"] = []
        for idx, c in enumerate(clientes_criticos[:15]):  # Top 15 clientes
            if not isinstance(c, dict):
                continue
            
            # Extrai nome do cliente
            nome_cliente = (
                c.get("nome_cliente") or
                c.get("cliente_nome") or
                c.get("nome") or
                "N/A"
            )
            
            # Extrai vendedor responsável
            vendedor_nome = (
                c.get("vendedor_nome") or
                c.get("vendedor") or
                None
            )
            
            # Extrai faturamento e quantidade de pedidos
            faturamento_mes = float(c.get("faturamento_mes", 0) or 0)
            qtd_pedidos = int(c.get("qtd_pedidos", 0) or 0)
            faturamento_medio_pedido = float(c.get("faturamento_medio_pedido", 0) or 0)
            
            # Extrai histórico (se disponível)
            faturamento_media_3m = c.get("faturamento_media_3m")
            if faturamento_media_3m is not None:
                faturamento_media_3m = float(faturamento_media_3m)
            
            variacao_percentual = c.get("variacao_percentual")
            if variacao_percentual is not None:
                variacao_percentual = float(variacao_percentual)
            
            tem_historico = c.get("tem_historico", False)
            
            # Só adiciona se tiver dados válidos
            if nome_cliente != "N/A" or faturamento_mes > 0:
                payload["clientesProblema"].append({
                    "cliente_id": c.get("cliente_id"),
                    "nome_cliente": nome_cliente,
                    "vendedor_nome": vendedor_nome,
                    "faturamento_mes": round(faturamento_mes, 2),
                    "qtd_pedidos": qtd_pedidos,
                    "faturamento_medio_pedido": round(faturamento_medio_pedido, 2) if faturamento_medio_pedido > 0 else None,
                    "faturamento_media_3m": round(faturamento_media_3m, 2) if faturamento_media_3m is not None else None,
                    "variacao_percentual": round(variacao_percentual, 2) if variacao_percentual is not None else None,
                    "tem_historico": tem_historico
                })
    
    # NOVO: Se não houver resposta estruturada mas houver dados suficientes, gera formato estruturado
    if "structured" not in payload and intent in ["consulta_meta", "consulta_vendedores_performance"]:
        # Tenta construir formato estruturado a partir dos dados mapeados
        structured_data: Dict[str, Any] = {}
        
        # Resumo executivo
        if payload.get("resumoExecutivo"):
            structured_data["resumoExecutivo"] = payload["resumoExecutivo"]
        
        # KPIs
        if payload.get("kpis"):
            kpis_data = payload["kpis"]
            structured_data["kpis"] = [
                {
                    "label": "Meta Total",
                    "value": 0,  # Será preenchido se disponível
                    "color": "neutral",
                    "icon": "🎯"
                },
                {
                    "label": "Atingimento Médio",
                    "value": f"{kpis_data.get('atingimentoMedio', 0):.1f}%",
                    "color": "positive" if kpis_data.get('atingimentoMedio', 0) >= 100 else "negative",
                    "icon": "📊"
                },
                {
                    "label": "Vendedores que Bateram",
                    "value": kpis_data.get('vendedoresQueBateram', 0),
                    "color": "positive" if kpis_data.get('vendedoresQueBateram', 0) > 0 else "neutral",
                    "icon": "✅"
                }
            ]
        
        # Ranking de vendedores
        if payload.get("topVendedores"):
            structured_data["rankingVendedores"] = [
                {
                    "vendedor": v.get("nome", "N/A"),
                    "meta": float(v.get("meta", 0) or 0),
                    "realizado": float(v.get("realizado", 0) or 0),
                    "atingimento": float(v.get("atingimento", 0) or 0),
                    "gap": float(v.get("realizado", 0) or 0) - float(v.get("meta", 0) or 0),
                    "supervisor": v.get("supervisor"),
                    "rank": v.get("rank", idx + 1)
                }
                for idx, v in enumerate(payload.get("topVendedores", []), 1)
            ]
        
        # Clientes críticos
        if payload.get("clientesProblema"):
            structured_data["clientesCriticos"] = [
                {
                    "cliente": c.get("nome_cliente", "N/A"),
                    "faturamento": float(c.get("faturamento_mes", 0) or 0),
                    "pedidos": int(c.get("qtd_pedidos", 0) or 0),
                    "variacao": float(c.get("variacao_percentual", 0)) if c.get("variacao_percentual") is not None else None,
                    "vendedor": c.get("vendedor_nome"),
                    "insight": None  # Será gerado se necessário
                }
                for c in payload["clientesProblema"][:15]
            ]
        
        # Insights e recomendações
        if payload.get("insights"):
            # Extrai insights do texto
            insights_text = payload["insights"]
            # Tenta separar em bullets
            insights_lines = [line.strip() for line in insights_text.split('\n') if line.strip() and line.strip().startswith(('•', '-', '*'))]
            if insights_lines:
                structured_data["insightsRecomendacoes"] = [
                    line.lstrip('•-* ').strip() for line in insights_lines[:5]
                ]
            else:
                # Fallback: usa parágrafo completo
                structured_data["insightsRecomendacoes"] = [insights_text[:200]]
        
        # Se conseguiu construir formato estruturado, adiciona ao payload
        if structured_data:
            payload["structured"] = structured_data
            logger.info(f"[copilot_mapper] Formato estruturado gerado automaticamente a partir de dados antigos")
    
    return payload

