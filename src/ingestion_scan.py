"""
Módulo utilitário para escanear e detectar tipos de arquivos CSV no diretório data_raw.

Este módulo contém funções para:
- Detectar o tipo de arquivo CSV (clientes, vendas, metas_vendedor, metas_departamento)
- Escanear o diretório data_raw e organizar arquivos por tipo
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from collections import defaultdict
import os

from src.config import config

logger = logging.getLogger(__name__)

# Flag de debug (pode ser controlada via variável de ambiente)
DEBUG_DETECT_FILE_TYPE = os.getenv("DEBUG_DETECT_FILE_TYPE", "false").lower() == "true"


def extract_mes_ano(filename: str, filename_lower: str) -> Optional[str]:
    """
    Extrai mês/ano do nome do arquivo.
    
    Suporta múltiplos formatos:
    - "Janeiro25", "Janeiro 25", "Janeiro-25", "Janeiro-2025"
    - "2025-01", "2025_01"
    - "Jan25", "Jan 25"
    
    Args:
        filename: Nome do arquivo original (case-sensitive para regex)
        filename_lower: Nome do arquivo em minúsculas
        
    Returns:
        Optional[str]: mês/ano no formato "YYYY-MM" ou None
    """
    meses_nomes_completos = {
        'janeiro': '01', 'fevereiro': '02', 'marco': '03', 'março': '03',
        'abril': '04', 'maio': '05', 'junho': '06',
        'julho': '07', 'agosto': '08', 'setembro': '09',
        'outubro': '10', 'novembro': '11', 'dezembro': '12'
    }
    
    meses_abreviados = {
        'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04',
        'mai': '05', 'jun': '06', 'jul': '07', 'ago': '08',
        'set': '09', 'out': '10', 'nov': '11', 'dez': '12'
    }
    
    # Padrão 1: "MêsAno" ou "Mês-Ano" ou "Mês Ano" (ex.: "Janeiro25", "Janeiro-25", "Janeiro 25")
    # IMPORTANTE: Verificar anos completos (4 dígitos) ANTES de anos com 2 dígitos para evitar falsos positivos
    # Procura por nome completo do mês
    for mes_nome, mes_num in meses_nomes_completos.items():
        # Padrão 1a: "mesnome" seguido de 4 dígitos (ano completo) - PRIORIDADE ALTA
        # Ex.: "janeiro2025", "janeiro-2025", "janeiro 2025"
        pattern_full_year = rf'{re.escape(mes_nome)}[-\s]?(\d{{4}})'
        match = re.search(pattern_full_year, filename_lower)
        if match:
            ano = match.group(1)
            mes_ano = f"{ano}-{mes_num}"
            if DEBUG_DETECT_FILE_TYPE:
                logger.debug(f"Extraído mês/ano (padrão completo, ano 4 dígitos): {mes_ano} de '{filename}'")
            return mes_ano
        
        # Padrão 1b: "mesnome" seguido de 2 dígitos (ano abreviado) - PRIORIDADE BAIXA
        # Ex.: "janeiro25", "janeiro-25", "janeiro 25"
        # Usa lookahead negativo para garantir que não é parte de um ano de 4 dígitos
        pattern = rf'{re.escape(mes_nome)}[-\s]?(\d{{2}})(?!\d)'
        match = re.search(pattern, filename_lower)
        if match:
            ano = match.group(1)
            mes_ano = f"20{ano}-{mes_num}"
            if DEBUG_DETECT_FILE_TYPE:
                logger.debug(f"Extraído mês/ano (padrão completo): {mes_ano} de '{filename}'")
            return mes_ano
    
    # Padrão 2: Nome abreviado do mês (ex.: "jan25", "jan 25", "jan-25")
    # IMPORTANTE: Verificar anos completos ANTES de anos com 2 dígitos
    for mes_abrev, mes_num in meses_abreviados.items():
        # Padrão 2a: "mesabrev" seguido de 4 dígitos (ano completo) - PRIORIDADE ALTA
        # Ex.: "jan2025", "jan-2025", "jan 2025"
        pattern_abrev_full_year = rf'{re.escape(mes_abrev)}[-\s]?(\d{{4}})'
        match = re.search(pattern_abrev_full_year, filename_lower)
        if match:
            ano = match.group(1)
            mes_ano = f"{ano}-{mes_num}"
            if DEBUG_DETECT_FILE_TYPE:
                logger.debug(f"Extraído mês/ano (padrão abreviado, ano 4 dígitos): {mes_ano} de '{filename}'")
            return mes_ano
        
        # Padrão 2b: "mesabrev" seguido de 2 dígitos (ano abreviado) - PRIORIDADE BAIXA
        # Ex.: "jan25", "jan-25", "jan 25"
        # Usa lookahead negativo para garantir que não é parte de um ano de 4 dígitos
        pattern_abrev = rf'{re.escape(mes_abrev)}[-\s]?(\d{{2}})(?!\d)'
        match = re.search(pattern_abrev, filename_lower)
        if match:
            ano = match.group(1)
            mes_ano = f"20{ano}-{mes_num}"
            if DEBUG_DETECT_FILE_TYPE:
                logger.debug(f"Extraído mês/ano (padrão abreviado): {mes_ano} de '{filename}'")
            return mes_ano
    
    # Padrão 3: "Ano-Mês" ou "Ano_Mês" (ex.: "2025-01", "2025_01")
    date_pattern = r'(\d{4})[-_](\d{1,2})'
    match = re.search(date_pattern, filename)
    if match:
        ano, mes = match.groups()
        mes_ano = f"{ano}-{mes.zfill(2)}"
        if DEBUG_DETECT_FILE_TYPE:
            logger.debug(f"Extraído mês/ano (padrão data): {mes_ano} de '{filename}'")
        return mes_ano
    
    return None


def detect_file_type(filename: str) -> Tuple[str, Dict]:
    """
    Detecta o tipo de arquivo pelo nome.
    
    Esta função verifica o nome do arquivo e classifica em uma das categorias:
    - 'clientes': arquivos com 'cliente'/'clientes' E 'ativo'/'ativos'
    - 'vendas': arquivos com 'venda'/'vendas' OU 'detalhe'/'detalhes'
    - 'metas_vendedor': arquivos com 'meta'/'metas' E 'vendedor'/'vendedores'
    - 'metas_departamento': arquivos com 'meta'/'metas' E ('departamento' OU 'depto')
    - 'unknown': não classificado
    
    A verificação é case-insensitive.
    
    Args:
        filename: Nome do arquivo
        
    Returns:
        Tuple[str, Dict]: (tipo, metadados)
        Tipos: 'clientes', 'vendas', 'metas_vendedor', 'metas_departamento', 'unknown'
    """
    filename_lower = filename.lower()
    
    if DEBUG_DETECT_FILE_TYPE:
        logger.debug(f"Detectando tipo para arquivo: '{filename}'")
    
    # Clientes ativos: deve conter "cliente"/"clientes" E "ativo"/"ativos"
    has_cliente = any(term in filename_lower for term in ['cliente', 'clientes'])
    has_ativo = any(term in filename_lower for term in ['ativo', 'ativos'])
    
    if has_cliente and has_ativo:
        if DEBUG_DETECT_FILE_TYPE:
            logger.debug(f"Classificado como 'clientes': '{filename}'")
        return 'clientes', {}
    
    # Vendas: deve conter "venda"/"vendas" OU "detalhe"/"detalhes"
    has_venda = any(term in filename_lower for term in ['venda', 'vendas'])
    has_detalhe = any(term in filename_lower for term in ['detalhe', 'detalhes'])
    
    if has_venda or has_detalhe:
        periodo = extract_mes_ano(filename, filename_lower)
        if DEBUG_DETECT_FILE_TYPE:
            logger.debug(f"Classificado como 'vendas' (periodo={periodo}): '{filename}'")
        return 'vendas', {'periodo_referencia': periodo}
    
    # Metas por vendedor: deve conter "meta"/"metas" E "vendedor"/"vendedores"
    has_meta = any(term in filename_lower for term in ['meta', 'metas'])
    has_vendedor = any(term in filename_lower for term in ['vendedor', 'vendedores'])
    
    if has_meta and has_vendedor:
        mes_ano = extract_mes_ano(filename, filename_lower)
        if not mes_ano:
            # Se não encontrou, usa mês atual como fallback
            mes_ano = f"{datetime.now().year}-{datetime.now().month:02d}"
            if DEBUG_DETECT_FILE_TYPE:
                logger.warning(f"Não foi possível extrair mês/ano de '{filename}', usando mês atual: {mes_ano}")
        else:
            if DEBUG_DETECT_FILE_TYPE:
                logger.debug(f"Classificado como 'metas_vendedor' (mes_ano={mes_ano}): '{filename}'")
        return 'metas_vendedor', {'mes_ano': mes_ano}
    
    # Metas por departamento: deve conter "meta"/"metas" E ("departamento" OU "depto")
    has_departamento = any(term in filename_lower for term in ['departamento', 'depto'])
    
    if has_meta and has_departamento:
        mes_ano = extract_mes_ano(filename, filename_lower)
        if not mes_ano:
            # Se não encontrou, usa mês atual como fallback
            mes_ano = f"{datetime.now().year}-{datetime.now().month:02d}"
            if DEBUG_DETECT_FILE_TYPE:
                logger.warning(f"Não foi possível extrair mês/ano de '{filename}', usando mês atual: {mes_ano}")
        else:
            if DEBUG_DETECT_FILE_TYPE:
                logger.debug(f"Classificado como 'metas_departamento' (mes_ano={mes_ano}): '{filename}'")
        return 'metas_departamento', {'mes_ano': mes_ano}
    
    # Não classificado
    if DEBUG_DETECT_FILE_TYPE:
        logger.debug(f"Classificado como 'unknown': '{filename}'")
    return 'unknown', {}


def scan_data_raw() -> Dict[str, List[Tuple[Path, Dict]]]:
    """
    Escaneia a pasta data_raw/ e organiza arquivos por tipo.
    
    Returns:
        Dict[str, List[Tuple[Path, Dict]]]: Dicionário com arquivos organizados por tipo
    """
    data_raw_dir = config.paths.data_raw_dir
    
    if not data_raw_dir.exists():
        return {}
    
    files_by_type = defaultdict(list)
    
    # Busca arquivos CSV (inclui subdiretórios)
    csv_files = list(data_raw_dir.rglob('*.csv'))
    
    if not csv_files:
        return {}
    
    for csv_file in csv_files:
        file_type, metadata = detect_file_type(csv_file.name)
        files_by_type[file_type].append((csv_file, metadata))
    
    return dict(files_by_type)

