"""
Executive Formatter - DIPAM COPILOT™.

Este módulo é responsável por transformar qualquer resultado DW em uma
narrativa executiva de alto padrão, de maneira consistente e reutilizável.

Cada tipo de intent DW tem sua própria narrativa específica, focada em:
- Resumo Executivo contextualizado
- Principais Achados com TOP N
- Implicações Comerciais focadas na dor real
- Plano de Ação Imediato com passos concretos
"""

from typing import Dict, Any, List, Optional


def formatar_execucao(dados, intent_spec, filtros, regras_behavior):
    """
    Gera narrativa executiva de alto nível com 4 blocos:
    1. Resumo Executivo
    2. Principais Achados
    3. Implicações Comerciais
    4. Plano de Ação Imediato
    
    Args:
        dados: Lista de dados retornados do DW (pode ser None ou lista vazia)
        intent_spec: IntentSpec (pode ser dict ou objeto)
        filtros: Dict com filtros aplicados
        regras_behavior: Lista de regras comportamentais aplicadas
    
    Returns:
        Dict com estrutura:
        {
            "resumo": str,
            "achados": List[str],
            "implicacoes": List[str],
            "plano": List[str],
            "top_alvos": List[str]  # TOP 10 alvos prioritários (lista vazia se não houver dados)
        }
    """
    # Extrai tipo do intent_spec (pode ser dict ou objeto)
    intent_tipo = None
    if hasattr(intent_spec, 'tipo'):
        intent_tipo = intent_spec.tipo
    elif isinstance(intent_spec, dict):
        intent_tipo = intent_spec.get("tipo", "outros")
    else:
        intent_tipo = "outros"
    
    # Normaliza dados
    if not dados or (isinstance(dados, list) and len(dados) == 0):
        dados = None
    
    # Dispatcher baseado no tipo de intent
    if intent_tipo == "clientes_sem_compra":
        return _format_clientes_sem_compra(dados, intent_spec, filtros, regras_behavior)
    elif intent_tipo == "queda_faturamento":
        return _format_queda_faturamento(dados, intent_spec, filtros, regras_behavior)
    elif intent_tipo == "meta_departamento":
        return _format_meta_departamento(dados, intent_spec, filtros, regras_behavior)
    elif intent_tipo == "positivacao":
        return _format_positivacao(dados, intent_spec, filtros, regras_behavior)
    elif intent_tipo == "vendas_baixas":
        return _format_vendas_baixas(dados, intent_spec, filtros, regras_behavior)
    elif intent_tipo == "recompra":
        return _format_recompra(dados, intent_spec, filtros, regras_behavior)
    elif intent_tipo == "clientes_sem_item":
        return _format_clientes_sem_item(dados, intent_spec, filtros, regras_behavior)
    elif intent_tipo == "mix_nissin":
        return _format_mix_nissin(dados, intent_spec, filtros, regras_behavior)
    elif intent_tipo == "mix":
        return _format_mix(dados, intent_spec, filtros, regras_behavior)
    else:
        # Fallback genérico para outros tipos
        return _format_generico(dados, intent_spec, filtros, regras_behavior)


def _format_clientes_sem_compra(dados, intent_spec, filtros, regras_behavior):
    """
    Formata narrativa para clientes sem compra há X dias.
    
    Campos esperados em 'dados':
    - cliente_id, nome
    - segmento, rota_id
    - data_ultima_compra
    - dias_sem_compra
    """
    if not dados:
        return {
            "resumo": "Nenhum cliente ativo foi identificado sem compras no período analisado.",
            "achados": [
                "A ausência de clientes sem compra pode indicar boa rotatividade de carteira.",
                "Pode também indicar que os filtros aplicados (dias, segmento, rota) estão muito restritivos."
            ],
            "implicacoes": [
                "Situação positiva: carteira ativa e engajada.",
                "Recomenda-se revisar periodicamente para evitar surpresas."
            ],
            "plano": [
                "Validar se os filtros de dias sem compra estão adequados.",
                "Manter monitoramento semanal da carteira fria.",
                "Criar alertas automáticos para clientes que ultrapassarem 60 dias sem compra."
            ],
            "top_alvos": []
        }
    
    # Ordena por dias_sem_compra (decrescente) se existir
    if dados and isinstance(dados[0], dict) and "dias_sem_compra" in dados[0]:
        dados_ordenados = sorted(dados, key=lambda x: x.get("dias_sem_compra", 0) or 0, reverse=True)
    else:
        dados_ordenados = dados
    
    # TOP 10 clientes mais críticos
    top_10 = dados_ordenados[:10] if len(dados_ordenados) > 10 else dados_ordenados
    
    # Calcula métricas
    total_clientes = len(dados)
    dias_min = filtros.get("dias", 60)
    
    # Tenta calcular média de dias sem compra
    dias_sem_compra_list = [d.get("dias_sem_compra") for d in dados if isinstance(d, dict) and d.get("dias_sem_compra")]
    media_dias = sum(dias_sem_compra_list) / len(dias_sem_compra_list) if dias_sem_compra_list else None
    
    # Tenta identificar rotas mais afetadas
    rotas_afetadas = {}
    for d in dados:
        if isinstance(d, dict) and d.get("rota_id"):
            rota = d.get("rota_id")
            rotas_afetadas[rota] = rotas_afetadas.get(rota, 0) + 1
    
    rotas_top = sorted(rotas_afetadas.items(), key=lambda x: x[1], reverse=True)[:3] if rotas_afetadas else []
    
    # Detecta cenário crítico (muitos clientes sem compra)
    is_critico = total_clientes >= 100 or (media_dias and media_dias > 90)
    
    # Constrói resumo executivo (2-3 frases, direto, com números)
    resumo_parts = [
        f"Foram identificados {total_clientes} clientes ativos sem compras há mais de {dias_min} dias."
    ]
    if media_dias:
        resumo_parts.append(f"A média de dias sem compra é de {media_dias:.0f} dias.")
    if rotas_top:
        rotas_str = ", ".join([f"{r[0]}" for r in rotas_top])
        resumo_parts.append(f"As rotas mais afetadas são: {rotas_str} ({rotas_top[0][1]} clientes cada).")
    
    resumo = " ".join(resumo_parts)
    
    # Principais Achados (3-5 bullets concretos)
    achados = [
        f"Os {min(10, total_clientes)} clientes mais críticos concentram-se principalmente em rotas específicas."
    ]
    if rotas_top:
        pct_rota = (rotas_top[0][1] * 100.0 / total_clientes) if total_clientes > 0 else 0
        achados.append(f"Rota {rotas_top[0][0]} concentra {pct_rota:.0f}% dos clientes sem compra ({rotas_top[0][1]} clientes).")
    if media_dias and media_dias > 100:
        achados.append(f"Média de {media_dias:.0f} dias sem compra indica carteira muito fria, com risco alto de churn.")
    if total_clientes > 500:
        achados.append(f"Volume crítico de {total_clientes} clientes sem compra representa risco significativo de receita.")
    achados.append("Alguns clientes estratégicos podem estar sendo atendidos de forma reativa, e não proativa.")
    
    # Implicações Comerciais (risco de receita, perda de share, etc.)
    implicacoes = [
        f"Risco de perda definitiva de {total_clientes} clientes para concorrentes, impactando receita recorrente."
    ]
    if media_dias and media_dias > 90:
        implicacoes.append("Queda de share em regiões onde a Dipam já tinha presença consolidada.")
    implicacoes.append("Necessidade de ações imediatas de reativação com foco em carteira fria.")
    if rotas_top:
        implicacoes.append(f"Rotas {', '.join([r[0] for r in rotas_top[:2]])} requerem atenção prioritária da supervisão.")
    
    # Plano de Ação Imediato (formato imperativo, acionável)
    plano = [
        f"Priorizar contato imediato com os {min(10, total_clientes)} clientes com maior tempo sem compra (acima de {max(100, int(media_dias)) if media_dias else 100} dias)."
    ]
    if rotas_top:
        plano.append(f"Agendar blitz de vendas nas rotas {', '.join([r[0] for r in rotas_top[:3]])} nos próximos 7 dias.")
    plano.append("Criar campanha específica de reativação com foco nos SKUs âncora da indústria e condições especiais.")
    plano.append("Acionar supervisores das rotas mais afetadas para plano tático de recuperação imediata.")
    plano.append("Monitorar semanalmente a evolução desses clientes até normalizar o ciclo de compras.")
    
    # Gera TOP 10 alvos prioritários
    top_alvos = []
    for row in top_10:
        partes = []
        
        if "nome" in row:
            partes.append(row["nome"])
        elif "nome_cliente" in row:
            partes.append(row["nome_cliente"])
        elif "cliente_id" in row:
            partes.append(f"Cliente {row['cliente_id']}")
        
        if "dias_sem_compra" in row:
            dias = row.get("dias_sem_compra", 0) or 0
            partes.append(f"{dias} dias sem compra")
        
        # Formata rota para o formato esperado pelo frontend: "CLIENTE | X dias sem compra | Rota: Y"
        if "rota_id" in row and row.get("rota_id"):
            rota_valor = row['rota_id']
            # Se rota_id for numérico, formata como "ROTA XX"
            if isinstance(rota_valor, (int, float)):
                partes.append(f"Rota: ROTA {int(rota_valor)}")
            else:
                partes.append(f"Rota: {rota_valor}")
        elif "rota" in row and row.get("rota"):
            partes.append(f"Rota: {row['rota']}")
        
        if "supervisor" in row:
            partes.append(f"Sup.: {row['supervisor']}")
        elif "supervisor_id" in row:
            partes.append(f"Sup.: {row['supervisor_id']}")
        
        if partes:
            top_alvos.append(" | ".join(partes))
    
    return {
        "resumo": resumo,
        "achados": achados,
        "implicacoes": implicacoes,
        "plano": plano,
        "top_alvos": top_alvos
    }


def _format_queda_faturamento(dados, intent_spec, filtros, regras_behavior):
    """
    Formata narrativa para queda de faturamento ano contra ano.
    
    Campos esperados em 'dados':
    - cliente_id, nome
    - faturamento_ano_base, faturamento_ano_comparado
    - variacao_abs, variacao_pct
    """
    if not dados:
        return {
            "resumo": "Nenhum cliente foi identificado com queda de faturamento no período analisado.",
            "achados": [
                "A ausência de quedas pode indicar estabilidade ou crescimento da carteira.",
                "Pode também indicar que os filtros aplicados estão muito restritivos."
            ],
            "implicacoes": [
                "Situação positiva: carteira mantendo ou crescendo faturamento.",
                "Recomenda-se monitorar tendências para identificar riscos antecipadamente."
            ],
            "plano": [
                "Validar se os anos comparados estão corretos.",
                "Manter análise comparativa trimestral.",
                "Criar alertas para quedas acima de 20%."
            ],
            "top_alvos": []
        }
    
    # Ordena por variação absoluta (decrescente) se existir
    if dados and isinstance(dados[0], dict) and "variacao_abs" in dados[0]:
        dados_ordenados = sorted(dados, key=lambda x: abs(x.get("variacao_abs", 0) or 0), reverse=True)
    elif dados and isinstance(dados[0], dict) and "variacao_pct" in dados[0]:
        dados_ordenados = sorted(dados, key=lambda x: abs(x.get("variacao_pct", 0) or 0), reverse=True)
    else:
        dados_ordenados = dados
    
    # TOP 10 clientes com maior queda
    top_10 = dados_ordenados[:10] if len(dados_ordenados) > 10 else dados_ordenados
    
    # Calcula métricas
    total_clientes = len(dados)
    ano_base = filtros.get("ano_base", "N/A")
    ano_comparado = filtros.get("ano_comparado", "N/A")
    
    # Tenta calcular queda total
    variacao_abs_list = [d.get("variacao_abs") for d in dados if isinstance(d, dict) and d.get("variacao_abs")]
    queda_total = sum([abs(v) for v in variacao_abs_list if v and v < 0]) if variacao_abs_list else None
    
    # Tenta calcular média de queda percentual
    variacao_pct_list = [d.get("variacao_pct") for d in dados if isinstance(d, dict) and d.get("variacao_pct")]
    media_queda_pct = sum([abs(v) for v in variacao_pct_list if v and v < 0]) / len([v for v in variacao_pct_list if v and v < 0]) if variacao_pct_list and any(v and v < 0 for v in variacao_pct_list) else None
    
    # Detecta cenário crítico (queda relevante)
    is_critico = (media_queda_pct and media_queda_pct > 20) or (queda_total and abs(queda_total) > 100000)
    
    # Constrói resumo executivo (2-3 frases, direto, com números)
    resumo_parts = [
        f"Foram identificados {total_clientes} clientes com queda de faturamento comparando {ano_comparado} vs {ano_base}."
    ]
    if queda_total:
        resumo_parts.append(f"A queda total acumulada é de R$ {abs(queda_total):,.2f}.")
    if media_queda_pct:
        resumo_parts.append(f"A média de queda percentual é de {media_queda_pct:.1f}%.")
    
    resumo = " ".join(resumo_parts)
    
    # Principais Achados (3-5 bullets concretos)
    achados = [
        f"Os {min(10, total_clientes)} clientes com maior queda concentram a maior parte do impacto financeiro."
    ]
    if queda_total:
        # Calcula impacto dos top 10
        top_10_queda = sum([abs(d.get("variacao_abs", 0) or 0) for d in top_10 if isinstance(d, dict) and d.get("variacao_abs") and d.get("variacao_abs") < 0])
        pct_top10 = (top_10_queda * 100.0 / abs(queda_total)) if queda_total != 0 else 0
        achados.append(f"Top 10 clientes respondem por {pct_top10:.0f}% da queda total (R$ {top_10_queda:,.2f}).")
    if media_queda_pct and media_queda_pct > 25:
        achados.append(f"Queda média de {media_queda_pct:.1f}% indica migração significativa para concorrentes ou redução estrutural de mix.")
    if total_clientes > 50:
        achados.append(f"Volume de {total_clientes} clientes com queda representa risco crítico de receita recorrente.")
    achados.append("Há concentração de quedas em clientes que antes eram considerados estratégicos.")
    
    # Implicações Comerciais (risco de receita, perda de share, etc.)
    implicacoes = [
        f"Perda de share de mercado em {total_clientes} clientes antes saudáveis, impactando receita recorrente."
    ]
    if queda_total:
        implicacoes.append(f"Impacto financeiro direto de R$ {abs(queda_total):,.2f} no faturamento total da empresa.")
    implicacoes.append("Risco de deterioração do relacionamento comercial com clientes estratégicos.")
    implicacoes.append("Necessidade de ações imediatas de recuperação para evitar perda definitiva.")
    
    # Plano de Ação Imediato (formato imperativo, acionável)
    plano = [
        f"Agendar reuniões de recuperação imediata com os {min(10, total_clientes)} clientes com maior queda (acima de R$ {abs(top_10[0].get('variacao_abs', 0)) if top_10 and isinstance(top_10[0], dict) else 0:,.2f} cada)."
    ]
    plano.append("Revisar mix de produtos oferecidos e identificar oportunidades de cross-sell e upsell.")
    plano.append("Criar ações conjuntas com indústrias para recuperação desses clientes com condições especiais.")
    plano.append("Acionar supervisores e vendedores responsáveis para plano tático de recuperação em 7 dias.")
    plano.append("Acompanhar evolução mensalmente até reverter a tendência e recuperar faturamento perdido.")
    
    # Gera TOP 10 alvos prioritários
    top_alvos = []
    for row in top_10:
        partes = []
        
        if "nome" in row:
            partes.append(row["nome"])
        elif "nome_cliente" in row:
            partes.append(row["nome_cliente"])
        elif "cliente_id" in row:
            partes.append(f"Cliente {row['cliente_id']}")
        
        if "variacao_abs" in row:
            variacao = row.get("variacao_abs", 0) or 0
            partes.append(f"Queda: R$ {abs(variacao):,.2f}")
        
        if "variacao_pct" in row:
            variacao_pct = row.get("variacao_pct", 0) or 0
            partes.append(f"Queda: {abs(variacao_pct):.1f}%")
        
        if "rota" in row:
            partes.append(f"Rota: {row['rota']}")
        elif "rota_id" in row:
            partes.append(f"Rota: {row['rota_id']}")
        
        if "equipe" in row:
            partes.append(f"Equipe: {row['equipe']}")
        
        if partes:
            top_alvos.append(" | ".join(partes))
    
    return {
        "resumo": resumo,
        "achados": achados,
        "implicacoes": implicacoes,
        "plano": plano,
        "top_alvos": top_alvos
    }


def _format_positivacao(dados, intent_spec, filtros, regras_behavior):
    """
    Formata narrativa para positivação de SKU/indústria.
    
    Campos esperados em 'dados':
    - Para rotas: rota_id, total_clientes_ativos, clientes_positivados, positivacao_pct
    - Para clientes: cliente_id, nome, rota_id
    """
    if not dados:
        return {
            "resumo": "Nenhum registro de positivação foi encontrado com base nos filtros aplicados.",
            "achados": [
                "A ausência de registros pode indicar que todos os clientes já foram positivados.",
                "Pode também indicar que os filtros (SKU, indústria, período) estão muito restritivos."
            ],
            "implicacoes": [
                "Situação positiva: cobertura completa do SKU/indústria.",
                "Recomenda-se validar se os filtros estão corretos."
            ],
            "plano": [
                "Validar filtros de SKU, indústria e período utilizados.",
                "Revisar atuação das equipes relacionadas ao tema.",
                "Criar rotina de monitoramento de positivação."
            ],
            "top_alvos": []
        }
    
    # Detecta se é análise por rota ou por cliente
    is_por_rota = dados and isinstance(dados[0], dict) and "rota_id" in dados[0] and "positivacao_pct" in dados[0]
    
    total_registros = len(dados)
    
    if is_por_rota:
        # Análise por rotas
        dados_ordenados = sorted(dados, key=lambda x: x.get("positivacao_pct", 0) or 0)
        piores_rotas = dados_ordenados[:5] if len(dados_ordenados) > 5 else dados_ordenados
        
        # Calcula métricas
        total_clientes_ativos = sum([d.get("total_clientes_ativos", 0) or 0 for d in dados])
        total_positivados = sum([d.get("clientes_positivados", 0) or 0 for d in dados])
        positivacao_media = (total_positivados * 100.0 / total_clientes_ativos) if total_clientes_ativos > 0 else 0.0
        
        industria = filtros.get("industria", "indústria")
        periodo = filtros.get("periodo", "período")
        
        # Detecta cenário crítico (baixa positivação)
        is_critico = positivacao_media < 50.0
        
        resumo = (
            f"Foram analisadas {total_registros} rotas quanto à positivação de {industria} no {periodo}. "
            f"A taxa média de positivação é de {positivacao_media:.1f}% ({total_positivados} clientes positivados de {total_clientes_ativos} ativos)."
        )
        if piores_rotas:
            pior_rota = piores_rotas[0]
            pct_pior = pior_rota.get("positivacao_pct", 0) or 0
            resumo += f" A rota {pior_rota.get('rota_id', 'N/A')} apresenta a menor taxa: {pct_pior:.1f}%."
        
        # Principais Achados (3-5 bullets concretos)
        achados = [
            f"As {min(5, total_registros)} rotas com menor taxa de positivação concentram a maior parte da oportunidade."
        ]
        if piores_rotas:
            pior_rota = piores_rotas[0]
            pct_pior = pior_rota.get("positivacao_pct", 0) or 0
            clientes_pior = pior_rota.get("total_clientes_ativos", 0) or 0
            positivados_pior = pior_rota.get("clientes_positivados", 0) or 0
            achados.append(f"Rota {pior_rota.get('rota_id', 'N/A')} tem apenas {pct_pior:.1f}% de positivação ({positivados_pior}/{clientes_pior} clientes).")
        if positivacao_media < 40:
            achados.append(f"Taxa média de {positivacao_media:.1f}% indica baixa penetração do produto, com risco de perda de espaço no PDV.")
        achados.append("Há concentração de clientes não positivados em rotas específicas, indicando necessidade de ações direcionadas.")
        if total_clientes_ativos - total_positivados > 100:
            nao_positivados = total_clientes_ativos - total_positivados
            achados.append(f"{nao_positivados} clientes ainda não foram positivados, representando oportunidade significativa de crescimento.")
        
        # Implicações Comerciais
        implicacoes = [
            f"Oportunidade de crescimento através de aumento de cobertura do SKU/indústria em {total_clientes_ativos - total_positivados} clientes não positivados."
        ]
        implicacoes.append("Risco de perda de espaço no PDV para concorrentes que oferecem o mesmo produto.")
        if positivacao_media < 50:
            implicacoes.append(f"Taxa de {positivacao_media:.1f}% está abaixo do ideal, indicando necessidade urgente de ações táticas.")
        implicacoes.append("Necessidade de ações imediatas de educação e convencimento para aumentar penetração.")
        
        # Plano de Ação Imediato
        plano = [
            f"Priorizar ações imediatas nas {min(5, len(piores_rotas))} rotas com menor taxa de positivação (abaixo de {positivacao_media:.0f}%)."
        ]
        if piores_rotas:
            rotas_criticas = [r.get("rota_id", "N/A") for r in piores_rotas[:3]]
            plano.append(f"Agendar blitz de vendas nas rotas {', '.join(rotas_criticas)} focada em positivação do produto.")
        plano.append(f"Criar rota de visita específica para {min(50, total_clientes_ativos - total_positivados)} clientes não positivados nas rotas críticas.")
        plano.append(f"Desenvolver argumento de venda focado no SKU/indústria {industria} para treinamento do time de vendas.")
        plano.append("Acompanhar evolução semanalmente até atingir meta de cobertura mínima de 60%.")
    else:
        # Análise por clientes (não positivados)
        industria = filtros.get("industria", "indústria")
        sku = filtros.get("sku", "SKU")
        periodo = filtros.get("periodo", "P12")
        
        resumo = (
            f"Foram identificados {total_registros} clientes que não tiveram positivação de {sku} ({industria}) no {periodo}."
        )
        
        # Tenta identificar rotas mais afetadas
        rotas_afetadas = {}
        for d in dados:
            if isinstance(d, dict) and d.get("rota_id"):
                rota = d.get("rota_id")
                rotas_afetadas[rota] = rotas_afetadas.get(rota, 0) + 1
        
        rotas_top = sorted(rotas_afetadas.items(), key=lambda x: x[1], reverse=True)[:3] if rotas_afetadas else []
        
        if rotas_top:
            rotas_str = ", ".join([f"rota {r[0]}" for r in rotas_top])
            resumo += f" As rotas mais afetadas são: {rotas_str}."
        
        achados = [
            f"Os {min(10, total_registros)} clientes mais estratégicos representam a maior oportunidade de crescimento.",
            "Há concentração de clientes não positivados em rotas específicas." if rotas_top else "Há distribuição de clientes não positivados em várias rotas.",
            "Alguns clientes podem não conhecer o produto ou ter resistência à mudança de mix."
        ]
        
        implicacoes = [
            "Oportunidade de incremento de ticket através de positivação do SKU.",
            "Risco de perda de espaço no PDV para concorrentes.",
            "Necessidade de ações de educação e convencimento."
        ]
        
        plano = [
            f"Criar rota de visita específica para os {min(20, total_registros)} clientes mais estratégicos não positivados.",
            "Desenvolver argumento de venda focado no SKU para apresentação aos clientes.",
            "Treinar time de vendas sobre benefícios e diferenciais do produto.",
            "Acompanhar taxa de conversão mensalmente."
        ]
    
    # Gera TOP 10 alvos prioritários
    top_alvos = []
    if is_por_rota:
        # Para análise por rotas, foca nas piores rotas
        for row in piores_rotas[:10]:
            partes = []
            
            if "rota_id" in row:
                partes.append(f"Rota {row['rota_id']}")
            
            if "positivacao_pct" in row:
                pct = row.get("positivacao_pct", 0) or 0
                partes.append(f"Positivação: {pct:.1f}%")
            
            if "clientes_positivados" in row and "total_clientes_ativos" in row:
                positivados = row.get("clientes_positivados", 0) or 0
                total = row.get("total_clientes_ativos", 0) or 0
                partes.append(f"{positivados}/{total} clientes")
            
            if partes:
                top_alvos.append(" | ".join(partes))
    else:
        # Para análise por clientes (não positivados)
        top_clientes = dados[:10] if len(dados) > 10 else dados
        for row in top_clientes:
            partes = []
            
            if "nome" in row:
                partes.append(row["nome"])
            elif "nome_cliente" in row:
                partes.append(row["nome_cliente"])
            elif "cliente_id" in row:
                partes.append(f"Cliente {row['cliente_id']}")
            
            if "rota_id" in row:
                partes.append(f"Rota: {row['rota_id']}")
            elif "rota" in row:
                partes.append(f"Rota: {row['rota']}")
            
            if "supervisor" in row:
                partes.append(f"Sup.: {row['supervisor']}")
            elif "supervisor_id" in row:
                partes.append(f"Sup.: {row['supervisor_id']}")
            
            if "sku" in row:
                partes.append(f"SKU: {row['sku']}")
            elif "descricao" in row:
                partes.append(f"Produto: {row['descricao']}")
            
            if partes:
                top_alvos.append(" | ".join(partes))
    
    return {
        "resumo": resumo,
        "achados": achados,
        "implicacoes": implicacoes,
        "plano": plano,
        "top_alvos": top_alvos
    }


def _format_vendas_baixas(dados, intent_spec, filtros, regras_behavior):
    """
    Formata narrativa para itens com baixa média de vendas mensal.
    
    Campos esperados em 'dados':
    - produto_id, descricao
    - media_mensal, total_vendido
    - meses_com_venda
    """
    if not dados:
        return {
            "resumo": "Nenhum item foi identificado com baixa média de vendas mensal no período analisado.",
            "achados": [
                "A ausência de itens com baixa média pode indicar boa rotação de portfólio.",
                "Pode também indicar que o limite de média está muito alto."
            ],
            "implicacoes": [
                "Situação positiva: portfólio com boa rotação.",
                "Recomenda-se revisar periodicamente para identificar itens em declínio."
            ],
            "plano": [
                "Validar se o limite de média mensal está adequado.",
                "Manter análise trimestral de rotação de itens.",
                "Criar alertas para itens com média abaixo de 10 caixas."
            ],
            "top_alvos": []
        }
    
    # Ordena por média mensal (crescente) se existir
    if dados and isinstance(dados[0], dict) and "media_mensal" in dados[0]:
        dados_ordenados = sorted(dados, key=lambda x: x.get("media_mensal", 0) or 0)
    else:
        dados_ordenados = dados
    
    # TOP 10 itens com menor média
    top_10 = dados_ordenados[:10] if len(dados_ordenados) > 10 else dados_ordenados
    
    # Calcula métricas
    total_itens = len(dados)
    limite_media = filtros.get("limite_media", 10.0)
    
    # Tenta calcular média geral
    media_list = [d.get("media_mensal") for d in dados if isinstance(d, dict) and d.get("media_mensal")]
    media_geral = sum(media_list) / len(media_list) if media_list else None
    
    # Detecta cenário crítico (muitos itens com baixa rotação)
    is_critico = total_itens > 20 or (media_geral and media_geral < 5.0)
    
    resumo = (
        f"Foram identificados {total_itens} itens com média de vendas mensal menor que {limite_media:.0f} caixas."
    )
    if media_geral:
        resumo += f" A média geral desses itens é de {media_geral:.2f} caixas/mês."
    if top_10:
        pior_item = top_10[0]
        media_pior = pior_item.get("media_mensal", 0) or 0
        resumo += f" O item com menor média vende apenas {media_pior:.2f} caixas/mês."
    
    # Principais Achados (3-5 bullets concretos)
    achados = [
        f"Os {min(10, total_itens)} itens com menor média concentram a maior parte do problema de rotação."
    ]
    if top_10:
        pior_item = top_10[0]
        media_pior = pior_item.get("media_mensal", 0) or 0
        desc_pior = pior_item.get("descricao", pior_item.get("sku", "N/A"))
        achados.append(f"Item '{desc_pior}' apresenta média de apenas {media_pior:.2f} caixas/mês, indicando risco de obsolescência.")
    if total_itens > 30:
        achados.append(f"Volume de {total_itens} itens com baixa rotação representa oportunidade significativa de limpeza de portfólio.")
    if media_geral and media_geral < 5.0:
        achados.append(f"Média geral de {media_geral:.2f} caixas/mês indica rotação muito baixa, com risco de perda de espaço no PDV.")
    achados.append("Há concentração de itens com baixa rotação em categorias ou indústrias específicas, indicando necessidade de revisão de mix.")
    
    # Implicações Comerciais
    implicacoes = [
        f"Risco de obsolescência e perda de espaço no PDV para {total_itens} itens com baixa rotação."
    ]
    implicacoes.append("Oportunidade de limpeza de portfólio e otimização de mix para focar em itens de maior rotatividade.")
    if total_itens > 20:
        implicacoes.append(f"Volume de {total_itens} itens requer decisão estratégica: acelerar vendas (push) ou remover do portfólio.")
    implicacoes.append("Necessidade de revisão imediata da política de sortimento e mix recomendado por cliente.")
    
    # Plano de Ação Imediato
    plano = [
        f"Priorizar análise estratégica dos {min(10, total_itens)} itens com menor média para decisão de continuidade ou remoção."
    ]
    plano.append("Avaliar se vale investir em ações de push (promoções, treinamento, merchandising) ou remover do portfólio.")
    plano.append("Revisar política de sortimento e mix recomendado por cliente para otimizar espaço no PDV.")
    plano.append("Criar plano de ação por item: itens com potencial recebem push, itens sem potencial são removidos.")
    plano.append("Monitorar evolução trimestralmente e tomar decisão de continuidade baseada em resultados.")
    
    # Gera TOP 10 alvos prioritários
    top_alvos = []
    for row in top_10:
        partes = []
        
        if "sku" in row:
            partes.append(f"SKU: {row['sku']}")
        elif "produto_id" in row:
            partes.append(f"Produto {row['produto_id']}")
        
        if "descricao" in row:
            partes.append(row["descricao"])
        elif "descricao_produto" in row:
            partes.append(row["descricao_produto"])
        
        if "media_mensal" in row:
            media = row.get("media_mensal", 0) or 0
            partes.append(f"Média: {media:.2f} caixas/mês")
        
        if "industria" in row:
            partes.append(f"Indústria: {row['industria']}")
        elif "marca" in row:
            partes.append(f"Marca: {row['marca']}")
        
        if partes:
            top_alvos.append(" | ".join(partes))
    
    return {
        "resumo": resumo,
        "achados": achados,
        "implicacoes": implicacoes,
        "plano": plano,
        "top_alvos": top_alvos
    }


def _format_mix(dados, intent_spec, filtros, regras_behavior):
    """
    Formata narrativa para análise de mix (Q5 - itens com média de vendas mensal < limite).
    
    Campos esperados em 'dados':
    - sku, descricao, produto_id
    - media_mensal, media_mensal_caixas
    - industria, categoria
    - total_vendido, meses_com_venda
    """
    if not dados:
        return {
            "resumo": "Nenhum item foi identificado com média de vendas mensal abaixo do limite no período analisado.",
            "achados": [
                "A ausência de itens críticos pode indicar boa rotação de portfólio.",
                "Pode também indicar que o limite de média está muito alto ou os filtros estão muito restritivos."
            ],
            "implicacoes": [
                "Situação positiva: portfólio com boa rotação e mix saudável.",
                "Recomenda-se manter monitoramento para identificar itens em declínio antecipadamente."
            ],
            "plano": [
                "Validar se o limite de média mensal está adequado.",
                "Manter análise trimestral de rotação de itens.",
                "Criar alertas para itens com média abaixo do limiar estabelecido."
            ],
            "top_alvos": []
        }
    
    # Ordena por média mensal (crescente) - piores primeiro
    if dados and isinstance(dados[0], dict) and "media_mensal" in dados[0]:
        dados_ordenados = sorted(dados, key=lambda x: x.get("media_mensal", 0) or 0)
    elif dados and isinstance(dados[0], dict) and "media_mensal_caixas" in dados[0]:
        dados_ordenados = sorted(dados, key=lambda x: x.get("media_mensal_caixas", 0) or 0)
    else:
        dados_ordenados = dados
    
    # TOP 10 itens mais críticos (menor média)
    top_10 = dados_ordenados[:10] if len(dados_ordenados) > 10 else dados_ordenados
    
    # Calcula métricas
    total_itens_criticos = len(dados)
    limite = filtros.get("limite", filtros.get("limite_media", 10.0))
    
    # Tenta calcular média geral dos itens críticos
    media_list = [d.get("media_mensal") for d in dados if isinstance(d, dict) and d.get("media_mensal")]
    if not media_list:
        media_list = [d.get("media_mensal_caixas") for d in dados if isinstance(d, dict) and d.get("media_mensal_caixas")]
    media_geral = sum(media_list) / len(media_list) if media_list else None
    
    # Tenta identificar indústrias/categorias mais impactadas
    industrias_afetadas = {}
    categorias_afetadas = {}
    for d in dados:
        if isinstance(d, dict):
            if d.get("industria"):
                industria = d.get("industria")
                industrias_afetadas[industria] = industrias_afetadas.get(industria, 0) + 1
            if d.get("categoria"):
                categoria = d.get("categoria")
                categorias_afetadas[categoria] = categorias_afetadas.get(categoria, 0) + 1
    
    industria_top = sorted(industrias_afetadas.items(), key=lambda x: x[1], reverse=True)[:1] if industrias_afetadas else []
    
    # Detecta cenário crítico
    is_critico = total_itens_criticos > 20 or (media_geral and media_geral < 5.0)
    
    # Constrói resumo executivo (2-3 frases, direto, com números)
    resumo_parts = [
        f"Foram identificados {total_itens_criticos} itens com média de vendas mensal abaixo de {limite:.0f} caixas."
    ]
    if media_geral:
        resumo_parts.append(f"A média geral desses itens é de {media_geral:.2f} caixas/mês.")
    if industria_top:
        resumo_parts.append(f"A indústria {industria_top[0][0]} concentra {industria_top[0][1]} itens críticos ({industria_top[0][1] * 100.0 / total_itens_criticos:.0f}% do total).")
    
    resumo = " ".join(resumo_parts)
    
    # Principais Achados (3-5 bullets concretos)
    achados = [
        f"Os {min(10, total_itens_criticos)} itens com menor média concentram a maior parte do problema de rotação."
    ]
    if top_10:
        pior_item = top_10[0]
        media_pior = pior_item.get("media_mensal", pior_item.get("media_mensal_caixas", 0)) or 0
        desc_pior = pior_item.get("descricao", pior_item.get("sku", "N/A"))
        achados.append(f"Item '{desc_pior}' apresenta média de apenas {media_pior:.2f} caixas/mês, indicando risco de obsolescência.")
    if industria_top:
        pct_industria = (industria_top[0][1] * 100.0 / total_itens_criticos) if total_itens_criticos > 0 else 0
        achados.append(f"Indústria {industria_top[0][0]} concentra {pct_industria:.0f}% dos itens críticos ({industria_top[0][1]} itens), indicando problema estrutural.")
    if total_itens_criticos > 30:
        achados.append(f"Volume de {total_itens_criticos} itens com baixa rotação representa oportunidade significativa de limpeza de portfólio.")
    if media_geral and media_geral < 5.0:
        achados.append(f"Média geral de {media_geral:.2f} caixas/mês indica rotação muito baixa, com risco de perda de espaço no PDV.")
    achados.append("Há concentração de itens com baixa rotação em categorias ou indústrias específicas, indicando necessidade de revisão de mix.")
    
    # Implicações Comerciais (risco de receita, estoque parado, etc.)
    implicacoes = [
        f"Risco de estoque parado e capital empatado em {total_itens_criticos} itens com baixa rotação."
    ]
    if media_geral and media_geral < 5.0:
        implicacoes.append(f"Média de {media_geral:.2f} caixas/mês indica risco de vencimento e obsolescência para produtos perecíveis.")
    implicacoes.append("Oportunidade de limpeza de portfólio e otimização de mix para focar em itens de maior rotatividade.")
    if total_itens_criticos > 20:
        implicacoes.append(f"Volume de {total_itens_criticos} itens requer decisão estratégica: acelerar vendas (push) ou remover do portfólio para liberar espaço no PDV.")
    implicacoes.append("Perda de oportunidade de margem em produtos estratégicos que poderiam ocupar o espaço desses itens parados.")
    
    # Plano de Ação Imediato (formato imperativo, acionável)
    plano = [
        f"Criar campanha de empurrão imediata para os {min(20, total_itens_criticos)} SKUs com menor média mensal."
    ]
    plano.append("Rever cadastro e mix por cliente para retirar itens que não fazem sentido no sortimento atual.")
    if industria_top:
        plano.append(f"Negociar ações de sell-out com a indústria {industria_top[0][0]} para os {industria_top[0][1]} itens críticos identificados.")
    plano.append("Criar plano de ação por item: itens com potencial recebem push (promoções, treinamento), itens sem potencial são removidos do portfólio.")
    plano.append("Monitorar evolução trimestralmente e tomar decisão de continuidade baseada em resultados de rotação.")
    
    # Gera TOP 10 alvos prioritários
    top_alvos = []
    for row in top_10:
        partes = []
        
        if "sku" in row:
            partes.append(f"SKU: {row['sku']}")
        elif "produto_id" in row:
            partes.append(f"Produto {row['produto_id']}")
        
        if "descricao" in row:
            partes.append(row["descricao"])
        elif "descricao_produto" in row:
            partes.append(row["descricao_produto"])
        
        media = row.get("media_mensal", row.get("media_mensal_caixas", 0)) or 0
        if media:
            partes.append(f"Média: {media:.2f} caixas/mês")
        
        if "industria" in row:
            partes.append(f"Indústria: {row['industria']}")
        elif "marca" in row:
            partes.append(f"Marca: {row['marca']}")
        
        if partes:
            top_alvos.append(" | ".join(partes))
    
    return {
        "resumo": resumo,
        "achados": achados,
        "implicacoes": implicacoes,
        "plano": plano,
        "top_alvos": top_alvos
    }


def _format_mix_nissin(dados, intent_spec, filtros, regras_behavior):
    """
    Formata narrativa para mix mínimo de Nissin.
    
    Campos esperados em 'dados':
    - cliente_id, nome
    - rota_id
    """
    if not dados:
        return {
            "resumo": "Nenhum cliente foi identificado com mix mínimo de Nissin no período analisado.",
            "achados": [
                "A ausência de clientes com mix mínimo pode indicar baixa adesão ao mix recomendado.",
                "Pode também indicar que os filtros aplicados estão muito restritivos."
            ],
            "implicacoes": [
                "Risco de não atingir metas de mix da indústria Nissin.",
                "Oportunidade de crescimento através de aumento de adesão ao mix mínimo."
            ],
            "plano": [
                "Validar se o período analisado está correto.",
                "Criar plano de incentivo para aumento de adesão ao mix mínimo.",
                "Alinhar metas de mix com vendedores e supervisores.",
                "Acompanhar evolução mensalmente."
            ],
            "top_alvos": []
        }
    
    # Tenta identificar rotas mais afetadas (clientes sem mix)
    # Se for análise de rotas, pode ter campos diferentes
    total_clientes = len(dados)
    
    # Tenta identificar rotas
    rotas_afetadas = {}
    for d in dados:
        if isinstance(d, dict) and d.get("rota_id"):
            rota = d.get("rota_id")
            rotas_afetadas[rota] = rotas_afetadas.get(rota, 0) + 1
    
    rotas_top = sorted(rotas_afetadas.items(), key=lambda x: x[1], reverse=True)[:3] if rotas_afetadas else []
    
    mes = filtros.get("mes", "período")
    ano = filtros.get("ano", "")
    
    # Detecta cenário (positivo se muitos clientes, negativo se poucos)
    is_positivo = total_clientes > 100
    
    resumo = (
        f"Foram identificados {total_clientes} clientes que compraram o mix mínimo de Nissin no {mes}."
    )
    if rotas_top:
        rotas_str = ", ".join([f"{r[0]}" for r in rotas_top])
        resumo += f" As rotas com maior adesão são: {rotas_str} ({rotas_top[0][1]} clientes cada)."
    
    # Principais Achados (3-5 bullets concretos)
    achados = [
        f"A adesão ao mix mínimo de Nissin está concentrada em {len(rotas_top) if rotas_top else 'várias'} rotas específicas." if rotas_top else "A adesão ao mix mínimo está distribuída em várias rotas."
    ]
    if rotas_top:
        pct_rota = (rotas_top[0][1] * 100.0 / total_clientes) if total_clientes > 0 else 0
        achados.append(f"Rota {rotas_top[0][0]} concentra {pct_rota:.0f}% dos clientes com mix mínimo ({rotas_top[0][1]} clientes).")
    if is_positivo:
        achados.append(f"Volume de {total_clientes} clientes com mix mínimo indica boa adesão ao mix recomendado pela indústria.")
    else:
        achados.append(f"Volume de apenas {total_clientes} clientes com mix mínimo indica necessidade de aumento de penetração.")
    achados.append("Há oportunidade de crescimento através de aumento de penetração do mix mínimo em clientes ainda não aderentes.")
    
    # Implicações Comerciais
    if is_positivo:
        implicacoes = [
            f"Boa adesão ao mix mínimo de Nissin em {total_clientes} clientes, fortalecendo relacionamento com a indústria."
        ]
        implicacoes.append("Oportunidade de replicar estratégia de sucesso em outras rotas e expandir adesão.")
    else:
        implicacoes = [
            f"Risco de não atingir metas de mix da indústria Nissin com apenas {total_clientes} clientes aderentes."
        ]
        implicacoes.append("Necessidade urgente de ações táticas para aumentar penetração do mix mínimo.")
    implicacoes.append("Impacto direto na relação comercial com a indústria Nissin e possibilidade de incentivos.")
    
    # Plano de Ação Imediato
    if is_positivo:
        plano = [
            f"Replicar estratégia de sucesso das rotas {', '.join([r[0] for r in rotas_top[:3]]) if rotas_top else 'com maior adesão'} para outras rotas."
        ]
        plano.append("Criar playbook de implementação do mix mínimo baseado nas melhores práticas identificadas.")
        plano.append("Alinhar metas de mix com vendedores e supervisores das rotas com menor adesão.")
    else:
        plano = [
            f"Criar plano de incentivo imediato para aumento de adesão ao mix mínimo de Nissin, focando em {min(50, total_clientes * 2)} clientes prioritários."
        ]
        if rotas_top:
            plano.append(f"Agendar blitz de vendas nas rotas {', '.join([r[0] for r in rotas_top[:3]])} focada em mix mínimo de Nissin.")
        plano.append("Alinhar metas de mix com vendedores e supervisores das rotas identificadas.")
    plano.append("Atuar em clusters de clientes com maior potencial de adesão ao mix mínimo.")
    plano.append("Acompanhar evolução mensalmente e ajustar estratégia conforme necessário para atingir meta de cobertura.")
    
    # Gera TOP 10 alvos prioritários
    top_alvos = []
    top_clientes = dados[:10] if len(dados) > 10 else dados
    for row in top_clientes:
        partes = []
        
        if "nome" in row:
            partes.append(row["nome"])
        elif "nome_cliente" in row:
            partes.append(row["nome_cliente"])
        elif "cliente_id" in row:
            partes.append(f"Cliente {row['cliente_id']}")
        
        if "rota_id" in row:
            partes.append(f"Rota: {row['rota_id']}")
        elif "rota" in row:
            partes.append(f"Rota: {row['rota']}")
        
        if "percentual_adesao" in row:
            pct = row.get("percentual_adesao", 0) or 0
            partes.append(f"Adesão: {pct:.1f}%")
        elif "flag_mix_minimo" in row:
            flag = row.get("flag_mix_minimo", False)
            partes.append("Mix mínimo: Sim" if flag else "Mix mínimo: Não")
        
        if partes:
            top_alvos.append(" | ".join(partes))
    
    return {
        "resumo": resumo,
        "achados": achados,
        "implicacoes": implicacoes,
        "plano": plano,
        "top_alvos": top_alvos
    }


def _format_meta_departamento(dados, intent_spec, filtros, regras_behavior):
    """
    Formata narrativa para análise de meta por departamento/indústria.
    
    Campos esperados em 'dados':
    - industria, departamento
    - total_vendedores, vendedores_fora_meta
    - percentual_fora_meta
    """
    if not dados:
        return {
            "resumo": "Nenhuma indústria foi identificada com vendedores fora da meta no período analisado.",
            "achados": [
                "A ausência de indústrias com problemas pode indicar bom desempenho geral.",
                "Pode também indicar que os filtros aplicados estão muito restritivos."
            ],
            "implicacoes": [
                "Situação positiva: equipes atingindo metas consistentemente.",
                "Recomenda-se manter monitoramento para identificar riscos antecipadamente."
            ],
            "plano": [
                "Validar se o período e filtros estão corretos.",
                "Manter análise mensal de desempenho por indústria.",
                "Criar alertas para indústrias com mais de 30% de vendedores fora da meta."
            ],
            "top_alvos": []
        }
    
    # Ordena por percentual de vendedores fora da meta (decrescente)
    if dados and isinstance(dados[0], dict) and "percentual_fora_meta" in dados[0]:
        dados_ordenados = sorted(dados, key=lambda x: x.get("percentual_fora_meta", 0) or 0, reverse=True)
    elif dados and isinstance(dados[0], dict) and "vendedores_fora_meta" in dados[0]:
        dados_ordenados = sorted(dados, key=lambda x: x.get("vendedores_fora_meta", 0) or 0, reverse=True)
    else:
        dados_ordenados = dados
    
    top_10 = dados_ordenados[:10] if len(dados_ordenados) > 10 else dados_ordenados
    
    # Calcula métricas
    total_industrias = len(dados)
    industria_critica = top_10[0] if top_10 else None
    
    # Constrói resumo executivo
    resumo_parts = [
        f"Foram analisadas {total_industrias} indústria(s) quanto ao desempenho de vendedores em relação à meta."
    ]
    if industria_critica:
        industria_nome = industria_critica.get("industria", industria_critica.get("departamento", "N/A"))
        vendedores_fora = industria_critica.get("vendedores_fora_meta", 0) or 0
        total_vendedores = industria_critica.get("total_vendedores", 0) or 0
        pct_fora = industria_critica.get("percentual_fora_meta", 0) or 0
        resumo_parts.append(f"A indústria {industria_nome} concentra {vendedores_fora} vendedores fora da meta ({pct_fora:.1f}% do total).")
    
    resumo = " ".join(resumo_parts)
    
    # Principais Achados
    achados = [
        f"A indústria {industria_critica.get('industria', 'N/A') if industria_critica else 'N/A'} concentra a maior parte dos vendedores fora da meta."
    ]
    if industria_critica:
        pct = industria_critica.get("percentual_fora_meta", 0) or 0
        if pct > 40:
            achados.append(f"{pct:.0f}% dos vendedores dessa indústria estão fora da meta, indicando problema estrutural.")
        vendedores_fora = industria_critica.get("vendedores_fora_meta", 0) or 0
        achados.append(f"{vendedores_fora} vendedores precisam de suporte imediato para recuperação.")
    achados.append("Há concentração de problemas em indústrias específicas, indicando necessidade de ações direcionadas.")
    
    # Implicações Comerciais
    implicacoes = [
        "Risco de não atingir meta total da empresa se indústrias críticas não forem recuperadas.",
        "Impacto direto no faturamento e na relação com indústrias parceiras.",
        "Necessidade de ações imediatas de coaching e suporte para vendedores em dificuldade."
    ]
    
    # Plano de Ação Imediato
    plano = [
        f"Priorizar ações de coaching e suporte para vendedores da indústria {industria_critica.get('industria', 'crítica') if industria_critica else 'crítica'} nos próximos 7 dias."
    ]
    plano.append("Agendar reuniões com supervisores das rotas mais afetadas para plano tático de recuperação.")
    plano.append("Criar ações conjuntas com a indústria para suporte aos vendedores em dificuldade.")
    plano.append("Monitorar evolução semanalmente até normalizar o desempenho.")
    
    # Gera TOP 10 alvos prioritários
    top_alvos = []
    for row in top_10:
        partes = []
        
        if "industria" in row:
            partes.append(f"Indústria: {row['industria']}")
        elif "departamento" in row:
            partes.append(f"Departamento: {row['departamento']}")
        
        if "vendedores_fora_meta" in row and "total_vendedores" in row:
            fora = row.get("vendedores_fora_meta", 0) or 0
            total = row.get("total_vendedores", 0) or 0
            partes.append(f"{fora}/{total} vendedores fora da meta")
        
        if "percentual_fora_meta" in row:
            pct = row.get("percentual_fora_meta", 0) or 0
            partes.append(f"{pct:.1f}% fora da meta")
        
        if partes:
            top_alvos.append(" | ".join(partes))
    
    return {
        "resumo": resumo,
        "achados": achados,
        "implicacoes": implicacoes,
        "plano": plano,
        "top_alvos": top_alvos
    }


def _format_recompra(dados, intent_spec, filtros, regras_behavior):
    """
    Formata narrativa para análise de recompra de SKU.
    
    Campos esperados em 'dados':
    - cliente_id, nome
    - sku, descricao
    - data_ultima_compra
    - dias_sem_recompra
    """
    if not dados:
        return {
            "resumo": "Nenhum cliente foi identificado sem recompra do SKU no período analisado.",
            "achados": [
                "A ausência de clientes sem recompra pode indicar boa rotatividade do SKU.",
                "Pode também indicar que os filtros aplicados estão muito restritivos."
            ],
            "implicacoes": [
                "Situação positiva: clientes mantendo ciclo de recompra do SKU.",
                "Recomenda-se manter monitoramento para identificar riscos antecipadamente."
            ],
            "plano": [
                "Validar se o período e SKU estão corretos.",
                "Manter análise mensal de taxa de recompra.",
                "Criar alertas para clientes sem recompra há mais de 6 meses."
            ],
            "top_alvos": []
        }
    
    # Ordena por dias_sem_recompra (decrescente)
    if dados and isinstance(dados[0], dict) and "dias_sem_recompra" in dados[0]:
        dados_ordenados = sorted(dados, key=lambda x: x.get("dias_sem_recompra", 0) or 0, reverse=True)
    else:
        dados_ordenados = dados
    
    top_10 = dados_ordenados[:10] if len(dados_ordenados) > 10 else dados_ordenados
    
    # Calcula métricas
    total_clientes = len(dados)
    sku = filtros.get("sku", "SKU")
    
    # Tenta calcular média de dias sem recompra
    dias_sem_recompra_list = [d.get("dias_sem_recompra") for d in dados if isinstance(d, dict) and d.get("dias_sem_recompra")]
    media_dias = sum(dias_sem_recompra_list) / len(dias_sem_recompra_list) if dias_sem_recompra_list else None
    
    # Tenta identificar rotas mais afetadas
    rotas_afetadas = {}
    for d in dados:
        if isinstance(d, dict) and d.get("rota_id"):
            rota = d.get("rota_id")
            rotas_afetadas[rota] = rotas_afetadas.get(rota, 0) + 1
    
    rotas_top = sorted(rotas_afetadas.items(), key=lambda x: x[1], reverse=True)[:3] if rotas_afetadas else []
    
    # Constrói resumo executivo
    resumo_parts = [
        f"Foram identificados {total_clientes} clientes que compraram {sku} mas não realizaram recompra."
    ]
    if media_dias:
        resumo_parts.append(f"A média de dias sem recompra é de {media_dias:.0f} dias.")
    if rotas_top:
        rotas_str = ", ".join([f"{r[0]}" for r in rotas_top])
        resumo_parts.append(f"As rotas mais afetadas são: {rotas_str} ({rotas_top[0][1]} clientes cada).")
    
    resumo = " ".join(resumo_parts)
    
    # Principais Achados
    achados = [
        f"Os {min(10, total_clientes)} clientes mais críticos concentram-se principalmente em rotas específicas."
    ]
    if rotas_top:
        pct_rota = (rotas_top[0][1] * 100.0 / total_clientes) if total_clientes > 0 else 0
        achados.append(f"Rota {rotas_top[0][0]} concentra {pct_rota:.0f}% dos clientes sem recompra ({rotas_top[0][1]} clientes).")
    if media_dias and media_dias > 180:
        achados.append(f"Média de {media_dias:.0f} dias sem recompra indica baixa fidelidade ao SKU, com risco de substituição.")
    if total_clientes > 100:
        achados.append(f"Volume de {total_clientes} clientes sem recompra representa oportunidade significativa de recuperação.")
    achados.append("Alguns clientes podem estar testando o produto ou migrando para alternativas.")
    
    # Implicações Comerciais
    implicacoes = [
        f"Risco de perda de espaço no PDV para o SKU {sku} em {total_clientes} clientes, impactando receita recorrente."
    ]
    implicacoes.append("Oportunidade de crescimento através de ações de recompra e fidelização.")
    implicacoes.append("Necessidade de ações imediatas para recuperar ciclo de compra do SKU.")
    if rotas_top:
        implicacoes.append(f"Rotas {', '.join([r[0] for r in rotas_top[:2]])} requerem atenção prioritária da supervisão.")
    
    # Plano de Ação Imediato
    plano = [
        f"Priorizar contato imediato com os {min(10, total_clientes)} clientes com maior tempo sem recompra do SKU {sku}."
    ]
    if rotas_top:
        plano.append(f"Agendar blitz de vendas nas rotas {', '.join([r[0] for r in rotas_top[:3]])} focada em recompra do SKU.")
    plano.append(f"Criar campanha específica de recompra para o SKU {sku} com condições especiais e argumentos de fidelização.")
    plano.append("Acionar supervisores das rotas mais afetadas para plano tático de recuperação em 7 dias.")
    plano.append("Monitorar taxa de recompra mensalmente até normalizar o ciclo de compra.")
    
    # Gera TOP 10 alvos prioritários
    top_alvos = []
    for row in top_10:
        partes = []
        
        if "nome" in row:
            partes.append(row["nome"])
        elif "nome_cliente" in row:
            partes.append(row["nome_cliente"])
        elif "cliente_id" in row:
            partes.append(f"Cliente {row['cliente_id']}")
        
        if "dias_sem_recompra" in row:
            dias = row.get("dias_sem_recompra", 0) or 0
            partes.append(f"{dias} dias sem recompra")
        
        if "rota_id" in row:
            partes.append(f"Rota: {row['rota_id']}")
        elif "rota" in row:
            partes.append(f"Rota: {row['rota']}")
        
        if "sku" in row:
            partes.append(f"SKU: {row['sku']}")
        
        if partes:
            top_alvos.append(" | ".join(partes))
    
    return {
        "resumo": resumo,
        "achados": achados,
        "implicacoes": implicacoes,
        "plano": plano,
        "top_alvos": top_alvos
    }


def _format_clientes_sem_item(dados, intent_spec, filtros, regras_behavior):
    """
    Formata narrativa para clientes sem compra de SKU/item específico.
    
    Campos esperados em 'dados':
    - cliente_id, nome
    - sku, descricao
    - rota_id
    """
    if not dados:
        return {
            "resumo": "Nenhum cliente foi identificado sem compra do item no período analisado.",
            "achados": [
                "A ausência de clientes sem o item pode indicar boa penetração do SKU.",
                "Pode também indicar que os filtros aplicados estão muito restritivos."
            ],
            "implicacoes": [
                "Situação positiva: boa cobertura do SKU na carteira.",
                "Recomenda-se manter monitoramento para identificar oportunidades de crescimento."
            ],
            "plano": [
                "Validar se o período e SKU estão corretos.",
                "Manter análise mensal de penetração de SKU.",
                "Criar alertas para clientes estratégicos sem o SKU."
            ],
            "top_alvos": []
        }
    
    top_10 = dados[:10] if len(dados) > 10 else dados
    
    # Calcula métricas
    total_clientes = len(dados)
    sku = filtros.get("sku", filtros.get("item", "SKU"))
    industria = filtros.get("industria", "")
    
    # Tenta identificar rotas mais afetadas
    rotas_afetadas = {}
    for d in dados:
        if isinstance(d, dict) and d.get("rota_id"):
            rota = d.get("rota_id")
            rotas_afetadas[rota] = rotas_afetadas.get(rota, 0) + 1
    
    rotas_top = sorted(rotas_afetadas.items(), key=lambda x: x[1], reverse=True)[:3] if rotas_afetadas else []
    
    # Constrói resumo executivo
    resumo_parts = [
        f"Foram identificados {total_clientes} clientes que não compraram {sku}"
    ]
    if industria:
        resumo_parts[0] += f" ({industria})"
    resumo_parts[0] += " no período analisado."
    if rotas_top:
        rotas_str = ", ".join([f"{r[0]}" for r in rotas_top])
        resumo_parts.append(f"As rotas mais afetadas são: {rotas_str} ({rotas_top[0][1]} clientes cada).")
    
    resumo = " ".join(resumo_parts)
    
    # Principais Achados
    achados = [
        f"Os {min(10, total_clientes)} clientes mais estratégicos representam a maior oportunidade de positivação."
    ]
    if rotas_top:
        pct_rota = (rotas_top[0][1] * 100.0 / total_clientes) if total_clientes > 0 else 0
        achados.append(f"Rota {rotas_top[0][0]} concentra {pct_rota:.0f}% dos clientes sem o SKU ({rotas_top[0][1]} clientes).")
    if total_clientes > 50:
        achados.append(f"Volume de {total_clientes} clientes sem o SKU representa oportunidade significativa de crescimento.")
    achados.append("Há concentração de clientes sem o SKU em rotas específicas, indicando necessidade de ações direcionadas.")
    
    # Implicações Comerciais
    implicacoes = [
        f"Oportunidade de incremento de ticket através de positivação do SKU {sku} em {total_clientes} clientes."
    ]
    implicacoes.append("Risco de perda de espaço no PDV para concorrentes que oferecem o mesmo produto.")
    implicacoes.append("Necessidade de ações imediatas de educação e convencimento para aumentar penetração.")
    if rotas_top:
        implicacoes.append(f"Rotas {', '.join([r[0] for r in rotas_top[:2]])} requerem atenção prioritária da supervisão.")
    
    # Plano de Ação Imediato
    plano = [
        f"Criar rota de visita específica para os {min(20, total_clientes)} clientes mais estratégicos sem o SKU {sku}."
    ]
    if rotas_top:
        plano.append(f"Agendar blitz de vendas nas rotas {', '.join([r[0] for r in rotas_top[:3]])} focada em positivação do SKU.")
    plano.append(f"Desenvolver argumento de venda focado no SKU {sku} para apresentação aos clientes e treinamento do time.")
    plano.append("Treinar time de vendas sobre benefícios e diferenciais do produto para aumentar taxa de conversão.")
    plano.append("Acompanhar taxa de positivação mensalmente até atingir meta de cobertura.")
    
    # Gera TOP 10 alvos prioritários
    top_alvos = []
    for row in top_10:
        partes = []
        
        if "nome" in row:
            partes.append(row["nome"])
        elif "nome_cliente" in row:
            partes.append(row["nome_cliente"])
        elif "cliente_id" in row:
            partes.append(f"Cliente {row['cliente_id']}")
        
        if "rota_id" in row:
            partes.append(f"Rota: {row['rota_id']}")
        elif "rota" in row:
            partes.append(f"Rota: {row['rota']}")
        
        if "sku" in row:
            partes.append(f"SKU: {row['sku']}")
        
        if partes:
            top_alvos.append(" | ".join(partes))
    
    return {
        "resumo": resumo,
        "achados": achados,
        "implicacoes": implicacoes,
        "plano": plano,
        "top_alvos": top_alvos
    }


def _format_generico(dados, intent_spec, filtros, regras_behavior):
    """
    Formata narrativa genérica para tipos de intent não específicos.
    """
    if not dados:
        return {
            "resumo": "Nenhum registro foi encontrado com base nos filtros aplicados.",
            "achados": [
                "A ausência de registros pode indicar baixa atuação comercial ou falta de reposição no período.",
                "SKU, rota ou equipe podem estar com baixa movimentação estrutural."
            ],
            "implicacoes": [
                "Existe risco de perda de espaço no PDV.",
                "Pode indicar necessidade de ação imediata da equipe comercial."
            ],
            "plano": [
                "Validar filtros e parâmetros utilizados.",
                "Iniciar follow-up com supervisores responsáveis.",
                "Criar rotina automática de monitoramento."
            ],
            "top_alvos": []
        }
    
    # Se houver dados → narrativa positiva genérica
    num_registros = len(dados) if isinstance(dados, list) else 1
    
    # Formata filtros para exibição
    filtros_str = ", ".join([f"{k}={v}" for k, v in filtros.items() if v is not None]) if filtros else "nenhum filtro específico"
    
    # Extrai tipo do intent_spec
    intent_tipo = None
    if hasattr(intent_spec, 'tipo'):
        intent_tipo = intent_spec.tipo
    elif isinstance(intent_spec, dict):
        intent_tipo = intent_spec.get("tipo", "outros")
    else:
        intent_tipo = "outros"
    
    # Gera TOP 10 alvos prioritários (genérico)
    top_alvos = []
    if isinstance(dados, list) and len(dados) > 0:
        top_dados = dados[:10] if len(dados) > 10 else dados
        for row in top_dados:
            if not isinstance(row, dict):
                continue
            
            fields = []
            # Campos mais importantes para exibição
            campos_importantes = ["cliente_id", "nome_cliente", "nome", "rota", "rota_id", 
                                 "industria", "sku", "vendedor", "supervisor", "produto_id"]
            
            for k in campos_importantes:
                if k in row and row[k] is not None:
                    v = row[k]
                    # Formata valores de forma legível
                    if isinstance(v, (int, float)) and k not in ["cliente_id", "produto_id"]:
                        fields.append(f"{k}: {v:.2f}" if isinstance(v, float) else f"{k}: {v}")
                    else:
                        fields.append(f"{k}: {v}")
            
            if fields:
                top_alvos.append(" | ".join(fields))
    
    return {
        "resumo": (
            f"Foram encontrados {num_registros} registros relevantes relacionados à intenção "
            f"'{intent_tipo}', considerando {filtros_str}."
        ),
        "achados": [
            "Os dados mostram padrões relevantes que exigem atenção da liderança.",
            "Identificou-se movimentação que pode representar oportunidades comerciais imediatas."
        ],
        "implicacoes": [
            "Possibilidade de recuperação ou aceleração das vendas.",
            "Ajustes táticos podem aumentar performance no curto prazo."
        ],
        "plano": [
            "Priorizar análises por rota/equipe conforme impacto.",
            "Acompanhar vendedores responsáveis pelos principais casos.",
            "Revisitar indicadores em 7 dias."
        ],
        "top_alvos": top_alvos
    }
