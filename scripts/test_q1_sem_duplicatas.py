#!/usr/bin/env python3
"""
Script para testar se a query Q1 retorna apenas 1 linha por cliente (sem duplicatas).
"""

import sys
import os
from pathlib import Path

# Adiciona o diretório raiz ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Define SQLITE_PATH para o caminho local se não estiver definido
if not os.getenv("SQLITE_PATH"):
    sqlite_path = Path(project_root) / "data" / "dipam_dw.db"
    os.environ["SQLITE_PATH"] = str(sqlite_path)

from src.dw.connection import init_db, get_db_session
from src.dw.queries import get_clientes_sem_compra_ha_dias
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Testa se a query Q1 retorna apenas 1 linha por cliente."""
    logger.info("=" * 80)
    logger.info("TESTE: Query Q1 - Verificação de Duplicatas")
    logger.info("=" * 80)
    
    try:
        init_db()
    except Exception as e:
        logger.error(f"Erro ao inicializar banco: {e}")
        return
    
    session_gen = get_db_session()
    session = next(session_gen)
    
    try:
        # Executa query Q1
        logger.info("\nExecutando query Q1 (clientes sem compra há mais de 60 dias)...")
        resultados = get_clientes_sem_compra_ha_dias(
            session=session,
            dias=60,
            data_referencia=None,
            filtros_behavior=None
        )
        
        logger.info(f"\n✅ Query retornou {len(resultados)} registros")
        
        # Verifica duplicatas por cliente_id
        cliente_ids = {}
        duplicatas = []
        
        for idx, cliente in enumerate(resultados):
            cliente_id = cliente.get("cliente_id")
            if cliente_id in cliente_ids:
                duplicatas.append({
                    "cliente_id": cliente_id,
                    "primeira_ocorrencia": cliente_ids[cliente_id],
                    "ocorrencia_atual": idx + 1
                })
            else:
                cliente_ids[cliente_id] = idx + 1
        
        # Resultado
        logger.info(f"\n📊 ANÁLISE DE DUPLICATAS:")
        logger.info(f"   - Total de registros: {len(resultados)}")
        logger.info(f"   - Clientes únicos: {len(cliente_ids)}")
        logger.info(f"   - Duplicatas encontradas: {len(duplicatas)}")
        
        if duplicatas:
            logger.error("\n❌ FALHA: Foram encontradas duplicatas!")
            logger.error("Primeiras 10 duplicatas:")
            for dup in duplicatas[:10]:
                logger.error(f"   - Cliente ID {dup['cliente_id']}: linhas {dup['primeira_ocorrencia']} e {dup['ocorrencia_atual']}")
            return False
        else:
            logger.info("\n✅ SUCESSO: Nenhuma duplicata encontrada!")
            logger.info(f"   - Todos os {len(resultados)} registros são de clientes únicos")
            
            # Verifica se o número de registros corresponde ao número de clientes únicos
            if len(resultados) == len(cliente_ids):
                logger.info("✅ CONFIRMADO: 1 linha por cliente (sem duplicatas)")
                return True
            else:
                logger.warning(f"⚠️  ATENÇÃO: Número de registros ({len(resultados)}) != número de clientes únicos ({len(cliente_ids)})")
                return False
        
    except Exception as e:
        logger.error(f"\n❌ Erro ao executar teste: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    finally:
        try:
            session.close()
        except:
            pass
        try:
            next(session_gen, None)
        except:
            pass


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

