"""
Mapper para converter resposta do handler refatorado para formato AskResponse.

Este módulo converte a resposta do novo fluxo (processar_pergunta_com_dw)
para o formato esperado pelo frontend (AskResponse).
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.agent.intent_spec import IntentSpec

logger = logging.getLogger(__name__)


def _calcular_confianca_q1(dados_dw: Dict[str, Any], resposta_handler: Dict[str, Any]) -> float:
    """
    Calcula confiança para Q1 baseada em critérios reais.
    
    Critérios:
    (a) % de clientes ativos sem vendedor faltante
    (b) presença de supervisão
    (c) coerência estatística das faixas
    (d) ausência de inconsistências no DW
    
    Args:
        dados_dw: Dados do DW
        resposta_handler: Resposta do handler
        
    Returns:
        float: Confiança entre 0.0 e 1.0
    """
    confianca_base = 0.5
    
    dados = dados_dw.get("dados", [])
    if not dados or len(dados) == 0:
        return 0.3  # Sem dados, confiança baixa
    
    total = len(dados)
    
    # (a) % de clientes com vendedor
    clientes_com_vendedor = sum(
        1 for c in dados 
        if c.get("vendedor_nome") or c.get("vendedor_codigo") or c.get("rota_id")
    )
    percentual_vendedor = (clientes_com_vendedor / total * 100) if total > 0 else 0
    
    if percentual_vendedor >= 95:
        confianca_base += 0.2
    elif percentual_vendedor >= 85:
        confianca_base += 0.15
    elif percentual_vendedor >= 70:
        confianca_base += 0.1
    # Se < 70%, não adiciona pontos
    
    # (b) Presença de supervisão
    clientes_com_supervisor = sum(
        1 for c in dados 
        if c.get("supervisor_nome") or c.get("supervisor_codigo")
    )
    percentual_supervisor = (clientes_com_supervisor / total * 100) if total > 0 else 0
    
    if percentual_supervisor >= 90:
        confianca_base += 0.15
    elif percentual_supervisor >= 70:
        confianca_base += 0.1
    elif percentual_supervisor >= 50:
        confianca_base += 0.05
    # Se < 50%, não adiciona pontos
    
    # (c) Coerência estatística das faixas
    # Verifica se há classificação_faixas nos dados
    classificacao_faixas = dados_dw.get("classificacao_faixas")
    if classificacao_faixas:
        total_faixas = (
            classificacao_faixas.get("faixa_61_120", 0) +
            classificacao_faixas.get("faixa_121_180", 0) +
            classificacao_faixas.get("faixa_181_300", 0) +
            classificacao_faixas.get("faixa_mais_300", 0)
        )
        # Se a soma das faixas bate com o total, há coerência
        if abs(total_faixas - total) <= 5:  # Tolerância de 5 clientes
            confianca_base += 0.1
    
    # (d) Ausência de inconsistências
    # Verifica se há clientes com dias_sem_compra None ou inválido
    clientes_inconsistentes = sum(
        1 for c in dados 
        if c.get("dias_sem_compra") is None or c.get("dias_sem_compra", 0) < 0
    )
    percentual_inconsistente = (clientes_inconsistentes / total * 100) if total > 0 else 0
    
    if percentual_inconsistente == 0:
        confianca_base += 0.05
    elif percentual_inconsistente <= 2:
        confianca_base += 0.02
    # Se > 2%, não adiciona pontos (ou pode subtrair)
    
    # Limita entre 0.0 e 1.0
    return min(1.0, max(0.0, confianca_base))


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
        
        # ✅ NOVO: Para Q1, calcula confiança baseada em critérios reais
        if intent == "clientes_sem_compra":
            dados_dw = resposta_handler.get("dados_dw", {})
            confianca_calculada = _calcular_confianca_q1(dados_dw, resposta_handler)
            logger.info(
                f"[map_handler_refatorado_to_ask_response] Q1 - Confiança calculada: {confianca_calculada:.2f} "
                f"(base: {getattr(intent_spec, 'confianca', 0.7):.2f})"
            )
            confianca = confianca_calculada
    
    # Resumo executivo
    resumo_executivo = resposta_handler.get("resumo_executivo", "")
    
    # KPIs (extrai da tabela_principal se disponível)
    kpis = _extrair_kpis_da_resposta(resposta_handler)
    
    # Top vendedores (extrai da tabela_principal se disponível)
    top_vendedores = _extrair_top_vendedores_da_resposta(resposta_handler)
    
    # Insights
    insights = resposta_handler.get("insights", [])
    
    # Contexto
    # ✅ Q1 LIGHT MODE: Adiciona informações de parcialidade ao contexto
    contexto = {
        "mes_ano": _extrair_mes_ano(resposta_handler),
        "periodo_analisado": resposta_handler.get("periodo_analisado", {})
    }
    
    # Copia campos de contexto do handler (is_partial, total_estimado, etc.)
    contexto_handler = resposta_handler.get("contexto", {})
    if contexto_handler:
        if "is_partial" in contexto_handler:
            contexto["is_partial"] = contexto_handler["is_partial"]
        if "total_estimado" in contexto_handler:
            contexto["total_estimado"] = contexto_handler["total_estimado"]
        if "dw_mode" in contexto_handler:
            contexto["dw_mode"] = contexto_handler["dw_mode"]
        if "partial_message" in contexto_handler:
            contexto["nota_parcialidade"] = contexto_handler["partial_message"]
    
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
    tabela_por_rota = dados_dw.get("tabela_por_rota") if isinstance(dados_dw, dict) else None
    
    # Para Q1 (clientes_sem_compra), monta tabela_principal com colunas corretas
    if intent == "clientes_sem_compra" and dados_dw.get("dados"):
        dados_clientes = dados_dw.get("dados", [])
        if dados_clientes and isinstance(dados_clientes, list) and len(dados_clientes) > 0:
            # Monta tabela_principal com colunas: Cliente ID, Nome, Dias sem Compra, Vendedor, Supervisor
            tabela_principal = [{
                "colunas": ["Cliente ID", "Nome", "Dias sem Compra", "Vendedor", "Supervisor"],
                "linhas": [
                    [
                        cliente.get("cliente_id", ""),
                        cliente.get("nome", ""),
                        cliente.get("dias_sem_compra", 0) or 0,
                        cliente.get("vendedor_nome", cliente.get("vendedor_codigo", cliente.get("rota_id", ""))),
                        cliente.get("supervisor_nome", cliente.get("supervisor_codigo", ""))
                    ]
                    for cliente in dados_clientes
                ]
            }]
    
    # Extrai KPIs e seções da tabela_principal
    kpis = []
    secoes = []
    
    if tabela_principal:
        # Normaliza: tabela_principal pode ser lista ou dict único
        tabelas = tabela_principal if isinstance(tabela_principal, list) else [tabela_principal]
        
        for tabela in tabelas:
            if not isinstance(tabela, dict):
                continue
                
            colunas = tabela.get("colunas", [])
            linhas = tabela.get("linhas", [])
            
            if not colunas or not linhas:
                continue
            
            # Para consultas de META: extrai KPIs agregados
            if intent == "meta" or intent == "analise_meta_detalhada":
                # Procura colunas de meta/realizado/atingimento
                meta_idx = _find_column_index(colunas, ["Meta Total", "meta_total", "Meta"])
                realizado_idx = _find_column_index(colunas, ["Realizado Total", "realizado_total", "Realizado"])
                atingimento_idx = _find_column_index(colunas, ["Atingimento", "atingimento", "Atingimento (%)"])
                mes_idx = _find_column_index(colunas, ["Mês", "mes_ano", "Mês/Ano"])
                
                # Se for tabela agregada (uma linha ou poucas linhas), extrai KPIs
                if len(linhas) <= 12:  # Provavelmente meses ou agregado
                    meta_total = 0.0
                    realizado_total = 0.0
                    atingimento_medio = 0.0
                    meses_com_dados = 0
                    
                    for linha in linhas:
                        if meta_idx is not None and meta_idx < len(linha):
                            meta_val = _parse_number(linha[meta_idx])
                            if meta_val:
                                meta_total += meta_val
                        if realizado_idx is not None and realizado_idx < len(linha):
                            real_val = _parse_number(linha[realizado_idx])
                            if real_val:
                                realizado_total += real_val
                        if atingimento_idx is not None and atingimento_idx < len(linha):
                            atg_val = _parse_number(linha[atingimento_idx])
                            if atg_val:
                                atingimento_medio += atg_val
                                meses_com_dados += 1
                    
                    if meses_com_dados > 0:
                        atingimento_medio = atingimento_medio / meses_com_dados
                    
                    # Cria KPIs
                    if meta_total > 0 or realizado_total > 0:
                        mes_ano_label = _format_periodo_label(periodo_analisado)
                        
                        kpis.append({
                            "label": "Meta Total",
                            "value": f"R$ {meta_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                            "color": "positive" if atingimento_medio >= 100 else "neutral"
                        })
                        kpis.append({
                            "label": "Realizado Total",
                            "value": f"R$ {realizado_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                            "color": "positive" if realizado_total >= meta_total else "neutral"
                        })
                        kpis.append({
                            "label": "Atingimento Médio",
                            "value": f"{atingimento_medio:.1f}%",
                            "color": "positive" if atingimento_medio >= 100 else "negative" if atingimento_medio < 90 else "neutral",
                            "variation": f"{atingimento_medio - 100:.1f}%" if atingimento_medio < 100 else f"+{atingimento_medio - 100:.1f}%"
                        })
                        
                        # Cria seção de tabela detalhada
                        secoes.append({
                            "tipo": "tabela_metas",
                            "titulo": f"Metas e Realizado por Mês - {mes_ano_label}" if mes_ano_label else "Metas e Realizado",
                            "dados": _convert_table_to_dict_list(colunas, linhas)
                        })
                
                # Se for tabela de vendedores (muitas linhas), cria seção de ranking
                elif len(linhas) > 12:
                    vendedor_idx = _find_column_index(colunas, ["Vendedor", "vendedor_nome", "Vendedor"])
                    if vendedor_idx is not None:
                        secoes.append({
                            "tipo": "lista_vendedores",
                            "titulo": "Ranking de Vendedores",
                            "dados": _convert_table_to_dict_list(colunas, linhas, intent="meta")
                        })
            
            # Para outras intents, cria seção genérica
            else:
                secoes.append({
                    "tipo": "tabela_detalhada",
                    "titulo": f"Dados Analíticos - {intent_label}",
                    "dados": _convert_table_to_dict_list(colunas, linhas)
                })
    
    # Para Q1 (clientes_sem_compra), extrai KPIs do post_processor
    resposta_estruturada = resposta.get("resposta_estruturada", {})
    if intent == "clientes_sem_compra" and isinstance(resposta_estruturada, dict):
        kpis_post_processor = resposta_estruturada.get("kpis", [])
        if kpis_post_processor:
            # Converte formato do post_processor para formato do structured
            kpis = [
                {
                    "label": kpi.get("label", ""),
                    "value": str(kpi.get("valor", 0)),
                    "color": "neutral"
                }
                for kpi in kpis_post_processor
            ]
    
    # Se não há KPIs mas há dados do DW, tenta extrair de dados_dw
    if not kpis and dados_dw.get("dados"):
        kpis_dw = _extrair_kpis_de_dados_dw(dados_dw.get("dados"), intent, periodo_analisado)
        if kpis_dw:
            kpis = kpis_dw
    
    # Se ainda não há KPIs mas há seções, tenta extrair das seções
    if not kpis and secoes:
        for secao in secoes:
            if secao.get("tipo") == "tabela_metas" and secao.get("dados"):
                # Agrega dados da seção
                meta_total = sum(float(item.get("meta_total", 0) or 0) for item in secao["dados"])
                realizado_total = sum(float(item.get("realizado_total", 0) or 0) for item in secao["dados"])
                if meta_total > 0:
                    atingimento = (realizado_total / meta_total) * 100
                    mes_ano_label = _format_periodo_label(periodo_analisado)
                    
                    kpis = [
                        {
                            "label": "Meta Total",
                            "value": f"R$ {meta_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                            "color": "neutral"
                        },
                        {
                            "label": "Realizado Total",
                            "value": f"R$ {realizado_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                            "color": "positive" if realizado_total >= meta_total else "neutral"
                        },
                        {
                            "label": "Atingimento Médio",
                            "value": f"{atingimento:.1f}%",
                            "color": "positive" if atingimento >= 100 else "negative" if atingimento < 90 else "neutral",
                            "variation": f"{atingimento - 100:.1f}%" if atingimento < 100 else f"+{atingimento - 100:.1f}%"
                        }
                    ]
                    break
    
    # Converte insights para formato esperado
    insights_recomendacoes = insights if isinstance(insights, list) else []
    
    # Extrai texto do post_processor se disponível (contém "Alvos Prioritários (TOP 10)")
    # Prioridade 1: texto_completo_post_processor (preservado pelo handler)
    texto_post_processor = resposta.get("texto_completo_post_processor")
    
    # Prioridade 2: resposta_estruturada.texto (fallback)
    if not texto_post_processor:
        resposta_estruturada = resposta.get("resposta_estruturada", {})
        if isinstance(resposta_estruturada, dict) and "texto" in resposta_estruturada:
            texto_post_processor = resposta_estruturada.get("texto", "")
    
    # Log para debug
    if texto_post_processor:
        logger.info(f"[mapper] Texto post_processor extraído: {len(texto_post_processor)} chars")
        logger.debug(f"[mapper] Primeiras 200 chars: {texto_post_processor[:200]}")
    
    # Cria detalhe_tabela a partir da tabela_principal (para o botão "Ver detalhamento")
    detalhe_tabela = None
    if tabela_principal:
        # Pega a primeira tabela (ou a única tabela)
        tabela = tabela_principal[0] if isinstance(tabela_principal, list) and len(tabela_principal) > 0 else tabela_principal
        if isinstance(tabela, dict):
            colunas = tabela.get("colunas", [])
            linhas = tabela.get("linhas", [])
            if colunas and linhas:
                detalhe_tabela = {
                    "titulo": f"Dados Analíticos - {intent_label}",
                    "colunas": colunas,
                    "linhas": linhas
                }
                logger.info(f"[mapper] ✅ detalhe_tabela criada: {len(linhas)} linhas, {len(colunas)} colunas")
    
    # ✅ Q1 LIGHT MODE: Calcula total_clientes_unicos para Q1
    # Se is_partial=True, usa total_estimado; senão, conta registros da tabela
    total_clientes_unicos = None
    is_partial = dados_dw.get("is_partial", False)
    total_estimado = dados_dw.get("total_estimado", None)
    
    if intent == "clientes_sem_compra":
        if is_partial and total_estimado is not None:
            # ✅ MODO LIGHT: Usa total_estimado quando resposta é parcial
            total_clientes_unicos = total_estimado
            registros_tabela = 0
            if tabela_principal:
                if isinstance(tabela_principal, list) and len(tabela_principal) > 0:
                    primeira_tabela = tabela_principal[0]
                    if isinstance(primeira_tabela, dict) and "linhas" in primeira_tabela:
                        registros_tabela = len(primeira_tabela["linhas"])
                elif isinstance(tabela_principal, dict) and "linhas" in tabela_principal:
                    registros_tabela = len(tabela_principal["linhas"])
            logger.info(
                f"[mapper] Q1 modo light: usando total_estimado={total_estimado} "
                f"(registros na tabela: {registros_tabela})"
            )
        elif tabela_principal:
            # ✅ MODO FULL: Conta registros da tabela (query completa)
            if isinstance(tabela_principal, list) and len(tabela_principal) > 0:
                primeira_tabela = tabela_principal[0]
                if isinstance(primeira_tabela, dict) and "linhas" in primeira_tabela:
                    total_clientes_unicos = len(primeira_tabela["linhas"])
            elif isinstance(tabela_principal, dict) and "linhas" in tabela_principal:
                total_clientes_unicos = len(tabela_principal["linhas"])
            
            # Validação: garante que total_clientes_unicos == len(dados_dw["dados"])
            if total_clientes_unicos is not None and dados_dw.get("dados"):
                dados_clientes = dados_dw.get("dados", [])
                if isinstance(dados_clientes, list):
                    total_dados_dw = len(dados_clientes)
                    if total_clientes_unicos != total_dados_dw:
                        logger.warning(
                            f"[mapper] ⚠️  INCONSISTÊNCIA Q1: "
                            f"total_clientes_unicos ({total_clientes_unicos}) != len(dados_dw) ({total_dados_dw})"
                        )
                        # Usa o valor da tabela (mais confiável, já deduplicado)
                        total_clientes_unicos = total_clientes_unicos
                    else:
                        logger.info(
                            f"[mapper] ✅ Q1 CONSISTENTE: "
                            f"total_clientes_unicos = {total_clientes_unicos} == len(dados_dw) = {total_dados_dw}"
                        )
    
    # Monta structured response
    structured = {
        "resumo_executivo": resumo_executivo,
        "kpis": kpis if kpis else None,
        "secoes": secoes if secoes else None,
        "rankingVendedores": [],
        "clientesCriticos": [],
        "insightsRecomendacoes": insights_recomendacoes,
        "respostaMarkdown": texto_post_processor,  # Texto completo do post_processor (inclui "Alvos Prioritários (TOP 10)")
        "detalhe_tabela": detalhe_tabela,  # Tabela para botão "Ver detalhamento" com paginação
        # ✅ CORREÇÃO: Adiciona campo metrics com total_clientes para Q1
        "metrics": {
            "total_clientes": total_clientes_unicos if total_clientes_unicos is not None else None,
            "total_registros": total_clientes_unicos if total_clientes_unicos is not None else None  # Alias para compatibilidade
        } if total_clientes_unicos is not None else None,
        "jsonTecnico": {
            "intent_spec": intent_spec.to_dict() if intent_spec and hasattr(intent_spec, 'to_dict') else None,
            "periodo_analisado": periodo_analisado,
            "regras_aplicadas": regras_aplicadas,
            "tem_dados": resposta.get("tem_dados", False),
            "tabela_principal": tabela_principal,
            "tabela_por_rota": tabela_por_rota,  # Tabela agregada por rota (Q1)
            # ✅ CORREÇÃO: Adiciona total_clientes_unicos no jsonTecnico também
            "total_clientes_unicos": total_clientes_unicos if total_clientes_unicos is not None else None
        }
    }
    
    # Log final para debug
    if texto_post_processor:
        logger.info(f"[mapper] ✅ respostaMarkdown populado: {len(texto_post_processor)} chars")
        logger.debug(f"[mapper] Primeiras 300 chars do respostaMarkdown: {texto_post_processor[:300]}")
    else:
        logger.warning(f"[mapper] ⚠️  respostaMarkdown está vazio ou None")
    
    return structured


def _find_column_index(colunas: List[str], nomes_possiveis: List[str]) -> Optional[int]:
    """Encontra índice de coluna por nomes possíveis."""
    for i, col in enumerate(colunas):
        col_lower = str(col).lower()
        for nome in nomes_possiveis:
            if nome.lower() in col_lower or col_lower in nome.lower():
                return i
    return None


def _parse_number(valor: Any) -> Optional[float]:
    """Converte valor para número."""
    if valor is None:
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    if isinstance(valor, str):
        # Remove R$, espaços, pontos de milhar
        valor_limpo = valor.replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".")
        try:
            return float(valor_limpo)
        except:
            return None
    return None


def _format_periodo_label(periodo: Dict[str, Any]) -> str:
    """Formata período para label legível."""
    inicio = periodo.get("inicio")
    fim = periodo.get("fim")
    
    if inicio and fim:
        try:
            from datetime import datetime
            dt_inicio = datetime.strptime(inicio, "%Y-%m-%d")
            dt_fim = datetime.strptime(fim, "%Y-%m-%d")
            
            if dt_inicio.year == dt_fim.year and dt_inicio.month == dt_fim.month:
                # Mesmo mês
                meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
                        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
                return f"{meses[dt_inicio.month - 1]} de {dt_inicio.year}"
            else:
                return f"{dt_inicio.strftime('%d/%m/%Y')} a {dt_fim.strftime('%d/%m/%Y')}"
        except:
            pass
    
    return "Período analisado"


def _convert_table_to_dict_list(colunas: List[str], linhas: List[List[Any]], intent: str = "") -> List[Dict[str, Any]]:
    """Converte tabela (colunas + linhas) para lista de dicionários."""
    resultado = []
    
    for linha in linhas:
        registro = {}
        for i, col in enumerate(colunas):
            if i < len(linha):
                # Normaliza nome da coluna para chave
                chave = col.lower().replace(" ", "_").replace("/", "_").replace("(%)", "pct")
                valor = linha[i]
                
                # Converte valores numéricos se possível
                if isinstance(valor, str) and (valor.replace(".", "").replace(",", "").replace("-", "").isdigit() or "R$" in valor):
                    valor_num = _parse_number(valor)
                    if valor_num is not None:
                        valor = valor_num
                
                registro[chave] = valor
        resultado.append(registro)
    
    # Para intent "meta" e vendedores, mapeia campos específicos
    if intent == "meta" and resultado:
        for reg in resultado:
            # Mapeia campos comuns
            if "vendedor" in reg or "vendedor_nome" in reg:
                reg["vendedor_nome"] = reg.get("vendedor") or reg.get("vendedor_nome")
            if "meta_total" in reg or "meta" in reg:
                reg["meta_total"] = reg.get("meta_total") or reg.get("meta") or 0
            if "realizado_total" in reg or "realizado" in reg:
                reg["realizado_total"] = reg.get("realizado_total") or reg.get("realizado") or 0
            if "atingimento" in reg or "atingimento_pct" in reg:
                atg = reg.get("atingimento_pct") or reg.get("atingimento") or 0
                reg["atingimento_pct"] = _parse_number(atg) or 0
            if "gap" in reg or "gap_total" in reg:
                gap = reg.get("gap_total") or reg.get("gap") or 0
                reg["gap_valor"] = _parse_number(gap) or 0
    
    return resultado


def _extrair_kpis_de_dados_dw(dados: List[Any], intent: str, periodo: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extrai KPIs diretamente dos dados do DW."""
    kpis = []
    
    if intent == "meta" and dados:
        # Tenta agregar dados
        meta_total = 0.0
        realizado_total = 0.0
        
        for item in dados:
            if isinstance(item, dict):
                meta_total += float(item.get("meta_total", 0) or 0)
                realizado_total += float(item.get("realizado_total", 0) or 0)
        
        if meta_total > 0:
            atingimento = (realizado_total / meta_total) * 100
            
            mes_ano_label = _format_periodo_label(periodo)
            
            kpis.append({
                "label": "Meta Total",
                "value": f"R$ {meta_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                "color": "neutral"
            })
            kpis.append({
                "label": "Realizado Total",
                "value": f"R$ {realizado_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                "color": "positive" if realizado_total >= meta_total else "neutral"
            })
            kpis.append({
                "label": "Atingimento Médio",
                "value": f"{atingimento:.1f}%",
                "color": "positive" if atingimento >= 100 else "negative" if atingimento < 90 else "neutral",
                "variation": f"{atingimento - 100:.1f}%" if atingimento < 100 else f"+{atingimento - 100:.1f}%"
            })
    
    return kpis

