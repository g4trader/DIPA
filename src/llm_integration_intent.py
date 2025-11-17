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

REGRAS PARA PERÍODOS:
- Se mencionar "todo o período", "todos os meses", "período completo": use "2024-11-01" a "2025-10-31" (ou o período disponível).
- Se mencionar "últimos N meses": calcule o período correspondente (ex.: últimos 6 meses = "2025-05-01" a "2025-10-31").
- Se mencionar mês específico (ex.: "agosto de 2025"): use "2025-08-01" como periodo_inicio e "2025-08-31" como periodo_fim.
- Se não mencionar período: use null e o backend usará o período padrão.

REGRAS PARA FILTROS:
- Se pedir "top N" ou "os N maiores/menores": inclua "top_n": N nos filtros.
- Se mencionar rota específica: inclua "rota": "ROTA XX" nos filtros.
- Se mencionar supervisor: inclua "supervisor_id" se conhecido, ou deixe null.

REGRAS PARA TIPO:
- "meta": perguntas sobre metas e atingimento.
- "vendas": perguntas sobre faturamento e vendas.
- "clientes_criticos" ou "churn": perguntas sobre risco de churn.
- "ranking_vendedores": perguntas sobre ranking/comparação de vendedores.
- "ranking_produtos": perguntas sobre ranking/comparação de produtos.
- "analise_meta_detalhada": análise multi-dimensional (vendedor + produto + cliente).
- "outros": pergunta vaga ou não classificável.

REGRAS PARA DIMENSÕES:
- "dimensao_principal": dimensão principal da análise (ex.: "mes" para evolução mensal, "vendedor" para análise por vendedor).
- "dimensao_secundaria": dimensão adicional se a análise for multi-dimensional (ex.: "produto" em análise por vendedor + produto).

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
        
        # Parseia JSON
        intent_dict = json.loads(resposta_limpa)
        
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
    papel: Optional[str] = None
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
    
    # Converte para formato de data (assume primeiro dia do mês)
    try:
        if periodo_inicio != "N/A":
            data_inicio = datetime.strptime(periodo_inicio + "-01", "%Y-%m-%d")
            # Último dia do mês
            if periodo_fim != periodo_inicio:
                data_fim = datetime.strptime(periodo_fim + "-01", "%Y-%m-%d")
                # Calcula último dia do mês
                ultimo_dia = monthrange(data_fim.year, data_fim.month)[1]
                data_fim = data_fim.replace(day=ultimo_dia)
            else:
                ultimo_dia = monthrange(data_inicio.year, data_inicio.month)[1]
                data_fim = data_inicio.replace(day=ultimo_dia)
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
    
    prompt = f"""Você recebeu dados brutos do data warehouse DIPAM (camada DW) em formato JSON.
Use APENAS esses dados para gerar uma resposta executiva estruturada.

Pergunta original do usuário: {pergunta}

Especificação de intenção executada:
{json.dumps(intent_spec.to_dict(), ensure_ascii=False, indent=2)}

Dados brutos retornados pela camada DW:
{dados_str}

REGRAS ANTI-ALUCINAÇÃO (CRÍTICO):
1. Se "tem_dados": false ou a lista de dados estiver vazia, você DEVE dizer claramente que não há dados para o período/filtro solicitado.
2. NUNCA invente metas, vendas, clientes, vendedores ou produtos que não estejam nos dados acima.
3. Se a pergunta for vaga demais e os dados não permitirem uma resposta completa, peça UM esclarecimento específico ao usuário.
4. Use APENAS os valores numéricos que estão nos dados. NÃO recalcule, NÃO invente, NÃO arredonde além do necessário.
5. Se um mês/vendedor/cliente não estiver na lista de dados, NÃO mencione.

Você deve retornar APENAS um JSON válido com a seguinte estrutura:

{{
  "resumo_executivo": "Texto objetivo de 2-4 linhas explicando os principais achados baseados nos dados. Use números exatos dos dados.",
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
    "Insight 1: ação específica baseada nos dados",
    "Insight 2: ação específica baseada nos dados",
    "Insight 3: ação específica baseada nos dados"
  ]
}}

INSTRUÇÕES PARA TABELA_PRINCIPAL:
- Se os dados contiverem lista de metas por mês, crie tabela com colunas: ["Mês", "Meta Total", "Realizado Total", "Gap", "Atingimento (%)"]
- Se os dados contiverem lista de vendedores, crie tabela com colunas: ["Vendedor", "Meta", "Realizado", "Gap", "Atingimento (%)"]
- Se os dados contiverem lista de clientes críticos, crie tabela com colunas: ["Cliente", "Vendedor", "Churn Score", "Dias sem Compra", "Faturamento 12m"]
- Use os dados exatos, sem inventar valores.

INSTRUÇÕES PARA INSIGHTS:
- Seja específico: cite nomes, valores, períodos que estão nos dados.
- Foque em ações acionáveis (o que fazer com base nos dados).
- Se não houver dados suficientes, o primeiro insight deve ser pedir esclarecimento ao usuário.

Retorne APENAS o JSON, sem texto adicional antes ou depois."""

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
    
    return f"""Você é o DIPAM COPILOT™, um assistente de inteligência comercial avançado da DIPAM.

PERSONA:
- Fala sempre em português brasileiro
- Tom consultivo, claro e direto
- Profissional mas acessível
- Focado em insights acionáveis
- Direcionado para {tratamento}

FONTE DE DADOS:
- Todos os dados vêm do data warehouse DIPAM (camada DW)
- NUNCA mencione BigQuery (não está implementado)
- Sempre cite "data warehouse DIPAM" ou "camada DW" quando referenciar a fonte de dados

REGRAS FUNDAMENTAIS - ZERO INVENÇÃO DE DADOS:
1. Use APENAS os dados numéricos fornecidos no JSON de dados brutos.
2. NUNCA invente valores, períodos, produtos, quantidades, vendedores, supervisores ou clientes.
3. Se um dado não estiver presente nos dados brutos, NÃO cite.
4. Se os dados estiverem vazios ou "tem_dados": false, diga claramente que não há dados.
5. Use formatação brasileira: R$ 1.000,00 (ponto para milhar, vírgula para decimal) e 85,5% (vírgula para decimal).
6. Seja preciso: use os números exatos dos dados, sem arredondar além do necessário.

FORMATO DE RESPOSTA:
Você deve retornar um JSON estruturado com:
- resumo_executivo: texto objetivo de 2-4 linhas
- periodo_analisado: período analisado nos dados
- tabela_principal: tabela com dados principais (colunas e linhas)
- insights: lista de 3-5 recomendações acionáveis específicas"""

