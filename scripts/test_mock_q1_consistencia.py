#!/usr/bin/env python3
"""
Script para validar consistência entre Q1 real e Q1 mock.

Este script:
1. Chama a query real get_clientes_sem_compra_ha_dias diretamente na base local
2. Lê os JSONs de mock/data/q1_clientes_sem_compra.json e q1_estatisticas.json
3. Valida:
   - len(json_clientes) == q1_real_total (ou margem configurável)
   - json_stats.total_clientes == len(json_clientes)
   - Não há clientes duplicados no JSON mock
   - Todos os dias_sem_compra do JSON >= 61
   - Soma das faixas bate com total_clientes

Se houver divergência, o script sai com código 1 e log claro.

Uso:
    python scripts/test_mock_q1_consistencia.py \
      --dias 60 \
      --data-referencia 2025-10-31 \
      --tolerancia 0
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
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
except ImportError as e:
    logger.error(f"❌ Erro ao importar módulos: {e}")
    logger.error("Certifique-se de que está executando do diretório raiz do projeto")
    sys.exit(1)


def carregar_json_mock(mock_data_dir: Path) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Carrega JSONs mock.
    
    Returns:
        tuple: (lista de clientes, estatísticas)
    """
    q1_clientes_path = mock_data_dir / "q1_clientes_sem_compra.json"
    q1_stats_path = mock_data_dir / "q1_estatisticas.json"
    
    if not q1_clientes_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {q1_clientes_path}")
    
    if not q1_stats_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {q1_stats_path}")
    
    with open(q1_clientes_path, "r", encoding="utf-8") as f:
        clientes_mock = json.load(f)
    
    with open(q1_stats_path, "r", encoding="utf-8") as f:
        stats_mock = json.load(f)
    
    return clientes_mock, stats_mock


def validar_consistencia(
    dias: int = 60,
    data_referencia: Optional[str] = None,
    mock_data_dir: Path = Path("./mock/data"),
    tolerancia: int = 0
) -> bool:
    """
    Valida consistência entre Q1 real e Q1 mock.
    
    Args:
        dias: Número de dias sem compra
        data_referencia: Data de referência (YYYY-MM-DD) ou None para hoje
        mock_data_dir: Diretório com os JSONs mock
        tolerancia: Tolerância para diferença de total (padrão: 0 = exato)
        
    Returns:
        bool: True se consistente, False caso contrário
    """
    logger.info("=" * 60)
    logger.info("🔍 Validando consistência entre Q1 real e Q1 mock...")
    logger.info("=" * 60)
    
    # Inicializa banco
    try:
        if SessionLocal is None:
            logger.info("Inicializando conexão com banco...")
            init_db()
        
        if SessionLocal is None:
            logger.error("❌ Não foi possível inicializar conexão com banco")
            return False
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar banco: {e}")
        return False
    
    # Carrega JSONs mock
    try:
        clientes_mock, stats_mock = carregar_json_mock(mock_data_dir)
        logger.info(f"✅ JSONs mock carregados: {len(clientes_mock)} clientes")
    except Exception as e:
        logger.error(f"❌ Erro ao carregar JSONs mock: {e}")
        return False
    
    # Executa query real
    session = None
    try:
        session = SessionLocal()
        
        logger.info(f"Executando query real: get_clientes_sem_compra_ha_dias(dias={dias}, data_referencia={data_referencia})...")
        
        clientes_real = get_clientes_sem_compra_ha_dias(
            session=session,
            dias=dias,
            data_referencia=data_referencia,
            filtros_behavior=None,
            query_id="Q1_VALIDACAO"
        )
        
        logger.info(f"✅ Query real executada: {len(clientes_real)} clientes")
        
        # Validações
        erros = []
        avisos = []
        
        # 1. Total de clientes
        total_real = len(clientes_real)
        total_mock = len(clientes_mock)
        total_stats = stats_mock.get("total_clientes", 0)
        
        logger.info(f"📊 Totais:")
        logger.info(f"   Real: {total_real}")
        logger.info(f"   Mock (JSON clientes): {total_mock}")
        logger.info(f"   Mock (JSON stats): {total_stats}")
        
        if abs(total_real - total_mock) > tolerancia:
            erros.append(
                f"Total de clientes divergente: real={total_real}, mock={total_mock}, "
                f"diferença={abs(total_real - total_mock)} (tolerância={tolerancia})"
            )
        else:
            logger.info("✅ Total de clientes: OK")
        
        # 2. Total do JSON stats deve bater com JSON clientes
        if total_stats != total_mock:
            erros.append(
                f"total_clientes no JSON stats ({total_stats}) != len(clientes) no JSON clientes ({total_mock})"
            )
        else:
            logger.info("✅ Total no JSON stats bate com JSON clientes: OK")
        
        # 3. Não há duplicatas no JSON mock
        cliente_ids_mock: Set[int] = set()
        duplicatas = []
        for cliente in clientes_mock:
            cliente_id = cliente.get("cliente_id")
            if cliente_id in cliente_ids_mock:
                duplicatas.append(cliente_id)
            else:
                cliente_ids_mock.add(cliente_id)
        
        if duplicatas:
            erros.append(f"Clientes duplicados no JSON mock: {len(duplicatas)} duplicatas (IDs: {duplicatas[:10]})")
        else:
            logger.info("✅ Sem duplicatas no JSON mock: OK")
        
        # 4. Todos os dias_sem_compra >= 61
        clientes_com_menos_61 = [
            c for c in clientes_mock
            if c.get("dias_sem_compra", 0) < 61
        ]
        
        if clientes_com_menos_61:
            erros.append(
                f"{len(clientes_com_menos_61)} clientes no JSON mock com menos de 61 dias sem compra "
                f"(IDs: {[c.get('cliente_id') for c in clientes_com_menos_61[:10]]})"
            )
        else:
            logger.info("✅ Todos os clientes têm >= 61 dias sem compra: OK")
        
        # 5. Soma das faixas bate com total_clientes
        faixas = stats_mock.get("faixas", {})
        soma_faixas = sum(faixas.values())
        
        logger.info(f"📊 Faixas:")
        logger.info(f"   61-120: {faixas.get('61_120', 0)}")
        logger.info(f"   121-180: {faixas.get('121_180', 0)}")
        logger.info(f"   181-300: {faixas.get('181_300', 0)}")
        logger.info(f"   >300: {faixas.get('acima_300', 0)}")
        logger.info(f"   Soma: {soma_faixas}")
        
        if soma_faixas != total_mock:
            erros.append(
                f"Soma das faixas ({soma_faixas}) != total_clientes ({total_mock})"
            )
        else:
            logger.info("✅ Soma das faixas bate com total_clientes: OK")
        
        # 6. Validação opcional: comparação de IDs (se tolerância permitir)
        if tolerancia == 0:
            cliente_ids_real: Set[int] = {c.get("cliente_id") for c in clientes_real}
            cliente_ids_mock_set: Set[int] = {c.get("cliente_id") for c in clientes_mock}
            
            apenas_real = cliente_ids_real - cliente_ids_mock_set
            apenas_mock = cliente_ids_mock_set - cliente_ids_real
            
            if apenas_real:
                avisos.append(
                    f"{len(apenas_real)} clientes apenas no real (não no mock): {list(apenas_real)[:10]}"
                )
            
            if apenas_mock:
                avisos.append(
                    f"{len(apenas_mock)} clientes apenas no mock (não no real): {list(apenas_mock)[:10]}"
                )
            
            if not apenas_real and not apenas_mock:
                logger.info("✅ IDs de clientes idênticos entre real e mock: OK")
        
        # Resultado final
        logger.info("=" * 60)
        
        if avisos:
            for aviso in avisos:
                logger.warning(f"⚠️  {aviso}")
        
        if erros:
            logger.error("❌ VALIDAÇÃO FALHOU:")
            for erro in erros:
                logger.error(f"   - {erro}")
            logger.info("=" * 60)
            return False
        else:
            logger.info("✅ VALIDAÇÃO PASSOU: Q1 mock está consistente com Q1 real!")
            logger.info("=" * 60)
            return True
        
    except Exception as e:
        logger.error(f"❌ Erro durante validação: {e}", exc_info=True)
        return False
    
    finally:
        if session:
            session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Valida consistência entre Q1 real e Q1 mock"
    )
    parser.add_argument(
        "--dias",
        type=int,
        default=60,
        help="Número de dias sem compra (padrão: 60)"
    )
    parser.add_argument(
        "--data-referencia",
        type=str,
        default=None,
        help="Data de referência (YYYY-MM-DD) ou None para hoje"
    )
    parser.add_argument(
        "--mock-data-dir",
        type=str,
        default="./mock/data",
        help="Diretório com os JSONs mock"
    )
    parser.add_argument(
        "--tolerancia",
        type=int,
        default=0,
        help="Tolerância para diferença de total (padrão: 0 = exato)"
    )
    
    args = parser.parse_args()
    
    mock_data_dir = Path(args.mock_data_dir)
    
    if not mock_data_dir.exists():
        logger.error(f"❌ Diretório não existe: {mock_data_dir}")
        sys.exit(1)
    
    try:
        sucesso = validar_consistencia(
            dias=args.dias,
            data_referencia=args.data_referencia,
            mock_data_dir=mock_data_dir,
            tolerancia=args.tolerancia
        )
        sys.exit(0 if sucesso else 1)
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}", exc_info=True)
        sys.exit(1)

