"""
Funções utilitárias para ETL.

Este módulo contém funções auxiliares para normalização, parsing de datas,
limpeza de dados, etc.
"""

import re
from datetime import datetime
from typing import Optional, Any
import unicodedata
import logging

logger = logging.getLogger(__name__)


def normalize_name(name: Any) -> str:
    """
    Normaliza nome removendo espaços extras, convertendo para maiúsculas e removendo acentos.
    
    Args:
        name: Nome a normalizar (pode ser string, float, etc.)
        
    Returns:
        String normalizada
    """
    if name is None:
        return ""
    
    # Converte para string
    name_str = str(name).strip()
    
    if not name_str or name_str.lower() in ["nan", "none", ""]:
        return ""
    
    # Remove acentos
    name_str = unicodedata.normalize('NFKD', name_str)
    name_str = ''.join(c for c in name_str if not unicodedata.combining(c))
    
    # Remove espaços extras
    name_str = re.sub(r'\s+', ' ', name_str).strip()
    
    return name_str.upper()


def parse_br_date(date_str: Any) -> Optional[datetime]:
    """
    Parse data no formato brasileiro (DD/MM/YYYY ou DD/MM/YY).
    
    Args:
        date_str: String com data no formato brasileiro
        
    Returns:
        datetime object ou None se não conseguir parsear
    """
    if date_str is None or str(date_str).strip() == "":
        return None
    
    date_str = str(date_str).strip()
    
    # Tenta formatos comuns
    formats = [
        "%d/%m/%Y",  # 01/01/2025
        "%d/%m/%y",  # 01/01/25
        "%Y-%m-%d",  # 2025-01-01
        "%d-%m-%Y",  # 01-01-2025
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    logger.warning(f"Não foi possível parsear data: {date_str}")
    return None


def parse_br_currency(value: Any) -> float:
    """
    Parse valor monetário brasileiro (R$ 1.234,56).
    
    Args:
        value: String ou número com valor monetário
        
    Returns:
        float com o valor numérico
    """
    if value is None:
        return 0.0
    
    if isinstance(value, (int, float)):
        return float(value)
    
    value_str = str(value).strip()
    
    # Remove prefixos
    value_str = re.sub(r'^R\$\s*', '', value_str, flags=re.IGNORECASE)
    value_str = value_str.strip()
    
    # Remove espaços
    value_str = value_str.replace(' ', '')
    
    # Se tem vírgula, assume formato brasileiro (1.234,56)
    if ',' in value_str:
        # Remove pontos (milhares) e substitui vírgula por ponto
        value_str = value_str.replace('.', '').replace(',', '.')
    # Se tem ponto mas não vírgula, pode ser formato americano (1234.56)
    elif '.' in value_str and value_str.count('.') == 1:
        # Assume formato americano
        pass
    # Se tem múltiplos pontos, assume formato brasileiro
    elif value_str.count('.') > 1:
        value_str = value_str.replace('.', '').replace(',', '.')
    
    try:
        # Remove qualquer caractere não numérico exceto ponto e menos
        value_str = re.sub(r'[^\d\.\-]', '', value_str)
        return float(value_str)
    except (ValueError, TypeError):
        logger.warning(f"Não foi possível parsear valor monetário: {value}")
        return 0.0


def parse_br_percent(value: Any) -> float:
    """
    Parse percentual brasileiro (96,75%).
    
    Args:
        value: String ou número com percentual
        
    Returns:
        float com o valor numérico (ex.: 96.75 para "96,75%")
    """
    if value is None:
        return 0.0
    
    if isinstance(value, (int, float)):
        return float(value)
    
    value_str = str(value).strip()
    
    # Remove símbolo de percentual
    value_str = value_str.replace('%', '').strip()
    
    # Remove espaços
    value_str = value_str.replace(' ', '')
    
    # Se tem vírgula, assume formato brasileiro
    if ',' in value_str:
        value_str = value_str.replace('.', '').replace(',', '.')
    
    try:
        return float(value_str)
    except (ValueError, TypeError):
        logger.warning(f"Não foi possível parsear percentual: {value}")
        return 0.0


def parse_integer(value: Any) -> Optional[int]:
    """
    Parse valor inteiro, tratando formatos brasileiros.
    
    Args:
        value: String ou número
        
    Returns:
        int ou None
    """
    if value is None:
        return None
    
    if isinstance(value, int):
        return value
    
    if isinstance(value, float):
        return int(value)
    
    value_str = str(value).strip()
    
    # Remove espaços e caracteres não numéricos exceto vírgula/ponto
    value_str = re.sub(r'[^\d,\.]', '', value_str)
    
    # Se tem vírgula, assume formato brasileiro
    if ',' in value_str:
        value_str = value_str.replace('.', '').replace(',', '.')
    
    try:
        return int(float(value_str))
    except (ValueError, TypeError):
        logger.warning(f"Não foi possível parsear inteiro: {value}")
        return None


def extract_mes_ano_from_filename(filename: str) -> Optional[tuple]:
    """
    Extrai mês e ano do nome do arquivo.
    
    Args:
        filename: Nome do arquivo (ex.: "Metas X Realizado Vendedor - Agosto25.xlsx")
        
    Returns:
        Tupla (ano, mes) ou None
    """
    # Mapeamento de meses
    meses_map = {
        "janeiro": 1, "jan": 1,
        "fevereiro": 2, "fev": 2,
        "março": 3, "mar": 3,
        "abril": 4, "abr": 4,
        "maio": 5, "mai": 5,
        "junho": 6, "jun": 6,
        "julho": 7, "jul": 7,
        "agosto": 8, "ago": 8,
        "setembro": 9, "set": 9,
        "outubro": 10, "out": 10,
        "novembro": 11, "nov": 11,
        "dezembro": 12, "dez": 12,
    }
    
    filename_lower = filename.lower()
    
    # Procura por padrão "MêsYY" ou "Mês YY"
    for mes_nome, mes_num in meses_map.items():
        pattern = rf"{mes_nome}(\d{{2}})"
        match = re.search(pattern, filename_lower)
        if match:
            ano_str = match.group(1)
            ano = 2000 + int(ano_str)
            return (ano, mes_num)
    
    # Procura por padrão "Mês-YY" ou "Mês YY" em vendas
    for mes_nome, mes_num in meses_map.items():
        pattern = rf"{mes_nome}[-\s](\d{{4}})"
        match = re.search(pattern, filename_lower)
        if match:
            ano = int(match.group(1))
            return (ano, mes_num)
    
    # Procura por bimestres (Jan-fev, Mar-Abr, etc.)
    bimestres_map = {
        ("jan", "fev"): (1, 2),
        ("mar", "abr"): (3, 4),
        ("mai", "jun"): (5, 6),
        ("jul", "ago"): (7, 8),
        ("set", "out"): (9, 10),
        ("nov", "dez"): (11, 12),
    }
    
    for (mes1, mes2), (mes_num1, mes_num2) in bimestres_map.items():
        if mes1 in filename_lower and mes2 in filename_lower:
            # Extrai ano
            ano_match = re.search(r'(\d{4})', filename)
            if ano_match:
                ano = int(ano_match.group(1))
                # Retorna o primeiro mês do bimestre
                return (ano, mes_num1)
    
    logger.warning(f"Não foi possível extrair mês/ano do arquivo: {filename}")
    return None


def clean_cnpj_cpf(value: Any) -> Optional[str]:
    """
    Limpa e formata CNPJ/CPF.
    
    Args:
        value: CNPJ/CPF a limpar
        
    Returns:
        String limpa ou None
    """
    if value is None:
        return None
    
    value_str = str(value).strip()
    
    # Remove caracteres não numéricos
    value_str = re.sub(r'[^\d]', '', value_str)
    
    if not value_str or value_str == "0":
        return None
    
    return value_str


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Converte valor para float de forma segura.
    
    Args:
        value: Valor a converter
        default: Valor padrão se conversão falhar
        
    Returns:
        float
    """
    if value is None:
        return default
    
    if isinstance(value, (int, float)):
        return float(value)
    
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    """
    Converte valor para int de forma segura.
    
    Args:
        value: Valor a converter
        default: Valor padrão se conversão falhar
        
    Returns:
        int ou None
    """
    if value is None:
        return default
    
    if isinstance(value, int):
        return value
    
    if isinstance(value, float):
        return int(value)
    
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default

