"""
Script para corrigir vendedores a partir dos clientes existentes.

Este script cria vendedores baseados nas rotas dos clientes que ainda não têm vendedor correspondente.
Execute após atualizar os modelos e antes de usar a aplicação.

Uso:
    python scripts/fix_vendedores_from_clientes.py
"""

import sys
import os

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.dw.connection import init_db, SessionLocal
from src.dw.models import Cliente, Vendedor, Supervisor
from sqlalchemy import distinct
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fix_vendedores_from_clientes():
    """
    Cria vendedores a partir das rotas dos clientes que ainda não têm vendedor correspondente.
    """
    logger.info("Inicializando banco de dados...")
    init_db()
    
    session = SessionLocal()
    created = 0
    updated = 0
    
    try:
        # Busca todas as rotas distintas dos clientes ativos
        rotas_distintas = session.query(
            distinct(Cliente.rota_rca).label('rota')
        ).filter(
            Cliente.ativo == True,
            Cliente.rota_rca.isnot(None),
            Cliente.rota_rca != ''
        ).all()
        
        logger.info(f"Encontradas {len(rotas_distintas)} rotas distintas de clientes ativos")
        
        for (rota,) in rotas_distintas:
            if not rota or rota.strip() == '':
                continue
            
            rota = rota.strip()
            
            # Verifica se já existe vendedor com esse código
            vendedor = session.query(Vendedor).filter(
                Vendedor.codigo == rota
            ).first()
            
            if not vendedor:
                # Cria novo vendedor usando rota como código
                # Busca nome do vendedor do primeiro cliente com essa rota
                cliente_exemplo = session.query(Cliente).filter(
                    Cliente.rota_rca == rota,
                    Cliente.ativo == True
                ).first()
                
                nome_vendedor = cliente_exemplo.nome_rca if cliente_exemplo and cliente_exemplo.nome_rca else rota
                supervisor_id = cliente_exemplo.supervisor_id if cliente_exemplo else None
                
                vendedor = Vendedor(
                    codigo=rota,
                    nome=nome_vendedor,
                    supervisor_id=supervisor_id,
                    rota_rca=rota,
                    ativo=True
                )
                session.add(vendedor)
                created += 1
                logger.info(f"✅ Vendedor criado: codigo={rota}, nome={nome_vendedor}")
            else:
                # Atualiza vendedor existente se necessário
                updated_fields = False
                
                # Se vendedor não tem nome mas cliente tem nome_rca
                if not vendedor.nome:
                    cliente_exemplo = session.query(Cliente).filter(
                        Cliente.rota_rca == rota,
                        Cliente.ativo == True,
                        Cliente.nome_rca.isnot(None),
                        Cliente.nome_rca != ''
                    ).first()
                    
                    if cliente_exemplo and cliente_exemplo.nome_rca:
                        vendedor.nome = cliente_exemplo.nome_rca
                        updated_fields = True
                
                # Se vendedor não tem supervisor mas cliente tem
                if not vendedor.supervisor_id:
                    cliente_exemplo = session.query(Cliente).filter(
                        Cliente.rota_rca == rota,
                        Cliente.ativo == True,
                        Cliente.supervisor_id.isnot(None)
                    ).first()
                    
                    if cliente_exemplo and cliente_exemplo.supervisor_id:
                        vendedor.supervisor_id = cliente_exemplo.supervisor_id
                        updated_fields = True
                
                if updated_fields:
                    updated += 1
                    logger.info(f"🔄 Vendedor atualizado: codigo={rota}")
        
        session.commit()
        logger.info(f"✅ Processo concluído: {created} vendedores criados, {updated} atualizados")
        
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Erro ao processar: {str(e)}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    fix_vendedores_from_clientes()


