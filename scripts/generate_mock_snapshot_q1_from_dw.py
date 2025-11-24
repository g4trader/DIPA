#!/usr/bin/env python3
"""
Script para gerar snapshot mock da Q1 usando a MESMA função do DW real.

Este script:
1. Conecta ao DW local (SQLite)
2. Executa get_clientes_sem_compra_ha_dias (mesma função usada em produção)
3. Gera arquivos JSON em mock/data/ com a mesma estrutura que o orquestrador retorna

Uso:
    python scripts/generate_mock_snapshot_q1_from_dw.py \
      --output-dir ./mock/data \
      --dias 60 \
      --data-referencia 2025-11-24
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

# Adiciona o diretório raiz ao path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.dw.connection import get_session
from src.dw.queries import get_clientes_sem_compra_ha_dias
from src.llm_integration_intent import _classificar_clientes_por_faixa

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def gerar_snapshot_q1_from_dw(
    output_dir: Path,
    dias: int = 60,
    data_referencia: Optional[str] = None
) -> bool:
    """
    Gera snapshot mock da Q1 usando a função real do DW.
    
    Args:
        output_dir: Diretório de saída para os JSONs
        dias: Número de dias sem compra (padrão: 60, significa >= 61 dias)
        data_referencia: Data de referência (YYYY-MM-DD) ou None para hoje
        
    Returns:
        bool: True se sucesso, False caso contrário
    """
    logger.info("=" * 60)
    logger.info("🚀 Gerando snapshot mock Q1 usando função REAL do DW...")
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
    
    try:
        # Conecta ao DW
        logger.info("Conectando ao DW...")
        session = get_session()
        
        # Executa a MESMA função usada em produção
        logger.info(f"Executando get_clientes_sem_compra_ha_dias(dias={dias}, data_referencia={data_referencia})...")
        clientes = get_clientes_sem_compra_ha_dias(
            session=session,
            dias=dias,
            data_referencia=data_referencia,
            filtros_behavior=None,
            query_id="Q1_MOCK_SNAPSHOT"
        )
        
        logger.info(f"✅ Query executada: {len(clientes)} clientes retornados")
        
        if not clientes:
            logger.warning("⚠️  Nenhum cliente retornado. Verifique se o DW está populado.")
            return False
        
        # Classifica por faixas usando a MESMA função do llm_integration_intent
        logger.info("Classificando clientes por faixas...")
        classificacao_faixas = _classificar_clientes_por_faixa(clientes)
        
        # Valida que todos os dias_sem_compra >= 61
        dias_minimo = dias + 1
        clientes_validos = []
        for cliente in clientes:
            dias_sem_compra = cliente.get("dias_sem_compra", 0)
            if isinstance(dias_sem_compra, (int, float)) and dias_sem_compra >= dias_minimo:
                clientes_validos.append(cliente)
            elif isinstance(dias_sem_compra, str):
                try:
                    dias_int = int(float(dias_sem_compra))
                    if dias_int >= dias_minimo:
                        cliente["dias_sem_compra"] = dias_int
                        clientes_validos.append(cliente)
                except (ValueError, TypeError):
                    logger.warning(f"Cliente {cliente.get('cliente_id')} tem dias_sem_compra inválido: {dias_sem_compra}")
        
        if len(clientes_validos) != len(clientes):
            logger.warning(f"⚠️  {len(clientes) - len(clientes_validos)} clientes foram filtrados (dias_sem_compra < {dias_minimo})")
        
        clientes = clientes_validos
        
        # Remove duplicatas por cliente_id (garantir 1 linha por cliente)
        seen = set()
        clientes_unicos = []
        for cliente in clientes:
            cliente_id = cliente.get("cliente_id")
            if cliente_id and cliente_id not in seen:
                seen.add(cliente_id)
                clientes_unicos.append(cliente)
        
        if len(clientes_unicos) != len(clientes):
            logger.warning(f"⚠️  {len(clientes) - len(clientes_unicos)} duplicatas removidas")
        
        clientes = clientes_unicos
        
        # ✅ ORDENAÇÃO: Ordena por dias_sem_compra crescente (mesma ordem da query real)
        # A query real ordena por dias_sem_compra ASC (queries.py linha 332)
        clientes.sort(key=lambda c: c.get("dias_sem_compra", 0))
        logger.info(f"✅ Dados ordenados por dias_sem_compra crescente")
        
        # Garante que todos os campos numéricos são int/float
        for cliente in clientes:
            if "cliente_id" in cliente:
                cliente["cliente_id"] = int(cliente["cliente_id"]) if cliente["cliente_id"] else 0
            if "dias_sem_compra" in cliente:
                cliente["dias_sem_compra"] = int(cliente["dias_sem_compra"]) if cliente["dias_sem_compra"] else 0
        
        # Monta estrutura igual ao que o orquestrador retorna
        total_clientes = len(clientes)
        
        # Gera q1_clientes_sem_compra.json (lista de clientes)
        arquivo_clientes = output_dir / "q1_clientes_sem_compra.json"
        with open(arquivo_clientes, 'w', encoding='utf-8') as f:
            json.dump(clientes, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"✅ Arquivo gerado: {arquivo_clientes} ({total_clientes} clientes)")
        
        # Gera q1_estatisticas.json (estatísticas agregadas)
        arquivo_estatisticas = output_dir / "q1_estatisticas.json"
        estatisticas = {
            "total_clientes": int(total_clientes),
            "faixas": {
                "61_120": int(classificacao_faixas.get("faixa_61_120", 0)),
                "121_180": int(classificacao_faixas.get("faixa_121_180", 0)),
                "181_300": int(classificacao_faixas.get("faixa_181_300", 0)),
                "acima_300": int(classificacao_faixas.get("faixa_mais_300", 0)),
            },
            "percentuais": {
                "61_120": float(classificacao_faixas.get("percentual_61_120", 0.0)),
                "121_180": float(classificacao_faixas.get("percentual_121_180", 0.0)),
                "181_300": float(classificacao_faixas.get("percentual_181_300", 0.0)),
                "acima_300": float(classificacao_faixas.get("percentual_mais_300", 0.0)),
            },
            "data_referencia": data_ref.strftime("%Y-%m-%d"),
            "data_exportacao": datetime.now().isoformat(),
            "dias_filtro": int(dias),
            "fonte": "dw_real"
        }
        
        with open(arquivo_estatisticas, 'w', encoding='utf-8') as f:
            json.dump(estatisticas, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Arquivo gerado: {arquivo_estatisticas}")
        logger.info(f"   - Total: {total_clientes} clientes")
        logger.info(f"   - Faixas: 61-120: {estatisticas['faixas']['61_120']}, "
                   f"121-180: {estatisticas['faixas']['121_180']}, "
                   f"181-300: {estatisticas['faixas']['181_300']}, "
                   f">300: {estatisticas['faixas']['acima_300']}")
        
        # Validações finais
        logger.info("=" * 60)
        logger.info("📊 Validações:")
        logger.info(f"   - Total de clientes: {total_clientes}")
        logger.info(f"   - Clientes únicos: {len(set(c.get('cliente_id') for c in clientes))}")
        logger.info(f"   - Todos dias_sem_compra >= {dias_minimo}: {all(c.get('dias_sem_compra', 0) >= dias_minimo for c in clientes)}")
        logger.info(f"   - Soma das faixas: {sum(estatisticas['faixas'].values())} (deve ser igual a {total_clientes})")
        
        if sum(estatisticas['faixas'].values()) != total_clientes:
            logger.warning(f"⚠️  Soma das faixas ({sum(estatisticas['faixas'].values())}) != total_clientes ({total_clientes})")
        
        session.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao gerar snapshot: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gera snapshot mock Q1 usando função real do DW")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./mock/data",
        help="Diretório de saída para os JSONs (padrão: ./mock/data)"
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
    
    sucesso = gerar_snapshot_q1_from_dw(
        output_dir=output_dir,
        dias=args.dias,
        data_referencia=args.data_referencia
    )
    
    sys.exit(0 if sucesso else 1)

