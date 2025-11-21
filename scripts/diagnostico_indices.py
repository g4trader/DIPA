#!/usr/bin/env python3
"""
Script para diagnosticar índices no banco de dados.

Verifica se os índices necessários para performance existem e estão sendo usados.
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

from src.dw.connection import init_db, get_db_engine
from sqlalchemy import inspect, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_indexes():
    """Verifica se os índices necessários existem."""
    logger.info("=" * 80)
    logger.info("DIAGNÓSTICO DE ÍNDICES - DIPAM COPILOT")
    logger.info("=" * 80)
    
    try:
        init_db()
        engine = get_db_engine()
        inspector = inspect(engine)
        
        # Índices necessários conforme especificação
        required_indexes = {
            "clientes": [
                ("data_ultima_compra", "Cliente.data_ultima_compra"),
                ("rota_rca", "Cliente.rota_rca"),
                ("supervisor_id", "Cliente.supervisor_id"),
                ("ativo", "Cliente.ativo"),
            ],
            "vendedores": [
                ("codigo", "Vendedor.codigo"),
                ("supervisor_id", "Vendedor.supervisor_id"),
                ("ativo", "Vendedor.ativo"),
            ],
            "supervisores": [
                ("id", "Supervisor.id"),
                ("pasta", "Supervisor.pasta"),
            ],
            "vendas": [
                ("data_venda", "Venda.data_venda"),
                ("cliente_id", "Venda.cliente_id"),
                ("produto_id", "Venda.produto_id"),
            ],
        }
        
        logger.info("\n📊 VERIFICAÇÃO DE ÍNDICES:")
        logger.info("-" * 80)
        
        all_ok = True
        
        for table_name, columns in required_indexes.items():
            logger.info(f"\n📋 Tabela: {table_name}")
            
            try:
                # Lista índices existentes na tabela
                indexes = inspector.get_indexes(table_name)
                index_names = [idx["name"] for idx in indexes]
                indexed_columns = set()
                for idx in indexes:
                    indexed_columns.update(idx.get("column_names", []))
                
                for column_name, description in columns:
                    if column_name in indexed_columns:
                        logger.info(f"  ✅ {description}: ÍNDICE EXISTE")
                    else:
                        logger.warning(f"  ⚠️  {description}: ÍNDICE NÃO ENCONTRADO")
                        all_ok = False
                
                # Lista todos os índices da tabela
                if indexes:
                    logger.info(f"  📌 Índices existentes: {', '.join(index_names)}")
                else:
                    logger.warning(f"  ⚠️  Nenhum índice encontrado na tabela {table_name}")
                    
            except Exception as e:
                logger.error(f"  ❌ Erro ao verificar tabela {table_name}: {str(e)}")
                all_ok = False
        
        # Verifica índices via SQL direto (SQLite)
        logger.info("\n" + "=" * 80)
        logger.info("VERIFICAÇÃO VIA SQL:")
        logger.info("-" * 80)
        
        try:
            with engine.connect() as conn:
                # SQLite: consulta sqlite_master
                result = conn.execute(text("""
                    SELECT name, tbl_name, sql 
                    FROM sqlite_master 
                    WHERE type = 'index' 
                    AND tbl_name IN ('clientes', 'vendedores', 'supervisores', 'vendas')
                    ORDER BY tbl_name, name
                """))
                
                indexes_sql = result.fetchall()
                
                if indexes_sql:
                    logger.info("\nÍndices encontrados no banco:")
                    for idx_name, tbl_name, idx_sql in indexes_sql:
                        logger.info(f"  - {tbl_name}.{idx_name}")
                        if idx_sql:
                            logger.debug(f"    SQL: {idx_sql[:100]}...")
                else:
                    logger.warning("Nenhum índice encontrado via SQL")
                    
        except Exception as e:
            logger.warning(f"Erro ao verificar índices via SQL: {str(e)}")
        
        # Resumo final
        logger.info("\n" + "=" * 80)
        if all_ok:
            logger.info("✅ TODOS OS ÍNDICES NECESSÁRIOS ESTÃO PRESENTES")
        else:
            logger.warning("⚠️  ALGUNS ÍNDICES ESTÃO FALTANDO")
            logger.info("\n💡 RECOMENDAÇÃO: Criar índices faltantes para melhorar performance")
            logger.info("   Exemplo SQL:")
            logger.info("   CREATE INDEX IF NOT EXISTS ix_clientes_rota_rca ON clientes(rota_rca);")
            logger.info("   CREATE INDEX IF NOT EXISTS ix_vendedores_codigo ON vendedores(codigo);")
            logger.info("   CREATE INDEX IF NOT EXISTS ix_vendas_data_venda ON vendas(data_venda);")
        
        logger.info("=" * 80)
        
        return all_ok
        
    except Exception as e:
        logger.error(f"Erro durante diagnóstico: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    success = check_indexes()
    sys.exit(0 if success else 1)

