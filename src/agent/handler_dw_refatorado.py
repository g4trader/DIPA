"""
Handler refatorado que usa IntentSpec + camada DW.

Este módulo implementa o novo fluxo:
1. LLM gera IntentSpec
2. Executa consulta DW baseada no IntentSpec
3. LLM gera resposta executiva com dados brutos

ARQUITETURA:
- Usa SEMPRE camada DW (analytics_metas.py, query_executor.py)
- NUNCA queries diretas no SQLite
- BigQuery NÃO implementado (apenas roadmap)
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from src.agent.intent_spec import IntentSpec
from src.agent.query_executor import executar_consulta_dw
from src.agent.orquestrador_dw import executar_intent_spec
from src.agent.rules import detectar_override_explicito
from src.agent.memoria_comportamental import (
    detectar_instrucoes_comportamentais,
    salvar_instrucao_comportamental,
    aplicar_instrucoes_comportamentais,
    gerar_contexto_instrucoes_para_llm
)
from src.agent.post_processor import processar_resposta
from src.agent.behavior_memory import aplicar_regras_ao_intent
from src.llm_integration_intent import (
    gerar_intent_spec_via_llm,
    gerar_resposta_executiva_com_dados_dw
)

logger = logging.getLogger(__name__)


def processar_pergunta_com_dw(
    pergunta: str,
    session: Session,
    papel: Optional[str] = None
) -> Dict[str, Any]:
    """
    Processa pergunta usando o novo fluxo: IntentSpec → DW → Resposta executiva.
    
    Fluxo:
    1. LLM gera IntentSpec a partir da pergunta
    2. Executa consulta DW baseada no IntentSpec
    3. LLM gera resposta executiva com dados brutos do DW
    
    Args:
        pergunta: Pergunta do usuário em linguagem natural
        session: Sessão SQLAlchemy
        papel: Papel do usuário (diretor, supervisor, vendedor)
        
    Returns:
        dict com estrutura:
        {
            "resumo_executivo": str,
            "periodo_analisado": {"inicio": "YYYY-MM-DD", "fim": "YYYY-MM-DD"},
            "tabela_principal": List[Dict],
            "insights": List[str],
            "intent_spec": IntentSpec,
            "dados_dw": Dict,
            "tem_dados": bool
        }
    """
    logger.info(f"[processar_pergunta_com_dw] Processando pergunta: {pergunta[:100]}...")
    
    # PASSO 1: LLM gera IntentSpec
    try:
        intent_spec = gerar_intent_spec_via_llm(pergunta, papel=papel)
        logger.info(
            f"[processar_pergunta_com_dw] IntentSpec gerado: "
            f"tipo={intent_spec.tipo}, "
            f"periodo={intent_spec.periodo_inicio} a {intent_spec.periodo_fim}"
        )
    except Exception as e:
        logger.error(f"[processar_pergunta_com_dw] Erro ao gerar IntentSpec: {e}")
        return {
            "resumo_executivo": "Não foi possível entender sua pergunta. Por favor, reformule de forma mais específica.",
            "periodo_analisado": {"inicio": None, "fim": None},
            "tabela_principal": [],
            "insights": ["Reformule sua pergunta de forma mais específica."],
            "intent_spec": None,
            "dados_dw": {},
            "tem_dados": False,
            "erro": str(e)
        }
    
    # PASSO 1.5: Detecta instruções comportamentais na pergunta
    instrucoes_detectadas = detectar_instrucoes_comportamentais(pergunta)
    
    # PASSO 1.6: Detecta override explícito na pergunta
    override_regras = detectar_override_explicito(pergunta)
    contexto_usuario = {
        "role": papel or "diretor",
        "override_regras": override_regras
    }
    
    # PASSO 1.7: Salva instruções comportamentais detectadas na memória permanente
    if instrucoes_detectadas and not override_regras:
        for instrucao in instrucoes_detectadas:
            try:
                salvar_instrucao_comportamental(
                    session=session,
                    instrucao=instrucao,
                    intent_spec=intent_spec,
                    owner_role=papel or "diretor"
                )
                logger.info(
                    f"[processar_pergunta_com_dw] Instrução comportamental salva: "
                    f"{instrucao['tipo']} - {instrucao['entidade']}"
                )
            except Exception as e:
                logger.error(
                    f"[processar_pergunta_com_dw] Erro ao salvar instrução comportamental: {e}"
                )
    
    # PASSO 2: Executa consulta DW via orquestrador (que aplica regras automaticamente)
    try:
        resultado_orquestrador = executar_intent_spec(
            session=session,
            intent_spec=intent_spec,
            contexto_usuario=contexto_usuario
        )
        
        # Extrai dados, regras aplicadas, análise de causas e causas_detector
        dados_dw = {
            "status": resultado_orquestrador.get("status"),
            "dados": resultado_orquestrador.get("dados", []),
            "tem_dados": resultado_orquestrador.get("status") == "ok" and len(resultado_orquestrador.get("dados", [])) > 0,
            "analise_causas": resultado_orquestrador.get("analise_causas", {}),
            "causas_detector": resultado_orquestrador.get("causas_detector", {}),
            "meta_total": resultado_orquestrador.get("dados", [{}])[0].get("meta_total", 0) if resultado_orquestrador.get("dados") else 0,
            "realizado_total": resultado_orquestrador.get("dados", [{}])[0].get("realizado_total", 0) if resultado_orquestrador.get("dados") else 0,
            "gap_total": resultado_orquestrador.get("dados", [{}])[0].get("gap_total", 0) if resultado_orquestrador.get("dados") else 0,
            "atingimento_medio": resultado_orquestrador.get("dados", [{}])[0].get("atingimento_medio", 0) if resultado_orquestrador.get("dados") else 0
        }
        regras_aplicadas = resultado_orquestrador.get("regras_aplicadas", {})
        analise_causas = resultado_orquestrador.get("analise_causas", {})
        causas_detector = resultado_orquestrador.get("causas_detector", {})
        tem_dados = dados_dw.get("tem_dados", False)
        
        logger.info(
            f"[processar_pergunta_com_dw] Consulta DW executada: "
            f"tem_dados={tem_dados}, "
            f"tipo={intent_spec.tipo}"
        )
        
        # Se não houver dados, retorna resposta direta
        if not tem_dados:
            periodo_inicio = intent_spec.periodo_inicio or "N/A"
            periodo_fim = intent_spec.periodo_fim or periodo_inicio
            
            return {
                "resumo_executivo": (
                    f"Não encontrei dados no data warehouse DIPAM para o período/filtro solicitado. "
                    f"Período solicitado: {periodo_inicio} a {periodo_fim}. "
                    f"Verifique se os dados foram carregados para este período."
                ),
                "periodo_analisado": {
                    "inicio": periodo_inicio + "-01" if periodo_inicio != "N/A" else None,
                    "fim": periodo_fim + "-01" if periodo_fim != "N/A" else None
                },
                "tabela_principal": [],
                "insights": [
                    "Verifique se os dados foram carregados no data warehouse DIPAM para o período solicitado.",
                    "Tente reformular a pergunta com um período diferente ou filtros mais amplos."
                ],
                "intent_spec": intent_spec,
                "dados_dw": dados_dw,
                "tem_dados": False
            }
        
    except Exception as e:
        logger.error(f"[processar_pergunta_com_dw] Erro ao executar consulta DW: {e}")
        return {
            "resumo_executivo": "Ocorreu um erro ao consultar o data warehouse DIPAM. Por favor, tente novamente.",
            "periodo_analisado": {"inicio": None, "fim": None},
            "tabela_principal": [],
            "insights": ["Tente novamente ou reformule sua pergunta."],
            "intent_spec": intent_spec,
            "dados_dw": {},
            "tem_dados": False,
            "erro": str(e)
        }
    
    # PASSO 3: Pós-processador estrutura resposta
    try:
        # Aplica behavior memory para obter regras aplicadas
        behavior_rules_aplicadas = []
        intent_dict_ajustado = aplicar_regras_ao_intent(intent_spec)
        if isinstance(intent_dict_ajustado, dict) and intent_dict_ajustado.get("filtros") != intent_spec.filtros:
            behavior_rules_aplicadas.append("Regras comportamentais aplicadas via behavior_memory.json")
        
        # Processa resposta usando post_processor
        resposta_estruturada = processar_resposta(
            intent_spec=intent_spec.to_dict() if hasattr(intent_spec, 'to_dict') else intent_spec,
            dados_dw=dados_dw,
            causas_detector=causas_detector,
            behavior_rules_aplicadas=behavior_rules_aplicadas
        )
        
        # PASSO 4: LLM gera resposta executiva com dados estruturados
        resposta_executiva = gerar_resposta_executiva_com_dados_dw(
            pergunta=pergunta,
            intent_spec=intent_spec,
            dados_dw=dados_dw,
            papel=papel,
            regras_aplicadas=regras_aplicadas,
            analise_causas=analise_causas,
            resposta_estruturada=resposta_estruturada  # Passa resposta estruturada para LLM
        )
    
    except Exception as e:
        logger.error(f"[processar_pergunta_com_dw] Erro ao processar resposta: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # Fallback: retorna resposta básica sem pós-processamento
        resposta_executiva = {
            "resumo_executivo": f"Resposta gerada, mas houve erro no pós-processamento: {str(e)}",
            "periodo_analisado": {
                "inicio": intent_spec.periodo_inicio,
                "fim": intent_spec.periodo_fim
            },
            "tabela_principal": dados_dw.get("dados", []),
            "insights": ["Erro no processamento avançado da resposta."],
            "intent_spec": intent_spec,
            "dados_dw": dados_dw,
            "tem_dados": dados_dw.get("tem_dados", False),
            "erro": str(e)
        }
    
    # Adiciona metadados e detalhes técnicos
    resposta_executiva["intent_spec"] = intent_spec
    resposta_executiva["dados_dw"] = dados_dw
    resposta_executiva["tem_dados"] = True
    
    # Adiciona resposta estruturada do pós-processador
    if 'resposta_estruturada' in locals():
        resposta_executiva["resposta_estruturada"] = resposta_estruturada
    
    # Adiciona detalhes técnicos para o template
    resposta_executiva["detalhes_tecnicos"] = {
        "intent_spec": intent_spec.to_dict() if hasattr(intent_spec, 'to_dict') else str(intent_spec),
        "filtros_aplicados": intent_spec.filtros if hasattr(intent_spec, 'filtros') else {},
        "regras_aplicadas": regras_aplicadas,
        "behavior_rules_aplicadas": behavior_rules_aplicadas if 'behavior_rules_aplicadas' in locals() else [],
        "query_executada": f"DW Query para tipo={intent_spec.tipo}, dimensao={intent_spec.dimensao_principal}"
    }
    
    logger.info(
        f"[processar_pergunta_com_dw] Resposta executiva gerada: "
        f"resumo={len(resposta_executiva.get('resumo_executivo', ''))} chars"
    )
    
    return resposta_executiva

