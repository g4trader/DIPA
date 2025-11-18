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
            "plano": List[str]
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
    elif intent_tipo == "positivacao":
        return _format_positivacao(dados, intent_spec, filtros, regras_behavior)
    elif intent_tipo == "vendas_baixas":
        return _format_vendas_baixas(dados, intent_spec, filtros, regras_behavior)
    elif intent_tipo == "mix_nissin":
        return _format_mix_nissin(dados, intent_spec, filtros, regras_behavior)
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
            ]
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
    
    # Constrói resumo
    resumo_parts = [
        f"Foram identificados {total_clientes} clientes ativos sem compras há mais de {dias_min} dias."
    ]
    if media_dias:
        resumo_parts.append(f"A média de dias sem compra é de {media_dias:.0f} dias.")
    if rotas_top:
        rotas_str = ", ".join([f"rota {r[0]}" for r in rotas_top])
        resumo_parts.append(f"As rotas mais afetadas são: {rotas_str}.")
    
    resumo = " ".join(resumo_parts)
    
    achados = [
        f"Os {min(10, total_clientes)} clientes mais críticos concentram-se principalmente em rotas específicas.",
        "Há concentração de dias sem compra acima da média em determinadas equipes ou supervisores." if media_dias else "Há concentração de clientes sem compra em determinadas rotas.",
        "Alguns clientes estratégicos podem estar sendo atendidos de forma reativa, e não proativa."
    ]
    
    implicacoes = [
        "Risco de perda definitiva desses clientes para concorrentes.",
        "Queda de share em regiões onde a Dipam já tinha presença consolidada.",
        "Necessidade de ações imediatas de reativação com foco em carteira fria."
    ]
    
    plano = [
        f"Priorizar contato com os {min(10, total_clientes)} clientes com maior tempo sem compra.",
        "Acionar supervisores das rotas mais afetadas para plano tático nos próximos 7 dias." if rotas_top else "Acionar supervisores das rotas identificadas para plano tático nos próximos 7 dias.",
        "Criar campanha específica de reativação com foco nos SKUs âncora da indústria.",
        "Monitorar semanalmente a evolução desses clientes até normalizar o ciclo de compras."
    ]
    
    return {
        "resumo": resumo,
        "achados": achados,
        "implicacoes": implicacoes,
        "plano": plano
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
            ]
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
    
    # Constrói resumo
    resumo_parts = [
        f"Foram identificados {total_clientes} clientes com queda de faturamento comparando {ano_comparado} vs {ano_base}."
    ]
    if queda_total:
        resumo_parts.append(f"A queda total acumulada é de R$ {abs(queda_total):,.2f}.")
    if media_queda_pct:
        resumo_parts.append(f"A média de queda percentual é de {media_queda_pct:.1f}%.")
    
    resumo = " ".join(resumo_parts)
    
    achados = [
        f"Os {min(10, total_clientes)} clientes com maior queda concentram a maior parte do impacto financeiro.",
        "Há concentração de quedas em clientes que antes eram considerados estratégicos." if total_clientes > 5 else "Os clientes identificados representam risco significativo.",
        "Alguns clientes podem estar migrando para concorrentes ou reduzindo mix de compras."
    ]
    
    implicacoes = [
        "Perda de share de mercado em clientes antes saudáveis.",
        "Risco de deterioração do relacionamento comercial com clientes estratégicos.",
        "Impacto direto no faturamento total da empresa."
    ]
    
    plano = [
        f"Agendar reuniões de recuperação com os {min(10, total_clientes)} clientes com maior queda.",
        "Revisar mix de produtos oferecidos e identificar oportunidades de cross-sell.",
        "Criar ações conjuntas com indústrias para recuperação desses clientes.",
        "Acompanhar evolução mensalmente até reverter a tendência."
    ]
    
    return {
        "resumo": resumo,
        "achados": achados,
        "implicacoes": implicacoes,
        "plano": plano
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
            ]
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
        
        resumo = (
            f"Foram analisadas {total_registros} rotas quanto à positivação de {industria} no {periodo}. "
            f"A taxa média de positivação é de {positivacao_media:.1f}% ({total_positivados} clientes positivados de {total_clientes_ativos} ativos)."
        )
        
        achados = [
            f"As {min(5, total_registros)} rotas com menor taxa de positivação concentram a maior parte da oportunidade.",
            "Há concentração de clientes não positivados em rotas específicas.",
            "Algumas rotas podem estar com dificuldade de argumentação ou acesso ao produto."
        ]
        
        implicacoes = [
            "Oportunidade de crescimento através de aumento de cobertura do SKU/indústria.",
            "Risco de perda de espaço no PDV para concorrentes que oferecem o mesmo produto.",
            "Necessidade de ações táticas para aumentar penetração."
        ]
        
        plano = [
            "Priorizar rotas com menor taxa de positivação para ações imediatas.",
            "Criar rota de visita específica para clientes não positivados nas rotas críticas.",
            "Desenvolver argumento de venda focado no SKU/indústria para treinamento do time.",
            "Acompanhar evolução semanalmente até atingir meta de cobertura."
        ]
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
    
    return {
        "resumo": resumo,
        "achados": achados,
        "implicacoes": implicacoes,
        "plano": plano
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
            ]
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
    
    resumo = (
        f"Foram identificados {total_itens} itens com média de vendas mensal menor que {limite_media:.0f} caixas."
    )
    if media_geral:
        resumo += f" A média geral desses itens é de {media_geral:.2f} caixas/mês."
    
    achados = [
        f"Os {min(10, total_itens)} itens com menor média concentram a maior parte do problema de rotação.",
        "Há concentração de itens com baixa rotação em categorias ou indústrias específicas." if total_itens > 5 else "Os itens identificados podem estar com erro de sortimento.",
        "Alguns itens podem estar em fase de declínio ou sendo substituídos por alternativas."
    ]
    
    implicacoes = [
        "Risco de obsolescência e perda de espaço no PDV.",
        "Oportunidade de limpeza de portfólio e otimização de mix.",
        "Necessidade de decisão: acelerar vendas (push) ou remover do portfólio."
    ]
    
    plano = [
        f"Priorizar análise dos {min(10, total_itens)} itens com menor média para decisão estratégica.",
        "Avaliar se vale investir em ações de push (promoções, treinamento) ou remover do portfólio.",
        "Revisar política de sortimento e mix recomendado por cliente.",
        "Monitorar evolução trimestralmente e tomar decisão de continuidade."
    ]
    
    return {
        "resumo": resumo,
        "achados": achados,
        "implicacoes": implicacoes,
        "plano": plano
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
            ]
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
    
    resumo = (
        f"Foram identificados {total_clientes} clientes que compraram o mix mínimo de Nissin no {mes}."
    )
    if rotas_top:
        rotas_str = ", ".join([f"rota {r[0]}" for r in rotas_top])
        resumo += f" As rotas com maior adesão são: {rotas_str}."
    
    achados = [
        f"A adesão ao mix mínimo de Nissin está concentrada em {len(rotas_top) if rotas_top else 'várias'} rotas específicas." if rotas_top else "A adesão ao mix mínimo está distribuída em várias rotas.",
        "Há oportunidade de crescimento através de aumento de penetração do mix mínimo.",
        "Algumas rotas podem estar com dificuldade de implementação do mix recomendado."
    ]
    
    implicacoes = [
        "Oportunidade de crescimento através de aumento de adesão ao mix mínimo.",
        "Risco de não atingir metas de mix da indústria Nissin se adesão não aumentar.",
        "Necessidade de ações táticas para aumentar penetração."
    ]
    
    plano = [
        "Criar plano de incentivo para aumento de adesão ao mix mínimo de Nissin.",
        "Alinhar metas de mix com vendedores e supervisores das rotas identificadas." if rotas_top else "Alinhar metas de mix com vendedores e supervisores.",
        "Atuar em clusters de clientes com maior potencial de adesão.",
        "Acompanhar evolução mensalmente e ajustar estratégia conforme necessário."
    ]
    
    return {
        "resumo": resumo,
        "achados": achados,
        "implicacoes": implicacoes,
        "plano": plano
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
            ]
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
        ]
    }
