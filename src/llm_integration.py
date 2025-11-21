"""
Integração com LLM (Large Language Model).

Este módulo contém funções para interagir com modelos de linguagem,
formatando prompts e processando respostas usando a API da OpenAI.

Otimizado para limitar custos e tamanho de contexto.
"""

import logging
from typing import Dict, Any, List, Tuple, Optional
import json

from src.llm_client import call_llm, LLMError
# Mantém compatibilidade com código existente
call_openai_llm = call_llm
OpenAIError = LLMError

# Importa GROQ Guard para proteção contra limites
try:
    from src.api.groq_client import (
        call_groq_model,
        GroqContentTooLongError,
        GroqError,
        truncate_prompt
    )
    GROQ_GUARD_AVAILABLE = True
except ImportError:
    GROQ_GUARD_AVAILABLE = False
    logger.warning("GROQ Guard não disponível. Usando cliente LLM padrão.")
    
    # Define função de fallback para truncate_prompt
    def truncate_prompt(prompt: str, max_chars: int = 8000) -> str:
        """Fallback simples de truncamento se GROQ Guard não estiver disponível."""
        if len(prompt) <= max_chars:
            return prompt
        return prompt[:max_chars - 20] + "[CONTEXTO TRUNCADO]"

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


def gerar_resposta_estruturada_consulta_meta(
    pergunta: str,
    contexto: Dict[str, Any]
) -> Tuple[Dict[str, Any], str, float]:
    """
    Gera resposta estruturada (JSON) para consultas de meta.
    
    NOVA FUNÇÃO: Retorna JSON estruturado no formato CopilotStructuredResponse.
    
    Args:
        pergunta: Pergunta do usuário em linguagem natural
        contexto: Dicionário com dados estruturados do contexto
        
    Returns:
        Tuple[Dict[str, Any], str, float]: (json_estruturado, texto_complementar, confianca)
    """
    logger.info(f"Gerando resposta estruturada (JSON) para consulta de meta: {pergunta[:100]}...")
    
    serie = contexto.get("serie_mensal", [])
    detalhe = contexto.get("detalhe_vendedores_mes", {}) or contexto.get("detalhe_vendedores", {})
    kpis = contexto.get("kpis", {})
    piores_vendedores = contexto.get("pioresVendedores", []) or contexto.get("piores_vendedores", [])
    melhores_vendedores = contexto.get("melhoresVendedores", []) or contexto.get("melhores_vendedores", [])
    clientes_criticos = contexto.get("clientesCriticos", []) or contexto.get("clientesProblema", []) or contexto.get("clientes_criticos", [])
    papel_usuario = contexto.get("papel", "usuario")
    mes_ano = contexto.get("mes_ano") or contexto.get("mes_ano_analise")
    
    # Valida dados
    tem_serie = isinstance(serie, list) and len(serie) > 0
    tem_detalhe = isinstance(detalhe, dict) and detalhe.get("vendedores") and len(detalhe.get("vendedores", [])) > 0
    
    # Calcula confiança
    confianca = 0.5
    if tem_serie:
        confianca += 0.2
    if tem_detalhe:
        confianca += 0.2
    if kpis:
        confianca += 0.05
    if piores_vendedores:
        confianca += 0.05
    if clientes_criticos:
        confianca += 0.05
    confianca = min(confianca, 0.95)
    
    # Prepara dados para JSON
    serie_json = serie if isinstance(serie, list) else []
    detalhe_json = detalhe if isinstance(detalhe, dict) else {}
    kpis_json = kpis if isinstance(kpis, dict) else {}
    piores_json = piores_vendedores[:15] if isinstance(piores_vendedores, list) else []
    clientes_json = clientes_criticos[:15] if isinstance(clientes_criticos, list) else []
    
    # Monta prompt para LLM gerar JSON estruturado
    system_msg = (
        "Você é um analista de inteligência comercial sênior da Dipam.\n"
        "Use SOMENTE os dados fornecidos abaixo para gerar um JSON estruturado.\n"
        "A resposta DEVE começar APENAS com um JSON válido, sem explicações antes ou depois.\n"
        "NUNCA diga que não há dados se houver elementos nas listas fornecidas.\n"
        "Use SEMPRE os dados fornecidos, mesmo que sejam poucos.\n"
    )
    
    user_msg = f"""Pergunta do usuário: {pergunta}

Dados disponíveis:

KPIs gerais:
{json.dumps(kpis_json, ensure_ascii=False, indent=2)}

Piores vendedores (top 15):
{json.dumps(piores_json, ensure_ascii=False, indent=2)}

Clientes críticos (top 15):
{json.dumps(clientes_json, ensure_ascii=False, indent=2)}

Série mensal:
{json.dumps(serie_json, ensure_ascii=False, indent=2)}

Detalhe vendedores:
{json.dumps(detalhe_json, ensure_ascii=False, indent=2)}

Instruções:

Gere um JSON válido seguindo EXATAMENTE esta estrutura (sem campos extras):

{{
  "resumoExecutivo": "Texto de 2-4 parágrafos explicando: se bateu meta, gap em R$ e %, quem puxou resultado para baixo, tendência geral. Use números reais dos dados fornecidos.",
  
  "kpis": [
    {{
      "label": "Meta Total",
      "value": <número ou string>,
      "variation": "<opcional: variação %>",
      "color": "<positive|negative|neutral>",
      "icon": "<emoji opcional>"
    }},
    {{
      "label": "Realizado Total",
      "value": <número ou string>,
      "variation": "<opcional>",
      "color": "<positive|negative|neutral>"
    }},
    {{
      "label": "Atingimento Médio",
      "value": "<número>%",
      "variation": "<opcional>",
      "color": "<positive|negative|neutral>"
    }},
    {{
      "label": "Vendedores que Bateram",
      "value": <número>,
      "color": "<positive|negative|neutral>"
    }}
  ],
  
  "rankingVendedores": [
    {{
      "vendedor": "<nome>",
      "meta": <número>,
      "realizado": <número>,
      "atingimento": <número>,
      "gap": <número>,
      "supervisor": "<opcional>",
      "rank": <número>
    }}
  ],
  
  "clientesCriticos": [
    {{
      "cliente": "<nome>",
      "faturamento": <número>,
      "pedidos": <número>,
      "variacao": <número opcional>,
      "vendedor": "<opcional>",
      "insight": "<texto opcional explicando problema>"
    }}
  ],
  
  "insightsRecomendacoes": [
    "Ação prática específica 1",
    "Ação prática específica 2",
    "Ação prática específica 3"
  ]
}}

REGRAS CRÍTICAS:

1. A resposta DEVE começar APENAS com {{ (abre chave) e terminar com }} (fecha chave).
2. NÃO adicione texto antes ou depois do JSON.
3. Se piores_json tiver elementos, OBRIGATORIAMENTE preencha rankingVendedores (top 10).
4. Se clientes_json tiver elementos, OBRIGATORIAMENTE preencha clientesCriticos (top 15).
5. Se kpis_json tiver dados, OBRIGATORIAMENTE preencha kpis (4-6 KPIs principais).
6. SEMPRE preencha resumoExecutivo usando números reais dos dados.
7. SEMPRE preencha insightsRecomendacoes com 3-5 ações práticas específicas.
8. NUNCA diga "não há dados" se as listas tiverem elementos.
9. Use números reais do contexto. NUNCA invente números.

Se não houver dados em nenhuma lista, retorne JSON com campos vazios [] e resumoExecutivo explicando que não há dados disponíveis."""
    
    try:
        # Chama LLM para gerar JSON estruturado
        resposta_llm = call_openai_llm(
            prompt=user_msg,
            system_prompt=system_msg,
            temperature=0.2,  # Muito conservador para JSON estruturado
            max_tokens=4000  # Mais tokens para JSON completo
        )
        
        # Extrai JSON da resposta
        json_str = _extrair_json_da_resposta(resposta_llm)
        
        if not json_str:
            logger.warning("Não foi possível extrair JSON da resposta do LLM. Gerando automaticamente...")
            # Fallback: gera JSON estruturado automaticamente a partir dos dados
            json_estruturado = _gerar_json_fallback(contexto, pergunta)
            texto_complementar = json_estruturado.get("resumoExecutivo", "")
        else:
            try:
                json_estruturado = json.loads(json_str)
                texto_complementar = json_estruturado.get("resumoExecutivo", "")
                
                # Valida e corrige JSON se necessário
                json_estruturado = _validar_e_corrigir_json(json_estruturado, contexto)
            except json.JSONDecodeError as e:
                logger.error(f"Erro ao fazer parse do JSON: {str(e)}")
                json_estruturado = _gerar_json_fallback(contexto, pergunta)
                texto_complementar = json_estruturado.get("resumoExecutivo", "")
        
        # Adiciona jsonTecnico para debug
        json_estruturado["jsonTecnico"] = {
            "contexto_keys": list(contexto.keys()),
            "tem_serie": tem_serie,
            "tem_detalhe": tem_detalhe,
            "qtd_piores_vendedores": len(piores_json),
            "qtd_clientes_criticos": len(clientes_json),
            "mes_ano": mes_ano
        }
        
        logger.info(f"Resposta estruturada gerada: {len(str(json_estruturado))} caracteres, confiança: {confianca:.2f}")
        return json_estruturado, texto_complementar, confianca
        
    except Exception as e:
        logger.error(f"Erro ao gerar resposta estruturada: {str(e)}")
        # Fallback: gera JSON básico
        json_estruturado = _gerar_json_fallback(contexto, pergunta)
        texto_complementar = json_estruturado.get("resumoExecutivo", "")
        return json_estruturado, texto_complementar, 0.7


def _extrair_json_da_resposta(texto: str) -> Optional[str]:
    """Extrai JSON válido de uma resposta do LLM."""
    import re
    # Tenta encontrar JSON entre { }
    pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(pattern, texto, re.DOTALL)
    
    for match in matches:
        try:
            # Testa se é JSON válido
            json.loads(match)
            return match
        except json.JSONDecodeError:
            continue
    
    # Se não encontrou, tenta extrair primeiro bloco entre { }
    inicio = texto.find('{')
    fim = texto.rfind('}')
    if inicio >= 0 and fim > inicio:
        candidato = texto[inicio:fim+1]
        try:
            json.loads(candidato)
            return candidato
        except json.JSONDecodeError:
            pass
    
    return None


def _validar_e_corrigir_json(json_data: Dict[str, Any], contexto: Dict[str, Any]) -> Dict[str, Any]:
    """Valida e corrige JSON estruturado baseado nos dados do contexto."""
    # Garante que campos obrigatórios existam
    if "resumoExecutivo" not in json_data:
        json_data["resumoExecutivo"] = "Análise de metas e realizados baseada nos dados disponíveis."
    
    # Corrige rankingVendedores se necessário
    if "rankingVendedores" not in json_data:
        json_data["rankingVendedores"] = []
    
    # Preenche rankingVendedores se houver dados no contexto
    piores = contexto.get("pioresVendedores", []) or contexto.get("piores_vendedores", [])
    if piores and len(json_data.get("rankingVendedores", [])) == 0:
        ranking = []
        for idx, v in enumerate(piores[:10], 1):
            ranking.append({
                "vendedor": v.get("vendedor_nome") or v.get("nome") or "N/A",
                "meta": float(v.get("meta", 0) or 0),
                "realizado": float(v.get("realizado", 0) or 0),
                "atingimento": float(v.get("atingimento", 0) or 0),
                "gap": float(v.get("gap", 0) or 0),
                "supervisor": v.get("supervisor_nome") or v.get("supervisor"),
                "rank": idx
            })
        json_data["rankingVendedores"] = ranking
    
    # Corrige clientesCriticos se necessário
    if "clientesCriticos" not in json_data:
        json_data["clientesCriticos"] = []
    
    clientes = contexto.get("clientesCriticos", []) or contexto.get("clientesProblema", [])
    if clientes and len(json_data.get("clientesCriticos", [])) == 0:
        clientes_list = []
        for c in clientes[:15]:
            # Gera insight baseado em variação se disponível
            insight = None
            if c.get("variacao_percentual") is not None:
                variacao = float(c.get("variacao_percentual", 0))
                if variacao < -10:
                    insight = f"Queda de {abs(variacao):.1f}% vs média dos últimos 3 meses"
            elif c.get("qtd_pedidos", 0) < 5:
                insight = "Poucos pedidos no mês (oportunidade de recuperação)"
            
            clientes_list.append({
                "cliente": c.get("nome_cliente") or c.get("cliente") or "N/A",
                "faturamento": float(c.get("faturamento_mes", 0) or 0),
                "pedidos": int(c.get("qtd_pedidos", 0) or 0),
                "variacao": float(c.get("variacao_percentual", 0)) if c.get("variacao_percentual") is not None else None,
                "vendedor": c.get("vendedor_nome") or c.get("vendedor"),
                "insight": insight
            })
        json_data["clientesCriticos"] = clientes_list
    
    # Corrige KPIs se necessário
    if "kpis" not in json_data:
        json_data["kpis"] = []
    
    kpis = contexto.get("kpis", {})
    if kpis and len(json_data.get("kpis", [])) == 0:
        kpis_list = []
        
        meta_total = float(kpis.get("metaTotal", 0) or 0)
        realizado_total = float(kpis.get("realizadoTotal", 0) or 0)
        atingimento_medio = float(kpis.get("atingimentoMedio", 0) or 0)
        vendedores_que_bateram = int(kpis.get("vendedoresQueBateram", 0) or 0)
        
        if meta_total > 0:
            kpis_list.append({
                "label": "Meta Total",
                "value": meta_total,
                "color": "neutral",
                "icon": "🎯"
            })
        
        if realizado_total > 0:
            gap = realizado_total - meta_total
            variacao = (gap / meta_total * 100) if meta_total > 0 else 0
            kpis_list.append({
                "label": "Realizado Total",
                "value": realizado_total,
                "variation": f"{variacao:+.1f}%",
                "color": "positive" if gap >= 0 else "negative",
                "icon": "💰"
            })
        
        if atingimento_medio > 0:
            kpis_list.append({
                "label": "Atingimento Médio",
                "value": f"{atingimento_medio:.1f}%",
                "color": "positive" if atingimento_medio >= 100 else "negative",
                "icon": "📊"
            })
        
        if vendedores_que_bateram >= 0:
            kpis_list.append({
                "label": "Vendedores que Bateram",
                "value": vendedores_que_bateram,
                "color": "positive" if vendedores_que_bateram > 0 else "neutral",
                "icon": "✅"
            })
        
        json_data["kpis"] = kpis_list
    
    # Corrige insightsRecomendacoes se necessário
    if "insightsRecomendacoes" not in json_data:
        json_data["insightsRecomendacoes"] = []
    
    if len(json_data.get("insightsRecomendacoes", [])) == 0:
        # Gera recomendações básicas baseadas nos dados
        insights = []
        if piores:
            top_3_piores = piores[:3]
            nomes = [v.get("vendedor_nome") or v.get("nome") for v in top_3_piores if v.get("vendedor_nome") or v.get("nome")]
            if nomes:
                insights.append(f"Priorizar coaching imediato para: {', '.join(nomes)}")
        
        if clientes:
            insights.append(f"Implementar plano de ação para {len(clientes)} clientes críticos identificados")
        
        if kpis and kpis.get("atingimentoMedio", 0) < 100:
            gap = float(kpis.get("metaTotal", 0)) - float(kpis.get("realizadoTotal", 0))
            if gap > 0:
                insights.append(f"Recuperar gap de R$ {gap:,.2f} através de ações direcionadas")
        
        json_data["insightsRecomendacoes"] = insights if insights else ["Analisar dados detalhados para identificar oportunidades"]
    
    return json_data


def _gerar_json_fallback(contexto: Dict[str, Any], pergunta: str) -> Dict[str, Any]:
    """Gera JSON estruturado automaticamente quando LLM não retorna JSON válido."""
    kpis = contexto.get("kpis", {})
    piores = contexto.get("pioresVendedores", []) or contexto.get("piores_vendedores", [])
    clientes = contexto.get("clientesCriticos", []) or contexto.get("clientesProblema", [])
    mes_ano = contexto.get("mes_ano") or contexto.get("mes_ano_analise")
    
    # Gera resumo executivo básico
    resumo = f"Análise de metas e realizados"
    if mes_ano:
        resumo += f" para {mes_ano}."
    else:
        resumo += "."
    
    if kpis:
        meta = float(kpis.get("metaTotal", 0) or 0)
        realizado = float(kpis.get("realizadoTotal", 0) or 0)
        atingimento = float(kpis.get("atingimentoMedio", 0) or 0)
        gap = realizado - meta
        
        resumo += f"\n\nMeta total: R$ {meta:,.2f} | Realizado: R$ {realizado:,.2f} | Atingimento: {atingimento:.1f}%"
        if gap < 0:
            resumo += f"\n\nGap negativo de R$ {abs(gap):,.2f} precisa ser recuperado."
        elif gap > 0:
            resumo += f"\n\nSuperação de R$ {gap:,.2f}."
    
    # Gera KPIs
    kpis_list = []
    if kpis:
        meta_total = float(kpis.get("metaTotal", 0) or 0)
        realizado_total = float(kpis.get("realizadoTotal", 0) or 0)
        atingimento_medio = float(kpis.get("atingimentoMedio", 0) or 0)
        vendedores_que_bateram = int(kpis.get("vendedoresQueBateram", 0) or 0)
        
        if meta_total > 0:
            kpis_list.append({
                "label": "Meta Total",
                "value": meta_total,
                "color": "neutral",
                "icon": "🎯"
            })
        
        if realizado_total > 0:
            gap = realizado_total - meta_total
            variacao = (gap / meta_total * 100) if meta_total > 0 else 0
            kpis_list.append({
                "label": "Realizado Total",
                "value": realizado_total,
                "variation": f"{variacao:+.1f}%",
                "color": "positive" if gap >= 0 else "negative",
                "icon": "💰"
            })
        
        if atingimento_medio > 0:
            kpis_list.append({
                "label": "Atingimento Médio",
                "value": f"{atingimento_medio:.1f}%",
                "color": "positive" if atingimento_medio >= 100 else "negative",
                "icon": "📊"
            })
        
        if vendedores_que_bateram >= 0:
            kpis_list.append({
                "label": "Vendedores que Bateram",
                "value": vendedores_que_bateram,
                "color": "positive" if vendedores_que_bateram > 0 else "neutral",
                "icon": "✅"
            })
    
    # Gera ranking
    ranking = []
    for idx, v in enumerate(piores[:10], 1):
        ranking.append({
            "vendedor": v.get("vendedor_nome") or v.get("nome") or "N/A",
            "meta": float(v.get("meta", 0) or 0),
            "realizado": float(v.get("realizado", 0) or 0),
            "atingimento": float(v.get("atingimento", 0) or 0),
            "gap": float(v.get("gap", 0) or 0),
            "supervisor": v.get("supervisor_nome") or v.get("supervisor"),
            "rank": idx
        })
    
    # Gera clientes críticos
    clientes_list = []
    for c in clientes[:15]:
        insight = None
        if c.get("variacao_percentual") is not None:
            variacao = float(c.get("variacao_percentual", 0))
            if variacao < -10:
                insight = f"Queda de {abs(variacao):.1f}% vs média dos últimos 3 meses"
        
        clientes_list.append({
            "cliente": c.get("nome_cliente") or c.get("cliente") or "N/A",
            "faturamento": float(c.get("faturamento_mes", 0) or 0),
            "pedidos": int(c.get("qtd_pedidos", 0) or 0),
            "variacao": float(c.get("variacao_percentual", 0)) if c.get("variacao_percentual") is not None else None,
            "vendedor": c.get("vendedor_nome") or c.get("vendedor"),
            "insight": insight
        })
    
    # Gera insights
    insights = []
    if piores:
        top_3 = piores[:3]
        nomes = [v.get("vendedor_nome") or v.get("nome") for v in top_3 if v.get("vendedor_nome") or v.get("nome")]
        if nomes:
            insights.append(f"Priorizar coaching imediato para: {', '.join(nomes)}")
    
    if clientes:
        insights.append(f"Implementar plano de ação para {len(clientes)} clientes críticos identificados")
    
    if kpis and kpis.get("atingimentoMedio", 0) < 100:
        gap = float(kpis.get("metaTotal", 0)) - float(kpis.get("realizadoTotal", 0))
        if gap > 0:
            insights.append(f"Recuperar gap de R$ {gap:,.2f} através de ações direcionadas")
    
    if not insights:
        insights = ["Analisar dados detalhados para identificar oportunidades de melhoria"]
    
    return {
        "resumoExecutivo": resumo,
        "kpis": kpis_list,
        "rankingVendedores": ranking,
        "clientesCriticos": clientes_list,
        "insightsRecomendacoes": insights
    }


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


def _gerar_resumo_executivo_fallback(contexto: Dict[str, Any]) -> str:
    """
    Gera um resumo executivo simples via código quando GROQ falha.
    
    Args:
        contexto: Contexto com dados estruturados
        
    Returns:
        str: Resumo executivo gerado via código
    """
    mes_ano = contexto.get('mes_ano', 'N/A')
    meta_total = contexto.get('meta_total', 0)
    realizado_total = contexto.get('realizado_total', 0)
    gap_total = contexto.get('gap_total', 0)
    atingimento_medio = contexto.get('atingimento_medio', 0)
    piores_vendedores = contexto.get('piores_vendedores', [])[:3]
    
    resumo = f"Foram identificados {contexto.get('total_vendedores', 0)} vendedores no período {mes_ano}. "
    
    if gap_total < 0:
        resumo += f"O gap negativo de R$ {abs(gap_total):,.2f} precisa ser recuperado. "
    else:
        resumo += f"Superação de R$ {gap_total:,.2f} foi alcançada. "
    
    resumo += f"O atingimento médio foi de {atingimento_medio:.1f}%. "
    
    if piores_vendedores:
        nomes = [v.get('vendedor_nome', 'N/A') for v in piores_vendedores]
        resumo += f"As rotas mais impactadas são: {', '.join(nomes[:3])}. "
    
    resumo += "Principais alertas: revisar estratégia comercial e acompanhamento de metas."
    
    return resumo


def gerar_resposta_llm_diretor(
    contexto: Dict[str, Any],
    pergunta: str,
    tipo: str = "resumo_executivo"
) -> str:
    """
    Gera resposta do LLM no estilo "Diretor Comercial Digital" (FASE 3).
    
    Args:
        contexto: Dicionário com dados estruturados (analytics)
        pergunta: Pergunta do usuário
        tipo: Tipo de resposta ("resumo_executivo", "recomendacoes")
        
    Returns:
        str: Resposta do LLM em linguagem de Diretor
    """
    logger.info(f"Gerando resposta LLM Diretor (tipo={tipo}) para: {pergunta[:100]}...")
    
    # System prompt estilo Diretor Comercial
    system_prompt = """Você é o DIPAM COPILOT, um Diretor Comercial Digital da DIPAM.

PERSONA:
- Fale sempre com foco em negócios, em tom executivo e direto
- Profissional mas acessível
- Focado em insights acionáveis

REGRAS FUNDAMENTAIS - ZERO INVENÇÃO DE DADOS:
1. Use APENAS os dados numéricos fornecidos no contexto JSON
2. NUNCA invente valores, períodos, produtos, quantidades, vendedores ou clientes
3. Se um dado não estiver presente no contexto, NÃO cite
4. Use formatação brasileira: R$ 1.000,00 e 85,5%
5. Seja preciso: use números exatos do contexto
6. CRÍTICO: Se o contexto fornecer meta_total, realizado_total e atingimento_medio, use EXATAMENTE esses valores. NÃO recalcule, NÃO arredonde além do necessário, NÃO invente novos números.

ESTRUTURA PARA RESUMO EXECUTIVO:
- 3-5 frases em linguagem de Diretor
- Cite números-chave (R$, %, ranking) de forma resumida
- Explique o que está acontecendo de forma geral
- Identifique principais responsáveis (vendedores, rotas)
- Mencione o impacto (gap total, % do gap)

NUNCA diga "não tenho dados" se o contexto indicar que há dados.
Se a camada de código marcar tem_dados = true, sempre traga alguma análise."""
    
    # Monta prompt específico
    if tipo == "resumo_executivo":
        # FASE 5: Adiciona informações sobre insights preditivos se disponíveis
        insights_texto = ""
        insights_preditivos = contexto.get("insights_preditivos", {})
        
        if insights_preditivos.get("meta_risk"):
            meta_risk = insights_preditivos["meta_risk"]
            vendedores_risco_alto = meta_risk.get("vendedores_risco_alto", 0)
            detalhes = meta_risk.get("detalhes", [])
            
            if vendedores_risco_alto > 0:
                insights_texto = f"\n\nINSIGHTS PREDITIVOS (ML):\n"
                insights_texto += f"- Há {vendedores_risco_alto} vendedores com probabilidade acima de 70% de não bater a meta (baseado em modelo de ML).\n"
                if detalhes:
                    top_vendedores = detalhes[:3]  # Top 3
                    nomes_risco = ", ".join([v.get("vendedor_nome", "N/A") for v in top_vendedores])
                    insights_texto += f"- Principais vendedores em risco: {nomes_risco}.\n"
        
        # ✅ CORREÇÃO: Condensa contexto para evitar exceder limite do GROQ
        # Não envia tabelas completas, apenas KPIs principais e top vendedores
        piores_vendedores = contexto.get('piores_vendedores', [])[:5]  # Top 5 apenas
        piores_vendedores_texto = ""
        if piores_vendedores:
            piores_vendedores_texto = "\nPrincipais responsáveis (top 5):\n"
            for i, v in enumerate(piores_vendedores, 1):
                nome = v.get('vendedor_nome', 'N/A')
                atingimento = v.get('atingimento', 0)
                gap = v.get('gap', 0)
                piores_vendedores_texto += f"{i}. {nome}: {atingimento:.1f}% atingimento, gap R$ {gap:,.2f}\n"
        
        prompt = f"""Com base nos dados abaixo, escreva um resumo executivo de 3-5 frases explicando por que não batemos a meta no mês {contexto.get('mes_ano', 'N/A')}.

Dados (USE EXATAMENTE ESTES VALORES - NÃO RECALCULE):
- Meta total: R$ {contexto.get('meta_total', 0):,.2f}
- Realizado total: R$ {contexto.get('realizado_total', 0):,.2f}
- Gap total: R$ {contexto.get('gap_total', 0):,.2f}
- Atingimento médio: {contexto.get('atingimento_medio', 0):.1f}%
- Total de vendedores: {contexto.get('total_vendedores', 0)}
- Vendedores em risco: {contexto.get('total_vendedores_em_risco', 0)}
{insights_texto}
{piores_vendedores_texto}

IMPORTANTE: Use EXATAMENTE os valores de Meta total, Realizado total e Atingimento médio fornecidos acima. NÃO recalcule, NÃO arredonde além do necessário, NÃO invente novos números.

Escreva o resumo executivo em linguagem de Diretor, citando os principais vendedores e o impacto deles no gap total.{" Se houver insights preditivos acima, mencione-os explicitamente no resumo." if insights_texto else ""}"""
    else:
        # Para recomendações, também condensa o contexto
        contexto_condensado = {
            "mes_ano": contexto.get('mes_ano'),
            "meta_total": contexto.get('meta_total'),
            "realizado_total": contexto.get('realizado_total'),
            "gap_total": contexto.get('gap_total'),
            "atingimento_medio": contexto.get('atingimento_medio'),
            "top_vendedores": contexto.get('piores_vendedores', [])[:5],
        }
        prompt = f"""Com base nos dados abaixo, gere recomendações práticas para o Diretor.

Dados:
{json.dumps(contexto_condensado, ensure_ascii=False, indent=2)}

Gere 3-7 ações claras e práticas."""
    
    try:
        # ✅ CORREÇÃO: Usa GROQ Guard se disponível, senão usa cliente padrão
        if GROQ_GUARD_AVAILABLE:
            try:
                resposta = call_groq_model(
                    prompt=prompt,
                    system=system_prompt,
                    max_tokens=512,
                    contexto="resumo_executivo",
                    temperature=0.3,
                )
                return resposta.strip()
            except GroqContentTooLongError as e:
                logger.error(
                    f"GROQ recusou conteúdo muito longo para resumo executivo: {str(e)}",
                    extra={
                        "event": "resumo_executivo_fallback_sem_groq",
                        "error": str(e),
                    }
                )
                # Fallback: gera resumo simples via código
                return _gerar_resumo_executivo_fallback(contexto)
            except GroqError as e:
                logger.error(f"Erro do GROQ ao gerar resumo executivo: {str(e)}")
                # Fallback: gera resumo simples via código
                return _gerar_resumo_executivo_fallback(contexto)
        else:
            # Usa cliente LLM padrão (compatibilidade)
            resposta = call_openai_llm(
                system_prompt=system_prompt,
                user_prompt=prompt,
                temperature=0.3,
                max_tokens=500
            )
            return resposta.strip()
    except Exception as e:
        logger.error(f"Erro ao gerar resposta LLM Diretor: {str(e)}")
        # Fallback: gera resumo simples via código
        return _gerar_resumo_executivo_fallback(contexto)


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
        # ✅ CORREÇÃO: Usa GROQ Guard se disponível, senão usa cliente padrão
        if GROQ_GUARD_AVAILABLE:
            try:
                resposta_texto = call_groq_model(
                    prompt=user_msg,
                    system=system_msg,
                    max_tokens=1024,  # Reduzido de 2000 para evitar limite
                    contexto="ask",
                    temperature=0.3,
                )
            except GroqContentTooLongError as e:
                logger.error(
                    f"GROQ recusou conteúdo muito longo para performance vendedores: {str(e)}",
                    extra={
                        "event": "groq_too_long",
                        "contexto": "performance_vendedores",
                        "error": str(e),
                    }
                )
                # Fallback: usa cliente padrão com prompt truncado
                user_msg_truncated = truncate_prompt(user_msg, max_chars=8000)
                resposta_texto = call_openai_llm(
                    prompt=user_msg_truncated,
                    system_prompt=system_msg,
                    temperature=0.3,
                    max_tokens=1024
                )
            except GroqError as e:
                logger.error(f"Erro do GROQ ao gerar resposta performance vendedores: {str(e)}")
                # Fallback: usa cliente padrão
                user_msg_truncated = truncate_prompt(user_msg, max_chars=8000)
                resposta_texto = call_openai_llm(
                    prompt=user_msg_truncated,
                    system_prompt=system_msg,
                    temperature=0.3,
                    max_tokens=1024
                )
        else:
            # Usa cliente LLM padrão (compatibilidade)
            # ✅ CORREÇÃO: Trunca prompt antes de enviar
            user_msg_truncated = truncate_prompt(user_msg, max_chars=8000) if 'truncate_prompt' in globals() else user_msg[:8000]
            resposta_texto = call_openai_llm(
                prompt=user_msg_truncated,
                system_prompt=system_msg,
                temperature=0.3,
                max_tokens=1024  # Reduzido de 2000
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
