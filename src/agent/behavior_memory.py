"""
Behavior Memory - DIPAM COPILOT™.

Este módulo gerencia a memória comportamental do agente, armazenando instruções permanentes
do Diretor (ex.: "ignorar pasta verde") em arquivo JSON.

ARQUITETURA:
- Armazena regras em data/behavior_rules.json
- Não toca dados do DW
- Apenas ajusta IntentSpec / filtros antes da consulta DW
- Logs mostrando regras aplicadas
"""

import json
import logging
import os
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

# Caminho do arquivo de regras
BEHAVIOR_RULES_FILE = Path(__file__).parent.parent.parent / "data" / "behavior_rules.json"


def _garantir_arquivo_existe() -> None:
    """Garante que o arquivo behavior_rules.json existe."""
    BEHAVIOR_RULES_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not BEHAVIOR_RULES_FILE.exists():
        with open(BEHAVIOR_RULES_FILE, 'w', encoding='utf-8') as f:
            json.dump({"regras_por_tipo_analise": {}}, f, indent=2, ensure_ascii=False)
        logger.info(f"[behavior_memory] Arquivo criado: {BEHAVIOR_RULES_FILE}")


def carregar_regras() -> Dict[str, Any]:
    """
    Carrega regras comportamentais do arquivo JSON.
    
    Returns:
        dict com estrutura:
        {
            "regras_por_tipo_analise": {
                "analise_meta_mensal": {
                    "excluir_carteiras": ["pasta_verde"],
                    "comentario": "..."
                },
                ...
            }
        }
    """
    _garantir_arquivo_existe()
    
    try:
        with open(BEHAVIOR_RULES_FILE, 'r', encoding='utf-8') as f:
            regras = json.load(f)
        
        logger.debug(f"[behavior_memory] Regras carregadas: {len(regras.get('regras_por_tipo_analise', {}))} tipos")
        return regras
    except Exception as e:
        logger.error(f"[behavior_memory] Erro ao carregar regras: {e}")
        return {"regras_por_tipo_analise": {}}


def salvar_regras(regras: Dict[str, Any]) -> None:
    """
    Salva regras comportamentais no arquivo JSON.
    
    Args:
        regras: Dict com estrutura de regras
    """
    _garantir_arquivo_existe()
    
    try:
        with open(BEHAVIOR_RULES_FILE, 'w', encoding='utf-8') as f:
            json.dump(regras, f, indent=2, ensure_ascii=False)
        
        logger.info(f"[behavior_memory] Regras salvas: {len(regras.get('regras_por_tipo_analise', {}))} tipos")
    except Exception as e:
        logger.error(f"[behavior_memory] Erro ao salvar regras: {e}")
        raise


def registrar_feedback(
    tipo_analise: str,
    tipo_regra: str,
    valor: Any,
    comentario: Optional[str] = None,
    payload_opcional: Optional[Dict[str, Any]] = None
) -> None:
    """
    Registra feedback do Diretor como regra comportamental permanente.
    
    Args:
        tipo_analise: Tipo de análise (ex.: "analise_meta_mensal", "analise_clientes_queda")
        tipo_regra: Tipo de regra (ex.: "excluir_carteira", "priorizar_rota")
        valor: Valor da regra (ex.: "pasta_verde", ["rota_22", "rota_75"])
        comentario: Comentário opcional explicando a regra
        payload_opcional: Dados adicionais opcionais
        
    Exemplo:
        >>> registrar_feedback(
        ...     "analise_meta_mensal",
        ...     "excluir_carteira",
        ...     "pasta_verde",
        ...     "Regra definida pelo Diretor em 2025-11-17"
        ... )
    """
    regras = carregar_regras()
    
    # Inicializa estrutura se não existir
    if tipo_analise not in regras["regras_por_tipo_analise"]:
        regras["regras_por_tipo_analise"][tipo_analise] = {}
    
    # Adiciona ou atualiza regra
    if tipo_regra not in regras["regras_por_tipo_analise"][tipo_analise]:
        regras["regras_por_tipo_analise"][tipo_analise][tipo_regra] = []
    
    # Se valor é lista, adiciona cada item
    if isinstance(valor, list):
        regras["regras_por_tipo_analise"][tipo_analise][tipo_regra].extend(valor)
        # Remove duplicatas
        regras["regras_por_tipo_analise"][tipo_analise][tipo_regra] = list(set(
            regras["regras_por_tipo_analise"][tipo_analise][tipo_regra]
        ))
    else:
        # Se valor não está na lista, adiciona
        if valor not in regras["regras_por_tipo_analise"][tipo_analise][tipo_regra]:
            regras["regras_por_tipo_analise"][tipo_analise][tipo_regra].append(valor)
    
    # Adiciona comentário se fornecido
    if comentario:
        regras["regras_por_tipo_analise"][tipo_analise]["comentario"] = comentario
    
    # Adiciona payload opcional
    if payload_opcional:
        regras["regras_por_tipo_analise"][tipo_analise].update(payload_opcional)
    
    salvar_regras(regras)
    
    logger.info(
        f"[behavior_memory] Feedback registrado: "
        f"tipo_analise={tipo_analise}, tipo_regra={tipo_regra}, valor={valor}"
    )


def aplicar_regras_ao_intent(intent_spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aplica regras comportamentais ao IntentSpec, ajustando filtros conforme necessário.
    
    Args:
        intent_spec: IntentSpec como dict (ou objeto com .to_dict())
        
    Returns:
        IntentSpec ajustado com filtros aplicados
        
    Exemplo:
        >>> intent = {"tipo": "analise_meta_mensal", "filtros": {}}
        >>> intent_ajustado = aplicar_regras_ao_intent(intent)
        >>> intent_ajustado["filtros"]  # Pode conter "excluir_carteiras": ["pasta_verde"]
    """
    # Converte para dict se necessário
    if hasattr(intent_spec, 'to_dict'):
        intent_dict = intent_spec.to_dict()
    else:
        intent_dict = intent_spec.copy()
    
    # Carrega regras
    regras = carregar_regras()
    
    # Determina tipo de análise baseado no intent
    tipo_intent = intent_dict.get("tipo", "")
    
    # Mapeia tipo de intent para tipo de análise
    mapeamento_tipo = {
        "meta": "analise_meta_mensal",
        "analise_meta_detalhada": "analise_meta_mensal",
        "clientes_criticos": "analise_clientes_queda",
        "churn": "analise_clientes_queda",
        "vendas": "analise_vendas",
        "ranking_vendedores": "analise_meta_mensal",
        # Novos tipos do ENGINEERING_QUERIES.md
        "clientes_sem_compra": "analise_clientes_queda",
        "queda_faturamento": "analise_clientes_queda",
        "meta_departamento": "analise_meta_mensal",
        "positivacao": "analise_positivacao",
        "mix": "analise_mix",
        "recompra": "analise_recompra",
        "clientes_sem_item": "analise_clientes_queda",
        "vendas_baixas": "analise_vendas",
        "mix_nissin": "analise_mix"
    }
    
    tipo_analise = mapeamento_tipo.get(tipo_intent, tipo_intent)
    
    # Se não há regras para este tipo, retorna sem alterações
    if tipo_analise not in regras["regras_por_tipo_analise"]:
        return intent_dict
    
    regras_tipo = regras["regras_por_tipo_analise"][tipo_analise]
    
    # Inicializa filtros se não existir
    if "filtros" not in intent_dict:
        intent_dict["filtros"] = {}
    
    regras_aplicadas = []
    
    # Aplica regra "excluir_carteira"
    if "excluir_carteira" in regras_tipo:
        carteiras_excluir = regras_tipo["excluir_carteira"]
        if isinstance(carteiras_excluir, list):
            if "excluir_carteiras" not in intent_dict["filtros"]:
                intent_dict["filtros"]["excluir_carteiras"] = []
            intent_dict["filtros"]["excluir_carteiras"].extend(carteiras_excluir)
            regras_aplicadas.append(f"Excluindo carteiras: {', '.join(carteiras_excluir)}")
    
    # Aplica regra "excluir_rotas"
    if "excluir_rotas" in regras_tipo:
        rotas_excluir = regras_tipo["excluir_rotas"]
        if isinstance(rotas_excluir, list):
            if "excluir_rotas" not in intent_dict["filtros"]:
                intent_dict["filtros"]["excluir_rotas"] = []
            intent_dict["filtros"]["excluir_rotas"].extend(rotas_excluir)
            regras_aplicadas.append(f"Excluindo rotas: {', '.join(rotas_excluir)}")
    
    # Aplica regra "priorizar_rotas"
    if "priorizar_rotas" in regras_tipo:
        rotas_priorizar = regras_tipo["priorizar_rotas"]
        if isinstance(rotas_priorizar, list):
            intent_dict["filtros"]["priorizar_rotas"] = rotas_priorizar
            regras_aplicadas.append(f"Priorizando rotas: {', '.join(rotas_priorizar)}")
    
    # Loga regras aplicadas
    if regras_aplicadas:
        logger.info(
            f"[behavior_memory] Regras aplicadas ao intent {tipo_intent}: "
            f"{', '.join(regras_aplicadas)}"
        )
    
    return intent_dict

