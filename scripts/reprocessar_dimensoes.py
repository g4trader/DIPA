#!/usr/bin/env python3
"""
Script para reprocessar completamente as dimensões de Supervisores, Vendedores e Clientes.

Este script:
1. Recria Supervisores a partir do CSV "Supervisor pasta 1"
2. Recria Vendedores a partir do mesmo CSV
3. Reprocessa Clientes com enriquecimento completo
4. Apaga dados antigos inconsistentes

Uso:
    python scripts/reprocessar_dimensoes.py [--prod]
    
    --prod: Usa configuração de produção (banco de produção)
"""

import sys
import os
import argparse
from pathlib import Path

# Adiciona o diretório raiz ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Processa argumentos ANTES de definir SQLITE_PATH para poder copiar banco em produção
parser = argparse.ArgumentParser(description="Reprocessa dimensões de Supervisores, Vendedores e Clientes")
parser.add_argument("--prod", action="store_true", help="Usa configuração de produção")
args, _ = parser.parse_known_args()  # Usa parse_known_args para não falhar com imports

# Se for produção, copia banco para /tmp ANTES de importar connection
if args.prod:
    source_db = os.getenv("SQLITE_PATH", "/app/data/dipam_dw.db")
    tmp_db = "/tmp/dipam_dw.db"
    
    if os.path.exists(source_db):
        import shutil
        try:
            print(f"📥 Copiando banco de {source_db} para {tmp_db}...")
            shutil.copy2(source_db, tmp_db)
            os.chmod(tmp_db, 0o644)
            os.environ["SQLITE_PATH"] = tmp_db
            print(f"✅ Banco copiado para {tmp_db} com permissões de escrita")
        except Exception as e:
            print(f"❌ Erro ao copiar banco: {str(e)}")
            raise
    else:
        os.environ["SQLITE_PATH"] = tmp_db
else:
    # Define SQLITE_PATH para o caminho local se não estiver definido
    if not os.getenv("SQLITE_PATH"):
        sqlite_path = Path(project_root) / "data" / "dipam_dw.db"
        os.environ["SQLITE_PATH"] = str(sqlite_path)

from src.dw.connection import init_db, get_db_session
from src.dw.models import Cliente, Vendedor, Supervisor
from src.dw.etl import (
    load_supervisores_e_vendedores_from_csv,
    enrich_clientes_from_csv
)
import logging
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def limpar_dados_inconsistentes(session):
    """
    Limpa dados inconsistentes antes de reprocessar.
    
    Remove:
    - Vendedores órfãos (sem supervisor válido)
    - Clientes com rota_rca que não corresponde a nenhum vendedor
    """
    logger.info("Limpando dados inconsistentes...")
    
    try:
        # Remove rota_rca de clientes que não têm vendedor correspondente
        engine = session.bind
        with engine.connect() as conn:
            # Verifica se coluna vendedor_id existe
            from sqlalchemy import inspect as sqlalchemy_inspect
            inspector = sqlalchemy_inspect(engine)
            columns = [col['name'] for col in inspector.get_columns('clientes')]
            has_vendedor_id = 'vendedor_id' in columns
            
            # Atualiza clientes com rota_rca que não corresponde a nenhum vendedor
            if has_vendedor_id:
                query = text("""
                    UPDATE clientes
                    SET rota_rca = NULL, supervisor_id = NULL, vendedor_id = NULL
                    WHERE rota_rca IS NOT NULL
                    AND rota_rca NOT IN (SELECT codigo FROM vendedores WHERE ativo = 1)
                """)
            else:
                query = text("""
                    UPDATE clientes
                    SET rota_rca = NULL, supervisor_id = NULL
                    WHERE rota_rca IS NOT NULL
                    AND rota_rca NOT IN (SELECT codigo FROM vendedores WHERE ativo = 1)
                """)
            result = conn.execute(query)
            conn.commit()
            logger.info(f"Clientes com rota_rca inconsistente limpos: {result.rowcount}")
        
        session.commit()
        logger.info("✅ Dados inconsistentes limpos")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Erro ao limpar dados inconsistentes: {str(e)}")
        raise


def main(args=None):
    """Executa reprocessamento completo."""
    logger.info("=" * 80)
    logger.info("REPROCESSAMENTO COMPLETO: SUPERVISORES, VENDEDORES E CLIENTES")
    logger.info("=" * 80)
    
    # Em produção, se o banco foi copiado para /tmp, força reinicialização da conexão
    if args and args.prod and os.getenv("SQLITE_PATH", "").startswith("/tmp"):
        # Limpa cache de conexão se existir
        import importlib
        if 'src.dw.connection' in sys.modules:
            del sys.modules['src.dw.connection']
        # Reimporta para usar o novo caminho
        from src.dw.connection import init_db, get_db_session
    
    # Inicializa banco
    init_db()
    
    # Usa get_db_session que é um generator
    session_gen = get_db_session()
    session = next(session_gen)
    
    try:
        # 1. Limpa dados inconsistentes
        logger.info("\n1. LIMPANDO DADOS INCONSISTENTES")
        logger.info("-" * 80)
        limpar_dados_inconsistentes(session)
        
        # 2. Processa Supervisores e Vendedores
        logger.info("\n2. PROCESSANDO SUPERVISORES E VENDEDORES")
        logger.info("-" * 80)
        
        # Tenta local primeiro, depois Cloud Storage
        supervisor_csv_path = Path(project_root) / "data_raw" / "Supervisor pasta 1.xlsx - Sheet1.csv"
        if not supervisor_csv_path.exists():
            # Tenta baixar do Cloud Storage usando biblioteca Python
            logger.info("Arquivo local não encontrado, tentando baixar do Cloud Storage...")
            try:
                from google.cloud import storage
                client = storage.Client()
                bucket = client.bucket("trivihair-dipam-data")
                blob = bucket.blob("Supervisor pasta 1.xlsx - Sheet1.csv")
                local_gcs_path = Path("/tmp") / "Supervisor pasta 1.xlsx - Sheet1.csv"
                blob.download_to_filename(str(local_gcs_path))
                if local_gcs_path.exists():
                    supervisor_csv_path = local_gcs_path
                    logger.info(f"✅ Arquivo baixado do Cloud Storage: {local_gcs_path}")
                else:
                    logger.error(f"❌ Arquivo não foi baixado corretamente")
                    return
            except ImportError:
                logger.error("❌ Biblioteca google-cloud-storage não disponível. Instale com: pip install google-cloud-storage")
                return
            except Exception as e:
                logger.error(f"❌ Erro ao baixar do Cloud Storage: {str(e)}")
                return
        
        if supervisor_csv_path.exists():
            load_supervisores_e_vendedores_from_csv(str(supervisor_csv_path), session)
        else:
            logger.error(f"❌ Arquivo não encontrado: {supervisor_csv_path}")
            return
        
        # 3. Enriquece Clientes
        logger.info("\n3. ENRIQUECENDO CLIENTES")
        logger.info("-" * 80)
        
        # Tenta local primeiro, depois Cloud Storage
        clientes_csv_path = Path(project_root) / "data_raw" / "Clientes ativos.xls - Clientes ativos.csv"
        if not clientes_csv_path.exists():
            # Tenta baixar do Cloud Storage usando biblioteca Python
            logger.info("Arquivo local não encontrado, tentando baixar do Cloud Storage...")
            try:
                from google.cloud import storage
                client = storage.Client()
                bucket = client.bucket("trivihair-dipam-data")
                blob = bucket.blob("Clientes ativos.xls - Clientes ativos.csv")
                local_gcs_path = Path("/tmp") / "Clientes ativos.xls - Clientes ativos.csv"
                blob.download_to_filename(str(local_gcs_path))
                if local_gcs_path.exists():
                    clientes_csv_path = local_gcs_path
                    logger.info(f"✅ Arquivo baixado do Cloud Storage: {local_gcs_path}")
                else:
                    logger.error(f"❌ Arquivo não foi baixado corretamente")
                    return
            except ImportError:
                logger.error("❌ Biblioteca google-cloud-storage não disponível. Instale com: pip install google-cloud-storage")
                return
            except Exception as e:
                logger.error(f"❌ Erro ao baixar do Cloud Storage: {str(e)}")
                return
        
        if clientes_csv_path.exists():
            enrich_clientes_from_csv(str(clientes_csv_path), session)
        else:
            logger.error(f"❌ Arquivo não encontrado: {clientes_csv_path}")
            return
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ REPROCESSAMENTO CONCLUÍDO COM SUCESSO!")
    
    # Atualiza timestamp do ETL para invalidar cache
    try:
        from src.core.cache_layer import update_etl_timestamp
        update_etl_timestamp()
        logger.info("✅ Timestamp do ETL atualizado (cache será invalidado)")
    except Exception as e:
        logger.warning(f"⚠️  Erro ao atualizar timestamp do ETL: {str(e)}")
        logger.info("=" * 80)
        
        # Em produção, faz upload do banco atualizado de volta para Cloud Storage
        if args and args.prod and os.getenv("SQLITE_PATH", "").startswith("/tmp"):
            logger.info("\n📤 Fazendo upload do banco atualizado para Cloud Storage...")
            try:
                from google.cloud import storage
                client = storage.Client()
                bucket = client.bucket("trivihair-dipam-data")
                blob = bucket.blob("dipam_dw.db")
                blob.upload_from_filename(os.getenv("SQLITE_PATH"))
                logger.info("✅ Banco atualizado enviado para Cloud Storage com sucesso")
            except ImportError:
                logger.warning("⚠️  Biblioteca google-cloud-storage não disponível. Upload não realizado.")
            except Exception as e:
                logger.warning(f"⚠️  Erro ao fazer upload do banco: {str(e)}")
        
        logger.info("\nExecute o script de validação para verificar os resultados:")
        logger.info("  python scripts/diagnostico_pos_etl.py")
        
    except Exception as e:
        session.rollback()
        logger.error(f"\n❌ Erro durante reprocessamento: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise
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
    if args.prod:
        logger.info("🔴 MODO PRODUÇÃO: Usando banco de dados de produção")
    else:
        logger.info("🔵 MODO LOCAL: Usando banco de dados local")
    
    main(args)

