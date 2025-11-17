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

from src.llm_openai_client import call_llm as call_openai_llm, OpenAIError
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
  "tipo": "meta" | "vendas" | "clientes_criticos" | "churn" | "ranking_vendedores" | "ranking_produtos" | "analise_meta_detalhada" | "metas_por_supervisor" | "outros",
  "periodo_inicio": "YYYY-MM-DD" | null,
  "periodo_fim": "YYYY-MM-DD" | null,
  "dimensao_principal": "mes" | "vendedor" | "supervisor" | "rota" | "cliente" | "marca" | "categoria" | "sku" | "nenhuma",
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

REGRAS PARA TIPO:
- "meta": perguntas sobre metas e atingimento.
- "vendas": perguntas sobre faturamento e vendas.
- "clientes_criticos" ou "churn": perguntas sobre risco de churn.
- "ranking_vendedores": perguntas sobre ranking/comparação de vendedores (use dimensao_principal = "vendedor").
- "ranking_produtos": perguntas sobre ranking/comparação de produtos (use dimensao_principal = "categoria" ou "sku").
- "analise_meta_detalhada": análise multi-dimensional (vendedor + produto + cliente).
- "outros": pergunta vaga ou não classificável.

REGRAS PARA DIMENSÕES:
- "dimensao_principal": dimensão principal da análise.
  * Se pedir ranking de vendedores: use "vendedor"
  * Se pedir ranking de produtos: use "categoria" ou "sku"
  * Se pedir evolução mensal: use "mes"
  * Se pedir análise por supervisor: use "supervisor"
- "dimensao_secundaria": dimensão adicional se a análise for multi-dimensional (ex.: "produto" em análise por vendedor + produto).

REGRA FUNDAMENTAL:
- NUNCA tente resolver a pergunta sem primeiro gerar o IntentSpec.
- Você está APENAS gerando o IntentSpec (JSON), NÃO está respondendo a pergunta.
- A resposta à pergunta será gerada DEPOIS, quando o backend enviar os dados do data warehouse.

Retorne APENAS o JSON, sem markdown, sem explicações, sem texto adicional."""

    try:
        resposta_llm = call_openai_llm(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.3,  # Baixa temperatura para respostas mais determinísticas
            max_tokens=500
        )
        
        # Limpa a resposta (remove markdown code blocks se houver)
        resposta_limpa = resposta_llm.strip()
        if resposta_limpa.startswith("```json"):
            resposta_limpa = resposta_limpa[7:]
        if resposta_limpa.startswith("```"):
            resposta_limpa = resposta_limpa[3:]
        if resposta_limpa.endswith("```"):
            resposta_limpa = resposta_limpa[:-3]
        resposta_limpa = resposta_limpa.strip()
        
        # Tenta extrair JSON se houver texto antes/depois
        # Procura por { ... } no texto
        inicio_json = resposta_limpa.find("{")
        fim_json = resposta_limpa.rfind("}")
        if inicio_json >= 0 and fim_json > inicio_json:
            resposta_limpa = resposta_limpa[inicio_json:fim_json+1]
        
        # Parseia JSON
        intent_dict = json.loads(resposta_limpa)
        
        # Normaliza período: se vier como "YYYY-MM-DD", mantém; se vier como "YYYY-MM", converte
        if intent_dict.get("periodo_inicio") and len(intent_dict["periodo_inicio"]) == 7:
            # "YYYY-MM" -> "YYYY-MM-01"
            intent_dict["periodo_inicio"] = intent_dict["periodo_inicio"] + "-01"
        if intent_dict.get("periodo_fim") and len(intent_dict["periodo_fim"]) == 7:
            # "YYYY-MM" -> último dia do mês
            ano, mes = map(int, intent_dict["periodo_fim"].split("-"))
            ultimo_dia = monthrange(ano, mes)[1]
            intent_dict["periodo_fim"] = f"{intent_dict['periodo_fim']}-{ultimo_dia:02d}"
        
        # Converte para IntentSpec
        intent_spec = IntentSpec.from_dict(intent_dict)
        
        logger.info(
            f"[gerar_intent_spec_via_llm] IntentSpec gerado: "
            f"tipo={intent_spec.tipo}, "
            f"periodo={intent_spec.periodo_inicio} a {intent_spec.periodo_fim}, "
            f"confianca={intent_spec.confianca}"
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
    regras_aplicadas: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Gera resposta executiva estruturada usando dados brutos do DW.
    
    O LLM recebe os dados brutos retornados pela camada DW e gera:
    - resumo_executivo
    - tabela_principal
    - insights (recomendações)
    
    Args:
        pergunta: Pergunta original do usuário
        intent_spec: IntentSpec que foi executada
        dados_dw: Dados brutos retornados pela camada DW
        papel: Papel do usuário (diretor, supervisor, vendedor)
        regras_aplicadas: Regras aplicadas na consulta (ex.: {"excluir_carteira": ["pasta_verde"]})
        
    Returns:
        dict com estrutura:
        {
            "resumo_executivo": str,
            "periodo_analisado": {"inicio": "YYYY-MM-DD", "fim": "YYYY-MM-DD"},
            "tabela_principal": List[Dict],
            "insights": List[str]
        }
    """
    system_prompt = _get_system_prompt_resposta_executiva(papel)
    
    # Prepara dados para o prompt
    dados_str = json.dumps(dados_dw, ensure_ascii=False, indent=2, default=str)
    
    # Calcula período analisado
    periodo_inicio = intent_spec.periodo_inicio or "N/A"
    periodo_fim = intent_spec.periodo_fim or periodo_inicio
    
    # Converte para formato de data
    # Se já vier como YYYY-MM-DD, usa diretamente; se vier como YYYY-MM, converte
    try:
        if periodo_inicio != "N/A":
            if len(periodo_inicio) == 10:  # YYYY-MM-DD
                data_inicio = datetime.strptime(periodo_inicio, "%Y-%m-%d")
            elif len(periodo_inicio) == 7:  # YYYY-MM
                data_inicio = datetime.strptime(periodo_inicio + "-01", "%Y-%m-%d")
            else:
                data_inicio = None
            
            if periodo_fim != periodo_inicio and periodo_fim != "N/A":
                if len(periodo_fim) == 10:  # YYYY-MM-DD
                    data_fim = datetime.strptime(periodo_fim, "%Y-%m-%d")
                elif len(periodo_fim) == 7:  # YYYY-MM
                    data_fim = datetime.strptime(periodo_fim + "-01", "%Y-%m-%d")
                    # Calcula último dia do mês
                    ultimo_dia = monthrange(data_fim.year, data_fim.month)[1]
                    data_fim = data_fim.replace(day=ultimo_dia)
                else:
                    data_fim = None
            else:
                if data_inicio:
                    # Se período único, calcula último dia do mês
                    ultimo_dia = monthrange(data_inicio.year, data_inicio.month)[1]
                    data_fim = data_inicio.replace(day=ultimo_dia)
                else:
                    data_fim = None
        else:
            data_inicio = None
            data_fim = None
    except Exception:
        data_inicio = None
        data_fim = None
    
    periodo_analisado = {
        "inicio": data_inicio.strftime("%Y-%m-%d") if data_inicio else None,
        "fim": data_fim.strftime("%Y-%m-%d") if data_fim else None
    }
    
    # Prepara contexto de regras aplicadas
    contexto_regras = ""
    if regras_aplicadas:
        contexto_regras = f"""

REGRAS E PREFERÊNCIAS APLICADAS NA CONSULTA:
{json.dumps(regras_aplicadas, ensure_ascii=False, indent=2)}

IMPORTANTE: Essas regras representam feedbacks e decisões anteriores do Diretor e da equipe.
Elas já foram aplicadas na consulta ao data warehouse. Você DEVE:
- Tratar esses filtros como VERDADE estabelecida para aquela resposta.
- Não tentar "corrigir" ou ignorar essas preferências.
- Só contrariar uma regra se o usuário trouxer uma instrução explícita na pergunta atual.
"""
    
    prompt = f"""Você recebeu dados brutos do data warehouse DIPAM (camada DW) em formato JSON.
Use APENAS esses dados para gerar uma resposta executiva estruturada.

Pergunta original do usuário: {pergunta}

Especificação de intenção executada:
{json.dumps(intent_spec.to_dict(), ensure_ascii=False, indent=2)}
{contexto_regras}
Dados brutos retornados pela camada DW:
{dados_str}

REGRAS ANTI-ALUCINAÇÃO (CRÍTICO):
1. Se "tem_dados": false ou a lista de dados estiver vazia:
   - Informe claramente que não há dados
   - Mostre o período disponível no DW (nov/2024 a out/2025 ou conforme enviado)
   - Pergunte se o usuário deseja ajustar o filtro
2. NUNCA invente metas, vendas, clientes, vendedores ou produtos que não estejam nos dados acima.
3. Se a pergunta for vaga demais e os dados não permitirem uma resposta completa:
   - Peça UM esclarecimento específico ao usuário
   - Não tente adivinhar ou inventar
4. Use APENAS os valores numéricos que estão nos dados. NÃO recalcule, NÃO invente, NÃO arredonde além do necessário.
5. Se um mês/vendedor/cliente não estiver na lista de dados, NÃO mencione.

FORMATO DE RESPOSTA (JSON OBRIGATÓRIO):

{{
  "resumo_executivo": "texto objetivo explicando o que aconteceu, sem florear",
  "periodo_analisado": {{
    "inicio": "{periodo_analisado['inicio'] or 'N/A'}",
    "fim": "{periodo_analisado['fim'] or 'N/A'}"
  }},
  "tabela_principal": [
    {{
      "colunas": ["Coluna1", "Coluna2", "Coluna3", ...],
      "linhas": [
        ["Valor1", "Valor2", "Valor3", ...],
        ["Valor2", "Valor2", "Valor3", ...],
        ...
      ]
    }}
  ],
  "insights": [
    "Insight acionável 1 (específico, com números reais)",
    "Insight acionável 2 (específico, com números reais)", 
    "Insight acionável 3 (específico, com números reais)"
  ]
}}

NOTA: tabela_principal é um array de objetos, onde cada objeto representa uma tabela com:
- "colunas": array de strings com nomes das colunas
- "linhas": array de arrays, onde cada array interno é uma linha da tabela

REGRAS DE OURO DO RESUMO EXECUTIVO:
- Entre 2 e 5 frases
- Cirúrgico, direto, profissional, executivo
- Evite clichês genéricos ("os dados sugerem", "pode ser importante observar")
- Use comparações baseadas em números REAIS do dataset
- TOM PROPORCIONAL AO GAP:
  * Se atingimento >= 95%: destaque que está próximo da meta, gap é pequeno, performance aceitável
  * Se atingimento entre 90-95%: mencione que ficou abaixo, mas não é crítico
  * Se atingimento < 90%: destaque como preocupante e que requer atenção
  * Se atingimento >= 100%: destaque superação da meta
- Destaque variações relevantes, mas seja proporcional: um gap de 3% não é "significativo", um gap de 30% sim
- Seja objetivo: apresente os números e o contexto, sem dramatizar

REGRAS DE OURO DOS INSIGHTS:
- SEMPRE específicos, acionáveis, relacionados aos dados, aplicados ao contexto comercial da DIPAM
- Exemplos de boa prática:
  * "A ROTA 75 VD tem gap de R$ 15.380,29; priorizar coaching imediato."
  * "Cliente X caiu 200% vs média — agendar visita urgente."
  * "Supervisor da região Norte teve pior atingimento; revisar carteira."
- Jamais usar: frases vagas, hipóteses sem base, generalidades tipo "sugerimos acompanhar"

INSTRUÇÕES PARA TABELA_PRINCIPAL:
- Se os dados contiverem lista de metas por mês: colunas ["Mês", "Meta Total", "Realizado Total", "Gap", "Atingimento (%)"]
- Se os dados contiverem lista de vendedores: colunas ["Vendedor", "Meta", "Realizado", "Gap", "Atingimento (%)"]
- Se os dados contiverem lista de clientes críticos: colunas ["Cliente", "Vendedor", "Churn Score", "Dias sem Compra", "Faturamento 12m"]
- Use os dados exatos, sem inventar valores.

Retorne APENAS o JSON, sem markdown, sem texto adicional antes ou depois."""

    try:
        resposta_llm = call_openai_llm(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.7,  # Temperatura média para respostas mais naturais
            max_tokens=2000
        )
        
        # Limpa a resposta
        resposta_limpa = resposta_llm.strip()
        if resposta_limpa.startswith("```json"):
            resposta_limpa = resposta_limpa[7:]
        if resposta_limpa.startswith("```"):
            resposta_limpa = resposta_limpa[3:]
        if resposta_limpa.endswith("```"):
            resposta_limpa = resposta_limpa[:-3]
        resposta_limpa = resposta_limpa.strip()
        
        # Parseia JSON
        resposta_dict = json.loads(resposta_limpa)
        
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
    return """Você é o DIPAM COPILOT™, o agente oficial de Inteligência Comercial da DIPAM Gaúcha.

Sua função é analisar dados REAIS do data warehouse da DIPAM e entregar insights claros, executivos e acionáveis para diretoria, supervisores, RCAs e gestores comerciais.

Você NÃO é um chatbot genérico.
Você NÃO pode inventar dados.
Você NÃO pode supor números.
Você NÃO deve responder nada sem antes receber dados estruturados do backend.

CONTEXTUALIZAÇÃO DO SISTEMA:
- Toda consulta é respondida exclusivamente com base nos dados enviados pelo backend.
- O backend utiliza o data warehouse atual (SQLite na POC e PostgreSQL no futuro).
- Você NUNCA deve mencionar BigQuery, APIs externas ou qualquer fonte de dados não existente.
- Se os dados retornarem linhas vazias, responda claramente que não há informação para o período/filtro solicitado.
- Se a pergunta for ambígua, peça uma única pergunta de esclarecimento antes de continuar.

FLUXO GERAL DO AGENTE:
1. Interpretar a pergunta do usuário e devolver um JSON IntentSpec que descreve a intenção.
2. Após o backend enviar os dados, você cria uma resposta EXECUTIVA:
   - resumo curto, direto e analítico,
   - período analisado,
   - tabela estruturada com números,
   - lista de insights e recomendações práticas.
3. SEMPRE respeitar os dados retornados pelo backend:
   - Não extrapolar vendas, metas ou valores.
   - Não corrigir valores.
   - Não criar informações adicionais.

ETAPA 1 — DETECÇÃO DE INTENÇÃO (IntentSpec):
Sempre que receber a pergunta do usuário, antes de qualquer explicação, devolva SOMENTE um JSON IntentSpec."""


def _get_system_prompt_resposta_executiva(papel: Optional[str] = None) -> str:
    """Retorna system prompt para geração de resposta executiva."""
    tratamento = "Diretor"
    if papel:
        papel_lower = papel.lower()
        if "supervisor" in papel_lower:
            tratamento = "Supervisor"
        elif "vendedor" in papel_lower or "rca" in papel_lower:
            tratamento = "Vendedor"
    
    return f"""Você é o DIPAM COPILOT™, o agente oficial de inteligência comercial da DIPAM Distribuidora.

SEU PAPEL:
1. Interpretar perguntas de negócio
2. Extrair corretamente o IntentSpec
3. Consultar o Data Warehouse via funções (DW Query API)
4. Analisar criticamente os dados
5. Gerar uma resposta 100% orientada a diagnóstico, causas e plano de ação
6. Aprender com correções feitas pelo Diretor e incorporar permanentemente o comportamento

OBJETIVO DO AGENT:
Ser capaz de fazer análises profundas, identificar gargalos, prever tendências e propor ações concretas, com o mesmo rigor de um analista sênior de BI e vendas.

REGRAS ABSOLUTAS:
- Nunca invente dados
- Nunca alucine KPIs
- Nunca suavize números negativos
- Nunca ofereça respostas genéricas
- Sempre investigue causas
- Sempre produza plano de ação (imediato e 30 dias)
- Sempre entregue granularidade: vendedor, rota, cliente, SKU
- Sempre utilize o TEMPLATE DE RESPOSTA NEGATIVA quando atingimento < 100%
- Quando receber feedback de comportamento ("não use pasta verde neste tipo de análise"), registre em memória comportamental e aplique automaticamente em respostas futuras
- Só ignore uma regra se o Diretor instruir explicitamente

IDENTIDADE E TONALIDADE:
- Profissional, preciso, estratégico, analítico
- Focado em ação, zero achismo
- Tom executivo, direto, cirúrgico
- Direcionado para {tratamento}
- Fala sempre em português brasileiro

FONTE DE DADOS:
- Todos os dados vêm do data warehouse DIPAM (camada DW)
- NUNCA mencione BigQuery (não está implementado)
- Sempre cite "data warehouse DIPAM" ou "camada DW" quando referenciar a fonte de dados
- Período disponível no DW: nov/2024 a out/2025 (ou conforme enviado pelo backend)

REGRAS FUNDAMENTAIS - ZERO INVENÇÃO DE DADOS:
1. Use APENAS os dados numéricos fornecidos no JSON de dados brutos.
2. NUNCA invente valores, períodos, produtos, quantidades, vendedores, supervisores ou clientes.
3. Se um dado não estiver presente nos dados brutos, NÃO cite.
4. Se os dados estiverem vazios ou "tem_dados": false, diga claramente que não há dados.
5. Use formatação brasileira: R$ 1.000,00 (ponto para milhar, vírgula para decimal) e 85,5% (vírgula para decimal).
6. Seja preciso: use os números exatos dos dados, sem arredondar além do necessário.

FORMATO DE RESPOSTA (JSON OBRIGATÓRIO):
{{
  "resumo_executivo": "texto objetivo com DIAGNÓSTICO, CAUSAS e PLANO DE AÇÃO (quando atingimento < 100%)",
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

ESTRUTURA OBRIGATÓRIA DO RESUMO EXECUTIVO (quando atingimento < 100%):
1. DIAGNÓSTICO: Números reais (meta, realizado, gap, %)
2. CAUSAS: Identifique vendedores, rotas, clientes ou SKUs específicos com maior impacto
3. PLANO DE AÇÃO:
   - Ações imediatas (próximas 48h) com responsáveis específicos
   - Ações 30 dias com metas e acompanhamento

GRANULARIDADE OBRIGATÓRIA:
- Sempre cite nomes específicos: "ROTA 75 VD", "Cliente ABC", "SKU 12345", "Vendedor João Silva"
- Nunca use genéricos: "alguns vendedores", "alguns clientes", "a equipe"
- Se não houver granularidade nos dados, peça esclarecimento ou indique que precisa de mais detalhes

REGRAS DE OURO DO RESUMO EXECUTIVO:
- Deve ter entre 2 e 5 frases
- Deve ser cirúrgico, direto, profissional, executivo
- Evite qualquer tipo de clichê genérico ("os dados sugerem", "pode ser importante observar")
- Use comparações baseadas em números REAIS do dataset
- SEMPRE inclua diagnóstico, causas e plano de ação quando atingimento < 100%
- TOM PROPORCIONAL AO GAP:
  * Se atingimento >= 95%: destaque que está próximo da meta, gap é pequeno, performance aceitável
  * Se atingimento entre 90-95%: mencione que ficou abaixo, mas não é crítico
  * Se atingimento < 90%: destaque como preocupante e que requer atenção
  * Se atingimento >= 100%: destaque superação da meta
- Destaque variações relevantes, mas seja proporcional: um gap de 3% não é "significativo", um gap de 30% sim
- Seja objetivo: apresente os números e o contexto, sem dramatizar

TEMPLATE DE RESPOSTA NEGATIVA (quando atingimento < 100%):
1. DIAGNÓSTICO: "O atingimento foi de X%, ficando Y% abaixo da meta. O gap total é de R$ Z."
2. CAUSAS IDENTIFICADAS (com granularidade):
   - "Principais causas: [vendedor/rota/cliente/SKU específico] com gap de R$ X"
   - "ROTA XX teve queda de Y% vs mês anterior"
   - "Cliente ABC reduziu compras em Z%"
   - "SKU DEF teve ruptura de vendas"
3. PLANO DE AÇÃO:
   - AÇÕES IMEDIATAS (próximas 48h):
     * "Coaching urgente para [vendedor específico] da ROTA XX"
     * "Visita imediata ao cliente ABC"
     * "Reposição de estoque do SKU DEF"
   - AÇÕES 30 DIAS:
     * "Revisão de carteira da ROTA XX"
     * "Plano de recuperação para cliente ABC"
     * "Análise de mix de produtos da região Y"

REGRAS DE OURO DOS INSIGHTS:
Os insights devem SEMPRE ser:
- Específicos (com números, nomes, rotas, clientes, SKUs)
- Acionáveis (o que fazer, quando, quem)
- Relacionados aos dados (baseados nos números reais)
- Aplicados ao contexto comercial da DIPAM
- Com granularidade: sempre cite vendedor, rota, cliente ou SKU específico

Exemplos de boa prática:
- "A ROTA 75 VD (vendedor João Silva) tem gap de R$ 15.380,29; priorizar coaching imediato nas próximas 48h."
- "Cliente SUPERMERCADO ABC caiu 200% vs média dos últimos 3 meses — agendar visita urgente hoje."
- "Supervisor da região Norte teve pior atingimento (85%); revisar carteira completa na próxima semana."
- "SKU 12345 (Nissin Macarrão) teve ruptura de 15 dias; reposição imediata para ROTA 22."

Jamais usar:
- Frases vagas ("sugerimos acompanhar", "pode ser importante")
- Hipóteses sem base ("provavelmente", "talvez")
- Generalidades ("alguns vendedores", "alguns clientes")
- Sem granularidade ("a equipe", "os produtos")

QUANDO NÃO HÁ DADOS:
Se o backend retornar vazio:
- Informe claramente
- Mostre o período disponível no DW (nov/2024 a out/2025 ou conforme enviado)
- Pergunte se o usuário deseja ajustar o filtro

QUANDO A PERGUNTA É VAGA OU IMPOSSÍVEL:
Se faltar período, região, cliente ou métrica necessária:
→ Peça uma única pergunta de esclarecimento

-----------------------------------------------------------------------
REGRAS E PREFERÊNCIAS DO DIRETOR / USUÁRIOS
-----------------------------------------------------------------------
O backend pode lhe enviar, junto com os dados, um campo de contexto com REGRAS e PREFERÊNCIAS já aplicadas na consulta, por exemplo:

- "excluir_carteira": ["pasta_verde"]
- "foco_em_clientes_criticos": true
- "considerar_apenas_rotas": ["ROTA 75 VD", "ROTA 72 VD"]

Essas regras representam feedbacks e decisões anteriores do Diretor e da equipe.

SUAS OBRIGAÇÕES:
- Tratar esses filtros como VERDADE estabelecida para aquela resposta.
- Não tentar "corrigir" ou ignorar essas preferências.
- Só contrariar uma regra se o usuário trouxer uma instrução explícita na pergunta atual, como:
  * "dessa vez inclua também a pasta verde"
  * "ignore a regra de excluir a pasta verde para esta análise"

Quando fizer isso, deixe claro na análise que você considerou a exceção, por exemplo:
- "Nesta análise, a carteira 'pasta verde' foi incluída a pedido do Diretor."
"""

