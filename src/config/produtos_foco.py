"""
Configuração de Produtos de Foco.

Este módulo gerencia o mapeamento de produtos-chave (marcas conhecidas) para
códigos de produto e termos de busca, permitindo buscas otimizadas.
"""

import os
import logging
import re
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Tenta importar YAML, fallback para JSON se não disponível
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    import json

# Caminho do arquivo de configuração
_CONFIG_FILE = Path(__file__).parent / "produtos_foco.yaml"
_JSON_CONFIG_FILE = Path(__file__).parent / "produtos_foco.json"

# Cache global para evitar recarregar múltiplas vezes
_cached_config: Optional[Dict] = None


def _normalize_text(text: str) -> str:
    """
    Normaliza texto para comparação (lowercase, remove acentos simples).
    
    Args:
        text: Texto a normalizar
        
    Returns:
        str: Texto normalizado
    """
    if not text:
        return ""
    
    # Converte para lowercase
    text = text.lower().strip()
    
    # Remove acentos básicos (pode ser expandido para incluir todos os acentos)
    replacements = {
        'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a', 'ä': 'a',
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
        'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
        'ó': 'o', 'ò': 'o', 'õ': 'o', 'ô': 'o', 'ö': 'o',
        'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
        'ç': 'c', 'ñ': 'n'
    }
    
    for accent, replacement in replacements.items():
        text = text.replace(accent, replacement)
    
    return text


def carregar_produtos_foco(force_reload: bool = False) -> Dict:
    """
    Carrega a configuração de produtos de foco do arquivo YAML/JSON.
    
    Args:
        force_reload: Se True, força recarregar mesmo se já estiver em cache
        
    Returns:
        dict: Dicionário com a configuração de produtos
            {
                "nissin": {
                    "termos": ["nissin", "miojo"],
                    "codigos": ["12345", "67890"]
                },
                ...
            }
    """
    global _cached_config
    
    # Retorna cache se disponível e não forçar reload
    if _cached_config is not None and not force_reload:
        return _cached_config
    
    # Tenta carregar YAML primeiro
    config = None
    if HAS_YAML and _CONFIG_FILE.exists():
        try:
            with open(_CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                logger.info(f"Configuração de produtos de foco carregada de {_CONFIG_FILE}")
        except Exception as e:
            logger.warning(f"Erro ao carregar YAML: {str(e)}, tentando JSON...")
            config = None
    
    # Fallback para JSON
    if config is None and _JSON_CONFIG_FILE.exists():
        try:
            with open(_JSON_CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logger.info(f"Configuração de produtos de foco carregada de {_JSON_CONFIG_FILE}")
        except Exception as e:
            logger.error(f"Erro ao carregar JSON: {str(e)}")
            config = None
    
    # Se não encontrou nenhum arquivo, cria configuração padrão
    if config is None:
        logger.warning(
            f"Nenhum arquivo de configuração encontrado em {_CONFIG_FILE} ou {_JSON_CONFIG_FILE}. "
            f"Usando configuração vazia."
        )
        config = {}
    
    # Garante estrutura consistente
    if not isinstance(config, dict):
        logger.error("Configuração inválida: não é um dicionário")
        config = {}
    
    # Normaliza estrutura: garante que cada produto tenha 'termos' e 'codigos'
    for produto_key, produto_config in config.items():
        if not isinstance(produto_config, dict):
            logger.warning(f"Configuração inválida para produto '{produto_key}': não é um dicionário")
            continue
        
        # Garante que termos e codigos existam
        if 'termos' not in produto_config:
            produto_config['termos'] = []
        if 'codigos' not in produto_config:
            produto_config['codigos'] = []
        
        # Normaliza listas
        if not isinstance(produto_config['termos'], list):
            produto_config['termos'] = []
        if not isinstance(produto_config['codigos'], list):
            produto_config['codigos'] = []
    
    _cached_config = config
    return config


def obter_codigos_por_nome(nome_produto: str) -> List[str]:
    """
    Obtém lista de códigos de produto para um nome de produto específico.
    
    Faz match por:
    1. Chave exata (ex.: "nissin" -> "nissin")
    2. Termos dentro do nome (ex.: "produto nissin" -> "nissin")
    
    Args:
        nome_produto: Nome do produto a buscar (ex.: "nissin", "Nissin", "produto Nissin")
        
    Returns:
        list[str]: Lista de códigos de produto encontrados, ou lista vazia se não encontrar
    """
    if not nome_produto or not nome_produto.strip():
        return []
    
    # Carrega configuração
    config = carregar_produtos_foco()
    
    if not config:
        logger.debug("Nenhuma configuração de produtos de foco disponível")
        return []
    
    # Normaliza nome do produto para busca
    nome_normalizado = _normalize_text(nome_produto)
    
    # Estratégia 1: Match por chave exata (normalizada)
    for produto_key, produto_config in config.items():
        produto_key_normalizado = _normalize_text(produto_key)
        
        # Match exato na chave
        if nome_normalizado == produto_key_normalizado:
            codigos = produto_config.get('codigos', [])
            if codigos:
                logger.info(
                    f"Match exato encontrado para '{nome_produto}' -> produto '{produto_key}' "
                    f"com {len(codigos)} código(s)"
                )
                return codigos
    
    # Estratégia 2: Match por termos
    for produto_key, produto_config in config.items():
        termos = produto_config.get('termos', [])
        
        # Verifica se algum termo está contido no nome do produto
        for termo in termos:
            termo_normalizado = _normalize_text(termo)
            
            # Match se o termo estiver contido no nome OU o nome estiver contido no termo
            if termo_normalizado in nome_normalizado or nome_normalizado in termo_normalizado:
                codigos = produto_config.get('codigos', [])
                
                # Se encontrou match mas não tem códigos, retorna lista vazia
                # (o sistema usará fallback por termo)
                if codigos:
                    logger.info(
                        f"Match por termo encontrado para '{nome_produto}' -> produto '{produto_key}' "
                        f"(termo: '{termo}') com {len(codigos)} código(s)"
                    )
                    return codigos
                else:
                    logger.debug(
                        f"Match por termo encontrado para '{nome_produto}' -> produto '{produto_key}' "
                        f"(termo: '{termo}'), mas sem códigos configurados (usará fallback)"
                    )
                    # Retorna lista vazia para forçar uso do termo como fallback
                    return []
    
    logger.debug(f"Nenhum match encontrado para produto '{nome_produto}'")
    return []


def obter_termos_por_nome(nome_produto: str) -> Optional[List[str]]:
    """
    Obtém lista de termos de busca para um nome de produto específico.
    
    Útil quando não há códigos configurados e precisa usar busca por termo.
    
    Args:
        nome_produto: Nome do produto a buscar
        
    Returns:
        list[str] | None: Lista de termos de busca, ou None se não encontrar
    """
    if not nome_produto or not nome_produto.strip():
        return None
    
    config = carregar_produtos_foco()
    
    if not config:
        return None
    
    nome_normalizado = _normalize_text(nome_produto)
    
    # Match por chave ou termos (similar ao obter_codigos_por_nome)
    for produto_key, produto_config in config.items():
        produto_key_normalizado = _normalize_text(produto_key)
        
        # Match exato na chave
        if nome_normalizado == produto_key_normalizado:
            termos = produto_config.get('termos', [])
            if termos:
                return termos
        
        # Match por termos
        termos = produto_config.get('termos', [])
        for termo in termos:
            termo_normalizado = _normalize_text(termo)
            if termo_normalizado in nome_normalizado or nome_normalizado in termo_normalizado:
                if termos:
                    return termos
    
    return None




