"""
Integração com LLM (Large Language Model).

Este módulo contém funções para interagir com modelos de linguagem,
formatando prompts e processando respostas usando a API da OpenAI.

Otimizado para limitar custos e tamanho de contexto.
"""

import logging
from typing import Dict, Any, List, Tuple, Optional
import json

from src.llm_openai_client import call_llm as call_openai_llm, OpenAIError

logger = logging.getLogger(__name__)

# Limites para truncar listas grandes no contexto (evitar custos desnecessários)
MAX_VENDEDORES_CONTEXT = 20
MAX_PRODUTOS_CONTEXT = 50
MAX_CLIENTES_CONTEXT = 30
MAX_DEPARTAMENTOS_CONTEXT = 15
MAX_ITEMS_GENERIC = 25  # Para outras listas genéricas


def _truncar_lista_contexto(
    contexto: Dict[str, Any],
    chave: str,
    limite: int,
    manter_top: bool = True
) -> int:
    """
    Trunca uma lista no contexto se exceder o limite especificado.
    
    Args:
        contexto: Dicionário de contexto (modificado in-place)
        chave: Chave da lista a truncar
        limite: Número máximo de itens a manter
        manter_top: Se True, mantém os primeiros N itens. Se False, mantém os últimos N.
        
    Returns:
        int: Número de itens removidos (0 se não houver truncamento)
    """
    if chave not in contexto:
        return 0
    
    lista = contexto[chave]
    if not isinstance(lista, list):
        return 0
    
    tamanho_original = len(lista)
    if tamanho_original <= limite:
        return 0
    
    # Trunca a lista
    if manter_top:
        contexto[chave] = lista[:limite]
    else:
        contexto[chave] = lista[-limite:]
    
    itens_removidos = tamanho_original - limite
    
    # Adiciona informação sobre truncamento
    if "_truncamento_info" not in contexto:
        contexto["_truncamento_info"] = {}
    
    contexto["_truncamento_info"][chave] = {
        "total_original": tamanho_original,
        "mantidos": limite,
        "removidos": itens_removidos
    }
    
    logger.info(f"Lista '{chave}' truncada: {tamanho_original} -> {limite} itens ({itens_removidos} removidos)")
    
    return itens_removidos


def _otimizar_contexto(contexto: Dict[str, Any]) -> Dict[str, Any]:
    """
    Otimiza contexto truncando listas grandes para limitar tamanho e custos.
    
    Args:
        contexto: Contexto original (não modificado)
        
    Returns:
        dict: Contexto otimizado com listas truncadas
    """
    # Cria cópia para não modificar o original
    contexto_otimizado = json.loads(json.dumps(contexto))
    
    # Trunca listas conhecidas baseado em padrões de chave
    itens_truncados = []
    
    # Vendedores
    for chave in ["vendedores", "top_vendedores", "demais_vendedores", "vendedores_que_bateram", 
                  "vendedores_baixo_desempenho", "vendedores_detalhados"]:
        removidos = _truncar_lista_contexto(contexto_otimizado, chave, MAX_VENDEDORES_CONTEXT, manter_top=True)
        if removidos > 0:
            itens_truncados.append((chave, removidos))
    
    # Produtos
    for chave in ["produtos", "top_produtos", "produtos_vendidos"]:
        removidos = _truncar_lista_contexto(contexto_otimizado, chave, MAX_PRODUTOS_CONTEXT, manter_top=True)
        if removidos > 0:
            itens_truncados.append((chave, removidos))
    
    # Clientes
    for chave in ["clientes", "clientes_risco", "clientes_churn"]:
        removidos = _truncar_lista_contexto(contexto_otimizado, chave, MAX_CLIENTES_CONTEXT, manter_top=True)
        if removidos > 0:
            itens_truncados.append((chave, removidos))
    
    # Departamentos
    for chave in ["departamentos", "supervisores"]:
        removidos = _truncar_lista_contexto(contexto_otimizado, chave, MAX_DEPARTAMENTOS_CONTEXT, manter_top=True)
        if removidos > 0:
            itens_truncados.append((chave, removidos))
    
    # Trunca outras listas genéricas (detecta listas longas)
    for chave, valor in list(contexto_otimizado.items()):
        if isinstance(valor, list) and len(valor) > MAX_ITEMS_GENERIC:
            # Ignora se já foi truncado acima
            if chave not in [item[0] for item in itens_truncados]:
                removidos = _truncar_lista_contexto(contexto_otimizado, chave, MAX_ITEMS_GENERIC, manter_top=True)
                if removidos > 0:
                    itens_truncados.append((chave, removidos))
    
    # Adiciona resumo de truncamento se houver
    if itens_truncados and "_truncamento_info" in contexto_otimizado:
        total_removidos = sum(removidos for _, removidos in itens_truncados)
        contexto_otimizado["_resumo_truncamento"] = (
            f"Foram omitidos {total_removidos} itens menos relevantes para manter o contexto compacto. "
            f"Listas truncadas: {', '.join(f'{chave} ({removidos} itens)' for chave, removidos in itens_truncados)}."
        )
    
    # Remove informações de truncamento detalhadas (não precisa no prompt final, apenas o resumo)
    contexto_otimizado.pop("_truncamento_info", None)
    
    return contexto_otimizado


def _montar_prompt_metas_resumo(
    contexto: Dict[str, Any],
    pergunta: str,
    papel: Optional[str] = None
) -> Tuple[str, str]:
    """
    Monta prompt específico para contexto de resumo de metas dos últimos meses.
    
    Usa estrutura Markdown fixa como as outras intents analíticas.
    
    Args:
        contexto: Contexto com tipo "metas_resumo_ultimos_meses"
        pergunta: Pergunta do usuário
        papel: Papel do usuário (diretor, supervisor, vendedor)
        
    Returns:
        tuple: (system_prompt, prompt)
    """
    # Usa o system prompt padrão com estrutura Markdown fixa
    system_prompt = _get_system_prompt_dipam_copilot(papel)
    
    data_base = contexto.get("data_base", "N/A")
    n_meses_solicitados = contexto.get("n_meses_solicitados", contexto.get("n_meses", "N/A"))
    n_meses_disponiveis = contexto.get("n_meses_disponiveis", len(contexto.get("meses", [])))
    meses = contexto.get("meses", [])
    observacao = contexto.get("observacao", "")
    
    # Formata meses para o prompt (mantém números brutos para precisão)
    meses_formatados = []
    for mes_data in meses:
        mes_ano = mes_data.get("mes_ano", "N/A")
        valor_meta = mes_data.get("valor_meta", 0.0)
        valor_faturado = mes_data.get("valor_faturado", 0.0)
        perc_atingido = mes_data.get("percentual_atingido_valor", 0.0)
        
        meses_formatados.append({
            "mes_ano": mes_ano,
            "valor_meta": valor_meta,
            "valor_faturado": valor_faturado,
            "percentual_atingido_valor": perc_atingido
        })
    
    contexto_formatado = {
        "tipo": "metas_resumo_ultimos_meses",
        "data_base": data_base,
        "n_meses_solicitados": n_meses_solicitados,
        "n_meses_disponiveis": n_meses_disponiveis,
        "meses": meses_formatados
    }
    
    if observacao:
        contexto_formatado["observacao"] = observacao
    
    contexto_str = json.dumps(contexto_formatado, ensure_ascii=False, indent=2)
    
    prompt = f"""Você receberá dados de metas e realizados dos últimos meses em formato JSON.
Use APENAS esses dados para responder.

Dados e análises fornecidos:
{contexto_str}

Pergunta do usuário: {pergunta}

INSTRUÇÕES ESPECÍFICAS PARA ANÁLISE DE METAS:
1. Responda SEMPRE usando a estrutura Markdown obrigatória definida nas instruções do sistema.
2. Na seção "Números-chave", liste cada mês na lista acima usando este formato:
   - [Mês/Ano]: Meta R$ [valor] | Realizado R$ [valor] | Atingimento [percentual]%
   Exemplo: - Agosto 2025: Meta R$ 1.280.000,00 | Realizado R$ 1.050.000,00 | Atingimento 82,0%
3. Use APENAS os meses que estão na lista acima. NÃO invente ou mencione meses que não estão na lista.
4. Use os números exatos do contexto, formatando com ponto para milhar e vírgula para decimal.
5. Se houver apenas {n_meses_disponiveis} mês(es) disponível(is), mencione isso na seção "Observações sobre os dados".
6. Analise a evolução mês a mês e identifique tendências (melhora, queda, estabilidade) nos "Insights relevantes".
7. Seja específico nas "Ações recomendadas": cite meses, valores, percentuais que estão nos dados.

Responda agora seguindo a estrutura Markdown obrigatória:"""
    
    return system_prompt, prompt


def _get_system_prompt_dipam_copilot(papel: Optional[str] = None) -> str:
    """
    Retorna o prompt de sistema padrão para o DIPAM COPILOT™.
    
    Persona e regras fundamentais do agente comercial com estrutura Markdown fixa.
    
    Args:
        papel: Papel do usuário (diretor, supervisor, vendedor) para adaptar tom
        
    Returns:
        str: System prompt completo
    """
    # Determina tratamento baseado no papel
    tratamento = "Diretor"
    enfoque = "visão estratégica e números consolidados"
    if papel:
        papel_lower = papel.lower()
        if "supervisor" in papel_lower:
            tratamento = "Supervisor"
            enfoque = "equipe e performance por vendedor/rota"
        elif "vendedor" in papel_lower or "rca" in papel_lower:
            tratamento = "Vendedor"
            enfoque = "resultados pessoais e clientes"
    
    base_prompt = f"""Você é o DIPAM COPILOT™, um assistente de inteligência comercial avançado da DIPAM,
voltado para diretores, supervisores e vendedores.

PERSONA:
- Fala sempre em português brasileiro
- Tom consultivo, claro e direto
- Profissional mas acessível
- Focado em insights acionáveis

REGRAS FUNDAMENTAIS - ZERO INVENÇÃO DE DADOS:
1. Use APENAS os dados numéricos e análises fornecidas no contexto JSON.
2. NUNCA invente valores, períodos, produtos, quantidades, vendedores, supervisores ou clientes.
3. Se um dado não estiver presente no contexto, NÃO cite. Use apenas o que foi fornecido.
4. Se determinado mês/produto/supervisor não estiver no contexto, NÃO mencione.
5. Use formatação brasileira para números: R$ 1.000,00 (ponto para milhar, vírgula para decimal) e 85,5% (vírgula para decimal).
6. Seja preciso: use os números exatos do contexto, sem arredondar além do necessário.

ESTRUTURA OBRIGATÓRIA EM MARKDOWN (SEMPRE SEGUIR):

Responda SEMPRE usando esta estrutura exata em Markdown:

## Resumo executivo

[Um parágrafo curto (2-4 linhas) falando com o {tratamento.lower()}, explicando o que está acontecendo de forma geral baseado nos dados. Use os números do contexto para fundamentar.]

## Números-chave

[Use bullets (-) ou linhas curtas listando os principais números por mês/produto/supervisor/cliente, conforme o tipo de análise. CITE APENAS o que está no contexto.]

Exemplos de formato:
- Agosto 2025: Meta R$ 1.280.000,00 | Realizado R$ 1.050.000,00 | Atingimento 82,0%
- Supervisor João: Meta R$ 500.000,00 | Realizado R$ 420.000,00 | Atingimento 84,0%

## Insights relevantes

[3 a 5 bullets explicando o que os números mostram. Use verbos como: "houve melhora", "observa-se queda", "há concentração", "existe risco", etc.]

- [Insight baseado nos dados do contexto]
- [Insight baseado nos dados do contexto]
- [Insight baseado nos dados do contexto]

## Ações recomendadas

[3 bullets extremamente práticas e específicas. Seja concreto: cite nomes, rotas, departamentos, produtos que estão no contexto.]

- [Ação 1: específica e acionável, citando dados do contexto]
- [Ação 2: específica e acionável, citando dados do contexto]
- [Ação 3: específica e acionável, citando dados do contexto]

## Observações sobre os dados

[OPCIONAL - Inclua apenas se:
- Faltarem dados (período incompleto, poucos meses, etc.)
- O período solicitado for maior que o disponível
- Houver limitações nos dados fornecidos
Se os dados estiverem completos, OMITA esta seção.]

[Explicação clara das limitações, mencionando o que está disponível e o que não está.]

REGRAS IMPORTANTES:
- Se o contexto indicar "tem_dados_suficientes": false ou houver "mensagem_dados_insuficientes", seja explícito sobre a limitação na seção "Observações sobre os dados".
- Se a lista de meses/produtos/clientes for curta (ex.: só 2 meses), explique isso claramente.
- Nunca responda com "não tenho dados" se o contexto tiver números - use pelo menos o que tiver.
- Se houver truncamento de listas (indicado no contexto), mencione naturalmente nas observações.
- Mantenha cada seção concisa e objetiva.
- Use Markdown corretamente: ## para títulos, - para bullets.

FOCO PARA {tratamento.upper()}:
- {enfoque.title()}
- Priorize insights de alto nível e tendências (diretor) / comparações e gaps de gestão (supervisor) / oportunidades de vendas (vendedor)
- Sugira ações de gestão e acompanhamento (diretor) / acompanhamento de equipe (supervisor) / ações práticas de campo (vendedor)"""

    return base_prompt


def gerar_resposta_analytics(
    intent: str,
    insight_bundle: Dict[str, Any],
    pergunta: str,
    papel: Optional[str] = None
) -> str:
    """
    Gera resposta consultiva para análises estruturadas (analytics).
    
    Função principal para gerar respostas do DIPAM COPILOT™ usando
    o sistema de insights estruturados.
    
    Args:
        intent: Intent detectada (ex.: "consulta_meta", "clientes_churn_produto")
        insight_bundle: Bundle de insights com dados_brutos, scores_ml, pontos_chave
        pergunta: Pergunta original do usuário
        papel: Papel do usuário (diretor, supervisor, vendedor)
        
    Returns:
        str: Resposta em português brasileiro
    """
    # Verifica se há dados suficientes
    tem_dados = insight_bundle.get("tem_dados_suficientes", True)
    mensagem_insuficiente = insight_bundle.get("mensagem_dados_insuficientes")
    
    if not tem_dados:
        # Retorna resposta direta se não houver dados
        if mensagem_insuficiente:
            return mensagem_insuficiente
        else:
            return (
                "Não há dados cadastrados suficientes para responder essa pergunta. "
                "Verifique se há vendas e metas cadastradas no período/produto/região solicitados."
            )
    
    # Otimiza contexto antes de enviar
    contexto_otimizado = _otimizar_contexto(insight_bundle.get("dados_brutos", {}))
    
    # Adiciona pontos-chave e scores ML ao contexto
    contexto_completo = {
        "intent": intent,
        "dados": contexto_otimizado,
        "pontos_chave": insight_bundle.get("pontos_chave", []),
        "scores_ml": insight_bundle.get("scores_ml", {}),
        "data_base": insight_bundle.get("data_base"),
        "periodo_analisado": insight_bundle.get("periodo_analisado")
    }
    
    # Intents analíticas que devem seguir estrutura Markdown fixa
    intents_analytics = [
        "consulta_meta",
        "clientes_churn_produto",
        "clientes_oportunidades",
        "desempenho_supervisores",
        "oportunidades_diretoria",
        "clientes_risco_churn",
        "produtos_baixa_venda",
        "consulta_vendedores_performance"
    ]
    
    # Verifica se é intent analítica que precisa de estrutura Markdown fixa
    usar_estrutura_fixa = intent in intents_analytics
    
    # Prompt específico para metas (atualizado para Markdown)
    if intent == "consulta_meta" and contexto_completo["dados"].get("tipo") == "metas_resumo_ultimos_meses":
        system_prompt, prompt = _montar_prompt_metas_resumo(contexto_completo["dados"], pergunta, papel)
    elif usar_estrutura_fixa:
        # Prompt com estrutura Markdown fixa para intents analíticas
        system_prompt = _get_system_prompt_dipam_copilot(papel)
        
        contexto_str = json.dumps(contexto_completo, ensure_ascii=False, indent=2)
        
        prompt = f"""Você receberá dados e análises em formato JSON. Use APENAS esses dados para responder.

Dados e análises fornecidos:
{contexto_str}

Pergunta do usuário: {pergunta}

INSTRUÇÕES IMPORTANTES:
1. Responda SEMPRE usando a estrutura Markdown obrigatória definida nas instruções do sistema.
2. Use APENAS os dados que estão no JSON acima.
3. Se um mês/produto/supervisor/cliente não estiver na lista acima, NÃO mencione.
4. Se houver poucos dados (ex.: só 2 meses), mencione isso na seção "Observações sobre os dados".
5. Seja específico nas ações recomendadas: cite nomes, valores, períodos que estão nos dados.
6. Use formatação brasileira: R$ 1.000,00 e 85,5%.

Responda agora seguindo a estrutura Markdown obrigatória:"""
    else:
        # Prompt genérico para outras intents (mantém compatibilidade)
        system_prompt = _get_system_prompt_dipam_copilot(papel)
        
        contexto_str = json.dumps(contexto_completo, ensure_ascii=False, indent=2)
        
        prompt = f"""Dados e análises:
{contexto_str}

Pergunta: {pergunta}

Resposta:"""
    
    try:
        resposta = call_openai_llm(prompt, system_prompt=system_prompt)
        return resposta
    except Exception as e:
        logger.error(f"Erro ao gerar resposta LLM: {str(e)}")
        # Fallback: retorna resposta simples baseada nos pontos-chave
        pontos = insight_bundle.get("pontos_chave", [])
        if pontos:
            resposta_fallback = "\n".join(f"- {ponto}" for ponto in pontos[:5])
            return f"Com base nos dados disponíveis:\n{resposta_fallback}"
        else:
            return "Não foi possível gerar uma resposta consultiva. Os dados numéricos estão disponíveis, mas houve um erro ao processar a resposta textual."


def gerar_resposta_llm(contexto: Dict[str, Any], pergunta: str) -> str:
    """
    Gera resposta do LLM baseada em contexto estruturado e pergunta.
    
    DEPRECATED: Use gerar_resposta_analytics() para análises estruturadas.
    Mantido para compatibilidade com código legado.
    
    Args:
        contexto: Dicionário com dados estruturados (ex.: resultados de queries, métricas)
        pergunta: Pergunta do usuário em linguagem natural
        
    Returns:
        str: Resposta do LLM em linguagem natural
        
    Raises:
        OpenAIError: Se houver erro na chamada à API
        
    Example:
        contexto = {
            "vendedor": "ROTA 77",
            "mes_ano": "2024-12",
            "meta_valor": 100000,
            "realizado_valor": 85000,
            "perc_atingido": 85.0
        }
        pergunta = "Por que o vendedor ROTA 77 não bateu a meta em dezembro?"
        resposta = gerar_resposta_llm(contexto, pergunta)
    """
    logger.info(f"Gerando resposta LLM para pergunta: {pergunta[:100]}...")
    
    # Verifica se é contexto de resumo de metas dos últimos meses
    tipo_contexto = contexto.get("tipo")
    if tipo_contexto == "metas_resumo_ultimos_meses":
        logger.info("Usando prompt especializado para metas_resumo_ultimos_meses")
        system_prompt, prompt = _montar_prompt_metas_resumo(contexto, pergunta)
    else:
        # Otimiza contexto antes de serializar (trunca listas grandes)
        contexto_otimizado = _otimizar_contexto(contexto)
        
        # Monta system prompt compacto e direto
        system_prompt = (
            "Você é um assistente comercial da Dipam. "
            "Use APENAS os dados fornecidos no contexto. "
            "NÃO invente ou assuma dados que não existem. "
            "Se informação não existir, diga claramente. "
            "Seja objetivo, conciso e baseado em fatos numéricos."
        )
        
        # Serializa contexto de forma compacta (sem indentação excessiva)
        contexto_str = json.dumps(contexto_otimizado, ensure_ascii=False, indent=1)
        
        # Monta prompt compacto
        prompt = f"""Dados: {contexto_str}

Pergunta: {pergunta}

Resposta:"""
    
    try:
        # Chama LLM
        resposta = call_openai_llm(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=1500
        )
        
        logger.info(f"Resposta LLM gerada ({len(resposta)} caracteres)")
        return resposta
        
    except OpenAIError as e:
        logger.error(f"Erro ao chamar OpenAI API: {str(e)}")
        # Retorna resposta fallback em caso de erro
        return (
            f"Desculpe, não foi possível processar sua pergunta no momento devido a um erro na API. "
            f"Erro: {str(e)}\n\n"
            f"Com base nos dados disponíveis, aqui está um resumo básico:\n"
            f"{json.dumps(contexto, ensure_ascii=False, indent=2)}"
        )


# Função legada para compatibilidade (mantida para não quebrar código existente)
def call_llm(
    contexto: Dict[str, Any],
    pergunta: str,
    temperatura: float = 0.7,
    max_tokens: int = 1000
) -> str:
    """
    Função legada para compatibilidade com código existente.
    
    Esta função chama `gerar_resposta_llm` internamente.
    Prefira usar `gerar_resposta_llm` diretamente em novo código.
    
    Args:
        contexto: Dicionário com dados estruturados
        pergunta: Pergunta do usuário
        temperatura: Temperatura para geração (0.0-1.0) - ignorado, mantido para compatibilidade
        max_tokens: Número máximo de tokens na resposta - ignorado, mantido para compatibilidade
        
    Returns:
        str: Resposta do LLM em linguagem natural
    """
    logger.warning(
        "call_llm() está deprecado. Use gerar_resposta_llm() diretamente. "
        "A função será removida em versões futuras."
    )
    
    try:
        return gerar_resposta_llm(contexto, pergunta)
    except Exception as e:
        logger.error(f"Erro ao gerar resposta LLM: {str(e)}")
        # Fallback para resposta básica em caso de erro
        return f"Erro ao processar pergunta: {str(e)}"


def gerar_resposta_consulta_meta(pergunta: str, contexto: Dict[str, Any]) -> Tuple[str, float]:
    """
    Gera uma resposta em linguagem natural para consultas de meta,
    usando APENAS os dados presentes em contexto.
    
    Args:
        pergunta: Pergunta do usuário em linguagem natural
        contexto: Dicionário com dados estruturados de metas:
            - serie_mensal: Lista de dicts com mes_ano, meta, realizado, atingimento
            - detalhe_vendedores_mes: Dict com mes_ano e lista de vendedores
            - tem_serie_mensal: bool
            - tem_detalhe_vendedores: bool
            - meses_disponiveis: Lista de meses disponíveis
            - observacao: str (opcional)
            
    Returns:
        Tuple[str, float]: (resposta_texto, confianca)
            - resposta_texto: Resposta em linguagem natural
            - confianca: Nível de confiança (0.0-1.0) baseado na completude dos dados
    """
    logger.info(f"Gerando resposta especializada para consulta de meta: {pergunta[:100]}...")
    
    serie = contexto.get("serie_mensal", [])
    detalhe = contexto.get("detalhe_vendedores_mes", {}) or contexto.get("detalhe_vendedores", {})
    tem_serie = contexto.get("tem_serie_mensal", False)
    tem_detalhe = contexto.get("tem_detalhe_vendedores", False)
    meses_disponiveis = contexto.get("meses_disponiveis", [])
    observacao = contexto.get("observacao")
    
    # Calcula confiança baseada na completude dos dados
    confianca = 0.5  # Base
    if tem_serie and len(serie) > 0:
        confianca += 0.2
    if tem_detalhe and detalhe.get("vendedores"):
        confianca += 0.2
    if len(serie) >= 3:  # Série robusta
        confianca += 0.1
    confianca = min(confianca, 0.9)  # Cap em 0.9 (conforme solicitado)
    
    # Monta system message
    system_msg = (
        "Você é um analista de inteligência comercial sênior da Dipam.\n"
        "Use SOMENTE os dados fornecidos abaixo para responder.\n"
        "Se algum mês ou vendedor não estiver na lista, não invente números.\n"
        "Explique claramente quando os dados estiverem incompletos.\n"
        "Seja objetivo, preciso e baseado apenas nos fatos numéricos fornecidos.\n"
    )
    
    # Prepara dados para formatação JSON
    serie_para_json = serie if isinstance(serie, list) else []
    detalhe_para_json = detalhe if isinstance(detalhe, dict) else {}
    
    # Monta user message com estrutura específica
    user_msg = f"""Pergunta do usuário:

{pergunta}



Dados agregados por mês (serie_mensal):

{json.dumps(serie_para_json, ensure_ascii=False, indent=2)}



Detalhe por vendedor para um mês específico (se disponível):

{json.dumps(detalhe_para_json, ensure_ascii=False, indent=2)}



Monte a resposta em português, com a seguinte estrutura em Markdown:



## Resumo executivo



Texto curto explicando como está a foto geral de metas x realizado.



## Números-chave



Liste cada mês disponível com: mês_ano, meta, realizado e atingimento (%).



## Insights relevantes



Liste 3 a 5 bullets com leitura de tendência (melhora, queda, mês crítico, etc.).



## Ações recomendadas



Liste 3 ações práticas para o diretor/supervisor baseado nesses dados.



## Observações sobre os dados



Explique apenas se faltarem meses, se não houver detalhe por vendedor ou se a série for curta.



NUNCA diga que "não há dados" se a lista serie_mensal tiver algum elemento.

Se não houver nenhum dado em serie_mensal, explique isso claramente,

mas ainda assim não invente números.

"""
    
    try:
        # Chama LLM com temperatura mais baixa para respostas mais precisas
        resposta = call_openai_llm(
            prompt=user_msg,
            system_prompt=system_msg,
            temperature=0.3,  # Mais conservador para não inventar dados
            max_tokens=2000
        )
        
        logger.info(f"Resposta especializada para consulta de meta gerada ({len(resposta)} caracteres, confiança: {confianca:.2f})")
        return resposta, confianca
        
    except OpenAIError as e:
        logger.error(f"Erro ao chamar OpenAI API: {str(e)}")
        # Fallback: resposta básica usando os dados
        if tem_serie and len(serie) > 0:
            # Se há série, nunca diz "não há dados", explica limitações
            resposta_fallback = "## Resumo executivo\n\n"
            resposta_fallback += "Dados de metas e realizados disponíveis para análise.\n\n"
            resposta_fallback += "## Números-chave\n\n"
            for mes_data in serie[:6]:  # Limita a 6 meses no fallback
                mes_ano = mes_data.get("mes_ano", "N/A")
                meta = mes_data.get("meta", 0)
                realizado = mes_data.get("realizado", 0)
                atingimento = mes_data.get("atingimento")
                atingimento_str = f"{atingimento:.1f}%" if atingimento is not None else "N/A"
                resposta_fallback += f"- {mes_ano}: Meta R$ {meta:,.2f}, Realizado R$ {realizado:,.2f}, Atingimento: {atingimento_str}\n"
            resposta_fallback += "\n## Observações sobre os dados\n\n"
            resposta_fallback += "Dados processados via template devido a erro na API. Resposta completa disponível após correção."
        else:
            # Se não há série, explica claramente sem inventar
            resposta_fallback = "Os dados de metas/realizado ainda não estão disponíveis nas tabelas de metas para o período solicitado."
        
        return resposta_fallback, 0.3  # Confiança baixa em caso de erro
    except Exception as e:
        logger.error(f"Erro inesperado ao gerar resposta: {str(e)}")
        return f"Erro ao processar pergunta: {str(e)}", 0.2


def gerar_resposta_performance_vendedores(
    pergunta: str,
    contexto: Dict[str, Any]
) -> Tuple[str, float]:
    """
    Gera uma resposta em linguagem natural para consultas de performance de vendedores,
    usando APENAS os dados presentes em contexto.
    
    Args:
        pergunta: Pergunta do usuário em linguagem natural
        contexto: Dicionário com dados estruturados:
            - mes_ano_solicitado: Mês/ano solicitado pelo usuário (ex.: "2025-08")
            - mes_ano_analise: Mês/ano para o qual há dados disponíveis (ex.: "2025-08" ou None)
            - tem_dados: bool - Indica se há dados disponíveis para o período
            - piores_meta: Lista de vendedores com pior atingimento de meta
            - menores_venda: Lista de vendedores com menor faturamento
            
    Returns:
        Tuple[str, float]: (resposta_texto, confianca)
            - resposta_texto: Resposta em linguagem natural
            - confianca: Nível de confiança (0.0-1.0) - retorna 0.9 conforme especificado
    """
    logger.info(f"Gerando resposta especializada para performance de vendedores: {pergunta[:100]}...")
    
    mes_solic = contexto.get("mes_ano_solicitado")
    mes_analise = contexto.get("mes_ano_analise")
    tem_dados = contexto.get("tem_dados", False)
    piores_meta = contexto.get("piores_meta", [])
    menores_venda = contexto.get("menores_venda", [])
    
    # Prepara dados para JSON
    piores_meta_json = piores_meta if isinstance(piores_meta, list) else []
    menores_venda_json = menores_venda if isinstance(menores_venda, list) else []
    
    # Monta system message conforme especificado
    system_msg = (
        "Você é um analista de inteligência comercial sênior da Dipam.\n"
        "Use SOMENTE os dados fornecidos para responder.\n"
        "Se não houver dados para o período solicitado, explique isso de forma clara.\n"
        "NÃO invente números, não use meses diferentes sem avisar explicitamente.\n"
    )
    
    # Monta user message conforme formato especificado
    user_msg = f"""Pergunta do usuário:

{pergunta}



Mês solicitado: {mes_solic or "não identificado"}

Mês analisado: {mes_analise if tem_dados else "sem dados — listas vazias"}



Piores vendedores por meta (impacto negativo):

{json.dumps(piores_meta_json, ensure_ascii=False)}



Vendedores com menor faturamento no período:

{json.dumps(menores_venda_json, ensure_ascii=False)}



Instruções:



1. Se tem_dados for False (listas vazias), responda em até 2 parágrafos:

   - Diga que não há dados de metas/vendas para o período solicitado.

   - Informe, se fizer sentido, que o DW só contém dados até o mês X (não invente, só diga se vier no contexto – caso contrário, diga apenas que não há dados carregados).

   - Sugira ao usuário perguntar sobre um período em que os dados já estejam disponíveis.



2. Se tem_dados for True, siga esta estrutura em Markdown:



## Resumo executivo

Explique em 2-3 frases quais vendedores puxaram o resultado para baixo

no período analisado e quão relevante foi o impacto.



## Top vendedores com impacto negativo na meta

Liste em bullet points:

- Nome, atingimento (%) e valor de impacto (realizado - meta, valor negativo),

  do pior para o menos pior. Use apenas `piores_meta`.



## Vendedores que menos venderam

Liste em bullet points nome e faturamento dos vendedores com menor venda,

usando somente `menores_venda`.



## Insights e recomendações

Traga de 3 a 5 recomendações práticas (mix, rota, visita, supervisão, etc.).



## Observações sobre os dados

Explique qualquer limitação de dados de forma clara e objetiva.

"""
    
    try:
        # Chama LLM usando a função padrão do projeto
        resposta_texto = call_openai_llm(
            prompt=user_msg,
            system_prompt=system_msg,
            temperature=0.3,  # Mais conservador para não inventar dados
            max_tokens=2000
        )
        
        logger.info(f"Resposta especializada para performance de vendedores gerada ({len(resposta_texto)} caracteres)")
        # Retorna confiança fixa de 0.9 conforme especificado
        return resposta_texto, 0.9
        
    except OpenAIError as e:
        logger.error(f"Erro ao chamar OpenAI API: {str(e)}")
        # Fallback: resposta básica usando os dados
        if tem_dados and (piores_meta or menores_venda):
            resposta_fallback = "## Resumo executivo\n\n"
            resposta_fallback += f"Dados de performance de vendedores disponíveis para análise no período {mes_analise}.\n\n"
            
            if piores_meta:
                resposta_fallback += "## Top vendedores com impacto negativo na meta\n\n"
                for vendedor in piores_meta[:10]:
                    nome = vendedor.get("vendedor_nome", "N/A")
                    atingimento = vendedor.get("atingimento")
                    gap = vendedor.get("gap", 0)
                    impacto_valor = vendedor.get("impacto_valor", gap)
                    
                    atingimento_str = f"{atingimento:.1f}%" if atingimento is not None else "N/A"
                    impacto_str = f"R$ {abs(impacto_valor):,.2f}" if impacto_valor < 0 else f"R$ {impacto_valor:,.2f}"
                    resposta_fallback += f"- {nome}, atingimento {atingimento_str}, impacto {impacto_str}\n"
            
            if menores_venda:
                resposta_fallback += "\n## Vendedores que menos venderam\n\n"
                for vendedor in menores_venda[:10]:
                    nome = vendedor.get("vendedor_nome", "N/A")
                    faturamento = vendedor.get("faturamento_total", 0)
                    resposta_fallback += f"- {nome}, faturamento R$ {faturamento:,.2f}\n"
            
            resposta_fallback += "\n## Observações sobre os dados\n\n"
            resposta_fallback += "Dados processados via template devido a erro na API. Resposta completa disponível após correção."
        else:
            # Sem dados para o período solicitado
            resposta_fallback = f"Não há dados de metas ou vendas para o período solicitado ({mes_solic or 'não identificado'}). "
            resposta_fallback += "Assim que as metas e vendas desse período forem carregadas no DW, será possível fazer essa análise. "
            resposta_fallback += "Sugiro perguntar sobre um período em que os dados já estejam disponíveis."
        
        return resposta_fallback, 0.9  # Confiança conforme especificado
    except Exception as e:
        logger.error(f"Erro inesperado ao gerar resposta: {str(e)}")
        return f"Erro ao processar pergunta: {str(e)}", 0.9
