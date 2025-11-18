"""
Pós-processador de Respostas - DIPAM COPILOT™.

Este módulo refatora o pós-processamento de respostas usando modelos narrativos claros,
alinhados ao TEMPLATE DE RESPOSTA NEGATIVA e POSITIVA.

ARQUITETURA:
- Recebe: intent_spec, dados DW, causas_detector, behavior_rules_aplicadas
- Emite: dict estruturado com todas as seções do template
- Não inventa dados, apenas estrutura o que vem do DW
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from src.agent.executive_formatter import formatar_execucao

logger = logging.getLogger(__name__)


def post_processar_resposta(resposta_dw, intent_spec, regras_aplicadas, regras_behavior):
    """
    Gera a resposta final no formato executivo obrigatório:
    - Resumo Executivo
    - Principais Achados
    - Implicações Comerciais
    - Plano de Ação Imediato
    """
    
    # Extrai dados da resposta do DW (pode vir como lista direta ou dentro de dict)
    dados = None
    if isinstance(resposta_dw, dict):
        dados = resposta_dw.get("dados", None)
        # Se dados é None, tenta pegar diretamente se for uma lista
        if dados is None and isinstance(resposta_dw.get("dados_normalizados"), list):
            dados = resposta_dw.get("dados_normalizados")
    elif isinstance(resposta_dw, list):
        dados = resposta_dw
    
    # Se dados ainda for None ou lista vazia, trata como sem dados
    if not dados or (isinstance(dados, list) and len(dados) == 0):
        dados = None
    
    # Extrai filtros do intent_spec
    filtros = intent_spec.filtros if hasattr(intent_spec, 'filtros') else intent_spec.get("filtros", {})
    
    # Usa executive_formatter para gerar narrativa executiva
    resultado_exec = formatar_execucao(
        dados=dados,
        intent_spec=intent_spec,
        filtros=filtros,
        regras_behavior=regras_behavior or []
    )
    
    # Construi o texto final da resposta
    texto_final = (
        "Resumo Executivo\n"
        + resultado_exec["resumo"] + "\n\n"
        + "Principais Achados\n"
        + "\n".join(f"- {a}" for a in resultado_exec["achados"]) + "\n\n"
        + "Implicações Comerciais\n"
        + "\n".join(f"- {i}" for i in resultado_exec["implicacoes"]) + "\n\n"
        + "Plano de Ação Imediato\n"
        + "\n".join(f"- {p}" for p in resultado_exec["plano"])
    )
    
    return {
        "texto": texto_final,
        "detalhes_tecnicos": resposta_dw.get("detalhes_tecnicos", {}) if isinstance(resposta_dw, dict) else {}
    }


def processar_resposta(
    intent_spec: Dict[str, Any],
    dados_dw: Dict[str, Any],
    causas_detector: Optional[Dict[str, Any]] = None,
    behavior_rules_aplicadas: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Processa resposta estruturada baseado nos dados do DW e causas detectadas.
    
    DEPRECATED: Esta função mantém compatibilidade, mas agora usa post_processar_resposta.
    
    Args:
        intent_spec: IntentSpec como dict
        dados_dw: Dados retornados do DW
        causas_detector: Resultado de detectar_causas_para_mes (opcional)
        behavior_rules_aplicadas: Lista de regras comportamentais aplicadas (opcional)
        
    Returns:
        dict estruturado com seções:
        - resumo_executivo
        - diagnostico_causas
        - checklist_problemas
        - plano_acao_7_dias
        - plano_acao_30_dias
        - tendencias_previsao
        - detalhes_tecnicos
    """
    # Chama a nova função post_processar_resposta
    return post_processar_resposta(
        resposta_dw=dados_dw,
        intent_spec=intent_spec,
        regras_aplicadas=[],
        regras_behavior=behavior_rules_aplicadas or []
    )


def _processar_template_negativo(
    intent_spec: Dict[str, Any],
    dados_dw: Dict[str, Any],
    causas_detector: Optional[Dict[str, Any]],
    behavior_rules_aplicadas: Optional[List[str]]
) -> Dict[str, Any]:
    """
    Processa template de resposta negativa (atingimento < 100%).
    """
    gap_total = causas_detector.get("gap_total", 0.0) if causas_detector else dados_dw.get("gap_total", 0.0)
    atingimento_medio = causas_detector.get("atingimento_medio", 0.0) if causas_detector else dados_dw.get("atingimento_medio", 0.0)
    
    causas = causas_detector.get("causas", {}) if causas_detector else {}
    resumo_causas = causas_detector.get("resumo_causas", []) if causas_detector else []
    
    # Monta resumo executivo
    resumo_executivo = _gerar_resumo_executivo_negativo(
        gap_total, atingimento_medio, resumo_causas
    )
    
    # Monta diagnóstico de causas
    # Conforme ENGINEERING_MASTER_PLAN.md seção 9:
    # - Rotas Críticas
    # - Vendedores Críticos
    # - Clientes com Queda
    # - SKUs com Queda
    diagnostico_causas = {
        "rotas_criticas": causas.get("rotas", []),
        "vendedores_criticos": causas.get("vendedores", []),
        "clientes_com_queda": causas.get("clientes", []),
        "skus_com_queda": causas.get("skus", []),
        "outras_causas": causas.get("outras_causas", [])
    }
    
    # Monta checklist de problemas
    checklist_problemas = _gerar_checklist_problemas(causas, gap_total)
    
    # Monta planos de ação
    plano_acao_7_dias = _gerar_plano_acao_7_dias(causas)
    plano_acao_30_dias = _gerar_plano_acao_30_dias(causas)
    
    # Monta tendências e previsão
    tendencias_previsao = _gerar_tendencias_previsao(dados_dw, gap_total, atingimento_medio)
    
    # Monta detalhes técnicos
    detalhes_tecnicos = {
        "intent_spec": intent_spec,
        "filtros_aplicados": intent_spec.get("filtros", {}),
        "behavior_rules_aplicadas": behavior_rules_aplicadas or [],
        "query_executada": f"DW Query para tipo={intent_spec.get('tipo')}, dimensao={intent_spec.get('dimensao_principal')}"
    }
    
    # Conforme ENGINEERING_MASTER_PLAN.md seção 9 - Template Negativo:
    # - resumo_executivo
    # - diagnostico_causas (rotas_criticas, vendedores_criticos, clientes_com_queda, skus_com_queda)
    # - checklist_problemas
    # - plano_acao_7_dias
    # - plano_acao_30_dias
    # - tendencias_riscos (renomeado de tendencias_previsao)
    # - detalhes_tecnicos
    return {
        "resumo_executivo": resumo_executivo,
        "diagnostico_causas": diagnostico_causas,
        "checklist_problemas": checklist_problemas,
        "plano_acao_7_dias": plano_acao_7_dias,
        "plano_acao_30_dias": plano_acao_30_dias,
        "tendencias_riscos": tendencias_previsao,  # Renomeado conforme blueprint
        "detalhes_tecnicos": detalhes_tecnicos
    }


def _processar_template_positivo(
    intent_spec: Dict[str, Any],
    dados_dw: Dict[str, Any],
    behavior_rules_aplicadas: Optional[List[str]]
) -> Dict[str, Any]:
    """
    Processa template de resposta positiva (atingimento >= 100%).
    """
    atingimento_medio = dados_dw.get("atingimento_medio", 100.0)
    meta_total = dados_dw.get("meta_total", 0.0)
    realizado_total = dados_dw.get("realizado_total", 0.0)
    
    # Monta resumo executivo positivo
    resumo_executivo = _gerar_resumo_executivo_positivo(
        meta_total, realizado_total, atingimento_medio
    )
    
    # Conforme ENGINEERING_MASTER_PLAN.md seção 9 - Template Positivo:
    # - resumo_executivo
    # - o_que_deu_certo
    # - quem_puxou_resultado
    # - oportunidades_crescimento
    # - riscos_ocultos
    # - plano_continuidade
    # - detalhes_tecnicos
    
    # Monta seções do template positivo
    o_que_deu_certo = _gerar_o_que_deu_certo(dados_dw)
    quem_puxou_resultado = _gerar_quem_puxou_resultado(dados_dw)
    oportunidades_crescimento = _gerar_oportunidades_crescimento(dados_dw)
    riscos_ocultos = _gerar_riscos_ocultos(dados_dw)
    plano_continuidade = _gerar_plano_continuidade(dados_dw)
    
    # Monta detalhes técnicos
    detalhes_tecnicos = {
        "intent_spec": intent_spec,
        "filtros_aplicados": intent_spec.get("filtros", {}),
        "behavior_rules_aplicadas": behavior_rules_aplicadas or [],
        "query_executada": f"DW Query para tipo={intent_spec.get('tipo')}"
    }
    
    return {
        "resumo_executivo": resumo_executivo,
        "o_que_deu_certo": o_que_deu_certo,
        "quem_puxou_resultado": quem_puxou_resultado,
        "oportunidades_crescimento": oportunidades_crescimento,
        "riscos_ocultos": riscos_ocultos,
        "plano_continuidade": plano_continuidade,
        "detalhes_tecnicos": detalhes_tecnicos
    }


def _gerar_resumo_executivo_negativo(
    gap_total: float,
    atingimento_medio: float,
    resumo_causas: List[str]
) -> str:
    """Gera resumo executivo para template negativo."""
    gap_abs = abs(gap_total)
    
    resumo = f"O atingimento foi de {atingimento_medio:.2f}%, ficando {100.0 - atingimento_medio:.2f}% abaixo da meta. "
    resumo += f"O gap total é de R$ {gap_abs:,.2f}. "
    
    if resumo_causas:
        resumo += "Principais causas: " + "; ".join(resumo_causas[:2]) + "."
    
    return resumo


def _gerar_resumo_executivo_positivo(
    meta_total: float,
    realizado_total: float,
    atingimento_medio: float
) -> str:
    """Gera resumo executivo para template positivo."""
    superacao = realizado_total - meta_total
    
    resumo = f"Meta superada com atingimento de {atingimento_medio:.2f}%. "
    resumo += f"Realizado de R$ {realizado_total:,.2f} superou a meta de R$ {meta_total:,.2f} em R$ {superacao:,.2f}."
    
    return resumo


def _gerar_checklist_problemas(
    causas: Dict[str, Any],
    gap_total: float
) -> List[Dict[str, Any]]:
    """Gera checklist de problemas baseado nas causas."""
    problemas = []
    
    rotas = causas.get("rotas", [])
    if rotas:
        impacto_rotas = sum(abs(r.get("gap_rota", 0)) for r in rotas)
        problemas.append({
            "problema": f"{len(rotas)} rota(s) com gap significativo",
            "impacto": f"R$ {impacto_rotas:,.2f}",
            "causa_provavel": "Baixa performance de rotas específicas",
            "urgencia": "alta" if impacto_rotas >= abs(gap_total) * 0.3 else "media"
        })
    
    vendedores = causas.get("vendedores", [])
    if vendedores:
        impacto_vendedores = sum(abs(v.get("gap_vendedor", 0)) for v in vendedores)
        problemas.append({
            "problema": f"{len(vendedores)} vendedor(es) abaixo de 85% de atingimento",
            "impacto": f"R$ {impacto_vendedores:,.2f}",
            "causa_provavel": "Baixa performance individual",
            "urgencia": "alta" if len(vendedores) > 5 else "media"
        })
    
    clientes = causas.get("clientes", [])
    if clientes:
        impacto_clientes = sum(abs(c.get("variacao_abs", 0)) for c in clientes)
        problemas.append({
            "problema": f"{len(clientes)} cliente(s) com queda significativa",
            "impacto": f"R$ {impacto_clientes:,.2f}",
            "causa_provavel": "Perda de clientes ou redução de pedidos",
            "urgencia": "alta"
        })
    
    skus = causas.get("skus", [])
    if skus:
        impacto_skus = sum(abs(s.get("variacao_abs", 0)) for s in skus)
        problemas.append({
            "problema": f"{len(skus)} SKU(s) com queda expressiva",
            "impacto": f"R$ {impacto_skus:,.2f}",
            "causa_provavel": "Ruptura de estoque ou mix desfavorável",
            "urgencia": "alta"
        })
    
    # Garante mínimo de 5 itens
    while len(problemas) < 5:
        problemas.append({
            "problema": "Análise adicional necessária",
            "impacto": "A definir",
            "causa_provavel": "Revisar dados detalhados",
            "urgencia": "baixa"
        })
    
    return problemas


def _gerar_plano_acao_7_dias(causas: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Gera plano de ação imediata (7 dias)."""
    acoes = []
    
    vendedores = causas.get("vendedores", [])
    if vendedores:
        top_vendedor = min(vendedores, key=lambda x: x.get("atingimento_vendedor", 100))
        acoes.append({
            "acao": f"Coaching urgente para {top_vendedor.get('vendedor_nome')}",
            "responsavel": top_vendedor.get("supervisor_nome", "Supervisor"),
            "prazo": "48 horas",
            "como_medir": f"Aumentar atingimento de {top_vendedor.get('atingimento_vendedor', 0):.1f}% para pelo menos 90%"
        })
    
    rotas = causas.get("rotas", [])
    if rotas:
        top_rota = min(rotas, key=lambda x: x.get("gap_rota", 0))
        acoes.append({
            "acao": f"Revisão imediata da {top_rota.get('rota_nome')}",
            "responsavel": top_rota.get("supervisor_nome", "Supervisor"),
            "prazo": "72 horas",
            "como_medir": "Redução do gap em pelo menos 20%"
        })
    
    clientes = causas.get("clientes", [])
    if clientes:
        top_cliente = min(clientes, key=lambda x: x.get("variacao_pct", 0))
        acoes.append({
            "acao": f"Visita urgente ao cliente {top_cliente.get('cliente_nome')}",
            "responsavel": "Vendedor responsável",
            "prazo": "24 horas",
            "como_medir": "Recuperar pelo menos 50% do faturamento perdido"
        })
    
    return acoes


def _gerar_plano_acao_30_dias(causas: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Gera plano de ação de mitigação (30 dias)."""
    acoes = []
    
    vendedores = causas.get("vendedores", [])
    if vendedores:
        acoes.append({
            "acao": "Programa de treinamento para vendedores abaixo de 85%",
            "objetivo": "Elevar atingimento médio para pelo menos 90%",
            "responsavel": "Supervisão",
            "prazo": "30 dias",
            "metrica_sucesso": "Atingimento médio >= 90%"
        })
    
    rotas = causas.get("rotas", [])
    if rotas:
        acoes.append({
            "acao": "Revisão completa de carteira das rotas com maior gap",
            "objetivo": "Redistribuir clientes e otimizar rotas",
            "responsavel": "Gerência",
            "prazo": "30 dias",
            "metrica_sucesso": "Redução de 30% no gap total"
        })
    
    clientes = causas.get("clientes", [])
    if clientes:
        acoes.append({
            "acao": "Plano de recuperação para clientes com queda > 25%",
            "objetivo": "Recuperar faturamento perdido",
            "responsavel": "Equipe comercial",
            "prazo": "30 dias",
            "metrica_sucesso": "Recuperação de 40% do faturamento perdido"
        })
    
    return acoes


def _gerar_tendencias_previsao(
    dados_dw: Dict[str, Any],
    gap_total: float,
    atingimento_medio: float
) -> Dict[str, Any]:
    """Gera tendências e previsão baseado nos dados."""
    # Simplificado: usa dados atuais para projetar
    # Em produção, poderia usar histórico de meses anteriores
    
    gap_abs = abs(gap_total)
    
    # Cenário atual: mantém ritmo
    cenario_atual = {
        "fechamento_previsto": dados_dw.get("realizado_total", 0.0),
        "gap_previsto": gap_total,
        "atingimento_previsto": atingimento_medio
    }
    
    # Cenário otimista: recupera 50% do gap
    cenario_otimista = {
        "fechamento_previsto": dados_dw.get("realizado_total", 0.0) + (gap_abs * 0.5),
        "gap_previsto": gap_total * 0.5,
        "atingimento_previsto": min(100.0, atingimento_medio + ((100.0 - atingimento_medio) * 0.5))
    }
    
    # Cenário pessimista: gap aumenta 20%
    cenario_pessimista = {
        "fechamento_previsto": dados_dw.get("realizado_total", 0.0) - (gap_abs * 0.2),
        "gap_previsto": gap_total * 1.2,
        "atingimento_previsto": max(0.0, atingimento_medio - ((100.0 - atingimento_medio) * 0.2))
    }
    
    return {
        "tendencias_identificadas": [
            "Gap concentrado em poucas rotas",
            "Vendedores com baixa performance precisam de suporte imediato"
        ],
        "probabilidade_recuperacao": 60.0 if gap_abs < 1000000 else 40.0,
        "cenario_atual": cenario_atual,
        "cenario_otimista": cenario_otimista,
        "cenario_pessimista": cenario_pessimista
    }


def _gerar_o_que_deu_certo(dados_dw: Dict[str, Any]) -> List[str]:
    """Gera lista do que deu certo (template positivo)."""
    o_que_deu_certo = []
    
    atingimento_medio = dados_dw.get("atingimento_medio", 0.0)
    if atingimento_medio >= 100.0:
        o_que_deu_certo.append(f"Meta superada com {atingimento_medio:.2f}% de atingimento")
    
    realizado_total = dados_dw.get("realizado_total", 0.0)
    meta_total = dados_dw.get("meta_total", 0.0)
    if realizado_total > meta_total:
        superacao = realizado_total - meta_total
        o_que_deu_certo.append(f"Superação de R$ {superacao:,.2f} sobre a meta")
    
    # Adiciona mais itens baseado nos dados disponíveis
    vendedores_top = dados_dw.get("top_vendedores", [])
    if vendedores_top:
        o_que_deu_certo.append(f"{len(vendedores_top)} vendedor(es) com performance acima da média")
    
    return o_que_deu_certo if o_que_deu_certo else ["Análise detalhada necessária"]


def _gerar_quem_puxou_resultado(dados_dw: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Gera lista de quem puxou o resultado para cima (template positivo)."""
    quem_puxou = []
    
    # Top vendedores
    vendedores_top = dados_dw.get("top_vendedores", [])
    for v in vendedores_top[:5]:  # Top 5
        quem_puxou.append({
            "tipo": "vendedor",
            "nome": v.get("vendedor_nome", ""),
            "contribuicao": f"R$ {v.get('realizado_vendedor_mes', 0):,.2f}",
            "atingimento": f"{v.get('atingimento_vendedor', 0):.1f}%"
        })
    
    # Top rotas
    rotas_top = dados_dw.get("top_rotas", [])
    for r in rotas_top[:3]:  # Top 3
        quem_puxou.append({
            "tipo": "rota",
            "nome": r.get("rota_nome", ""),
            "contribuicao": f"R$ {r.get('realizado_rota_mes', 0):,.2f}",
            "atingimento": f"{r.get('atingimento_rota', 0):.1f}%"
        })
    
    return quem_puxou if quem_puxou else [{"tipo": "geral", "nome": "Equipe", "contribuicao": "Distribuída", "atingimento": "N/A"}]


def _gerar_riscos_ocultos(dados_dw: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Gera lista de riscos ocultos (template positivo)."""
    riscos = []
    
    # Concentração excessiva
    top_clientes = dados_dw.get("top_clientes", [])
    if top_clientes:
        faturamento_top3 = sum(c.get("faturamento_total", 0) for c in top_clientes[:3])
        faturamento_total = dados_dw.get("realizado_total", 1)
        concentracao_pct = (faturamento_top3 / faturamento_total * 100) if faturamento_total > 0 else 0
        
        if concentracao_pct > 40:
            riscos.append({
                "risco": "Concentração excessiva em poucos clientes",
                "severidade": "alta" if concentracao_pct > 60 else "média",
                "descricao": f"Top 3 clientes representam {concentracao_pct:.1f}% do faturamento"
            })
    
    # Dependência de produtos específicos
    produtos_top = dados_dw.get("top_produtos", [])
    if produtos_top:
        faturamento_top5 = sum(p.get("faturamento_total", 0) for p in produtos_top[:5])
        faturamento_total = dados_dw.get("realizado_total", 1)
        concentracao_produtos = (faturamento_top5 / faturamento_total * 100) if faturamento_total > 0 else 0
        
        if concentracao_produtos > 50:
            riscos.append({
                "risco": "Dependência de mix reduzido",
                "severidade": "média",
                "descricao": f"Top 5 produtos representam {concentracao_produtos:.1f}% do faturamento"
            })
    
    return riscos if riscos else [{"risco": "Nenhum risco crítico identificado", "severidade": "baixa", "descricao": "Situação estável"}]


def _gerar_plano_continuidade(dados_dw: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Gera plano de continuidade (template positivo)."""
    plano = []
    
    # Manter performance
    plano.append({
        "acao": "Manter ritmo atual de vendas",
        "objetivo": "Sustentar atingimento acima de 100%",
        "responsavel": "Equipe comercial",
        "prazo": "Contínuo",
        "metrica_sucesso": "Atingimento >= 100%"
    })
    
    # Expandir oportunidades
    oportunidades = dados_dw.get("oportunidades_crescimento", [])
    if oportunidades:
        plano.append({
            "acao": "Explorar oportunidades de crescimento identificadas",
            "objetivo": f"Expandir {len(oportunidades)} oportunidade(s)",
            "responsavel": "Equipe comercial",
            "prazo": "30 dias",
            "metrica_sucesso": "Aumento de 10% no faturamento"
        })
    
    # Diversificar mix
    plano.append({
        "acao": "Diversificar mix de produtos",
        "objetivo": "Reduzir dependência de produtos específicos",
        "responsavel": "Equipe comercial",
        "prazo": "60 dias",
        "metrica_sucesso": "Redução de concentração em top 5 produtos"
    })
    
    return plano


def _gerar_oportunidades_crescimento(dados_dw: Dict[str, Any]) -> Dict[str, Any]:
    """Gera oportunidades de crescimento para template positivo."""
    return {
        "vendedores_destaque": [],
        "rotas_superaram_meta": [],
        "clientes_expansao": [],
        "riscos_concentracao": []
    }

