"""
Sistema de Memória Comportamental - DIPAM COPILOT™.

Este módulo detecta, armazena e aplica instruções comportamentais do Diretor,
classificadas por tipo de pergunta (intent).

REGRAS:
- Nunca expor a memória bruta
- Nunca contradizer uma instrução anterior do Diretor
- Nunca perder uma instrução
- Aplicar automaticamente em todas as próximas respostas
- Exceto se o Diretor pedir explicitamente o contrário

PADRÕES DETECTADOS:
- "não use X"
- "sempre considere Y"
- "ignore Z para este tipo de pergunta"
- "aprofunde mais em W"
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
import json

from src.dw.models_agent import AgentFeedbackRule
from src.agent.intent_spec import IntentSpec

logger = logging.getLogger(__name__)


# Padrões de detecção de instruções comportamentais
PADROES_INSTRUCOES = {
    "nao_use": [
        r"não use\s+([^\.\,\!\?]+)",
        r"não usar\s+([^\.\,\!\?]+)",
        r"nunca use\s+([^\.\,\!\?]+)",
        r"nunca usar\s+([^\.\,\!\?]+)",
        r"evite\s+([^\.\,\!\?]+)",
        r"não inclua\s+([^\.\,\!\?]+)",
        r"exclua\s+([^\.\,\!\?]+)"
    ],
    "sempre_considere": [
        r"sempre considere\s+([^\.\,\!\?]+)",
        r"sempre considerar\s+([^\.\,\!\?]+)",
        r"inclua sempre\s+([^\.\,\!\?]+)",
        r"considere sempre\s+([^\.\,\!\?]+)",
        r"use sempre\s+([^\.\,\!\?]+)",
        r"priorize\s+([^\.\,\!\?]+)"
    ],
    "ignore": [
        r"ignore\s+([^\.\,\!\?]+)\s+para\s+([^\.\,\!\?]+)",
        r"ignore\s+([^\.\,\!\?]+)",
        r"desconsidere\s+([^\.\,\!\?]+)",
        r"não considere\s+([^\.\,\!\?]+)\s+para\s+([^\.\,\!\?]+)"
    ],
    "aprofunde": [
        r"aprofunde mais\s+em\s+([^\.\,\!\?]+)",
        r"aprofunde\s+([^\.\,\!\?]+)",
        r"detalhe mais\s+([^\.\,\!\?]+)",
        r"explore mais\s+([^\.\,\!\?]+)",
        r"seja mais detalhado\s+em\s+([^\.\,\!\?]+)"
    ]
}


def detectar_instrucoes_comportamentais(
    pergunta: str,
    resposta_anterior: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Detecta instruções comportamentais na pergunta ou resposta do Diretor.
    
    Args:
        pergunta: Pergunta atual do Diretor
        resposta_anterior: Resposta anterior do agente (opcional, para contexto)
        
    Returns:
        Lista de instruções detectadas, cada uma com:
        - tipo: "nao_use", "sempre_considere", "ignore", "aprofunde"
        - entidade: O que foi mencionado (X, Y, Z, W)
        - contexto: Contexto adicional (tipo de pergunta, etc.)
        - texto_original: Texto original da instrução
    """
    instrucoes = []
    texto_completo = pergunta.lower()
    
    if resposta_anterior:
        texto_completo += " " + resposta_anterior.lower()
    
    # Detecta padrões "não use X"
    for padrao in PADROES_INSTRUCOES["nao_use"]:
        matches = re.finditer(padrao, texto_completo, re.IGNORECASE)
        for match in matches:
            entidade = match.group(1).strip()
            if len(entidade) > 2:  # Evita capturar palavras muito curtas
                instrucoes.append({
                    "tipo": "nao_use",
                    "entidade": entidade,
                    "contexto": None,
                    "texto_original": match.group(0),
                    "acao": {
                        "excluir_dos_filtros": True,
                        "campo": _inferir_campo(entidade),
                        "valor": entidade
                    }
                })
    
    # Detecta padrões "sempre considere Y"
    for padrao in PADROES_INSTRUCOES["sempre_considere"]:
        matches = re.finditer(padrao, texto_completo, re.IGNORECASE)
        for match in matches:
            entidade = match.group(1).strip()
            if len(entidade) > 2:
                instrucoes.append({
                    "tipo": "sempre_considere",
                    "entidade": entidade,
                    "contexto": None,
                    "texto_original": match.group(0),
                    "acao": {
                        "adicionar_filtro": True,
                        "campo": _inferir_campo(entidade),
                        "valor": entidade
                    }
                })
    
    # Detecta padrões "ignore Z para este tipo de pergunta"
    for padrao in PADROES_INSTRUCOES["ignore"]:
        matches = re.finditer(padrao, texto_completo, re.IGNORECASE)
        for match in matches:
            if len(match.groups()) >= 2:
                entidade = match.group(1).strip()
                contexto = match.group(2).strip() if len(match.groups()) > 1 else None
            else:
                entidade = match.group(1).strip()
                contexto = None
            
            if len(entidade) > 2:
                instrucoes.append({
                    "tipo": "ignore",
                    "entidade": entidade,
                    "contexto": contexto,
                    "texto_original": match.group(0),
                    "acao": {
                        "excluir_dos_filtros": True,
                        "campo": _inferir_campo(entidade),
                        "valor": entidade,
                        "contexto_tipo": contexto
                    }
                })
    
    # Detecta padrões "aprofunde mais em W"
    for padrao in PADROES_INSTRUCOES["aprofunde"]:
        matches = re.finditer(padrao, texto_completo, re.IGNORECASE)
        for match in matches:
            entidade = match.group(1).strip()
            if len(entidade) > 2:
                instrucoes.append({
                    "tipo": "aprofunde",
                    "entidade": entidade,
                    "contexto": None,
                    "texto_original": match.group(0),
                    "acao": {
                        "aprofundar": True,
                        "campo": _inferir_campo(entidade),
                        "valor": entidade
                    }
                })
    
    if instrucoes:
        logger.info(
            f"[memoria_comportamental] Detectadas {len(instrucoes)} instruções comportamentais: "
            f"{[i['tipo'] for i in instrucoes]}"
        )
    
    return instrucoes


def _inferir_campo(entidade: str) -> str:
    """
    Infere o campo do banco baseado na entidade mencionada.
    
    Exemplos:
    - "pasta verde" -> "carteira"
    - "rota 22" -> "rota"
    - "cliente ABC" -> "cliente"
    - "supervisor X" -> "supervisor"
    """
    entidade_lower = entidade.lower()
    
    if "pasta" in entidade_lower or "carteira" in entidade_lower:
        return "carteira"
    elif "rota" in entidade_lower:
        return "rota"
    elif "cliente" in entidade_lower:
        return "cliente"
    elif "supervisor" in entidade_lower:
        return "supervisor"
    elif "vendedor" in entidade_lower or "rca" in entidade_lower:
        return "vendedor"
    elif "produto" in entidade_lower or "sku" in entidade_lower:
        return "produto"
    else:
        return "outros"


def salvar_instrucao_comportamental(
    session: Session,
    instrucao: Dict[str, Any],
    intent_spec: IntentSpec,
    owner_role: str = "diretor",
    owner_id: Optional[str] = None
) -> AgentFeedbackRule:
    """
    Salva uma instrução comportamental na memória permanente.
    
    Args:
        session: Sessão SQLAlchemy
        instrucao: Instrução detectada (retornada por detectar_instrucoes_comportamentais)
        intent_spec: IntentSpec da pergunta atual
        owner_role: Papel do usuário (padrão: "diretor")
        owner_id: ID do usuário (opcional)
        
    Returns:
        AgentFeedbackRule criada
    """
    # Determina escopo baseado no tipo de intent
    rule_scope = intent_spec.tipo
    
    # Cria condição baseada no contexto
    condition = {
        "tipo_pergunta": intent_spec.tipo,
        "dimensao": intent_spec.dimensao_principal
    }
    
    if instrucao.get("contexto"):
        condition["contexto"] = instrucao["contexto"]
    
    # Cria ação baseada no tipo de instrução
    action = instrucao.get("acao", {})
    
    # Descrição legível
    descricao = f"{instrucao['tipo']}: {instrucao['entidade']}"
    if instrucao.get("contexto"):
        descricao += f" (contexto: {instrucao['contexto']})"
    
    # Verifica se já existe regra similar (evita duplicação)
    regras_existentes = session.query(AgentFeedbackRule).filter(
        AgentFeedbackRule.owner_role == owner_role,
        AgentFeedbackRule.rule_scope == rule_scope,
        AgentFeedbackRule.active == 1
    ).all()
    
    for regra_existente in regras_existentes:
        condition_existente = json.loads(regra_existente.condition_json)
        action_existente = json.loads(regra_existente.action_json)
        
        # Se a condição e ação são similares, não cria duplicata
        if (condition_existente.get("tipo_pergunta") == condition.get("tipo_pergunta") and
            action_existente.get("campo") == action.get("campo") and
            action_existente.get("valor") == action.get("valor")):
            logger.info(
                f"[memoria_comportamental] Instrução similar já existe (ID: {regra_existente.id}). "
                f"Atualizando ao invés de criar nova."
            )
            # Atualiza regra existente
            regra_existente.condition_json = json.dumps(condition, ensure_ascii=False)
            regra_existente.action_json = json.dumps(action, ensure_ascii=False)
            regra_existente.description = descricao
            regra_existente.updated_at = func.now()
            session.commit()
            session.refresh(regra_existente)
            return regra_existente
    
    # Cria nova regra
    from datetime import datetime
    from sqlalchemy.sql import func
    
    regra = AgentFeedbackRule(
        owner_role=owner_role,
        owner_id=owner_id,
        rule_scope=rule_scope,
        condition_json=json.dumps(condition, ensure_ascii=False),
        action_json=json.dumps(action, ensure_ascii=False),
        description=descricao,
        priority=10,
        active=1,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    session.add(regra)
    session.commit()
    session.refresh(regra)
    
    logger.info(
        f"[memoria_comportamental] Instrução comportamental salva: "
        f"ID={regra.id}, tipo={instrucao['tipo']}, entidade={instrucao['entidade']}, "
        f"scope={rule_scope}"
    )
    
    return regra


def aplicar_instrucoes_comportamentais(
    session: Session,
    intent_spec: IntentSpec,
    filtros_sql: Dict[str, Any],
    contexto_usuario: Dict[str, Any],
    instrucoes_explicitas: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Aplica instruções comportamentais salvas na memória.
    
    Esta função é um wrapper que chama aplicar_regras de rules.py,
    mas com foco em instruções comportamentais do Diretor.
    
    Args:
        session: Sessão SQLAlchemy
        intent_spec: IntentSpec atual
        filtros_sql: Filtros SQL que serão ajustados
        contexto_usuario: Contexto do usuário
        instrucoes_explicitas: Instruções detectadas na pergunta atual (opcional)
        
    Returns:
        Dict com "filtros_ajustados" e "instrucoes_aplicadas"
    """
    from src.agent.rules import aplicar_regras
    
    # Aplica regras existentes (que incluem instruções comportamentais salvas)
    resultado = aplicar_regras(
        session=session,
        intent_spec=intent_spec,
        filtros_sql=filtros_sql,
        contexto_usuario=contexto_usuario
    )
    
    # Se há instruções explícitas na pergunta atual, aplica também
    if instrucoes_explicitas:
        for instrucao in instrucoes_explicitas:
            acao = instrucao.get("acao", {})
            
            if acao.get("excluir_dos_filtros"):
                campo = acao.get("campo")
                valor = acao.get("valor")
                if campo and valor:
                    if campo not in resultado["filtros_ajustados"]:
                        resultado["filtros_ajustados"][campo] = []
                    if isinstance(resultado["filtros_ajustados"][campo], list):
                        if valor not in resultado["filtros_ajustados"][campo]:
                            resultado["filtros_ajustados"][campo].append(valor)
            
            elif acao.get("adicionar_filtro"):
                campo = acao.get("campo")
                valor = acao.get("valor")
                if campo:
                    resultado["filtros_ajustados"][campo] = valor
            
            elif acao.get("aprofundar"):
                # Para aprofundar, adiciona flag especial
                campo = acao.get("campo")
                if campo:
                    resultado["filtros_ajustados"][f"aprofundar_{campo}"] = True
    
    # Adiciona resumo de instruções aplicadas (sem expor memória bruta)
    instrucoes_aplicadas_resumo = {}
    if resultado.get("regras_aplicadas"):
        for key, value in resultado["regras_aplicadas"].items():
            if key != "override_explicito":
                instrucoes_aplicadas_resumo[key] = value
    
    resultado["instrucoes_aplicadas"] = instrucoes_aplicadas_resumo
    
    return resultado


def gerar_contexto_instrucoes_para_llm(
    instrucoes_aplicadas: Dict[str, Any],
    expor_detalhes: bool = False
) -> str:
    """
    Gera contexto de instruções para o LLM, sem expor a memória bruta.
    
    Args:
        instrucoes_aplicadas: Dict com instruções aplicadas
        expor_detalhes: Se True, expõe mais detalhes (padrão: False)
        
    Returns:
        String com contexto formatado para o prompt do LLM
    """
    if not instrucoes_aplicadas:
        return ""
    
    contexto = "\n\nINSTRUÇÕES COMPORTAMENTAIS DO DIRETOR (aplicadas automaticamente):\n"
    contexto += "- Estas instruções foram aprendidas de interações anteriores\n"
    contexto += "- Elas já foram aplicadas na consulta ao data warehouse\n"
    contexto += "- Você DEVE respeitar essas preferências na sua resposta\n"
    contexto += "- Só ignore se o Diretor instruir explicitamente o contrário na pergunta atual\n\n"
    
    # Lista instruções de forma genérica (sem expor memória bruta)
    if "excluir_carteira" in instrucoes_aplicadas:
        valores = instrucoes_aplicadas["excluir_carteira"]
        contexto += f"- Excluir da análise: {', '.join(valores)}\n"
    
    # Adiciona outras instruções de forma genérica
    for key, value in instrucoes_aplicadas.items():
        if key not in ["excluir_carteira", "override_explicito"]:
            if isinstance(value, list):
                contexto += f"- {key}: {', '.join(str(v) for v in value)}\n"
            else:
                contexto += f"- {key}: {value}\n"
    
    return contexto

