"""
Registry de modelos ML (FASE 5).

Gerencia metadados dos modelos treinados em um arquivo JSON simples.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Caminho padrão do registry
DEFAULT_REGISTRY_PATH = Path(__file__).parent.parent.parent / "models" / "registry.json"


def get_registry_path() -> Path:
    """
    Retorna o caminho do arquivo de registry.
    
    Returns:
        Path do arquivo registry.json
    """
    registry_path = DEFAULT_REGISTRY_PATH
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    return registry_path


def load_registry() -> Dict[str, Any]:
    """
    Carrega o registry de modelos do arquivo JSON.
    
    Returns:
        Dict com informações dos modelos
    """
    registry_path = get_registry_path()
    
    if not registry_path.exists():
        logger.info(f"📝 Registry não encontrado, criando novo em {registry_path}")
        return {}
    
    try:
        with open(registry_path, 'r', encoding='utf-8') as f:
            registry = json.load(f)
        return registry
    except Exception as e:
        logger.warning(f"⚠️  Erro ao carregar registry: {str(e)}, retornando registry vazio")
        return {}


def save_registry(registry: Dict[str, Any]) -> None:
    """
    Salva o registry de modelos no arquivo JSON.
    
    Args:
        registry: Dict com informações dos modelos
    """
    registry_path = get_registry_path()
    
    try:
        with open(registry_path, 'w', encoding='utf-8') as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ Registry salvo em {registry_path}")
    except Exception as e:
        logger.error(f"❌ Erro ao salvar registry: {str(e)}")
        raise


def get_model_info(tipo: str) -> Optional[Dict[str, Any]]:
    """
    Obtém informações de um modelo específico.
    
    Args:
        tipo: Tipo do modelo ("churn", "meta_risk", "oportunidades")
        
    Returns:
        Dict com informações do modelo ou None se não encontrado
    """
    registry = load_registry()
    return registry.get(tipo)


def update_model_info(tipo: str, info: Dict[str, Any]) -> None:
    """
    Atualiza informações de um modelo no registry.
    
    Args:
        tipo: Tipo do modelo ("churn", "meta_risk", "oportunidades")
        info: Dict com informações do modelo (path, trained_at, mes_inicio, mes_fim, n_samples, etc.)
    """
    registry = load_registry()
    registry[tipo] = info
    save_registry(registry)
    logger.info(f"✅ Registry atualizado para modelo '{tipo}'")


def list_models() -> Dict[str, Any]:
    """
    Lista todos os modelos no registry.
    
    Returns:
        Dict completo do registry
    """
    return load_registry()


def model_exists(tipo: str) -> bool:
    """
    Verifica se um modelo existe no registry.
    
    Args:
        tipo: Tipo do modelo
        
    Returns:
        True se o modelo existe, False caso contrário
    """
    registry = load_registry()
    return tipo in registry and registry[tipo].get("treinado", False)

