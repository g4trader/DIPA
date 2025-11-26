"""
Formatadores de Resposta Executiva para diferentes tipos de análise.

Este módulo contém funções que transformam dados brutos do DW em
textos executivos prontos para consumo da diretoria/comercial.

ARQUITETURA:
- Cada função recebe dados estruturados do DW
- Gera texto em português, direto e objetivo
- Sem jargões técnicos (DW, query, etc.)
- Foco em insights acionáveis
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def formatar_valor_br(valor: float) -> str:
    """
    Formata valor monetário em formato brasileiro.
    
    Args:
        valor: Valor em float
        
    Returns:
        String formatada (ex: "R$ 843.012,12")
    """
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_percentual(valor: float, casas_decimais: int = 2) -> str:
    """
    Formata percentual em formato brasileiro.
    
    Args:
        valor: Percentual em float
        casas_decimais: Número de casas decimais
        
    Returns:
        String formatada (ex: "71,48%")
    """
    return f"{valor:.{casas_decimais}f}%".replace(".", ",")


def formatar_periodo_descricao(
    data_ini_mes_anterior: Optional[str],
    data_fim_mes_anterior: Optional[str],
    data_ini_mes_atual: Optional[str],
    data_fim_mes_atual: Optional[str]
) -> str:
    """
    Formata descrição do período analisado.
    
    Args:
        data_ini_mes_anterior: Data inicial do mês anterior
        data_fim_mes_anterior: Data final do mês anterior
        data_ini_mes_atual: Data inicial do mês atual
        data_fim_mes_atual: Data final do mês atual
        
    Returns:
        String descritiva (ex: "Set/25 x Out/25")
    """
    if not data_ini_mes_anterior or not data_ini_mes_atual:
        return "período analisado"
    
    try:
        # Extrai mês e ano
        dt_anterior = datetime.strptime(data_ini_mes_anterior, "%Y-%m-%d")
        dt_atual = datetime.strptime(data_ini_mes_atual, "%Y-%m-%d")
        
        mes_anterior_num = dt_anterior.month
        mes_atual_num = dt_atual.month
        ano = dt_anterior.year
        
        # Mapeia números de mês para abreviações em português
        meses_pt = {
            1: "jan", 2: "fev", 3: "mar", 4: "abr",
            5: "mai", 6: "jun", 7: "jul", 8: "ago",
            9: "set", 10: "out", 11: "nov", 12: "dez"
        }
        
        mes_anterior_pt = meses_pt.get(mes_anterior_num, f"{mes_anterior_num:02d}")
        mes_atual_pt = meses_pt.get(mes_atual_num, f"{mes_atual_num:02d}")
        
        # Extrai últimos 2 dígitos do ano
        ano_curto = str(ano)[-2:]
        
        return f"{mes_anterior_pt}/{ano_curto} x {mes_atual_pt}/{ano_curto}"
    except Exception as e:
        logger.warning(f"[formatar_periodo_descricao] Erro ao formatar período: {e}")
        return "período analisado"


def calcular_metricas_q2(dados: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calcula métricas agregadas a partir dos dados Q2.
    
    Args:
        dados: Lista de clientes com queda de faturamento
        
    Returns:
        Dict com métricas calculadas
    """
    if not dados:
        return {
            "total_clientes": 0,
            "queda_media_absoluta": 0.0,
            "queda_media_percentual": 0.0,
            "queda_maxima_absoluta": 0.0,
            "queda_maxima_percentual": 0.0,
            "queda_total_absoluta": 0.0
        }
    
    total_clientes = len(dados)
    quedas_absolutas = [c.get("queda_absoluta", 0.0) for c in dados if isinstance(c.get("queda_absoluta"), (int, float))]
    quedas_percentuais = [c.get("queda_percentual", 0.0) for c in dados if isinstance(c.get("queda_percentual"), (int, float))]
    
    queda_media_absoluta = sum(quedas_absolutas) / len(quedas_absolutas) if quedas_absolutas else 0.0
    queda_media_percentual = sum(quedas_percentuais) / len(quedas_percentuais) if quedas_percentuais else 0.0
    queda_maxima_absoluta = max(quedas_absolutas) if quedas_absolutas else 0.0
    queda_maxima_percentual = max(quedas_percentuais) if quedas_percentuais else 0.0
    queda_total_absoluta = sum(quedas_absolutas)
    
    return {
        "total_clientes": total_clientes,
        "queda_media_absoluta": queda_media_absoluta,
        "queda_media_percentual": queda_media_percentual,
        "queda_maxima_absoluta": queda_maxima_absoluta,
        "queda_maxima_percentual": queda_maxima_percentual,
        "queda_total_absoluta": queda_total_absoluta
    }


def agrupar_por_rota(dados: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Agrupa clientes por rota e calcula totais.
    
    Args:
        dados: Lista de clientes com queda
        
    Returns:
        Dict com rota como chave e dict com contagem e queda total
    """
    rotas = {}
    
    for cliente in dados:
        rota = cliente.get("rota") or cliente.get("vendedor_nome") or "N/A"
        
        if rota not in rotas:
            rotas[rota] = {
                "total_clientes": 0,
                "queda_total": 0.0,
                "clientes": []
            }
        
        rotas[rota]["total_clientes"] += 1
        rotas[rota]["queda_total"] += cliente.get("queda_absoluta", 0.0)
        rotas[rota]["clientes"].append(cliente)
    
    return rotas


def formatar_resposta_q2_exec(dados_q2: Dict[str, Any]) -> str:
    """
    Formata resposta executiva para Q2 (queda de faturamento).
    
    Gera um texto em português, direto e objetivo, voltado para diretoria/comercial,
    sem jargões técnicos.
    
    Estrutura do texto:
    1. Abertura executiva (período, visão geral)
    2. Destaques (top 5 clientes)
    3. Análise por rota (se aplicável)
    4. Recomendações de ação
    
    Args:
        dados_q2: Dict com estrutura:
            - "dados_dw": resultado do orquestrador
                - "dados": lista de clientes
                - "metrics": métricas agregadas (opcional)
            - "periodo": dict com datas do período
            - "intent_spec": IntentSpec (opcional)
        
    Returns:
        String com texto executivo formatado
    """
    # Extrai dados principais
    dados_dw = dados_q2.get("dados_dw", {})
    periodo = dados_q2.get("periodo", {})
    
    # Lista de clientes
    clientes = dados_dw.get("dados", [])
    if not isinstance(clientes, list):
        clientes = []
    
    # Métricas (pode vir do DW ou calcular)
    metrics = dados_dw.get("metrics", {})
    
    # Se não tem métricas ou está vazio, calcula
    if not metrics or len(metrics) == 0:
        metrics = calcular_metricas_q2(clientes)
    
    # Período
    periodo_desc = formatar_periodo_descricao(
        periodo.get("data_ini_mes_anterior"),
        periodo.get("data_fim_mes_anterior"),
        periodo.get("data_ini_mes_atual"),
        periodo.get("data_fim_mes_atual")
    )
    
    # ========================================================================
    # 1. ABERTURA EXECUTIVA
    # ========================================================================
    texto = f"Análise de Queda de Faturamento - {periodo_desc}\n\n"
    
    # Prioriza total_clientes_queda das métricas fornecidas
    total_clientes = metrics.get("total_clientes_queda") or metrics.get("total_clientes", len(clientes))
    queda_media_abs = metrics.get("queda_media_absoluta", 0.0)
    queda_media_pct = metrics.get("queda_media_percentual", 0.0)
    queda_max_abs = metrics.get("queda_maxima_absoluta", 0.0)
    queda_max_pct = metrics.get("queda_maxima_percentual", 0.0)
    
    # Calcula percentual de clientes com queda (se tiver total de clientes que compraram)
    total_com_faturamento = dados_dw.get("total_com_faturamento_mes_anterior")
    if total_com_faturamento and total_com_faturamento > 0:
        pct_clientes_queda = (total_clientes / total_com_faturamento) * 100
        texto += (
            f"Foram identificados {total_clientes} clientes com queda de faturamento "
            f"({formatar_percentual(pct_clientes_queda, 1)} dos clientes que compraram no mês anterior). "
        )
    else:
        texto += f"Foram identificados {total_clientes} clientes com queda de faturamento. "
    
    texto += (
        f"A queda média foi de {formatar_valor_br(queda_media_abs)} "
        f"({formatar_percentual(queda_media_pct)}), com queda máxima de "
        f"{formatar_valor_br(queda_max_abs)} ({formatar_percentual(queda_max_pct)}).\n\n"
    )
    
    # ========================================================================
    # 2. DESTAQUES - TOP 5 CLIENTES
    # ========================================================================
    if clientes:
        top_5 = clientes[:5]
        texto += "Principais clientes com queda:\n\n"
        
        for i, cliente in enumerate(top_5, 1):
            nome = cliente.get("cliente_nome", "Cliente sem nome")
            queda_abs = cliente.get("queda_absoluta", 0.0)
            queda_pct = cliente.get("queda_percentual", 0.0)
            
            texto += (
                f"{i}. {nome}: queda de {formatar_valor_br(queda_abs)} "
                f"({formatar_percentual(queda_pct)}).\n"
            )
        
        # Comentário sobre concentração (top 2)
        if len(top_5) >= 2:
            queda_top2 = sum(c.get("queda_absoluta", 0.0) for c in top_5[:2])
            # Usa queda_total das métricas ou calcula da lista
            queda_total = metrics.get("queda_total_absoluta")
            if not queda_total or queda_total == 0:
                queda_total = sum(c.get("queda_absoluta", 0.0) for c in clientes)
            
            if queda_total > 0:
                pct_top2 = (queda_top2 / queda_total) * 100
                if pct_top2 > 20:  # Só menciona se for significativo
                    texto += (
                        f"\nOs dois principais clientes ({top_5[0].get('cliente_nome', 'Cliente 1')} e "
                        f"{top_5[1].get('cliente_nome', 'Cliente 2')}) representam juntos "
                        f"{formatar_percentual(pct_top2, 1)} da queda total.\n\n"
                    )
                else:
                    texto += "\n"
        else:
            texto += "\n"
    
    # ========================================================================
    # 3. ANÁLISE POR ROTA
    # ========================================================================
    if clientes:
        rotas = agrupar_por_rota(clientes)
        
        # Ordena rotas por queda total
        rotas_ordenadas = sorted(
            rotas.items(),
            key=lambda x: x[1]["queda_total"],
            reverse=True
        )
        
        # Pega top 3 rotas
        top_rotas = rotas_ordenadas[:3]
        
        if top_rotas and len(top_rotas) > 0:
            texto += "Rotas mais impactadas:\n\n"
            
            for rota, dados_rota in top_rotas:
                if rota != "N/A":
                    texto += (
                        f"- {rota}: {dados_rota['total_clientes']} cliente(s) com queda total de "
                        f"{formatar_valor_br(dados_rota['queda_total'])}.\n"
                    )
            
            texto += "\n"
    
    # ========================================================================
    # 4. RECOMENDAÇÕES DE AÇÃO
    # ========================================================================
    texto += "Recomendações:\n\n"
    
    # Calcula threshold para recomendação
    if clientes:
        quedas_pct = [c.get("queda_percentual", 0.0) for c in clientes if isinstance(c.get("queda_percentual"), (int, float))]
        quedas_abs = [c.get("queda_absoluta", 0.0) for c in clientes if isinstance(c.get("queda_absoluta"), (int, float))]
        
        # Threshold: percentil 80 de queda percentual
        if quedas_pct:
            quedas_pct_sorted = sorted(quedas_pct, reverse=True)
            threshold_pct = quedas_pct_sorted[min(9, len(quedas_pct_sorted) - 1)]  # Top 10 ou menos
        
        # Threshold: percentil 80 de queda absoluta
        if quedas_abs:
            quedas_abs_sorted = sorted(quedas_abs, reverse=True)
            threshold_abs = quedas_abs_sorted[min(9, len(quedas_abs_sorted) - 1)]  # Top 10 ou menos
        
        # Conta clientes prioritários
        clientes_prioritarios = [
            c for c in clientes
            if c.get("queda_percentual", 0) >= 70.0
            and c.get("faturamento_mes_anterior", 0) >= 5000.0
        ]
        
        if clientes_prioritarios:
            texto += (
                f"Recomenda-se contato ativo com {len(clientes_prioritarios)} clientes prioritários "
                f"(queda superior a 70% e ticket médio mensal acima de R$ 5.000,00). "
            )
        else:
            texto += (
                f"Recomenda-se contato ativo com os top 20 clientes com maior queda, "
                f"priorizando aqueles com queda superior a 70% e ticket médio mensal acima de R$ 5.000,00. "
            )
        
        texto += (
            "A equipe comercial deve investigar as causas da queda (mudança de fornecedor, "
            "fechamento temporário, sazonalidade) e propor ações de reativação imediata.\n"
        )
    else:
        texto += (
            "Não foram identificados clientes com queda significativa no período analisado. "
            "Recomenda-se monitoramento contínuo para detectar tendências de queda.\n"
        )
    
    return texto.strip()


def formatar_resposta_q2_completa(
    dados_q2: Dict[str, Any],
    incluir_dados_estruturados: bool = True
) -> Dict[str, Any]:
    """
    Formata resposta completa Q2 incluindo texto executivo e dados estruturados.
    
    Args:
        dados_q2: Dict com dados Q2 (mesmo formato de formatar_resposta_q2_exec)
        incluir_dados_estruturados: Se True, inclui dados brutos na resposta
        
    Returns:
        Dict com:
        - tipo: "Q2_QUEDA_FATURAMENTO"
        - periodo: descrição do período
        - texto_executivo: texto formatado
        - dados: dados estruturados (se incluir_dados_estruturados=True)
    """
    texto_executivo = formatar_resposta_q2_exec(dados_q2)
    
    periodo = dados_q2.get("periodo", {})
    periodo_desc = formatar_periodo_descricao(
        periodo.get("data_ini_mes_anterior"),
        periodo.get("data_fim_mes_anterior"),
        periodo.get("data_ini_mes_atual"),
        periodo.get("data_fim_mes_atual")
    )
    
    resultado = {
        "tipo": "Q2_QUEDA_FATURAMENTO",
        "periodo": periodo_desc,
        "texto_executivo": texto_executivo
    }
    
    if incluir_dados_estruturados:
        resultado["dados"] = dados_q2.get("dados_dw", {})
    
    return resultado

