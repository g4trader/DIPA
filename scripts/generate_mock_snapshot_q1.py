#!/usr/bin/env python3
"""
Script para gerar snapshot mock da Q1 usando a query REAL do DW.

Este script:
1. Conecta na base local já alimentada pelo ETL
2. Chama a função get_clientes_sem_compra_ha_dias (query real)
3. Gera arquivos JSON em mock/data/ para uso no modo mock

OPÇÃO A (preferencial): Usa a base local e a query real
OPÇÃO B (fallback): Se a base não estiver disponível, pode usar CSVs (via export_mock_from_csv.py)

Uso:
    python scripts/generate_mock_snapshot_q1.py \
      --output-dir mock/data \
      --dias 60 \
      --data-referencia 2025-10-31
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Adiciona o diretório raiz ao path para importar módulos do projeto
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.dw.connection import SessionLocal, init_db
    from src.dw.queries import get_clientes_sem_compra_ha_dias
    from src.config import config
except ImportError as e:
    logger.error(f"❌ Erro ao importar módulos: {e}")
    logger.error("Certifique-se de que está executando do diretório raiz do projeto")
    sys.exit(1)


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


def sanitizar_dados(clientes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sanitiza dados para garantir tipos corretos (números como int, não string).
    """
    clientes_sanitizados = []
    
    for cliente in clientes:
        cliente_sanitizado = {
            "cliente_id": int(cliente.get("cliente_id", 0)) if cliente.get("cliente_id") else 0,
            "nome": str(cliente.get("nome", "")),
            "segmento": str(cliente.get("segmento", "")),
            "rota_id": str(cliente.get("rota_id", "")),
            "vendedor_nome": str(cliente.get("vendedor_nome", "")),
            "vendedor_codigo": str(cliente.get("vendedor_codigo", "")),
            "supervisor_nome": str(cliente.get("supervisor_nome", "")),
            "supervisor_codigo": str(cliente.get("supervisor_codigo", "")),
            "data_ultima_compra": cliente.get("data_ultima_compra"),
            "dias_sem_compra": int(cliente.get("dias_sem_compra", 0)) if cliente.get("dias_sem_compra") else 0,
        }
        clientes_sanitizados.append(cliente_sanitizado)
    
    return clientes_sanitizados


def gerar_snapshot_q1(
    output_dir: Path,
    dias: int = 60,
    data_referencia: Optional[str] = None
) -> bool:
    """
    Gera snapshot mock da Q1 usando a query real do DW.
    
    Args:
        output_dir: Diretório de saída para os JSONs
        dias: Número de dias sem compra (padrão: 60)
        data_referencia: Data de referência (YYYY-MM-DD) ou None para hoje
        
    Returns:
        bool: True se sucesso, False caso contrário
    """
    logger.info("=" * 60)
    logger.info("🚀 Gerando snapshot mock Q1 a partir da query REAL do DW...")
    logger.info("=" * 60)
    
    # Inicializa banco se necessário
    try:
        if SessionLocal is None:
            logger.info("Inicializando conexão com banco...")
            init_db()
        
        if SessionLocal is None:
            logger.error("❌ Não foi possível inicializar conexão com banco")
            logger.error("   Certifique-se de que o ETL foi executado e o banco existe")
            return False
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar banco: {e}")
        logger.error("   Tente executar o ETL primeiro ou use export_mock_from_csv.py como fallback")
        return False
    
    # Cria diretório de saída
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Executa query real
    logger.info(f"Executando query real: get_clientes_sem_compra_ha_dias(dias={dias}, data_referencia={data_referencia})...")
    
    session = None
    try:
        session = SessionLocal()
        
        # Chama a query real
        clientes_q1 = get_clientes_sem_compra_ha_dias(
            session=session,
            dias=dias,
            data_referencia=data_referencia,
            filtros_behavior=None,  # Sem filtros de behavior para snapshot
            query_id="Q1_MOCK_SNAPSHOT"
        )
        
        logger.info(f"✅ Query executada: {len(clientes_q1)} clientes encontrados")
        
        if len(clientes_q1) == 0:
            logger.warning("⚠️  Nenhum cliente encontrado. Verifique se o ETL foi executado corretamente.")
            return False
        
        # Sanitiza dados (garante tipos corretos)
        clientes_sanitizados = sanitizar_dados(clientes_q1)
        
        # Remove duplicatas (garantia extra)
        seen = set()
        clientes_unicos = []
        for cliente in clientes_sanitizados:
            cliente_id = cliente["cliente_id"]
            if cliente_id not in seen:
                seen.add(cliente_id)
                clientes_unicos.append(cliente)
        
        logger.info(f"✅ Dados sanitizados: {len(clientes_unicos)} clientes únicos")
        
        # Classifica por faixas
        faixas = classificar_por_faixas(clientes_unicos)
        
        # Gera JSON de clientes
        q1_clientes_path = output_dir / "q1_clientes_sem_compra.json"
        with open(q1_clientes_path, "w", encoding="utf-8") as f:
            json.dump(clientes_unicos, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ Dados Q1 exportados: {q1_clientes_path} ({len(clientes_unicos)} clientes)")
        
        # Gera JSON de estatísticas
        estatisticas = {
            "total_clientes": int(len(clientes_unicos)),
            "faixas": {
                "61_120": int(faixas.get("61_120", 0)),
                "121_180": int(faixas.get("121_180", 0)),
                "181_300": int(faixas.get("181_300", 0)),
                "acima_300": int(faixas.get("acima_300", 0)),
            },
            "data_referencia": data_referencia or datetime.now().strftime("%Y-%m-%d"),
            "data_exportacao": datetime.now().isoformat(),
            "dias_filtro": int(dias),
            "fonte": "query_real_dw",  # Indica que veio da query real
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
        if soma_faixas != len(clientes_unicos):
            logger.warning(f"⚠️  Inconsistência: soma das faixas ({soma_faixas}) != total de clientes ({len(clientes_unicos)})")
        else:
            logger.info("✅ Validação: soma das faixas bate com total de clientes")
        
        # Valida que todos têm >= 61 dias
        clientes_com_menos_61 = [c for c in clientes_unicos if c["dias_sem_compra"] < 61]
        if clientes_com_menos_61:
            logger.warning(f"⚠️  {len(clientes_com_menos_61)} clientes com menos de 61 dias encontrados")
        else:
            logger.info("✅ Validação: todos os clientes têm >= 61 dias sem compra")
        
        logger.info("=" * 60)
        logger.info("✅ Snapshot gerado com sucesso!")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao gerar snapshot: {e}", exc_info=True)
        return False
    
    finally:
        if session:
            session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Gera snapshot mock Q1 a partir da query REAL do DW"
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
    
    output_dir = Path(args.output_dir)
    
    try:
        success = gerar_snapshot_q1(
            output_dir=output_dir,
            dias=args.dias,
            data_referencia=args.data_referencia
        )
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}", exc_info=True)
        sys.exit(1)

