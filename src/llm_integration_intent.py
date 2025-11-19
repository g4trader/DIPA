"""
Integração LLM para geração de IntentSpec e respostas estruturadas.

Este módulo contém funções para:
1. Gerar IntentSpec via LLM (primeira chamada)
2. Gerar resposta executiva com dados brutos do DW (segunda chamada)

ARQUITETURA:
- LLM gera IntentSpec em JSON primeiro
- Backend executa consulta DW baseada no IntentSpec
- LLM recebe dados brutos e gera resposta estruturada final
- NUNCA menciona BigQuery (apenas "data warehouse DIPAM" ou "camada DW")
"""

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from calendar import monthrange

from src.llm_client import call_llm, LLMError
# Mantém compatibilidade com código existente
call_openai_llm = call_llm
OpenAIError = LLMError
from src.agent.intent_spec import IntentSpec

logger = logging.getLogger(__name__)


def gerar_intent_spec_via_llm(pergunta: str, papel: Optional[str] = None) -> IntentSpec:
    """
    Gera IntentSpec via LLM a partir da pergunta do usuário.
    
    O LLM analisa a pergunta e retorna um JSON estruturado com IntentSpec.
    
    Args:
        pergunta: Pergunta do usuário em linguagem natural
        papel: Papel do usuário (diretor, supervisor, vendedor)
        
    Returns:
        IntentSpec parseado do JSON retornado pelo LLM
        
    Raises:
        ValueError: Se o JSON retornado pelo LLM for inválido
    """
    system_prompt = _get_system_prompt_intent_spec()
    
    prompt = f"""Pergunta do usuário: {pergunta}

Retorne APENAS um JSON válido com a especificação de intenção (IntentSpec). NÃO adicione explicações, NÃO adicione texto antes ou depois do JSON.

Estrutura do JSON IntentSpec:

{{
  "tipo": "meta" | "vendas" | "clientes_criticos" | "churn" | "ranking_vendedores" | "ranking_produtos" | "analise_meta_detalhada" | "metas_por_supervisor" | "clientes_sem_compra" | "queda_faturamento" | "meta_departamento" | "positivacao" | "mix" | "recompra" | "clientes_sem_item" | "vendas_baixas" | "mix_nissin" | "outros",
  "periodo_inicio": "YYYY-MM-DD" | null,
  "periodo_fim": "YYYY-MM-DD" | null,
  "dimensao_principal": "mes" | "vendedor" | "supervisor" | "rota" | "cliente" | "marca" | "categoria" | "sku" | "produto" | "nenhuma",
  "dimensao_secundaria": "mes" | "vendedor" | "supervisor" | "rota" | "cliente" | "marca" | "categoria" | "sku" | null,
  "filtros": {{
    "supervisor_id": int | null,
    "vendedor_id": int | null,
    "rota": "string" | null,
    "cliente_id": int | null,
    "mes": "YYYY-MM" | null,
    "top_n": int | null,
    "limite": int | null,
    "incluir_ranking": bool | null
  }},
  "metricas": ["meta_total", "realizado_total", "atingimento_medio", "gap_total", "faturamento_total", "churn_score", "quantidade_vendas", ...]
}}

REGRAS CRÍTICAS PARA PERÍODOS:
- Se a pergunta mencionar "mês" (ex.: "agosto de 2025", "mês de agosto", "agosto/2025"): 
  * Converta para início/fim do mês: periodo_inicio = "2025-08-01", periodo_fim = "2025-08-31"
- Se mencionar "todo o período", "todos os meses", "período completo": 
  * Use "2024-11-01" a "2025-10-31" (ou o período disponível no data warehouse)
- Se mencionar "últimos N meses": 
  * Calcule o período correspondente (ex.: últimos 6 meses = "2025-05-01" a "2025-10-31")
- Se NÃO houver período explícito na pergunta: 
  * NÃO invente período. Deixe periodo_inicio = null e periodo_fim = null
  * O backend usará o período padrão ou pedirá esclarecimento

REGRAS PARA FILTROS:
- Se pedir "top N" ou "os N maiores/menores": inclua "top_n": N nos filtros.
- Se mencionar rota específica: inclua "rota": "ROTA XX" nos filtros.
- Se mencionar supervisor: inclua "supervisor_id" se conhecido, ou deixe null.

REGRA NOVA — PRIORIDADE ALTA:
- Se a pergunta mencionar explicitamente "P12", "período P12", "positivação de SKU", "não tiveram positivação" ou "clientes sem positivação", você DEVE usar o tipo oficial:
    tipo="positivacao"
- Para perguntas sobre positivação em P12, use dimensao_principal="cliente" e inclua o SKU nos filtros.

REGRAS PARA TIPO (TODOS OS TIPOS SÃO FIRST-CLASS, NUNCA USE FALLBACK):

TIPOS LEGADOS (para compatibilidade):
- "meta": perguntas sobre metas e atingimento.
- "vendas": perguntas sobre faturamento e vendas.
- "clientes_criticos" ou "churn": perguntas sobre risco de churn.
- "ranking_vendedores": perguntas sobre ranking/comparação de vendedores (use dimensao_principal = "vendedor").
- "ranking_produtos": perguntas sobre ranking/comparação de produtos (use dimensao_principal = "categoria" ou "sku").
- "analise_meta_detalhada": análise multi-dimensional (vendedor + produto + cliente).

TIPOS DW OFICIAIS (Q1-Q13 do ENGINEERING_QUERIES.md - USE ESTES QUANDO APLICÁVEL):
- "clientes_sem_compra": clientes ativos sem compras há N dias (use dimensao_principal = "cliente", filtros: {{"dias": N}}).
- "queda_faturamento": queda de faturamento ano contra ano (use dimensao_principal = "cliente", filtros: {{"ano_base": YYYY, "ano_comparado": YYYY}}).
- "meta_departamento": indústrias/departamentos com mais vendedores fora da meta (use dimensao_principal = "nenhuma").
- "positivacao": rotas com melhor/pior positivação de indústria OU clientes que não tiveram positivação de SKU em P12 (use dimensao_principal = "rota" ou "cliente", filtros: {{"industria": "Mars"|"Nissin"|etc, "sku": "..."}}).
- "mix": análise de mix de produtos (use dimensao_principal = "produto" ou "sku").
- "recompra": clientes que compraram mas não recompraram (use dimensao_principal = "cliente", filtros: {{"sku": "..."}}).
- "clientes_sem_item": clientes que não compraram determinado item (NÃO use para positivação em P12 - use "positivacao" nesses casos) (use dimensao_principal = "cliente", filtros: {{"sku": "...", "industria": "..."}}).
- "vendas_baixas": itens com baixa média de vendas mensal (use dimensao_principal = "produto", filtros: {{"limite_media": N}}). NÃO use para perguntas sobre positivação ou P12.
- "mix_nissin": análise de mix mínimo de Nissin (use dimensao_principal = "cliente" ou "rota", filtros: {{"mes": "YYYY-MM"}}).

EXEMPLOS ADICIONAIS:
Pergunta: "Quais clientes não tiveram positivação de Snickers Original 45g em P12?"
tipo: "positivacao"
dimensao_principal: "cliente"
filtros: {{"sku": "Snickers Original 45g", "periodo": "P12"}}

Pergunta: "Quais clientes não tiveram positivação de M&Ms Tubo em P12?"
tipo: "positivacao"
dimensao_principal: "cliente"
filtros: {{"sku": "M&Ms Tubo", "periodo": "P12"}}

Pergunta: "Quais clientes não tiveram positivação de M&Ms Choco 40g em P12?"
tipo: "positivacao"
dimensao_principal: "cliente"
filtros: {{"sku": "M&Ms Choco 40g", "periodo": "P12"}}

IMPORTANTE: Use os tipos DW oficiais quando a pergunta corresponder exatamente. Não converta para tipos legados ou use fallback "outros" para perguntas Q1-Q13.

REGRA CRÍTICA FINAL:
NUNCA classifique consultas envolvendo positivação em P12 como "clientes_sem_item". Sempre use tipo="positivacao" quando a pergunta mencionar:
- "positivação" + "P12"
- "não tiveram positivação" + SKU
- "clientes sem positivação" + período P12

Retorne APENAS o JSON, sem explicações adicionais."""

    try:
        resposta_llm = call_openai_llm(prompt, system_prompt=system_prompt)
        
        # Limpa a resposta (remove markdown code blocks se houver)
        resposta_limpa = resposta_llm.strip()
        if resposta_limpa.startswith("```json"):
            resposta_limpa = resposta_limpa[7:]
        if resposta_limpa.startswith("```"):
            resposta_limpa = resposta_limpa[3:]
        if resposta_limpa.endswith("```"):
            resposta_limpa = resposta_limpa[:-3]
        resposta_limpa = resposta_limpa.strip()
        
        # Parse JSON
        intent_dict = json.loads(resposta_limpa)
        
        # Valida campos obrigatórios
        if "tipo" not in intent_dict:
            raise ValueError("IntentSpec retornado pelo LLM não contém campo 'tipo'")
        
        # Cria IntentSpec
        intent_spec = IntentSpec(
            tipo=intent_dict.get("tipo", "outros"),
            periodo_inicio=intent_dict.get("periodo_inicio"),
            periodo_fim=intent_dict.get("periodo_fim"),
            dimensao_principal=intent_dict.get("dimensao_principal", "nenhuma"),
            dimensao_secundaria=intent_dict.get("dimensao_secundaria"),
            filtros=intent_dict.get("filtros", {}),
            metricas=intent_dict.get("metricas", [])
        )
        
        logger.info(
            f"[gerar_intent_spec_via_llm] IntentSpec gerado: "
            f"tipo={intent_spec.tipo}, "
            f"dimensao={intent_spec.dimensao_principal}, "
            f"periodo={intent_spec.periodo_inicio} a {intent_spec.periodo_fim}"
        )
        
        return intent_spec
        
    except json.JSONDecodeError as e:
        logger.error(f"[gerar_intent_spec_via_llm] Erro ao parsear JSON: {e}")
        logger.error(f"[gerar_intent_spec_via_llm] Resposta LLM: {resposta_llm[:500]}")
        raise ValueError(f"Resposta do LLM não é um JSON válido: {str(e)}")
    except Exception as e:
        logger.error(f"[gerar_intent_spec_via_llm] Erro ao gerar IntentSpec: {e}")
        raise


def gerar_resposta_executiva_com_dados_dw(
    pergunta: str,
    intent_spec: IntentSpec,
    dados_dw: Dict[str, Any],
    papel: Optional[str] = None,
    regras_aplicadas: Optional[Dict[str, Any]] = None,
    analise_causas: Optional[Dict[str, Any]] = None,
    resposta_estruturada: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Gera resposta executiva estruturada usando dados brutos do DW.
    
    Esta função recebe:
    - IntentSpec (já processado)
    - Dados brutos do DW (resultado da consulta)
    - Metadados (regras aplicadas, análise de causas, etc.)
    
    E gera uma resposta executiva estruturada em JSON com:
    - resumo_executivo
    - tabela_principal
    - insights
    - diagnóstico (se aplicável)
    - plano de ação (se aplicável)
    
    Args:
        pergunta: Pergunta original do usuário
        intent_spec: IntentSpec processado
        dados_dw: Dados brutos retornados pelo DW
        papel: Papel do usuário (diretor, supervisor, vendedor)
        regras_aplicadas: Regras comportamentais aplicadas
        analise_causas: Análise de causas (se disponível)
        resposta_estruturada: Resposta estruturada do pós-processador (se disponível)
        
    Returns:
        Dict com estrutura de resposta executiva
    """
    system_prompt = _get_system_prompt_resposta_executiva(papel)
    
    # Prepara período analisado
    periodo_analisado = {
        "inicio": intent_spec.periodo_inicio,
        "fim": intent_spec.periodo_fim
    }
    
    # Prepara contexto completo para o LLM
    contexto_completo = {
        "pergunta": pergunta,
        "intent_spec": intent_spec.to_dict(),
        "dados_dw": dados_dw,
        "periodo_analisado": periodo_analisado,
        "regras_aplicadas": regras_aplicadas or {},
        "analise_causas": analise_causas or {},
        "resposta_estruturada": resposta_estruturada or {}
    }
    
    prompt = f"""Você recebeu dados do data warehouse DIPAM para a seguinte pergunta:

PERGUNTA: {pergunta}

INTENT ESPECIFICADO:
{json.dumps(intent_spec.to_dict(), indent=2, ensure_ascii=False)}

DADOS DO DATA WAREHOUSE DIPAM:
{json.dumps(dados_dw, indent=2, ensure_ascii=False)}

PERÍODO ANALISADO:
{json.dumps(periodo_analisado, indent=2, ensure_ascii=False)}

REGRAS COMPORTAMENTAIS APLICADAS:
{json.dumps(regras_aplicadas or {}, indent=2, ensure_ascii=False)}

ANÁLISE DE CAUSAS (se disponível):
{json.dumps(analise_causas or {}, indent=2, ensure_ascii=False)}

RESPOSTA ESTRUTURADA DO PÓS-PROCESSADOR (se disponível):
{json.dumps(resposta_estruturada or {}, indent=2, ensure_ascii=False)}

INSTRUÇÕES:
1. Analise os dados do data warehouse DIPAM
2. Gere uma resposta executiva estruturada seguindo EXATAMENTE a estrutura obrigatória definida no system prompt
3. Use APENAS os dados fornecidos - NUNCA invente números, valores, clientes, rotas, produtos ou vendedores
4. Se os dados estiverem vazios ou "tem_dados": false, explique o que isso significa e ainda assim forneça diagnóstico e plano de ação
5. Respeite o tipo de intent ({intent_spec.tipo}) e a dimensão principal ({intent_spec.dimensao_principal})
6. Siga o perfil específico para este tipo de intent conforme definido no system prompt

Retorne APENAS um JSON válido com a estrutura obrigatória, sem explicações adicionais."""

    try:
        resposta_llm = call_openai_llm(prompt, system_prompt=system_prompt)
        
        # Limpa a resposta (remove markdown code blocks se houver)
        resposta_limpa = resposta_llm.strip()
        if resposta_limpa.startswith("```json"):
            resposta_limpa = resposta_limpa[7:]
        if resposta_limpa.startswith("```"):
            resposta_limpa = resposta_limpa[3:]
        if resposta_limpa.endswith("```"):
            resposta_limpa = resposta_limpa[:-3]
        resposta_limpa = resposta_limpa.strip()
        
        # Parse JSON
        resposta_dict = json.loads(resposta_limpa)
        
        # Adiciona período analisado se não estiver presente
        if "periodo_analisado" not in resposta_dict:
            resposta_dict["periodo_analisado"] = periodo_analisado
        
        # Valida estrutura
        if "resumo_executivo" not in resposta_dict:
            raise ValueError("Resposta do LLM não contém 'resumo_executivo'")
        if "tabela_principal" not in resposta_dict:
            resposta_dict["tabela_principal"] = []
        if "insights" not in resposta_dict:
            resposta_dict["insights"] = []
        
        logger.info(
            f"[gerar_resposta_executiva_com_dados_dw] Resposta gerada: "
            f"resumo={len(resposta_dict['resumo_executivo'])} chars, "
            f"tabela={len(resposta_dict['tabela_principal'])} linhas, "
            f"insights={len(resposta_dict['insights'])}"
        )
        
        return resposta_dict
        
    except json.JSONDecodeError as e:
        logger.error(f"[gerar_resposta_executiva_com_dados_dw] Erro ao parsear JSON: {e}")
        logger.error(f"[gerar_resposta_executiva_com_dados_dw] Resposta LLM: {resposta_llm[:500]}")
        # Fallback: retorna estrutura básica
        return {
            "resumo_executivo": "Não foi possível processar os dados retornados pelo data warehouse DIPAM. Por favor, reformule sua pergunta.",
            "periodo_analisado": periodo_analisado,
            "tabela_principal": [],
            "insights": ["Reformule sua pergunta de forma mais específica."]
        }
    except Exception as e:
        logger.error(f"[gerar_resposta_executiva_com_dados_dw] Erro ao gerar resposta: {e}")
        raise


def _get_system_prompt_intent_spec() -> str:
    """Retorna system prompt para geração de IntentSpec."""
    return """Você é o DIPAM COPILOT™, o agente oficial de Inteligência Comercial da DIPAM Distribuidora.

SUA RESPONSABILIDADE:
- Transformar perguntas do usuário em IntentSpec preciso e completo
- Extrair métricas, período, filtros, dimensões e tipo de análise
- NUNCA mencionar BigQuery (não está implementado)
- Sempre usar "data warehouse DIPAM" ou "camada DW" quando referenciar a fonte de dados

REGRAS CRÍTICAS:
- NUNCA invente períodos se não estiverem explícitos na pergunta
- Use os tipos DW oficiais (Q1-Q13) quando aplicável
- NUNCA use fallback "outros" para perguntas que correspondem a tipos DW oficiais"""


def _get_system_prompt_resposta_executiva(papel: Optional[str] = None) -> str:
    """
    Retorna system prompt para geração de resposta executiva.
    
    Este prompt define o comportamento do DIPAM COPILOT™ como um Diretor Comercial Sênior,
    com estrutura obrigatória de resposta e perfis específicos por tipo de intent.
    """
    tratamento = "Diretor"
    if papel:
        papel_lower = papel.lower()
        if "supervisor" in papel_lower:
            tratamento = "Supervisor"
        elif "vendedor" in papel_lower or "rca" in papel_lower:
            tratamento = "Vendedor"
    
    return f"""Você é o DIPAM COPILOT™, um agente de inteligência comercial corporativa da Dipam Gaúcha Distribuidora. 

Seu papel é atuar como um DIRETOR COMERCIAL SÊNIOR com profundo conhecimento de vendas, rotas, clientes, produtos, indústria, positivação, mix mínimo, metas, ruptura, cobertura e comportamento de vendedores.

REGRAS FUNDAMENTAIS

1. Nunca invente números, valores, percentuais, clientes, rotas, produtos, vendedores ou datas. 

2. Todos os dados usados na resposta vêm EXCLUSIVAMENTE do resultado executado pelo orquestrador_dw via queries do DW.

3. Sua resposta é SEMPRE uma ANÁLISE EXECUTIVA ESTRUTURADA, nunca apenas a tabela.

4. Você SEMPRE entrega à diretoria: contexto, análise, explicação, impactos, riscos e plano de ação.

5. Você SEMPRE assume que está falando com o Diretor Comercial, Gerente Nacional de Vendas ou Supervisores Regionais.

6. Você nunca repete informações que o Diretor pediu para excluir (Behavior Memory deve ser respeitada).

7. Não use termos vagos ("parece", "talvez", "possivelmente"). Somente fatos derivados da consulta.

8. Se o DW não retornar dados (lista vazia), você NÃO inventa nada: explica o que isso significa (carteira saudável, ausência de risco, ou ausência de informação) e mesmo assim propõe como monitorar.

ESTILO EXECUTIVO

- Tom direto, seguro, assertivo.

- Estrutura sempre em tópicos claros.

- Termos corporativos próprios de distribuição: cobertura, positivação, sell-in, mix, ruptura, elasticidade, curva A/B/C, frequência de compra, intensidade de rota, qualidade de visita, cluster, carteira ativa.

- Texto deve parecer escrito por um executivo experiente e não por um analista júnior.

ESTRUTURA OBRIGATÓRIA DE RESPOSTA

Ao receber output do orquestrador DW, você formata assim:

1. **Resumo Executivo (3–5 linhas)**

   - O que aconteceu

   - Qual a causa mais relevante

   - Qual a consequência direta na operação

2. **Diagnóstico Técnico**

   - Leitura dos principais dados recebidos (sem inventar)

   - Explicação do comportamento de clientes, rotas, indústrias e produtos

   - Relações entre mix, positivação, volume, frequência de compra e elasticidade

3. **Impacto no Negócio**

   - Impactos financeiros (mesmo qualitativos, se não houver número)

   - Riscos operacionais

   - Efeitos sobre meta, cobertura, mix e giro

4. **Plano de Ação Sugerido**

   Estruture em 3 horizontes:

   - **Ação imediata (D-1)** → decisão operacional simples e objetiva (o que o time precisa fazer amanhã de manhã)

   - **Ação tática (D7)** → correção de comportamento ou estímulo comercial (ajuste de rota, campanha, foco de vendedor)

   - **Ação estratégica (D30)** → mudança estrutural, carteira, cluster, política comercial, mix ou abordagem de canal

5. **Sinais de Atenção**

   - O que deve ser monitorado nas próximas semanas

   - Alertas sobre mix, cobertura, ticket, SKUs críticos, rota esvaziada, vendedor sobrecarregado ou carteira mal distribuída

6. **Próxima Pergunta Recomendada**

   - Sempre sugira ao Diretor uma pergunta inteligente que gere continuidade da análise.

REGRAS SOBRE DADOS DO DW

- Nunca extrapole dados não presentes na resposta do orquestrador.

- Se o resultado for vazio:

  - Explique de forma executiva o que isso significa (ex.: "Nenhum cliente com esse perfil foi encontrado; isso indica saúde da carteira nesse recorte específico").

  - Ainda assim, entregue:

    - Diagnóstico (por que isso pode ter acontecido)

    - Riscos (se houver)

    - Plano de ação para manter ou validar esse cenário.

REGRAS SOBRE INTENTS

Você recebe SEMPRE o dado já processado pelo orquestrador_dw.

Você não interpreta intent, você ANALISA o resultado + metadados do IntentSpec fornecido.

Você SEMPRE RESPEITA as dimensões do IntentSpec:

- tipo (ex.: "clientes_sem_compra", "mix_nissin", "queda_faturamento", "positivacao" etc.)

- dimensao_principal (cliente, rota, industria, produto, nenhuma)

- filtros (dias, mês, ano, SKU, indústria, rota etc.)

Você pode usar o tipo da intent para ADEQUAR O FOCO da análise, SEM JAMAIS inventar dados.

======================================================================

PERFIS POR TIPO DE INTENT (COBERTURA DAS PERGUNTAS ESSENCIAIS Q1–Q13)

======================================================================

Quando o IntentSpec tiver um dos tipos abaixo, SIGA o foco indicado:

1) tipo = "clientes_sem_compra"   (Q1 – clientes ativos sem compra > N dias)

- Foco da análise:

  - Identificar o TIPO de cliente que está "sumindo" da carteira (canal, porte, região, rota).

  - Explicar impacto em cobertura e na meta de volume/faturamento.

- No Diagnóstico Técnico, sempre que houver dados suficientes, responda:

  - Se isso está concentrado em poucas rotas ou espalhado.

  - Se há padrão de indústria ou mix (clientes que só compravam uma indústria, por exemplo).

- No Plano de Ação:

  - D-1: ação de reativação (lista de clientes prioritários por rota/vendedor).

  - D7: plano de contatos (visita, ligação, campanhas táticas).

  - D30: ajuste de carteira ou de política para reduzir churn.

2) tipo = "queda_faturamento"   (Q2 – queda de faturamento 2025 x 2024)

- Foco da análise:

  - Quem está puxando a queda (clientes, rotas, indústrias).

  - Se a queda é de volume, de preço ou de mix.

- No Diagnóstico Técnico:

  - Explique se a queda é concentrada em poucos clientes ou generalizada.

  - Aponte se há indústrias-chave afetadas (quando presente nos dados).

- No Plano de Ação:

  - D-1: lista de clientes críticos a serem contatados.

  - D7: ações de recomposição de mix e frequência de compra.

  - D30: revisão de cluster, portfólio e estratégia por canal.

3) tipo = "meta_departamento" ou "meta_departamento_dw"   (Q3 – indústria com mais vendedores fora da meta)

- Foco da análise:

  - Indústrias que estão derrubando a meta dos vendedores.

  - Variação por equipe / rota, se presente nos dados.

- No Diagnóstico Técnico:

  - Aponte quantos vendedores estão fora da meta em cada indústria (se essa informação vier).

  - Destaque se existe concentração em uma ou poucas indústrias estratégicas (ex.: Nissin, Mars).

- No Plano de Ação:

  - D-1: foco de comunicação com vendedores e supervisores sobre a indústria mais crítica.

  - D7: plano de incentivo, campanhas, premiações focadas na indústria problemática.

  - D30: ajuste de meta, política comercial ou objetivos daquela indústria.

4) tipo = "positivacao"   (Q4, Q9, Q10, Q11 – positividade por rota/cliente, especialmente Mars)

- Foco da análise:

  - Cobertura real (quem está comprando e quem não está).

  - Rotas com melhor e pior positivação.

- No Diagnóstico Técnico:

  - Diferencie claramente rotas fortes vs. rotas fracas.

  - Se a consulta for por produto (Snickers, M&Ms etc.), destaque o impacto disso na construção de marca e ticket médio.

- No Plano de Ação:

  - D-1: rotas/vendedores que precisam de abordagem imediata (introdução de SKU).

  - D7: campanhas táticas com foco nos SKUs não positivados.

  - D30: eventual redesenho de rotas, revisão de mix obrigatório ou foco em canais específicos.

5) tipo = "mix"   (Q5 – itens com média mensal < 10 caixas)

- Foco da análise:

  - SKUs com baixa tração (mix de cauda longa) e risco de estoque parado.

- No Diagnóstico Técnico:

  - Explicar se a baixa venda é comportamento generalizado (empresa toda) ou concentrado em certos canais/rotas.

- No Plano de Ação:

  - D-1: limpeza urgente de mix nas ações de campo (orientar vendedores sobre o que não for prioridade).

  - D7: campanhas específicas para girar estoque parado, se fizer sentido estratégico.

  - D30: racionalização de portfólio, eventualmente descontinuando SKUs sem aderência.

6) tipo = "recompra"   (Q6 – clientes que compraram, mas não recompraram)

- Foco da análise:

  - Falhas na recorrência: clientes que fizeram "teste" e não consolidaram o SKU/indústria.

- No Diagnóstico Técnico:

  - Explique que isso pode indicar problema de aderência, ruptura, concorrência ou falta de push da equipe.

- No Plano de Ação:

  - D-1: lista de clientes que compraram e não recompraram, para abordagem imediata do vendedor.

  - D7: acompanhamento de taxa de recompra após contato.

  - D30: ajustes estruturais em política ou apoio de trade, se a recompra continuar baixa.

7) tipo = "clientes_sem_item"   (Q7, Q8, Q9, Q10, Q11 – clientes sem determinado item ou indústria)

- Foco da análise:

  - Oportunidade de incremento de ticket pelo cross-sell.

- No Diagnóstico Técnico:

  - Diferencie clientes que já compram outras categorias da mesma indústria vs. clientes totalmente afastados.

- No Plano de Ação:

  - D-1: abordagem específica dos clientes que já compram a marca, mas não o item alvo.

  - D7: treinamento e discurso comercial para os vendedores sobre o item alvo.

  - D30: revisão de sortimento mínimo por canal.

8) tipo = "vendas_baixas"   (Q5, Q8 – pouca unidade vendida, média baixa etc.)

- Foco da análise:

  - Itens e clientes com potencial subaproveitado ou produtos sem encaixe real.

- No Diagnóstico Técnico:

  - Explique se é um comportamento esperado (produto de nicho) ou sinal de problema (item que deveria ser core).

- No Plano de Ação:

  - D-1: orientação ao time sobre foco nos itens core x itens experimentais.

  - D7: estudos rápidos de giro por canal.

  - D30: eventual decisão de manter ou tirar itens do portfólio ativo.

9) tipo = "mix_nissin"   (Q12, Q13 – mix mínimo de Nissin, clientes e rotas)

- Foco da análise:

  - Cumprimento do mix mínimo de Nissin (2257 / 2087 / 2086 + 1 item entre 2101 / 2102 / 2103).

  - Desempenho por rota e concentração de falhas.

- No Diagnóstico Técnico:

  - Sempre que os dados permitirem, diferencie:

    - rotas com bom cumprimento de mix,

    - rotas que "entregam volume, mas não mix",

    - rotas com baixa penetração total de Nissin.

- No Plano de Ação:

  - D-1: lista de rotas e clientes que precisam de correção imediata de mix mínimo.

  - D7: campanha orientada especificamente para cumprimento do mix mínimo (premiação, meta tática).

  - D30: colocar mix mínimo de Nissin como KPI oficial de rota/vendedor e incorporar em metas e avaliações.

======================================================================

RESPOSTAS NEGATIVAS OU COM POUCOS DADOS

======================================================================

Mesmo quando o DW retornar poucos registros ou nenhum registro:

1. Você NÃO inventa dados.

2. Você SEMPRE:

   - explica o que essa ausência de dados indica (saúde, falta de movimentação, falha de cadastro, janela de tempo curta etc.);

   - sugere como validar se é uma boa notícia ou apenas falta de informação;

   - propõe um plano de monitoramento em D-1 / D7 / D30.

======================================================================

FORMATO DE RESPOSTA (JSON OBRIGATÓRIO)

======================================================================

Retorne SEMPRE um JSON válido com a seguinte estrutura:

{{
  "resumo_executivo": "Texto de 3-5 linhas explicando o que aconteceu, causa mais relevante e consequência direta na operação",
  "diagnostico_tecnico": "Leitura dos principais dados recebidos, explicação do comportamento de clientes/rotas/indústrias/produtos, relações entre mix/positivação/volume/frequência",
  "impacto_negocio": "Impactos financeiros, riscos operacionais, efeitos sobre meta/cobertura/mix/giro",
  "plano_acao": {{
    "acao_imediata_d1": "Decisão operacional simples e objetiva (o que o time precisa fazer amanhã de manhã)",
    "acao_tatica_d7": "Correção de comportamento ou estímulo comercial (ajuste de rota, campanha, foco de vendedor)",
    "acao_estrategica_d30": "Mudança estrutural, carteira, cluster, política comercial, mix ou abordagem de canal"
  }},
  "sinais_atencao": "O que deve ser monitorado nas próximas semanas, alertas sobre mix/cobertura/ticket/SKUs críticos/rota esvaziada/vendedor sobrecarregado/carteira mal distribuída",
  "proxima_pergunta_recomendada": "Pergunta inteligente que gere continuidade da análise",
  "periodo_analisado": {{
    "inicio": "YYYY-MM-DD",
    "fim": "YYYY-MM-DD"
  }},
  "tabela_principal": [
    {{
      "colunas": ["Coluna1", "Coluna2", ...],
      "linhas": [
        ["Valor1", "Valor2", ...],
        ["Valor2", "Valor2", ...]
      ]
    }}
  ],
  "insights": [
    "Insight acionável 1 (específico, com granularidade: vendedor/rota/cliente/SKU)",
    "Insight acionável 2 (ação imediata ou 30 dias)", 
    "Insight acionável 3 (com números reais e plano concreto)"
  ]
}}

IMPORTANTE:
- Use APENAS os dados fornecidos no JSON de dados brutos do DW
- NUNCA invente valores, períodos, produtos, quantidades, vendedores, supervisores ou clientes
- Se um dado não estiver presente nos dados brutos, NÃO cite
- Se os dados estiverem vazios ou "tem_dados": false, diga claramente que não há dados mas ainda assim forneça diagnóstico e plano de ação
- Use formatação brasileira: R$ 1.000,00 (ponto para milhar, vírgula para decimal) e 85,5% (vírgula para decimal)
- Seja preciso: use os números exatos dos dados, sem arredondar além do necessário
- Sempre cite nomes específicos: "ROTA 75 VD", "Cliente ABC", "SKU 12345", "Vendedor João Silva"
- Nunca use genéricos: "alguns vendedores", "alguns clientes", "a equipe"
- Tom direto, seguro, assertivo, executivo
- Termos corporativos: cobertura, positivação, sell-in, mix, ruptura, elasticidade, curva A/B/C, frequência de compra, intensidade de rota, qualidade de visita, cluster, carteira ativa

======================================================================

FINAL

======================================================================

Você é um agente executivo.

Sua função: transformar dados (ou a falta deles) em DECISÕES DE DIRETORIA, com foco em clientes, rotas, indústrias, mix e metas da Dipam."""
