#!/usr/bin/env python3
"""
Script para executar migração de vendedor_id localmente.

Este script:
1. Adiciona coluna vendedor_id na tabela clientes (se não existir)
2. Cria vendedores a partir das rotas dos clientes
3. Popula vendedor_id nos clientes
"""

import sys
import os
from sqlalchemy import text, distinct, func, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, ProgrammingError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.dw.connection import init_db, SessionLocal, get_db_engine
from src.dw.models import Cliente, Vendedor, Supervisor
from src.load_to_db import get_or_create_vendedor, get_or_create_supervisor
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def migrar_vendedor_id_local():
    """Executa migração localmente."""
    logger.info("=" * 80)
    logger.info("MIGRAÇÃO LOCAL: vendedor_id")
    logger.info("=" * 80)
    
    # Configura banco local
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    db_path = os.path.join(project_root, 'data', 'dipam_dw.db')
    
    if os.path.exists(db_path):
        os.environ['DB_TYPE'] = 'sqlite'
        os.environ['SQLITE_PATH'] = db_path
        if 'DIPAM_DW_GCS_URI' in os.environ:
            del os.environ['DIPAM_DW_GCS_URI']
        logger.info(f"✅ Usando banco SQLite local: {db_path}")
    else:
        logger.warning(f"⚠️  Banco SQLite não encontrado em {db_path}")
        logger.info("Tentando usar configuração padrão")
    
    init_db()
    from src.dw.connection import SessionLocal as SessionLocalUpdated
    
    if SessionLocalUpdated is None:
        logger.error("SessionLocal não foi inicializado.")
        return
    
    engine = get_db_engine()
    session: Session = SessionLocalUpdated()
    
    results = {
        "coluna_criada": False,
        "vendedores_criados": 0,
        "clientes_atualizados": 0,
        "erros": []
    }
    
    try:
        # 1. Verifica se coluna existe
        try:
            session.query(Cliente.vendedor_id).limit(1).all()
            logger.info("✅ Coluna vendedor_id já existe")
        except (OperationalError, ProgrammingError, AttributeError) as e:
            logger.info(f"Criando coluna vendedor_id... (erro: {str(e)})")
            db_url = str(engine.url)
            try:
                if 'sqlite' in db_url:
                    with engine.connect() as conn:
                        conn.execute(text("ALTER TABLE clientes ADD COLUMN vendedor_id INTEGER"))
                        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_clientes_vendedor_id ON clientes(vendedor_id)"))
                        conn.commit()
                else:
                    with engine.connect() as conn:
                        conn.execute(text("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS vendedor_id INTEGER"))
                        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_clientes_vendedor_id ON clientes(vendedor_id)"))
                        try:
                            conn.execute(text("ALTER TABLE clientes ADD CONSTRAINT fk_clientes_vendedor_id FOREIGN KEY (vendedor_id) REFERENCES vendedores(id)"))
                        except:
                            pass
                        conn.commit()
                
                results["coluna_criada"] = True
                logger.info("✅ Coluna vendedor_id criada")
            except Exception as create_error:
                logger.warning(f"Erro ao criar coluna (pode já existir): {str(create_error)}")
        
        # 2. Cria vendedores a partir das rotas
        rotas_distintas = session.query(distinct(Cliente.rota_rca)).filter(
            Cliente.ativo == True,
            Cliente.rota_rca.isnot(None),
            Cliente.rota_rca != ''
        ).all()
        
        logger.info(f"Encontradas {len(rotas_distintas)} rotas distintas")
        
        for (rota,) in rotas_distintas:
            if not rota or str(rota).strip() == '':
                continue
            
            rota = str(rota).strip()
            vendedor = session.query(Vendedor).filter(Vendedor.codigo == rota).first()
            
            if not vendedor:
                cliente_exemplo = session.query(Cliente).filter(
                    Cliente.rota_rca == rota,
                    Cliente.ativo == True
                ).first()
                
                if cliente_exemplo:
                    nome_vendedor = cliente_exemplo.nome_rca if cliente_exemplo.nome_rca else rota
                    supervisor_id = cliente_exemplo.supervisor_id
                    
                    vendedor = get_or_create_vendedor(
                        session,
                        nome=nome_vendedor,
                        codigo=rota,
                        supervisor_id=supervisor_id
                    )
                    results["vendedores_criados"] += 1
                    session.commit()
                    logger.info(f"✅ Vendedor criado: codigo={rota}, nome={nome_vendedor}")
        
        # 3. Popula vendedor_id
        clientes_sem_vendedor = session.query(Cliente).filter(
            Cliente.ativo == True,
            Cliente.rota_rca.isnot(None),
            Cliente.rota_rca != '',
            Cliente.vendedor_id.is_(None)
        ).all()
        
        logger.info(f"Atualizando {len(clientes_sem_vendedor)} clientes com vendedor_id...")
        
        for cliente in clientes_sem_vendedor:
            if cliente.rota_rca:
                vendedor = session.query(Vendedor).filter(Vendedor.codigo == cliente.rota_rca).first()
                if vendedor:
                    cliente.vendedor_id = vendedor.id
                    results["clientes_atualizados"] += 1
                else:
                    results["erros"].append(f"Vendedor para rota '{cliente.rota_rca}' do cliente '{cliente.id}' não encontrado.")
        
        session.commit()
        logger.info(f"✅ Migração concluída: {results['vendedores_criados']} vendedores criados, {results['clientes_atualizados']} clientes atualizados")
        
        logger.info("\n" + "=" * 80)
        logger.info("RESULTADOS:")
        logger.info("=" * 80)
        logger.info(f"  Coluna criada: {results['coluna_criada']}")
        logger.info(f"  Vendedores criados: {results['vendedores_criados']}")
        logger.info(f"  Clientes atualizados: {results['clientes_atualizados']}")
        if results['erros']:
            logger.warning(f"  Erros: {len(results['erros'])}")
            for erro in results['erros'][:5]:
                logger.warning(f"    - {erro}")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Erro durante migração: {str(e)}", exc_info=True)
    finally:
        session.close()


if __name__ == "__main__":
    migrar_vendedor_id_local()


