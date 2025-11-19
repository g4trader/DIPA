"""
Behavior Memory V1 - DIPAM COPILOT™.

Este módulo gerencia a memória comportamental do agente, armazenando instruções permanentes
do Diretor (ex.: "ignorar pasta verde") em tabela BehaviorRule do banco de dados.

ARQUITETURA:
- Armazena regras em tabela behavior_rules (BehaviorRule model)
- Não toca dados do DW
- Apenas ajusta IntentSpec / filtros antes da consulta DW
- Logs mostrando regras aplicadas
- Suporta escopos: global, tipo_intent, tipo_dimensao, tipo_intent_dimensao
"""

import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from src.dw.models import BehaviorRule
from src.agent.intent_spec import IntentSpec

logger = logging.getLogger(__name__)


def aplicar_regras_ao_intent(
    intent_spec: IntentSpec,
    session_dw: Session
) -> Tuple[IntentSpec, List[Dict[str, Any]]]:
    """
    Aplica regras comportamentais persistentes ao IntentSpec.
    
    Busca na tabela BehaviorRule todas as regras ativo=True compatíveis com o IntentSpec,
    aplica-as na ordem de prioridade e retorna o IntentSpec modificado.
    
    Args:
        intent_spec: IntentSpec a ser ajustado
        session_dw: Sessão SQLAlchemy para acessar BehaviorRule
        
    Returns:
        (intent_spec_modificado, regras_aplicadas)
        - intent_spec_modificado: IntentSpec com filtros ajustados
        - regras_aplicadas: Lista de dicts com {id, tipo_regra, escopo, resumo}
    """
    tipo_intent = intent_spec.tipo
    dimensao_principal = intent_spec.dimensao_principal
    
    # Verifica se a tabela behavior_rules existe, se não, retorna sem aplicar regras
    try:
        from sqlalchemy import inspect
        inspector = inspect(session_dw.bind)
        existing_tables = inspector.get_table_names()
        
        if "behavior_rules" not in existing_tables:
            logger.warning("[behavior_memory] Tabela behavior_rules não existe. Tentando criar...")
            # Tenta criar a tabela
            try:
                from src.dw.bootstrap_schema import ensure_application_schema
                from src.dw.connection import get_db_engine
                engine = get_db_engine()
                ensure_application_schema(engine)
                logger.info("[behavior_memory] ✅ Tabela behavior_rules criada com sucesso")
            except Exception as e:
                logger.warning(f"[behavior_memory] ⚠️  Não foi possível criar tabela behavior_rules: {e}")
                logger.info("[behavior_memory] Continuando sem aplicar regras comportamentais")
                return intent_spec, []
    except Exception as e:
        logger.warning(f"[behavior_memory] ⚠️  Erro ao verificar tabela behavior_rules: {e}")
        logger.info("[behavior_memory] Continuando sem aplicar regras comportamentais")
        return intent_spec, []
    
    # Busca regras compatíveis, ordenadas por prioridade
    regras_compatíveis = []
    
    try:
        # 1. Escopo tipo_intent_dimensao (maior prioridade)
        regras_tipo_dimensao = session_dw.query(BehaviorRule).filter(
            and_(
                BehaviorRule.ativo == True,
                BehaviorRule.escopo == "tipo_intent_dimensao",
                BehaviorRule.tipo_intent == tipo_intent,
                BehaviorRule.dimensao_principal == dimensao_principal
            )
        ).all()
        regras_compatíveis.extend([(r, 1) for r in regras_tipo_dimensao])
        
        # 2. Escopo tipo_intent
        regras_tipo = session_dw.query(BehaviorRule).filter(
            and_(
                BehaviorRule.ativo == True,
                BehaviorRule.escopo == "tipo_intent",
                BehaviorRule.tipo_intent == tipo_intent
            )
        ).all()
        regras_compatíveis.extend([(r, 2) for r in regras_tipo])
        
        # 3. Escopo tipo_dimensao
        regras_dimensao = session_dw.query(BehaviorRule).filter(
            and_(
                BehaviorRule.ativo == True,
                BehaviorRule.escopo == "tipo_dimensao",
                BehaviorRule.dimensao_principal == dimensao_principal
            )
        ).all()
        regras_compatíveis.extend([(r, 3) for r in regras_dimensao])
        
        # 4. Escopo global (menor prioridade)
        regras_global = session_dw.query(BehaviorRule).filter(
            and_(
                BehaviorRule.ativo == True,
                BehaviorRule.escopo == "global"
            )
        ).all()
        regras_compatíveis.extend([(r, 4) for r in regras_global])
    except Exception as e:
        # Se a tabela não existir ou houver erro na query, retorna sem aplicar regras
        logger.warning(f"[behavior_memory] ⚠️  Erro ao consultar behavior_rules: {e}")
        logger.info("[behavior_memory] Continuando sem aplicar regras comportamentais")
        return intent_spec, []
    
    # Ordena por prioridade (menor número = maior prioridade)
    # IMPORTANTE: Aplicamos na ordem inversa (maior prioridade por último) para que sobrescreva as anteriores
    regras_compatíveis.sort(key=lambda x: x[1], reverse=True)  # Inverte: maior prioridade (1) por último
    
    # Aplica regras na ordem (menor prioridade primeiro, maior prioridade por último para sobrescrever)
    intent_spec_modificado = intent_spec
    regras_aplicadas = []
    
    for regra, prioridade in regras_compatíveis:
        regra_json = regra.regra_json if isinstance(regra.regra_json, dict) else {}
        
        if regra.tipo_regra == "EXCLUIR_FILTRO":
            campo = regra_json.get("campo")
            operador = regra_json.get("operador", "!=")
            valor = regra_json.get("valor")
            
            if campo and valor:
                # Adiciona filtro de exclusão
                if campo == "pasta":
                    if "excluir_pastas" not in intent_spec_modificado.filtros:
                        intent_spec_modificado.filtros["excluir_pastas"] = []
                    if valor not in intent_spec_modificado.filtros["excluir_pastas"]:
                        intent_spec_modificado.filtros["excluir_pastas"].append(valor)
                elif campo == "rota":
                    if "excluir_rotas" not in intent_spec_modificado.filtros:
                        intent_spec_modificado.filtros["excluir_rotas"] = []
                    if valor not in intent_spec_modificado.filtros["excluir_rotas"]:
                        intent_spec_modificado.filtros["excluir_rotas"].append(valor)
                else:
                    # Campo genérico
                    chave_excluir = f"excluir_{campo}"
                    if chave_excluir not in intent_spec_modificado.filtros:
                        intent_spec_modificado.filtros[chave_excluir] = []
                    if valor not in intent_spec_modificado.filtros[chave_excluir]:
                        intent_spec_modificado.filtros[chave_excluir].append(valor)
                
                regras_aplicadas.append({
                    "id": regra.id,
                    "tipo_regra": regra.tipo_regra,
                    "escopo": regra.escopo,
                    "resumo": f"Excluir {campo}={valor}"
                })
        
        elif regra.tipo_regra == "FORÇAR_FILTRO":
            campo = regra_json.get("campo")
            valor = regra_json.get("valor")
            
            if campo and valor:
                # Força o filtro (sobrescreve se existir)
                intent_spec_modificado.filtros[campo] = valor
                
                regras_aplicadas.append({
                    "id": regra.id,
                    "tipo_regra": regra.tipo_regra,
                    "escopo": regra.escopo,
                    "resumo": f"Forçar {campo}={valor}"
                })
        
        elif regra.tipo_regra == "AJUSTAR_LIMIAR":
            campo = regra_json.get("campo")
            limiar = regra_json.get("limiar")
            
            if campo and limiar is not None:
                # Ajusta limiar (ex.: limite_media, atingimento_limite)
                intent_spec_modificado.filtros[campo] = limiar
                
                regras_aplicadas.append({
                    "id": regra.id,
                    "tipo_regra": regra.tipo_regra,
                    "escopo": regra.escopo,
                    "resumo": f"Ajustar {campo}={limiar}"
                })
    
    # Loga regras aplicadas
    if regras_aplicadas:
        logger.info(
            f"[behavior_memory] {len(regras_aplicadas)} regra(s) aplicada(s) ao intent "
            f"tipo={tipo_intent}, dimensao={dimensao_principal}"
        )
        for regra_info in regras_aplicadas:
            logger.debug(f"[behavior_memory] - {regra_info['resumo']} (id={regra_info['id']}, escopo={regra_info['escopo']})")
    
    return intent_spec_modificado, regras_aplicadas

