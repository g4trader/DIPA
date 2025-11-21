"""
Script de migração para adicionar coluna vendedor_id na tabela clientes.

Este script:
1. Adiciona a coluna vendedor_id se não existir
2. Popula vendedor_id baseado em rota_rca
3. Cria vendedores a partir das rotas dos clientes

Uso:
    python scripts/migrate_add_vendedor_id.py
"""

import sys
import os

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.dw.connection import init_db, SessionLocal, get_db_engine
from src.dw.models import Cliente, Vendedor, Supervisor
from src.load_to_db import get_or_create_vendedor
from sqlalchemy import distinct, text
from sqlalchemy.exc import OperationalError, ProgrammingError
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_add_vendedor_id():
    """
    Adiciona coluna vendedor_id na tabela clientes e popula dados.
    """
    logger.info("Inicializando banco de dados...")
    init_db()
    
    engine = get_db_engine()
    session = SessionLocal()
    
    try:
        # 1. Verifica se a coluna já existe
        logger.info("Verificando se coluna vendedor_id já existe...")
        try:
            # Tenta fazer uma query que usa vendedor_id
            session.query(Cliente.vendedor_id).limit(1).all()
            logger.info("✅ Coluna vendedor_id já existe")
        except (OperationalError, ProgrammingError, AttributeError):
            # Coluna não existe, precisa criar
            logger.info("Coluna vendedor_id não existe, criando...")
            
            # Detecta tipo de banco
            db_url = str(engine.url)
            if 'sqlite' in db_url:
                # SQLite
                session.execute(text("ALTER TABLE clientes ADD COLUMN vendedor_id INTEGER"))
                session.execute(text("CREATE INDEX IF NOT EXISTS ix_clientes_vendedor_id ON clientes(vendedor_id)"))
                logger.info("✅ Coluna vendedor_id criada no SQLite")
            else:
                # PostgreSQL
                session.execute(text("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS vendedor_id INTEGER"))
                session.execute(text("CREATE INDEX IF NOT EXISTS ix_clientes_vendedor_id ON clientes(vendedor_id)"))
                session.execute(text("ALTER TABLE clientes ADD CONSTRAINT fk_clientes_vendedor_id FOREIGN KEY (vendedor_id) REFERENCES vendedores(id)"))
                logger.info("✅ Coluna vendedor_id criada no PostgreSQL")
            
            session.commit()
        
        # 2. Cria vendedores a partir das rotas dos clientes
        logger.info("Criando vendedores a partir das rotas dos clientes...")
        rotas_distintas = session.query(
            distinct(Cliente.rota_rca).label('rota')
        ).filter(
            Cliente.ativo == True,
            Cliente.rota_rca.isnot(None),
            Cliente.rota_rca != ''
        ).all()
        
        created = 0
        for (rota,) in rotas_distintas:
            if not rota or rota.strip() == '':
                continue
            
            rota = rota.strip()
            
            # Verifica se já existe vendedor com esse código
            vendedor = session.query(Vendedor).filter(
                Vendedor.codigo == rota
            ).first()
            
            if not vendedor:
                # Busca informações do primeiro cliente com essa rota
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
                        codigo=rota,  # ✅ Usa rota como código
                        supervisor_id=supervisor_id,
                        rota_rca=rota
                    )
                    created += 1
                    logger.info(f"✅ Vendedor criado: codigo={rota}, nome={nome_vendedor}")
        
        session.commit()
        logger.info(f"✅ {created} vendedores criados")
        
        # 3. Popula vendedor_id nos clientes baseado em rota_rca
        logger.info("Populando vendedor_id nos clientes...")
        updated = 0
        
        clientes_sem_vendedor = session.query(Cliente).filter(
            Cliente.ativo == True,
            Cliente.rota_rca.isnot(None),
            Cliente.rota_rca != '',
            Cliente.vendedor_id.is_(None)
        ).all()
        
        for cliente in clientes_sem_vendedor:
            if cliente.rota_rca:
                vendedor = session.query(Vendedor).filter(
                    Vendedor.codigo == cliente.rota_rca
                ).first()
                
                if vendedor:
                    cliente.vendedor_id = vendedor.id
                    updated += 1
        
        session.commit()
        logger.info(f"✅ {updated} clientes atualizados com vendedor_id")
        
        logger.info("✅ Migração concluída com sucesso!")
        
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Erro na migração: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    migrate_add_vendedor_id()


