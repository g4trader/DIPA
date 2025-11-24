#!/usr/bin/env python3
"""
Script para gerar snapshot mock da Q1 a partir dos CSVs reais da Dipam.

Este script:
1. Lê os CSVs reais de mock/source_csv/
2. Consolida todos os CSVs de vendas em um único dataframe
3. Aplica a mesma lógica da Q1 real (clientes ativos, >= 61 dias sem compra)
4. Gera arquivos JSON em mock/data/ para uso no modo mock

Uso:
    python scripts/generate_mock_snapshot_q1.py \
      --input-dir ./mock/source_csv \
      --output-dir ./mock/data \
      --dias 60 \
      --data-referencia 2025-10-31
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
import logging

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse date string in various formats."""
    if pd.isna(date_str) or not date_str:
        return None
    
    date_str = str(date_str).strip()
    
    # Tenta diferentes formatos
    formats = [
        "%d/%m/%Y",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%Y/%m/%d",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    logger.warning(f"Não foi possível parsear data: {date_str}")
    return None


def load_csv_with_encoding(file_path: Path) -> pd.DataFrame:
    """Carrega CSV tentando diferentes encodings."""
    logger.info(f"Carregando: {file_path.name}")
    
    for encoding in ["utf-8", "latin-1", "cp1252"]:
        try:
            df = pd.read_csv(file_path, encoding=encoding, sep=",", low_memory=False)
            logger.info(f"✅ CSV carregado com encoding {encoding}: {len(df)} linhas")
            return df
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue
    
    raise ValueError(f"Não foi possível carregar {file_path}")


def encontrar_coluna_por_padrao(df: pd.DataFrame, padroes: List[str]) -> Optional[str]:
    """Encontra coluna que corresponde a algum padrão."""
    for col in df.columns:
        col_lower = str(col).lower()
        for padrao in padroes:
            if padrao.lower() in col_lower:
                return col
    return None


def consolidar_vendas(input_dir: Path) -> pd.DataFrame:
    """
    Consolida todos os CSVs de vendas em um único dataframe.
    
    Procura por arquivos que contenham "vendas" ou "detalhes" no nome.
    """
    logger.info("=" * 60)
    logger.info("📦 Consolidando CSVs de vendas...")
    logger.info("=" * 60)
    
    vendas_files = []
    for file in input_dir.glob("*.csv"):
        name_lower = file.name.lower()
        if ("vendas" in name_lower or "detalhes" in name_lower) and "clientes" not in name_lower:
            vendas_files.append(file)
    
    if not vendas_files:
        raise FileNotFoundError(f"Nenhum arquivo de vendas encontrado em {input_dir}")
    
    logger.info(f"Encontrados {len(vendas_files)} arquivos de vendas:")
    for f in vendas_files:
        logger.info(f"   - {f.name}")
    
    # Carrega e consolida todos os CSVs
    dfs_vendas = []
    for file in vendas_files:
        try:
            df = load_csv_with_encoding(file)
            dfs_vendas.append(df)
            logger.info(f"✅ {file.name}: {len(df)} registros")
        except Exception as e:
            logger.warning(f"⚠️  Erro ao carregar {file.name}: {e}")
            continue
    
    if not dfs_vendas:
        raise ValueError("Nenhum CSV de vendas foi carregado com sucesso")
    
    # Concatena todos os dataframes
    df_vendas_consolidado = pd.concat(dfs_vendas, ignore_index=True)
    logger.info(f"✅ Total consolidado: {len(df_vendas_consolidado)} registros de vendas")
    
    return df_vendas_consolidado


def calcular_ultima_compra_por_cliente(df_vendas: pd.DataFrame) -> Dict[int, datetime]:
    """Calcula a última data de compra por cliente."""
    logger.info("Calculando última compra por cliente...")
    
    # Encontra coluna de data
    col_data = encontrar_coluna_por_padrao(
        df_vendas,
        ["data", "Data", "DATA", "data_venda", "Data Venda"]
    )
    
    if not col_data:
        raise ValueError("Coluna de data não encontrada no CSV de vendas")
    
    # Encontra coluna de código cliente
    col_cliente = encontrar_coluna_por_padrao(
        df_vendas,
        ["código cliente", "codigo cliente", "Cliente ID", "cliente_id", "Código Cliente"]
    )
    
    if not col_cliente:
        raise ValueError("Coluna de código cliente não encontrada no CSV de vendas")
    
    # Converte datas
    df_vendas[col_data] = pd.to_datetime(
        df_vendas[col_data],
        format="%d/%m/%Y",
        errors="coerce"
    )
    
    # Remove linhas com data inválida
    df_vendas_validas = df_vendas.dropna(subset=[col_data, col_cliente])
    
    # Converte código cliente para int
    df_vendas_validas[col_cliente] = pd.to_numeric(
        df_vendas_validas[col_cliente],
        errors="coerce"
    )
    df_vendas_validas = df_vendas_validas.dropna(subset=[col_cliente])
    
    # Agrupa por cliente e pega a data máxima
    ultima_compra = df_vendas_validas.groupby(col_cliente)[col_data].max().to_dict()
    
    logger.info(f"✅ Última compra calculada para {len(ultima_compra)} clientes")
    
    return {int(k): v for k, v in ultima_compra.items() if pd.notna(v)}


def processar_q1(
    df_clientes: pd.DataFrame,
    ultima_compra: Dict[int, datetime],
    df_supervisor: Optional[pd.DataFrame] = None,
    dias_minimo: int = 60,
    data_referencia: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """
    Processa Q1: clientes ativos sem compra há mais de N dias.
    
    Replica a lógica de get_clientes_sem_compra_ha_dias do DW.
    """
    logger.info(f"Processando Q1 (dias mínimo: {dias_minimo})...")
    
    if data_referencia is None:
        data_referencia = datetime.now()
    
    # Encontra colunas do CSV de clientes
    col_codigo = encontrar_coluna_por_padrao(
        df_clientes,
        ["código", "codigo", "Cliente ID", "cliente_id", "Código Cliente"]
    )
    
    if not col_codigo:
        raise ValueError("Coluna de código não encontrada no CSV de clientes")
    
    col_nome = encontrar_coluna_por_padrao(
        df_clientes,
        ["fantasia", "nome", "cliente", "Nome Fantasia", "Razão Social"]
    )
    
    if not col_nome:
        col_nome = df_clientes.columns[1] if len(df_clientes.columns) > 1 else df_clientes.columns[0]
    
    col_rota = encontrar_coluna_por_padrao(
        df_clientes,
        ["rca", "rota", "vendedor", "Nome RCA", "Rota"]
    )
    
    # Encontra campo de ativo
    col_ativo = encontrar_coluna_por_padrao(
        df_clientes,
        ["bloquear", "inativo", "ativo", "situação", "Situação"]
    )
    
    # Filtra clientes ativos
    if col_ativo:
        # Remove clientes bloqueados/inativos
        df_clientes_ativos = df_clientes[
            ~df_clientes[col_ativo].astype(str).str.contains("Sim", case=False, na=False)
        ].copy()
    else:
        # Se não tem coluna de bloqueio, assume todos ativos
        logger.warning("Coluna de bloqueio não encontrada, assumindo todos clientes como ativos")
        df_clientes_ativos = df_clientes.copy()
    
    logger.info(f"Clientes ativos: {len(df_clientes_ativos)} de {len(df_clientes)} total")
    
    # Processa cada cliente
    resultados = []
    
    for _, row in df_clientes_ativos.iterrows():
        try:
            codigo = int(row[col_codigo]) if pd.notna(row[col_codigo]) else None
            if codigo is None:
                continue
            
            nome = str(row[col_nome]).strip() if pd.notna(row[col_nome]) else ""
            rota = str(row[col_rota]).strip() if col_rota and pd.notna(row[col_rota]) else ""
            
            # Calcula dias sem compra
            data_ultima_compra = ultima_compra.get(codigo)
            
            if data_ultima_compra:
                dias_sem_compra = (data_referencia - data_ultima_compra).days
            else:
                # Cliente nunca comprou, considera como muito tempo sem compra
                dias_sem_compra = 999
            
            # Filtra apenas clientes com mais de 60 dias (>= 61)
            if dias_sem_compra < (dias_minimo + 1):
                continue
            
            # Busca supervisor (se disponível)
            supervisor_nome = ""
            supervisor_codigo = ""
            vendedor_nome = rota
            vendedor_codigo = ""
            
            if df_supervisor is not None and rota:
                # Tenta encontrar supervisor pela rota/vendedor
                for _, sup_row in df_supervisor.iterrows():
                    vendedor_col = encontrar_coluna_por_padrao(
                        pd.DataFrame([sup_row]),
                        ["vendedor", "rota", "rca", "Nome RCA"]
                    )
                    
                    if vendedor_col and pd.notna(sup_row.get(vendedor_col)):
                        if str(sup_row[vendedor_col]).strip() == rota:
                            # Encontrou, pega supervisor
                            sup_nome_col = encontrar_coluna_por_padrao(
                                pd.DataFrame([sup_row]),
                                ["supervisor", "Supervisor"]
                            )
                            
                            if sup_nome_col and pd.notna(sup_row.get(sup_nome_col)):
                                supervisor_nome = str(sup_row[sup_nome_col]).strip()
                            
                            sup_codigo_col = encontrar_coluna_por_padrao(
                                pd.DataFrame([sup_row]),
                                ["código supervisor", "codigo supervisor", "Supervisor Código"]
                            )
                            
                            if sup_codigo_col and pd.notna(sup_row.get(sup_codigo_col)):
                                supervisor_codigo = str(sup_row[sup_codigo_col]).strip()
                            
                            break
            
            # Garante que dias_sem_compra é inteiro
            dias_sem_compra_int = int(dias_sem_compra) if dias_sem_compra else 0
            
            resultados.append({
                "cliente_id": int(codigo) if codigo else 0,
                "nome": str(nome) if nome else "",
                "segmento": "",  # Não temos no CSV de exemplo
                "rota_id": str(rota) if rota else "",
                "vendedor_nome": str(vendedor_nome) if vendedor_nome else "",
                "vendedor_codigo": str(vendedor_codigo) if vendedor_codigo else "",
                "supervisor_nome": str(supervisor_nome) if supervisor_nome else "",
                "supervisor_codigo": str(supervisor_codigo) if supervisor_codigo else "",
                "data_ultima_compra": data_ultima_compra.isoformat() if data_ultima_compra else None,
                "dias_sem_compra": dias_sem_compra_int  # Garantido como int
            })
        
        except Exception as e:
            logger.warning(f"Erro ao processar cliente {row.get(col_codigo, '?')}: {e}")
            continue
    
    # Remove duplicatas (mantém apenas o primeiro)
    seen = set()
    resultados_unicos = []
    for r in resultados:
        cliente_id = r["cliente_id"]
        if cliente_id not in seen:
            seen.add(cliente_id)
            resultados_unicos.append(r)
    
    logger.info(f"✅ Q1 processado: {len(resultados_unicos)} clientes únicos sem compra há mais de {dias_minimo} dias")
    
    return resultados_unicos


def classificar_por_faixas(clientes: List[Dict[str, Any]]) -> Dict[str, int]:
    """Classifica clientes por faixas de dias sem compra."""
    faixas = {
        "61_120": 0,
        "121_180": 0,
        "181_300": 0,
        "acima_300": 0,
    }
    
    for cliente in clientes:
        dias = cliente.get("dias_sem_compra", 0)
        dias_int = int(dias) if dias else 0
        
        if 61 <= dias_int <= 120:
            faixas["61_120"] += 1
        elif 121 <= dias_int <= 180:
            faixas["121_180"] += 1
        elif 181 <= dias_int <= 300:
            faixas["181_300"] += 1
        elif dias_int > 300:
            faixas["acima_300"] += 1
    
    return faixas


def gerar_snapshot_q1(
    input_dir: Path,
    output_dir: Path,
    dias: int = 60,
    data_referencia: Optional[str] = None
) -> bool:
    """
    Gera snapshot mock da Q1 a partir dos CSVs reais.
    
    Args:
        input_dir: Diretório com os CSVs de entrada
        output_dir: Diretório de saída para os JSONs
        dias: Número de dias sem compra (padrão: 60, significa >= 61 dias)
        data_referencia: Data de referência (YYYY-MM-DD) ou None para hoje
        
    Returns:
        bool: True se sucesso, False caso contrário
    """
    logger.info("=" * 60)
    logger.info("🚀 Gerando snapshot mock Q1 a partir dos CSVs reais...")
    logger.info("=" * 60)
    
    # Parse data de referência
    if data_referencia:
        data_ref = datetime.strptime(data_referencia, "%Y-%m-%d")
    else:
        data_ref = datetime.now()
    
    logger.info(f"Data de referência: {data_ref.strftime('%Y-%m-%d')}")
    logger.info(f"Dias mínimo: {dias} (>= {dias + 1} dias sem compra)")
    
    # Cria diretório de saída
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Encontra arquivos CSV
    clientes_file = None
    supervisor_file = None
    
    for file in input_dir.glob("*.csv"):
        name_lower = file.name.lower()
        if "clientes" in name_lower and "ativos" in name_lower:
            clientes_file = file
        elif "supervisor" in name_lower:
            supervisor_file = file
    
    if not clientes_file:
        raise FileNotFoundError(f"Arquivo de clientes não encontrado em {input_dir}")
    
    logger.info(f"📁 Arquivos encontrados:")
    logger.info(f"   Clientes: {clientes_file.name}")
    if supervisor_file:
        logger.info(f"   Supervisor: {supervisor_file.name}")
    
    # Carrega CSVs
    df_clientes = load_csv_with_encoding(clientes_file)
    df_supervisor = load_csv_with_encoding(supervisor_file) if supervisor_file else None
    
    # Consolida vendas
    df_vendas = consolidar_vendas(input_dir)
    
    # Calcula última compra por cliente
    ultima_compra = calcular_ultima_compra_por_cliente(df_vendas)
    
    # Processa Q1
    clientes_q1 = processar_q1(
        df_clientes,
        ultima_compra,
        df_supervisor,
        dias_minimo=dias,
        data_referencia=data_ref
    )
    
    if len(clientes_q1) == 0:
        logger.warning("⚠️  Nenhum cliente encontrado. Verifique os filtros e dados.")
        return False
    
    # Classifica por faixas
    faixas = classificar_por_faixas(clientes_q1)
    
    # Gera JSON de clientes
    q1_clientes_path = output_dir / "q1_clientes_sem_compra.json"
    with open(q1_clientes_path, "w", encoding="utf-8") as f:
        json.dump(clientes_q1, f, ensure_ascii=False, indent=2)
    
    logger.info(f"✅ Dados Q1 exportados: {q1_clientes_path} ({len(clientes_q1)} clientes)")
    
    # Gera JSON de estatísticas
    estatisticas = {
        "total_clientes": int(len(clientes_q1)),
        "faixas": {
            "61_120": int(faixas.get("61_120", 0)),
            "121_180": int(faixas.get("121_180", 0)),
            "181_300": int(faixas.get("181_300", 0)),
            "acima_300": int(faixas.get("acima_300", 0)),
        },
        "data_referencia": data_ref.strftime("%Y-%m-%d"),
        "data_exportacao": datetime.now().isoformat(),
        "dias_filtro": int(dias),
        "fonte": "csv_dipam",  # Indica que veio dos CSVs
    }
    
    q1_stats_path = output_dir / "q1_estatisticas.json"
    with open(q1_stats_path, "w", encoding="utf-8") as f:
        json.dump(estatisticas, f, ensure_ascii=False, indent=2)
    
    logger.info(f"✅ Estatísticas exportadas: {q1_stats_path}")
    logger.info(f"   Total: {estatisticas['total_clientes']} clientes")
    logger.info(f"   Faixas: 61-120: {faixas['61_120']}, 121-180: {faixas['121_180']}, "
                f"181-300: {faixas['181_300']}, >300: {faixas['acima_300']}")
    
    # Valida consistência
    soma_faixas = sum(faixas.values())
    if soma_faixas != len(clientes_q1):
        logger.warning(f"⚠️  Inconsistência: soma das faixas ({soma_faixas}) != total de clientes ({len(clientes_q1)})")
    else:
        logger.info("✅ Validação: soma das faixas bate com total de clientes")
    
    # Valida que todos têm >= 61 dias
    clientes_com_menos_61 = [c for c in clientes_q1 if c["dias_sem_compra"] < 61]
    if clientes_com_menos_61:
        logger.warning(f"⚠️  {len(clientes_com_menos_61)} clientes com menos de 61 dias encontrados")
    else:
        logger.info("✅ Validação: todos os clientes têm >= 61 dias sem compra")
    
    # Valida duplicatas
    cliente_ids = [c["cliente_id"] for c in clientes_q1]
    if len(cliente_ids) != len(set(cliente_ids)):
        logger.warning(f"⚠️  Duplicatas encontradas: {len(cliente_ids)} registros, {len(set(cliente_ids))} únicos")
    else:
        logger.info("✅ Validação: sem duplicatas")
    
    logger.info("=" * 60)
    logger.info("✅ Snapshot gerado com sucesso!")
    logger.info("=" * 60)
    
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Gera snapshot mock Q1 a partir dos CSVs reais da Dipam"
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        default="./mock/source_csv",
        help="Diretório com os CSVs de entrada"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./mock/data",
        help="Diretório de saída para os JSONs"
    )
    parser.add_argument(
        "--dias",
        type=int,
        default=60,
        help="Número de dias sem compra (padrão: 60, significa >= 61 dias)"
    )
    parser.add_argument(
        "--data-referencia",
        type=str,
        default=None,
        help="Data de referência (YYYY-MM-DD) ou None para hoje"
    )
    
    args = parser.parse_args()
    
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    
    if not input_dir.exists():
        logger.error(f"❌ Diretório de entrada não existe: {input_dir}")
        sys.exit(1)
    
    try:
        success = gerar_snapshot_q1(
            input_dir=input_dir,
            output_dir=output_dir,
            dias=args.dias,
            data_referencia=args.data_referencia
        )
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}", exc_info=True)
        sys.exit(1)
