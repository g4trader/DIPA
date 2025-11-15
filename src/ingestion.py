"""
Pipeline de Ingestão de Dados da Dipam.

Este módulo contém funções robustas para carregar e processar CSVs,
com detecção automática de separadores, normalização de colunas,
conversão de datas e valores monetários brasileiros.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import re
import logging
from datetime import datetime
import hashlib

from src.config import config

logger = logging.getLogger(__name__)


def detect_separator(file_path: str, sample_lines: int = 5) -> str:
    """
    Detecta automaticamente o separador do CSV.
    
    Testa os separadores mais comuns (',', ';', '\t') e retorna
    o que gerar mais colunas consistentes.
    
    Args:
        file_path: Caminho para o arquivo CSV
        sample_lines: Número de linhas para amostrar
        
    Returns:
        str: Separador detectado (',' ou ';' ou '\t')
    """
    separators = [',', ';', '\t']
    best_sep = ','
    max_cols = 0
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = [f.readline() for _ in range(sample_lines)]
        
        for sep in separators:
            cols_per_line = [len(line.split(sep)) for line in lines if line.strip()]
            if cols_per_line:
                avg_cols = sum(cols_per_line) / len(cols_per_line)
                # Penaliza separadores que geram muitas colunas (provavelmente incorretos)
                if 2 <= avg_cols <= 50 and avg_cols > max_cols:
                    max_cols = avg_cols
                    best_sep = sep
    except Exception as e:
        logger.warning(f"Erro ao detectar separador: {str(e)}, usando ',' como padrão")
        return ','
    
    logger.info(f"Separador detectado: '{best_sep}'")
    return best_sep


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza nomes de colunas para lower_snake_case.
    
    Remove espaços, acentos, caracteres especiais e converte para snake_case.
    
    Args:
        df: DataFrame com colunas originais
        
    Returns:
        pd.DataFrame: DataFrame com colunas normalizadas
    """
    df_normalized = df.copy()
    
    def to_snake_case(name: str) -> str:
        """Converte nome para snake_case."""
        if pd.isna(name):
            return "unnamed"
        
        # Converte para string e remove espaços
        name = str(name).strip()
        
        # Remove acentos (simplificado)
        name = name.lower()
        name = name.replace('á', 'a').replace('à', 'a').replace('ã', 'a').replace('â', 'a')
        name = name.replace('é', 'e').replace('ê', 'e')
        name = name.replace('í', 'i').replace('î', 'i')
        name = name.replace('ó', 'o').replace('ô', 'o').replace('õ', 'o')
        name = name.replace('ú', 'u').replace('û', 'u')
        name = name.replace('ç', 'c')
        
        # Remove caracteres especiais e converte espaços para underscore
        name = re.sub(r'[^a-z0-9_]+', '_', name)
        name = re.sub(r'_+', '_', name)  # Remove underscores duplicados
        name = name.strip('_')  # Remove underscores no início/fim
        
        return name
    
    df_normalized.columns = [to_snake_case(col) for col in df_normalized.columns]
    
    logger.info(f"Colunas normalizadas: {list(df_normalized.columns)}")
    return df_normalized


def convert_brazilian_date(date_str: str, date_format: Optional[str] = None) -> Optional[datetime]:
    """
    Converte data do formato brasileiro (dd/mm/aaaa) para datetime.
    
    Args:
        date_str: String com data no formato brasileiro
        date_format: Formato específico (None = tenta inferir)
        
    Returns:
        datetime ou None se não conseguir converter
    """
    if pd.isna(date_str) or date_str == '':
        return None
    
    date_str = str(date_str).strip()
    
    # Formatos comuns brasileiros
    formats = [
        '%d/%m/%Y',      # 31/12/2024
        '%d-%m-%Y',      # 31-12-2024
        '%d/%m/%y',      # 31/12/24
        '%d-%m-%y',      # 31-12-24
        '%Y-%m-%d',      # 2024-12-31 (ISO)
        '%d/%m/%Y %H:%M:%S',  # Com hora
    ]
    
    if date_format:
        formats = [date_format] + formats
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # Tenta com pandas (mais flexível)
    try:
        return pd.to_datetime(date_str, dayfirst=True, errors='coerce')
    except:
        pass
    
    logger.warning(f"Não foi possível converter data: {date_str}")
    return None


def convert_brazilian_currency(value: str) -> float:
    """
    Converte valor monetário brasileiro (R$ 1.234,56) para float.
    
    Args:
        value: String com valor monetário (ex.: "R$ 1.234,56" ou "-R$ 91,94")
        
    Returns:
        float: Valor numérico (0.0 se não conseguir converter)
    """
    if pd.isna(value) or value == '':
        return 0.0
    
    value_str = str(value).strip()
    
    # Remove símbolos de moeda
    value_str = re.sub(r'R\$\s*', '', value_str, flags=re.IGNORECASE)
    value_str = re.sub(r'\$\s*', '', value_str)
    
    # Detecta sinal negativo
    is_negative = '-' in value_str or value_str.startswith('(')
    value_str = value_str.replace('-', '').replace('(', '').replace(')', '')
    
    # Remove espaços
    value_str = value_str.strip()
    
    # Remove separador de milhares (ponto) e converte vírgula para ponto decimal
    if ',' in value_str:
        # Tem vírgula, então o ponto é separador de milhares
        value_str = value_str.replace('.', '').replace(',', '.')
    elif '.' in value_str:
        # Tem ponto mas não vírgula - pode ser decimal ou milhares
        # Se tiver mais de 3 dígitos após o ponto, provavelmente é decimal
        parts = value_str.split('.')
        if len(parts) == 2 and len(parts[1]) <= 2:
            # Decimal
            pass
        else:
            # Milhares
            value_str = value_str.replace('.', '')
    
    try:
        result = float(value_str)
        return -result if is_negative else result
    except (ValueError, TypeError):
        logger.warning(f"Não foi possível converter valor monetário: {value}")
        return 0.0


def convert_brazilian_number(value: str) -> float:
    """
    Converte número brasileiro com vírgula (ex.: "141.676,56") para float.
    
    Args:
        value: String com número brasileiro
        
    Returns:
        float: Valor numérico (0.0 se não conseguir converter)
    """
    if pd.isna(value) or value == '':
        return 0.0
    
    value_str = str(value).strip()
    
    # Detecta sinal negativo
    is_negative = '-' in value_str or value_str.startswith('(')
    value_str = value_str.replace('-', '').replace('(', '').replace(')', '')
    
    # Remove espaços
    value_str = value_str.strip()
    
    # Se tem vírgula, o ponto é separador de milhares
    if ',' in value_str:
        value_str = value_str.replace('.', '').replace(',', '.')
    # Se só tem ponto, pode ser decimal ou milhares
    elif '.' in value_str:
        parts = value_str.split('.')
        if len(parts) == 2 and len(parts[1]) <= 2:
            # Decimal
            pass
        else:
            # Milhares
            value_str = value_str.replace('.', '')
    
    try:
        result = float(value_str)
        return -result if is_negative else result
    except (ValueError, TypeError):
        logger.warning(f"Não foi possível converter número: {value}")
        return 0.0


def convert_percentage(value: str) -> float:
    """
    Converte percentual (ex.: "95,5%" ou "95.5%") para float.
    
    Args:
        value: String com percentual
        
    Returns:
        float: Percentual como número (0.0 se não conseguir converter)
    """
    if pd.isna(value) or value == '':
        return 0.0
    
    value_str = str(value).strip()
    
    # Remove símbolo de percentual
    value_str = value_str.replace('%', '').strip()
    
    # Converte vírgula para ponto se necessário
    if ',' in value_str:
        value_str = value_str.replace('.', '').replace(',', '.')
    
    try:
        return float(value_str)
    except (ValueError, TypeError):
        logger.warning(f"Não foi possível converter percentual: {value}")
        return 0.0


def load_csv_robust(
    csv_path: str,
    encoding: str = 'utf-8',
    sep: Optional[str] = None,
    skiprows: Optional[int] = None,
    nrows: Optional[int] = None
) -> pd.DataFrame:
    """
    Carrega CSV de forma robusta com detecção automática de separador e encoding.
    
    Args:
        csv_path: Caminho para o arquivo CSV
        encoding: Encoding do arquivo (tenta utf-8 primeiro, depois latin-1)
        sep: Separador (None = detecta automaticamente)
        skiprows: Linhas para pular no início
        nrows: Número máximo de linhas para ler
        
    Returns:
        pd.DataFrame: DataFrame carregado
    """
    csv_path = Path(csv_path)
    
    if not csv_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {csv_path}")
    
    # Detecta separador se não fornecido
    if sep is None:
        sep = detect_separator(str(csv_path))
    
    # Tenta carregar com encoding fornecido
    try:
        df = pd.read_csv(
            csv_path,
            encoding=encoding,
            sep=sep,
            skiprows=skiprows,
            nrows=nrows,
            low_memory=False
        )
    except UnicodeDecodeError:
        # Tenta com latin-1 se utf-8 falhar
        logger.warning(f"Encoding {encoding} falhou, tentando latin-1")
        df = pd.read_csv(
            csv_path,
            encoding='latin-1',
            sep=sep,
            skiprows=skiprows,
            nrows=nrows,
            low_memory=False
        )
    
    # Remove espaços em branco das colunas
    df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    
    # Normaliza nomes de colunas
    df = normalize_column_names(df)
    
    logger.info(f"CSV carregado: {len(df)} linhas, {len(df.columns)} colunas")
    
    return df


def generate_client_id(cnpj_cpf: str, codigo: str) -> str:
    """
    Gera ID consistente para cliente baseado em CNPJ/CPF e código.
    
    Args:
        cnpj_cpf: CNPJ/CPF do cliente
        codigo: Código do cliente
        
    Returns:
        str: ID único do cliente
    """
    # Usa código se disponível, senão usa hash do CNPJ/CPF
    if pd.notna(codigo) and str(codigo).strip():
        return str(codigo).strip()
    
    if pd.notna(cnpj_cpf) and str(cnpj_cpf).strip():
        # Remove formatação do CNPJ/CPF
        cnpj_clean = re.sub(r'[^0-9]', '', str(cnpj_cpf))
        if cnpj_clean:
            return cnpj_clean
    
    # Gera hash dos dois campos combinados
    combined = f"{cnpj_cpf}_{codigo}"
    return hashlib.md5(combined.encode()).hexdigest()[:16]


def load_clientes(csv_path: str) -> pd.DataFrame:
    """
    Carrega e processa CSV de clientes ativos.
    
    Args:
        csv_path: Caminho para o CSV de clientes
        
    Returns:
        pd.DataFrame: DataFrame processado com colunas normalizadas
    """
    logger.info(f"Carregando clientes de: {csv_path}")
    
    # Carrega CSV
    df = load_csv_robust(csv_path)
    
    # Gera ID do cliente
    # Tenta mapear campos comuns
    cnpj_field = None
    codigo_field = None
    
    for col in df.columns:
        col_lower = col.lower()
        if 'cnpj' in col_lower or 'cpf' in col_lower:
            cnpj_field = col
        if 'codigo' in col_lower and 'cliente' not in col_lower:
            codigo_field = col
    
    if cnpj_field and codigo_field:
        df['id_cliente'] = df.apply(
            lambda row: generate_client_id(
                row.get(cnpj_field, ''),
                row.get(codigo_field, '')
            ),
            axis=1
        )
    elif codigo_field:
        df['id_cliente'] = df[codigo_field].astype(str)
    elif cnpj_field:
        df['id_cliente'] = df.apply(
            lambda row: generate_client_id(row.get(cnpj_field, ''), ''),
            axis=1
        )
    else:
        # Usa índice como fallback
        df['id_cliente'] = df.index.astype(str)
    
    # Converte datas se houver
    date_columns = [col for col in df.columns if 'data' in col.lower() or 'cadastro' in col.lower()]
    for col in date_columns:
        df[col] = df[col].apply(convert_brazilian_date)
    
    logger.info(f"Clientes carregados: {len(df)} registros")
    
    return df


def load_vendas(csv_path: str, periodo_referencia: Optional[str] = None) -> pd.DataFrame:
    """
    Carrega e processa CSV de detalhes de vendas (bimestral).
    
    Args:
        csv_path: Caminho para o CSV de vendas
        periodo_referencia: Período de referência (ex.: "Nov-dez 2024")
        
    Returns:
        pd.DataFrame: DataFrame processado
    """
    logger.info(f"Carregando vendas de: {csv_path}")
    
    # Carrega CSV
    df = load_csv_robust(csv_path)
    
    # Converte coluna de data
    date_col = None
    for col in df.columns:
        if 'data' in col.lower() and 'venda' not in col.lower():
            date_col = col
            break
    
    if date_col:
        df['data_venda'] = df[date_col].apply(convert_brazilian_date)
    else:
        logger.warning("Coluna de data não encontrada")
    
    # Extrai mes_ano_referencia da data ou do período
    if 'data_venda' in df.columns:
        df['mes_ano_referencia'] = df['data_venda'].apply(
            lambda x: x.strftime('%Y-%m') if pd.notna(x) else None
        )
    elif periodo_referencia:
        # Tenta extrair mês/ano do período
        # Ex.: "Nov-dez 2024" -> ["2024-11", "2024-12"]
        meses = {
            'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04',
            'mai': '05', 'jun': '06', 'jul': '07', 'ago': '08',
            'set': '09', 'out': '10', 'nov': '11', 'dez': '12'
        }
        # Simplificado - assume que é bimestral
        df['mes_ano_referencia'] = periodo_referencia
    
    # Converte valores monetários
    currency_columns = [col for col in df.columns if any(
        term in col.lower() for term in ['valor', 'vlr', 'total', 'desconto']
    )]
    for col in currency_columns:
        if df[col].dtype == 'object':
            df[col] = df[col].apply(convert_brazilian_currency)
    
    # Converte quantidades (podem ter vírgula)
    qty_columns = [col for col in df.columns if any(
        term in col.lower() for term in ['qtd', 'quantidade', 'caixa', 'unidade']
    )]
    for col in qty_columns:
        if df[col].dtype == 'object':
            df[col] = df[col].apply(convert_brazilian_number)
    
    logger.info(f"Vendas carregadas: {len(df)} registros")
    
    return df


def load_metas_vendedor(csv_path: str, mes_ano: str) -> pd.DataFrame:
    """
    Carrega e processa CSV de Metas X Realizado por vendedor.
    
    Args:
        csv_path: Caminho para o CSV de metas
        mes_ano: Mês/ano de referência (ex.: "2024-12")
        
    Returns:
        pd.DataFrame: DataFrame processado
    """
    logger.info(f"Carregando metas de vendedor de: {csv_path}")
    
    # Carrega CSV
    df = load_csv_robust(csv_path)
    
    logger.debug(f"Shape inicial após load_csv_robust: {df.shape}")
    logger.debug(f"Colunas iniciais: {list(df.columns)}")
    
    # Remove espaços em branco de todas as células de string
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].apply(lambda x: str(x).strip() if pd.notna(x) else x)
    
    # Remove linhas completamente vazias
    df = df.dropna(how='all').copy()
    
    # Remove linha de totais (mais robusta)
    # Procura por linhas que contêm "Total" ou "TOTAL" em qualquer coluna
    # Mas evita remover linhas válidas que possam conter a palavra "total" em outro contexto
    if len(df) > 0:
        total_mask = df.apply(
            lambda row: any(
                pd.notna(val) and (
                    str(val).strip().upper() == 'TOTAL' or
                    str(val).strip().upper().startswith('TOTAL ') or
                    (len(str(val).strip()) < 20 and 'total' in str(val).lower() and 
                     any(char.isdigit() for char in str(val)) == False)  # Não é um valor numérico
                )
                for val in row.values
            ),
            axis=1
        )
        total_rows_count = total_mask.sum()
        df = df[~total_mask].copy()
        
        if total_rows_count > 0:
            logger.info(f"Linhas de totais removidas: {total_rows_count} linha(s)")
    
    # Adiciona coluna mes_ano
    df['mes_ano'] = mes_ano
    
    # Extrai ano e mês
    if '-' in mes_ano:
        ano, mes = mes_ano.split('-')
        df['ano'] = int(ano)
        df['mes'] = int(mes)
    
    # Mapeia colunas para campos normalizados
    # Procura coluna de vendedor (mais flexível)
    vendedor_col = None
    for col in df.columns:
        col_lower = col.lower()
        if any(term in col_lower for term in ['vendedor', 'rota', 'rca']):
            # Prioriza colunas que não são valores numéricos
            if df[col].dtype == 'object' or 'nome' in col_lower or 'vendedor' in col_lower:
                vendedor_col = col
                break
    
    # Se não encontrou, tenta a primeira coluna de texto
    if not vendedor_col:
        for col in df.columns:
            if df[col].dtype == 'object' and col.lower() not in ['mes_ano', 'ano', 'mes']:
                vendedor_col = col
                break
    
    if vendedor_col:
        df['vendedor_nome'] = df[vendedor_col].astype(str).str.strip()
        logger.debug(f"Coluna de vendedor mapeada: '{vendedor_col}' -> 'vendedor_nome'")
    else:
        logger.warning("Coluna de vendedor não encontrada!")
        df['vendedor_nome'] = ''
    
    # Normaliza valores monetários (mais robusta)
    valor_cols = {
        'meta_valor': ['valor_meta', 'meta_valor', 'meta'],
        'realizado_valor': ['vl_faturado', 'valor_faturado', 'vlr_faturado', 'faturado', 'realizado'],
        'valor_parado': ['vl_parado', 'valor_parado', 'vlr_parado', 'parado'],
        'valor_total': ['vlr_total', 'valor_total', 'vl_total', 'total'],
    }
    
    for target_col, possible_cols in valor_cols.items():
        found = False
        for col in df.columns:
            col_lower = col.lower()
            if any(pc in col_lower for pc in possible_cols):
                # Verifica se é uma coluna de valor (não percentual)
                if '%' not in str(df[col].iloc[0] if len(df) > 0 and df[col].dtype == 'object' else ''):
                    if df[col].dtype == 'object':
                        df[target_col] = df[col].apply(convert_brazilian_currency)
                    else:
                        df[target_col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
                    found = True
                    logger.debug(f"Coluna de valor mapeada: '{col}' -> '{target_col}'")
                    break
        if not found:
            df[target_col] = 0.0
            logger.debug(f"Coluna '{target_col}' não encontrada, usando 0.0")
    
    # Percentuais de valor
    perc_valor_col = None
    for col in df.columns:
        col_lower = col.lower()
        # Procura coluna com % ou "ating" relacionada a valor
        if ('ating' in col_lower or '%' in str(df[col].iloc[0] if len(df) > 0 and df[col].dtype == 'object' else '')):
            # Não é de volume
            if not any(term in col_lower for term in ['vol', 'volume', 'cx', 'caixa', 'qtd']):
                perc_valor_col = col
                logger.debug(f"Coluna de percentual de valor encontrada: '{col}'")
                break
    
    if perc_valor_col:
        df['perc_ating_valor'] = df[perc_valor_col].apply(convert_percentage)
    else:
        # Calcula se tiver meta e realizado
        if 'meta_valor' in df.columns and 'realizado_valor' in df.columns:
            df['perc_ating_valor'] = (df['realizado_valor'] / df['meta_valor'].replace(0, np.nan) * 100).fillna(0)
            logger.debug("Percentual de valor calculado a partir de meta_valor e realizado_valor")
        else:
            df['perc_ating_valor'] = 0.0
    
    # Volumes
    qtd_cols = {
        'meta_volume': ['qtd_meta', 'meta_volume', 'meta_qtd'],
        'realizado_volume': ['qtd_cx_faturado', 'cx_faturado', 'qtd_faturado', 'realizado_volume'],
        'qtd_cx_paradas': ['qtd_cx_paradas', 'cx_paradas', 'paradas'],
        'total_caixas': ['total_caixas', 'total_cx', 'total'],
    }
    
    for target_col, possible_cols in qtd_cols.items():
        found = False
        for col in df.columns:
            col_lower = col.lower()
            if any(pc in col_lower for pc in possible_cols):
                # Verifica se não é uma coluna de valor monetário
                if not any(term in col_lower for term in ['valor', 'vlr', 'vl_', 'r$']):
                    if df[col].dtype == 'object':
                        df[target_col] = df[col].apply(convert_brazilian_number)
                    else:
                        df[target_col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                    found = True
                    logger.debug(f"Coluna de volume mapeada: '{col}' -> '{target_col}'")
                    break
        if not found:
            df[target_col] = 0
            logger.debug(f"Coluna '{target_col}' não encontrada, usando 0")
    
    # Percentual de volume
    perc_vol_col = None
    for col in df.columns:
        col_lower = col.lower()
        if ('%' in str(df[col].iloc[0] if len(df) > 0 and df[col].dtype == 'object' else '') or 
            'ating' in col_lower) and any(term in col_lower for term in ['vol', 'volume', 'cx', 'caixa']):
            perc_vol_col = col
            logger.debug(f"Coluna de percentual de volume encontrada: '{col}'")
            break
    
    if perc_vol_col:
        df['perc_ating_volume'] = df[perc_vol_col].apply(convert_percentage)
    else:
        if 'meta_volume' in df.columns and 'realizado_volume' in df.columns:
            df['perc_ating_volume'] = (df['realizado_volume'] / df['meta_volume'].replace(0, np.nan) * 100).fillna(0)
            logger.debug("Percentual de volume calculado a partir de meta_volume e realizado_volume")
        else:
            df['perc_ating_volume'] = 0.0
    
    # Positivação
    pos_cols = {
        'meta_positivacao': ['meta_pos', 'meta_positivacao', 'meta_posit'],
        'clientes_positivados': ['cl_pos', 'clientes_pos', 'clientes_positivados', 'pos'],
    }
    
    for target_col, possible_cols in pos_cols.items():
        found = False
        for col in df.columns:
            col_lower = col.lower()
            if any(pc in col_lower for pc in possible_cols):
                if df[col].dtype == 'object':
                    df[target_col] = df[col].apply(lambda x: int(convert_brazilian_number(x)) if pd.notna(x) else 0)
                else:
                    df[target_col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
                found = True
                logger.debug(f"Coluna de positivação mapeada: '{col}' -> '{target_col}'")
                break
        if not found:
            df[target_col] = 0
            logger.debug(f"Coluna '{target_col}' não encontrada, usando 0")
    
    # Percentual de positivação
    perc_pos_col = None
    for col in df.columns:
        col_lower = col.lower()
        if ('%' in str(df[col].iloc[0] if len(df) > 0 and df[col].dtype == 'object' else '') or 
            'ating' in col_lower) and any(term in col_lower for term in ['pos', 'positivacao']):
            perc_pos_col = col
            logger.debug(f"Coluna de percentual de positivação encontrada: '{col}'")
            break
    
    if perc_pos_col:
        df['perc_ating_positivacao'] = df[perc_pos_col].apply(convert_percentage)
    else:
        if 'meta_positivacao' in df.columns and 'clientes_positivados' in df.columns:
            df['perc_ating_positivacao'] = (
                (df['clientes_positivados'] / df['meta_positivacao'].replace(0, np.nan) * 100) 
                if df['meta_positivacao'].sum() > 0 else 0
            ).fillna(0)
            logger.debug("Percentual de positivação calculado")
        else:
            df['perc_ating_positivacao'] = 0.0
    
    # Remove linhas onde vendedor_nome está vazio ou é inválido
    initial_count = len(df)
    df = df[df['vendedor_nome'].str.strip() != ''].copy()
    df = df[df['vendedor_nome'] != 'nan'].copy()
    removed_count = initial_count - len(df)
    if removed_count > 0:
        logger.info(f"Removidas {removed_count} linhas com vendedor_nome inválido")
    
    logger.info(f"Metas de vendedor carregadas: {len(df)} registros")
    logger.debug(f"Shape final: {df.shape}")
    logger.debug(f"Colunas finais: {list(df.columns)}")
    
    return df


def load_metas_departamento(csv_path: str, mes_ano: str) -> pd.DataFrame:
    """
    Carrega e processa CSV de Metas X Realizado por departamento.
    
    Similar a load_metas_vendedor, mas agregado por departamento/supervisor.
    
    Args:
        csv_path: Caminho para o CSV de metas
        mes_ano: Mês/ano de referência (ex.: "2024-12")
        
    Returns:
        pd.DataFrame: DataFrame processado
    """
    logger.info(f"Carregando metas de departamento de: {csv_path}")
    
    # Carrega CSV
    df = load_csv_robust(csv_path)
    
    logger.debug(f"Shape inicial após load_csv_robust: {df.shape}")
    logger.debug(f"Colunas iniciais: {list(df.columns)}")
    
    # Remove espaços em branco de todas as células de string
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].apply(lambda x: str(x).strip() if pd.notna(x) else x)
    
    # Remove linhas completamente vazias
    df = df.dropna(how='all').copy()
    
    # Remove linha de totais (mais robusta)
    if len(df) > 0:
        total_mask = df.apply(
            lambda row: any(
                pd.notna(val) and (
                    str(val).strip().upper() == 'TOTAL' or
                    str(val).strip().upper().startswith('TOTAL ') or
                    (len(str(val).strip()) < 20 and 'total' in str(val).lower() and 
                     any(char.isdigit() for char in str(val)) == False)  # Não é um valor numérico
                )
                for val in row.values
            ),
            axis=1
        )
        total_rows_count = total_mask.sum()
        df = df[~total_mask].copy()
        
        if total_rows_count > 0:
            logger.info(f"Linhas de totais removidas: {total_rows_count} linha(s)")
    
    # Adiciona coluna mes_ano
    df['mes_ano'] = mes_ano
    
    # Extrai ano e mês
    if '-' in mes_ano:
        ano, mes = mes_ano.split('-')
        df['ano'] = int(ano)
        df['mes'] = int(mes)
    
    # Procura coluna de departamento/supervisor (mais flexível)
    dept_col = None
    for col in df.columns:
        col_lower = col.lower()
        if any(term in col_lower for term in ['departamento', 'supervisor', 'gerente']):
            # Prioriza colunas que não são valores numéricos
            if df[col].dtype == 'object' or 'nome' in col_lower:
                dept_col = col
                break
    
    # Se não encontrou, tenta a primeira coluna de texto
    if not dept_col:
        for col in df.columns:
            if df[col].dtype == 'object' and col.lower() not in ['mes_ano', 'ano', 'mes']:
                dept_col = col
                break
    
    if dept_col:
        df['supervisor_nome'] = df[dept_col].astype(str).str.strip()
        logger.debug(f"Coluna de departamento/supervisor mapeada: '{dept_col}' -> 'supervisor_nome'")
    else:
        logger.warning("Coluna de departamento/supervisor não encontrada!")
        df['supervisor_nome'] = ''
    
    # Preserva coluna departamento se existir
    if 'departamento' in df.columns and dept_col != 'departamento':
        df['departamento'] = df['departamento'].astype(str).str.strip()
    elif dept_col and dept_col.lower() == 'departamento':
        # Já está mapeada como supervisor_nome, mas mantém também como departamento
        df['departamento'] = df['supervisor_nome']
    
    # Valores monetários (mais robusta)
    valor_cols = {
        'meta_valor': ['valor_meta', 'meta_valor', 'meta'],
        'realizado_valor': ['vl_faturado', 'valor_faturado', 'vlr_faturado', 'faturado', 'realizado'],
        'valor_parado': ['vl_parado', 'valor_parado', 'vlr_parado', 'parado'],
        'valor_total': ['vlr_total', 'valor_total', 'vl_total', 'total'],
    }
    
    for target_col, possible_cols in valor_cols.items():
        found = False
        for col in df.columns:
            col_lower = col.lower()
            if any(pc in col_lower for pc in possible_cols):
                # Verifica se é uma coluna de valor (não percentual)
                if '%' not in str(df[col].iloc[0] if len(df) > 0 and df[col].dtype == 'object' else ''):
                    if df[col].dtype == 'object':
                        df[target_col] = df[col].apply(convert_brazilian_currency)
                    else:
                        df[target_col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
                    found = True
                    logger.debug(f"Coluna de valor mapeada: '{col}' -> '{target_col}'")
                    break
        if not found:
            df[target_col] = 0.0
            logger.debug(f"Coluna '{target_col}' não encontrada, usando 0.0")
    
    # Percentual de valor
    perc_valor_col = None
    for col in df.columns:
        col_lower = col.lower()
        if ('ating' in col_lower or '%' in str(df[col].iloc[0] if len(df) > 0 and df[col].dtype == 'object' else '')):
            # Não é de volume
            if not any(term in col_lower for term in ['vol', 'volume', 'cx', 'caixa', 'qtd']):
                perc_valor_col = col
                logger.debug(f"Coluna de percentual de valor encontrada: '{col}'")
                break
    
    if perc_valor_col:
        df['perc_ating_valor'] = df[perc_valor_col].apply(convert_percentage)
    else:
        if 'meta_valor' in df.columns and 'realizado_valor' in df.columns:
            df['perc_ating_valor'] = (df['realizado_valor'] / df['meta_valor'].replace(0, np.nan) * 100).fillna(0)
            logger.debug("Percentual de valor calculado a partir de meta_valor e realizado_valor")
        else:
            df['perc_ating_valor'] = 0.0
    
    # Volumes
    qtd_cols = {
        'meta_volume': ['qtd_meta', 'meta_volume', 'meta_qtd'],
        'realizado_volume': ['qtd_cx_faturado', 'cx_faturado', 'qtd_faturado', 'realizado_volume'],
        'qtd_cx_paradas': ['qtd_cx_paradas', 'cx_paradas', 'paradas'],
        'total_caixas': ['total_caixas', 'total_cx', 'total'],
    }
    
    for target_col, possible_cols in qtd_cols.items():
        found = False
        for col in df.columns:
            col_lower = col.lower()
            if any(pc in col_lower for pc in possible_cols):
                # Verifica se não é uma coluna de valor monetário
                if not any(term in col_lower for term in ['valor', 'vlr', 'vl_', 'r$']):
                    if df[col].dtype == 'object':
                        df[target_col] = df[col].apply(convert_brazilian_number)
                    else:
                        df[target_col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                    found = True
                    logger.debug(f"Coluna de volume mapeada: '{col}' -> '{target_col}'")
                    break
        if not found:
            df[target_col] = 0
            logger.debug(f"Coluna '{target_col}' não encontrada, usando 0")
    
    # Percentual de volume
    perc_vol_col = None
    for col in df.columns:
        col_lower = col.lower()
        if ('%' in str(df[col].iloc[0] if len(df) > 0 and df[col].dtype == 'object' else '') or 
            'ating' in col_lower) and any(term in col_lower for term in ['vol', 'volume', 'cx', 'caixa']):
            perc_vol_col = col
            logger.debug(f"Coluna de percentual de volume encontrada: '{col}'")
            break
    
    if perc_vol_col:
        df['perc_ating_volume'] = df[perc_vol_col].apply(convert_percentage)
    else:
        if 'meta_volume' in df.columns and 'realizado_volume' in df.columns:
            df['perc_ating_volume'] = (df['realizado_volume'] / df['meta_volume'].replace(0, np.nan) * 100).fillna(0)
            logger.debug("Percentual de volume calculado a partir de meta_volume e realizado_volume")
        else:
            df['perc_ating_volume'] = 0.0
    
    # Positivação
    pos_cols = {
        'meta_positivacao': ['meta_pos', 'meta_positivacao', 'meta_posit'],
        'clientes_positivados': ['cl_pos', 'clientes_pos', 'clientes_positivados', 'pos'],
    }
    
    for target_col, possible_cols in pos_cols.items():
        found = False
        for col in df.columns:
            col_lower = col.lower()
            if any(pc in col_lower for pc in possible_cols):
                if df[col].dtype == 'object':
                    df[target_col] = df[col].apply(lambda x: int(convert_brazilian_number(x)) if pd.notna(x) else 0)
                else:
                    df[target_col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
                found = True
                logger.debug(f"Coluna de positivação mapeada: '{col}' -> '{target_col}'")
                break
        if not found:
            df[target_col] = 0
            logger.debug(f"Coluna '{target_col}' não encontrada, usando 0")
    
    # Percentual de positivação
    perc_pos_col = None
    for col in df.columns:
        col_lower = col.lower()
        if ('%' in str(df[col].iloc[0] if len(df) > 0 and df[col].dtype == 'object' else '') or 
            'ating' in col_lower) and any(term in col_lower for term in ['pos', 'positivacao']):
            perc_pos_col = col
            logger.debug(f"Coluna de percentual de positivação encontrada: '{col}'")
            break
    
    if perc_pos_col:
        df['perc_ating_positivacao'] = df[perc_pos_col].apply(convert_percentage)
    else:
        if 'meta_positivacao' in df.columns and 'clientes_positivados' in df.columns:
            df['perc_ating_positivacao'] = (
                (df['clientes_positivados'] / df['meta_positivacao'].replace(0, np.nan) * 100) 
                if df['meta_positivacao'].sum() > 0 else 0
            ).fillna(0)
            logger.debug("Percentual de positivação calculado")
        else:
            df['perc_ating_positivacao'] = 0.0
    
    # Remove linhas onde supervisor_nome está vazio ou é inválido
    initial_count = len(df)
    df = df[df['supervisor_nome'].str.strip() != ''].copy()
    df = df[df['supervisor_nome'] != 'nan'].copy()
    removed_count = initial_count - len(df)
    if removed_count > 0:
        logger.info(f"Removidas {removed_count} linhas com supervisor_nome inválido")
    
    logger.info(f"Metas de departamento carregadas: {len(df)} registros")
    logger.debug(f"Shape final: {df.shape}")
    logger.debug(f"Colunas finais: {list(df.columns)}")
    
    return df

