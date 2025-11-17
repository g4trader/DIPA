"""
Camada de Regras e Preferências do Agente DIPAM COPILOT™.

Este módulo gerencia regras e preferências aprendidas com feedbacks
do Diretor e da equipe, permitindo que o agente "lembre" de decisões anteriores.

ARQUITETURA:
- LLM = cérebro estável (não mexe nos pesos toda hora)
- DW (SQLite/Postgres) = verdade absoluta dos dados
- Camada de REGRAS & PREFERÊNCIAS = aprendizado

O aprendizado vem de:
- Feedback explícito do Diretor ("não use pasta verde nesse tipo de análise")
- Decisões registradas no banco como regras permanentes ou condicionais
- Backend aplicando essas regras toda vez antes de chamar o LLM

O modelo não "se lembra magicamente", quem lembra é o banco de regras;
o agent só aplica o que o backend manda.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.dw.models_agent import AgentFeedbackRule
from src.agent.intent_spec import IntentSpec

logger = logging.getLogger(__name__)


@dataclass
class AgentRule:
    """Representa uma regra de feedback do agente."""
    id: int
    owner_role: str
    owner_id: Optional[str]
    rule_scope: str
    condition_json: Dict[str, Any]
    action_json: Dict[str, Any]
    description: Optional[str]
    priority: int
    active: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            "id": self.id,
            "owner_role": self.owner_role,
            "owner_id": self.owner_id,
            "rule_scope": self.rule_scope,
            "condition_json": self.condition_json,
            "action_json": self.action_json,
            "description": self.description,
            "priority": self.priority,
            "active": self.active
        }


def listar_regras_ativas(
    session: Session,
    owner_role: str,
    rule_scope: str,
    owner_id: Optional[str] = None
) -> List[AgentRule]:
    """
    Lista regras ativas para um owner_role e rule_scope específicos.
    
    Args:
        session: Sessão SQLAlchemy
        owner_role: Papel do usuário ('diretor', 'supervisor', etc.)
        rule_scope: Escopo da regra ('meta', 'vendas', 'clientes_criticos', etc.)
        owner_id: ID opcional do usuário (para regras específicas)
        
    Returns:
        Lista de AgentRule ordenada por priority (menor = maior prioridade)
    """
    query = session.query(AgentFeedbackRule).filter(
        and_(
            AgentFeedbackRule.owner_role == owner_role,
            AgentFeedbackRule.rule_scope == rule_scope,
            AgentFeedbackRule.active == 1
        )
    )
    
    # Se owner_id fornecido, filtra também por owner_id (ou regras globais sem owner_id)
    if owner_id:
        query = query.filter(
            (AgentFeedbackRule.owner_id == owner_id) | (AgentFeedbackRule.owner_id.is_(None))
        )
    else:
        # Se não fornecido, busca apenas regras globais (sem owner_id)
        query = query.filter(AgentFeedbackRule.owner_id.is_(None))
    
    # Ordena por priority (menor = maior prioridade)
    query = query.order_by(AgentFeedbackRule.priority.asc())
    
    regras_db = query.all()
    
    # Converte para AgentRule
    regras = []
    for regra_db in regras_db:
        try:
            condition_json = json.loads(regra_db.condition_json) if regra_db.condition_json else {}
            action_json = json.loads(regra_db.action_json) if regra_db.action_json else {}
            
            regras.append(AgentRule(
                id=regra_db.id,
                owner_role=regra_db.owner_role,
                owner_id=regra_db.owner_id,
                rule_scope=regra_db.rule_scope,
                condition_json=condition_json,
                action_json=action_json,
                description=regra_db.description,
                priority=regra_db.priority,
                active=bool(regra_db.active)
            ))
        except json.JSONDecodeError as e:
            logger.error(f"[rules] Erro ao parsear JSON da regra {regra_db.id}: {e}")
            continue
    
    logger.info(
        f"[rules] listar_regras_ativas: "
        f"owner_role={owner_role}, rule_scope={rule_scope}, "
        f"encontradas {len(regras)} regras ativas"
    )
    
    return regras


def salvar_regra_feedback(
    session: Session,
    owner_role: str,
    rule_scope: str,
    condition_json: Dict[str, Any],
    action_json: Dict[str, Any],
    description: Optional[str] = None,
    owner_id: Optional[str] = None,
    priority: int = 10,
    active: bool = True
) -> AgentFeedbackRule:
    """
    Salva uma nova regra de feedback.
    
    Args:
        session: Sessão SQLAlchemy
        owner_role: Papel do usuário ('diretor', 'supervisor', etc.)
        rule_scope: Escopo da regra ('meta', 'vendas', etc.)
        condition_json: Condição da regra (ex.: {"carteira": "pasta_verde"})
        action_json: Ação da regra (ex.: {"excluir_dos_filtros": true})
        description: Descrição humana da regra
        owner_id: ID opcional do usuário
        priority: Prioridade (menor = maior prioridade, default=10)
        active: Se a regra está ativa (default=True)
        
    Returns:
        AgentFeedbackRule criada
    """
    regra = AgentFeedbackRule(
        owner_role=owner_role,
        owner_id=owner_id,
        rule_scope=rule_scope,
        condition_json=json.dumps(condition_json, ensure_ascii=False),
        action_json=json.dumps(action_json, ensure_ascii=False),
        description=description,
        priority=priority,
        active=1 if active else 0
    )
    
    session.add(regra)
    session.commit()
    session.refresh(regra)
    
    logger.info(
        f"[rules] salvar_regra_feedback: "
        f"regra criada com id={regra.id}, "
        f"owner_role={owner_role}, rule_scope={rule_scope}"
    )
    
    return regra


def aplicar_regras(
    intent_spec: IntentSpec,
    filtros_sql: Dict[str, Any],
    contexto_usuario: Dict[str, Any],
    session: Session
) -> Dict[str, Any]:
    """
    Aplica regras ativas ao IntentSpec e filtros SQL.
    
    Esta função:
    1. Carrega regras ativas para (owner_role, rule_scope=intent.tipo)
    2. Aplica cada regra aos filtros SQL
    3. Retorna filtros ajustados + resumo das regras aplicadas
    
    Args:
        intent_spec: IntentSpec gerado pela IA
        filtros_sql: Filtros SQL atuais (ex.: {"carteira": "pasta_verde"})
        contexto_usuario: Contexto do usuário (ex.: {"role": "diretor", "user_id": "123"})
        session: Sessão SQLAlchemy
        
    Returns:
        dict com:
        {
            "filtros_ajustados": {...},  # Filtros SQL após aplicar regras
            "regras_aplicadas": {...},   # Resumo das regras aplicadas para enviar ao LLM
            "regras_usadas": [...]       # Lista de AgentRule aplicadas
        }
    """
    owner_role = contexto_usuario.get("role", "diretor")
    owner_id = contexto_usuario.get("user_id")
    rule_scope = intent_spec.tipo
    
    # Verifica se há override explícito na pergunta
    override_regras = contexto_usuario.get("override_regras", False)
    
    if override_regras:
        logger.info(
            f"[rules] aplicar_regras: "
            f"override_regras=True, pulando aplicação de regras"
        )
        return {
            "filtros_ajustados": filtros_sql,
            "regras_aplicadas": {},
            "regras_usadas": []
        }
    
    # Carrega regras ativas
    regras = listar_regras_ativas(session, owner_role, rule_scope, owner_id)
    
    if not regras:
        logger.info(
            f"[rules] aplicar_regras: "
            f"nenhuma regra ativa para owner_role={owner_role}, rule_scope={rule_scope}"
        )
        return {
            "filtros_ajustados": filtros_sql,
            "regras_aplicadas": {},
            "regras_usadas": []
        }
    
    # Aplica cada regra aos filtros
    filtros_ajustados = filtros_sql.copy()
    regras_aplicadas = {}
    regras_usadas = []
    
    for regra in regras:
        # Verifica se a condição da regra se aplica
        if _condicao_aplica(regra.condition_json, filtros_ajustados):
            # Aplica a ação da regra
            filtros_ajustados = _aplicar_acao(regra.action_json, filtros_ajustados)
            
            # Adiciona ao resumo de regras aplicadas
            if "excluir_carteira" not in regras_aplicadas:
                regras_aplicadas["excluir_carteira"] = []
            if "excluir_carteira" in regra.action_json:
                carteiros_excluidas = regra.action_json.get("excluir_carteira", [])
                if isinstance(carteiros_excluidas, list):
                    regras_aplicadas["excluir_carteira"].extend(carteiros_excluidas)
                else:
                    regras_aplicadas["excluir_carteira"].append(carteiros_excluidas)
            
            if "excluir_dos_filtros" in regra.action_json:
                # Se a ação é excluir dos filtros, remove do filtros_ajustados
                campo_excluir = regra.condition_json.get("carteira")
                if campo_excluir:
                    if "carteira" in filtros_ajustados:
                        if isinstance(filtros_ajustados["carteira"], list):
                            filtros_ajustados["carteira"] = [
                                c for c in filtros_ajustados["carteira"]
                                if c.upper() != campo_excluir.upper()
                            ]
                        else:
                            if filtros_ajustados["carteira"].upper() == campo_excluir.upper():
                                del filtros_ajustados["carteira"]
            
            regras_usadas.append(regra)
            
            logger.info(
                f"[rules] aplicar_regras: "
                f"regra {regra.id} aplicada: {regra.description}"
            )
    
    # Remove duplicatas de excluir_carteira
    if "excluir_carteira" in regras_aplicadas:
        regras_aplicadas["excluir_carteira"] = list(set(regras_aplicadas["excluir_carteira"]))
    
    logger.info(
        f"[rules] aplicar_regras: "
        f"{len(regras_usadas)} regras aplicadas, "
        f"filtros ajustados: {filtros_ajustados}"
    )
    
    return {
        "filtros_ajustados": filtros_ajustados,
        "regras_aplicadas": regras_aplicadas,
        "regras_usadas": regras_usadas
    }


def _condicao_aplica(condition_json: Dict[str, Any], filtros: Dict[str, Any]) -> bool:
    """
    Verifica se a condição da regra se aplica aos filtros atuais.
    
    Args:
        condition_json: Condição da regra (ex.: {"carteira": "pasta_verde"})
        filtros: Filtros atuais
        
    Returns:
        True se a condição se aplica
    """
    # Se não há condição, sempre aplica
    if not condition_json:
        return True
    
    # Verifica cada campo da condição
    for campo, valor_esperado in condition_json.items():
        if campo in filtros:
            valor_atual = filtros[campo]
            # Comparação case-insensitive para strings
            if isinstance(valor_esperado, str) and isinstance(valor_atual, str):
                if valor_atual.upper() == valor_esperado.upper():
                    return True
            elif valor_atual == valor_esperado:
                return True
    
    # Se a condição não se aplica, retorna False
    return False


def _aplicar_acao(action_json: Dict[str, Any], filtros: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aplica a ação da regra aos filtros.
    
    Args:
        action_json: Ação da regra (ex.: {"excluir_dos_filtros": true})
        filtros: Filtros atuais
        
    Returns:
        Filtros ajustados
    """
    filtros_ajustados = filtros.copy()
    
    # Se a ação é excluir dos filtros
    if action_json.get("excluir_dos_filtros"):
        # Remove o campo da condição dos filtros
        # (isso será tratado na função aplicar_regras)
        pass
    
    # Se a ação é excluir carteira específica
    if "excluir_carteira" in action_json:
        carteiros_excluidas = action_json["excluir_carteira"]
        if not isinstance(carteiros_excluidas, list):
            carteiros_excluidas = [carteiros_excluidas]
        
        # Adiciona à lista de carteiros excluídas
        if "carteira_excluida" not in filtros_ajustados:
            filtros_ajustados["carteira_excluida"] = []
        filtros_ajustados["carteira_excluida"].extend(carteiros_excluidas)
    
    return filtros_ajustados


def detectar_override_explicito(pergunta: str) -> bool:
    """
    Detecta se a pergunta contém instrução explícita para ignorar regras.
    
    Exemplos:
    - "incluindo pasta verde"
    - "dessa vez considere também a pasta verde"
    - "ignore a regra de excluir a pasta verde"
    
    Args:
        pergunta: Pergunta do usuário
        
    Returns:
        True se há override explícito
    """
    pergunta_lower = pergunta.lower()
    
    # Palavras-chave que indicam override
    override_keywords = [
        "incluindo pasta verde",
        "incluindo a pasta verde",
        "considerando também a pasta verde",
        "dessa vez inclua",
        "ignore a regra",
        "ignorar a regra",
        "exceção",
        "exceto se",
        "mesmo com a regra"
    ]
    
    for keyword in override_keywords:
        if keyword in pergunta_lower:
            logger.info(
                f"[rules] detectar_override_explicito: "
                f"override detectado: '{keyword}'"
            )
            return True
    
    return False

