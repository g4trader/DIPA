#!/usr/bin/env python3
"""
Script para exportar dados Q1 dos CSVs reais para JSON (modo mock).

Este script:
1. Lê os CSVs reais (Clientes ativos, Vendas, Supervisor)
2. Aplica a mesma lógica da Q1 do DW
3. Gera arquivos JSON em mock/data/ para uso no modo mock

Uso:
    python scripts/export_mock_from_csv.py \
      --input-dir ./mock/source_csv \
      --output-dir ./mock/data
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
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


def load_clientes_csv(file_path: Path) -> pd.DataFrame:
    """Carrega CSV de clientes ativos."""
    logger.info(f"Carregando clientes de: {file_path}")
    
    try:
        # Tenta diferentes encodings
        for encoding in ["utf-8", "latin-1", "cp1252"]:
            try:
                df = pd.read_csv(file_path, encoding=encoding, sep=",", low_memory=False)
                logger.info(f"✅ CSV carregado com encoding {encoding}: {len(df)} linhas")
                return df
            except (UnicodeDecodeError, pd.errors.ParserError):
                continue
        
        raise ValueError(f"Não foi possível carregar {file_path}")
    except Exception as e:
        logger.error(f"Erro ao carregar clientes: {e}")
        raise


def load_vendas_csv(file_path: Path) -> pd.DataFrame:
    """Carrega CSV de vendas."""
    logger.info(f"Carregando vendas de: {file_path}")
    
    try:
        for encoding in ["utf-8", "latin-1", "cp1252"]:
            try:
                df = pd.read_csv(file_path, encoding=encoding, sep=",", low_memory=False)
                logger.info(f"✅ CSV carregado com encoding {encoding}: {len(df)} linhas")
                return df
            except (UnicodeDecodeError, pd.errors.ParserError):
                continue
        
        raise ValueError(f"Não foi possível carregar {file_path}")
    except Exception as e:
        logger.error(f"Erro ao carregar vendas: {e}")
        raise


def load_supervisor_csv(file_path: Path) -> pd.DataFrame:
    """Carrega CSV de supervisores."""
    logger.info(f"Carregando supervisores de: {file_path}")
    
    try:
        for encoding in ["utf-8", "latin-1", "cp1252"]:
            try:
                df = pd.read_csv(file_path, encoding=encoding, sep=",", low_memory=False)
                logger.info(f"✅ CSV carregado com encoding {encoding}: {len(df)} linhas")
                return df
            except (UnicodeDecodeError, pd.errors.ParserError):
                continue
        
        raise ValueError(f"Não foi possível carregar {file_path}")
    except Exception as e:
        logger.error(f"Erro ao carregar supervisores: {e}")
        raise


def calcular_ultima_compra_por_cliente(df_vendas: pd.DataFrame) -> Dict[int, datetime]:
    """Calcula a última data de compra por cliente."""
    logger.info("Calculando última compra por cliente...")
    
    # Normaliza nome da coluna de data
    col_data = None
    for col in df_vendas.columns:
        if "data" in col.lower() or "Data" in col:
            col_data = col
            break
    
    if not col_data:
        raise ValueError("Coluna de data não encontrada no CSV de vendas")
    
    # Normaliza nome da coluna de código cliente
    col_cliente = None
    for col in df_vendas.columns:
        if "código" in col.lower() or "codigo" in col.lower() or "Código Cliente" in col:
            col_cliente = col
            break
    
    if not col_cliente:
        raise ValueError("Coluna de código cliente não encontrada no CSV de vendas")
    
    # Converte datas
    df_vendas[col_data] = pd.to_datetime(
        df_vendas[col_data],
        format="%d/%m/%Y",
        errors="coerce"
    )
    
    # Remove linhas com data inválida
    df_vendas = df_vendas.dropna(subset=[col_data])
    
    # Agrupa por cliente e pega a data máxima
    ultima_compra = df_vendas.groupby(col_cliente)[col_data].max().to_dict()
    
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
    
    # Normaliza colunas do CSV de clientes
    # Procura coluna de código
    col_codigo = None
    for col in df_clientes.columns:
        if "código" in col.lower() or "codigo" in col.lower():
            if "cliente" not in col.lower() or col_codigo is None:
                col_codigo = col
                break
    
    if not col_codigo:
        raise ValueError("Coluna de código não encontrada no CSV de clientes")
    
    # Procura coluna de nome
    col_nome = None
    for col in df_clientes.columns:
        if "fantasia" in col.lower() or "nome" in col.lower() or "cliente" in col.lower():
            if "código" not in col.lower():
                col_nome = col
                break
    
    if not col_nome:
        col_nome = df_clientes.columns[1] if len(df_clientes.columns) > 1 else df_clientes.columns[0]
    
    # Procura coluna de rota (Nome RCA)
    col_rota = None
    for col in df_clientes.columns:
        if "rca" in col.lower() or "rota" in col.lower() or "vendedor" in col.lower():
            col_rota = col
            break
    
    # Procura campo de ativo
    col_ativo = None
    for col in df_clientes.columns:
        if "bloquear" in col.lower() and "inatividade" in col.lower():
            col_ativo = col
            break
    
    # Filtra clientes ativos
    if col_ativo:
        # "Sim(S)" ou similar indica bloqueado (não ativo)
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
            supervisor = ""
            vendedor_nome = rota
            
            if df_supervisor is not None and rota:
                # Tenta encontrar supervisor pela rota/vendedor
                for _, sup_row in df_supervisor.iterrows():
                    vendedor_col = None
                    for col in df_supervisor.columns:
                        if "vendedor" in col.lower() and "código" not in col.lower():
                            vendedor_col = col
                            break
                    
                    if vendedor_col and pd.notna(sup_row.get(vendedor_col)):
                        if str(sup_row[vendedor_col]).strip() == rota:
                            # Encontrou, pega supervisor
                            sup_col = None
                            for col in df_supervisor.columns:
                                if "supervisor" in col.lower():
                                    sup_col = col
                                    break
                            
                            if sup_col and pd.notna(sup_row.get(sup_col)):
                                supervisor = str(sup_row[sup_col]).strip()
                            break
            
            resultados.append({
                "cliente_id": codigo,
                "nome": nome,
                "segmento": "",  # Não temos no CSV de exemplo
                "rota_id": rota,
                "vendedor_nome": vendedor_nome,
                "vendedor_codigo": "",
                "supervisor_nome": supervisor,
                "supervisor_codigo": "",
                "data_ultima_compra": data_ultima_compra.isoformat() if data_ultima_compra else None,
                "dias_sem_compra": dias_sem_compra
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
        
        if 61 <= dias <= 120:
            faixas["61_120"] += 1
        elif 121 <= dias <= 180:
            faixas["121_180"] += 1
        elif 181 <= dias <= 300:
            faixas["181_300"] += 1
        elif dias > 300:
            faixas["acima_300"] += 1
    
    return faixas


def exportar_mock_from_csv(
    input_dir: Path,
    output_dir: Path,
    dias_minimo: int = 60
):
    """Função principal: exporta dados mock dos CSVs."""
    logger.info("=" * 60)
    logger.info("🚀 Exportando dados mock dos CSVs reais...")
    logger.info("=" * 60)
    
    # Cria diretório de saída
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Encontra arquivos CSV
    clientes_file = None
    vendas_file = None
    supervisor_file = None
    
    for file in input_dir.glob("*.csv"):
        name_lower = file.name.lower()
        if "clientes" in name_lower and "ativos" in name_lower:
            clientes_file = file
        elif "vendas" in name_lower or "detalhes" in name_lower:
            vendas_file = file
        elif "supervisor" in name_lower:
            supervisor_file = file
    
    if not clientes_file:
        raise FileNotFoundError(f"Arquivo de clientes não encontrado em {input_dir}")
    
    if not vendas_file:
        raise FileNotFoundError(f"Arquivo de vendas não encontrado em {input_dir}")
    
    logger.info(f"📁 Arquivos encontrados:")
    logger.info(f"   Clientes: {clientes_file.name}")
    logger.info(f"   Vendas: {vendas_file.name}")
    if supervisor_file:
        logger.info(f"   Supervisor: {supervisor_file.name}")
    
    # Carrega CSVs
    df_clientes = load_clientes_csv(clientes_file)
    df_vendas = load_vendas_csv(vendas_file)
    df_supervisor = load_supervisor_csv(supervisor_file) if supervisor_file else None
    
    # Calcula última compra por cliente
    ultima_compra = calcular_ultima_compra_por_cliente(df_vendas)
    
    # Processa Q1
    clientes_q1 = processar_q1(
        df_clientes,
        ultima_compra,
        df_supervisor,
        dias_minimo=dias_minimo
    )
    
    # Classifica por faixas
    faixas = classificar_por_faixas(clientes_q1)
    
    # Gera JSON de clientes
    q1_clientes_path = output_dir / "q1_clientes_sem_compra.json"
    with open(q1_clientes_path, "w", encoding="utf-8") as f:
        json.dump(clientes_q1, f, ensure_ascii=False, indent=2)
    
    logger.info(f"✅ Dados Q1 exportados: {q1_clientes_path} ({len(clientes_q1)} clientes)")
    
    # Gera JSON de estatísticas
    estatisticas = {
        "total_clientes": len(clientes_q1),
        "faixas": faixas,
        "data_exportacao": datetime.now().isoformat(),
        "dias_filtro": dias_minimo,
    }
    
    q1_stats_path = output_dir / "q1_estatisticas.json"
    with open(q1_stats_path, "w", encoding="utf-8") as f:
        json.dump(estatisticas, f, ensure_ascii=False, indent=2)
    
    logger.info(f"✅ Estatísticas exportadas: {q1_stats_path}")
    logger.info(f"   Total: {estatisticas['total_clientes']} clientes")
    logger.info(f"   Faixas: 61-120: {faixas['61_120']}, 121-180: {faixas['121_180']}, "
                f"181-300: {faixas['181_300']}, >300: {faixas['acima_300']}")
    
    logger.info("=" * 60)
    logger.info("✅ Exportação concluída com sucesso!")
    logger.info("=" * 60)
    
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Exporta dados mock dos CSVs reais para JSON"
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
        "--dias-minimo",
        type=int,
        default=60,
        help="Número mínimo de dias sem compra (padrão: 60)"
    )
    
    args = parser.parse_args()
    
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    
    if not input_dir.exists():
        logger.error(f"❌ Diretório de entrada não existe: {input_dir}")
        sys.exit(1)
    
    try:
        exportar_mock_from_csv(input_dir, output_dir, dias_minimo=args.dias_minimo)
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Erro ao exportar: {e}", exc_info=True)
        sys.exit(1)

