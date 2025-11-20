#!/usr/bin/env python3
"""
Script de diagnóstico para verificar dados de Vendedor e Supervisor.

Este script verifica:
1. Quantos clientes existem no banco
2. Quantos têm rota_rca preenchido
3. Quantos vendedores existem
4. Se a query de clientes sem compra retorna vendedor/supervisor
5. Testa a criação de vendedores a partir das rotas
"""

import sys
import os
from sqlalchemy import func, distinct, or_
from sqlalchemy.orm import Session

# Adiciona o diretório raiz do projeto ao sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.dw.connection import init_db, SessionLocal, get_db_engine
from src.dw.models import Cliente, Vendedor, Supervisor
from src.dw.queries import get_clientes_sem_compra_ha_dias
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def diagnostico_completo():
    """Executa diagnóstico completo dos dados."""
    logger.info("=" * 60)
    logger.info("DIAGNÓSTICO: Vendedor e Supervisor")
    logger.info("=" * 60)
    
    # Configura para usar SQLite local se existir
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    db_path = os.path.join(project_root, 'data', 'dipam_dw.db')
    
    if os.path.exists(db_path):
        # Define variáveis de ambiente para usar SQLite local
        os.environ['DB_TYPE'] = 'sqlite'
        os.environ['SQLITE_PATH'] = db_path
        # Remove DIPAM_DW_GCS_URI se existir para forçar uso do arquivo local
        if 'DIPAM_DW_GCS_URI' in os.environ:
            del os.environ['DIPAM_DW_GCS_URI']
        logger.info(f"✅ Usando banco SQLite local: {db_path}")
    else:
        logger.warning(f"⚠️  Banco SQLite não encontrado em {db_path}")
        logger.info("Tentando usar configuração padrão (pode ser GCS ou PostgreSQL)")
    
    init_db()
    
    # Importa novamente após init_db para pegar SessionLocal atualizado
    from src.dw.connection import SessionLocal as SessionLocalUpdated
    
    # Verifica se SessionLocal foi inicializado
    if SessionLocalUpdated is None:
        logger.error("SessionLocal não foi inicializado. Verifique a configuração do banco.")
        return
    
    session: Session = SessionLocalUpdated()
    
    try:
        # 1. Verifica clientes
        logger.info("\n1. CLIENTES:")
        total_clientes = session.query(func.count(Cliente.id)).scalar()
        clientes_ativos = session.query(func.count(Cliente.id)).filter(Cliente.ativo == True).scalar()
        clientes_com_rota = session.query(func.count(Cliente.id)).filter(
            Cliente.ativo == True,
            Cliente.rota_rca.isnot(None),
            Cliente.rota_rca != ''
        ).scalar()
        clientes_sem_rota = session.query(func.count(Cliente.id)).filter(
            Cliente.ativo == True,
            or_(Cliente.rota_rca.is_(None), Cliente.rota_rca == '')
        ).scalar()
        
        logger.info(f"  Total de clientes: {total_clientes}")
        logger.info(f"  Clientes ativos: {clientes_ativos}")
        logger.info(f"  Clientes ativos COM rota_rca: {clientes_com_rota}")
        logger.info(f"  Clientes ativos SEM rota_rca: {clientes_sem_rota}")
        
        # Exemplos de rotas
        if clientes_com_rota > 0:
            rotas_exemplo = session.query(Cliente.rota_rca).filter(
                Cliente.ativo == True,
                Cliente.rota_rca.isnot(None),
                Cliente.rota_rca != ''
            ).distinct().limit(5).all()
            logger.info(f"  Exemplos de rotas_rca: {[r[0] for r in rotas_exemplo]}")
        
        # 2. Verifica vendedores
        logger.info("\n2. VENDEDORES:")
        total_vendedores = session.query(func.count(Vendedor.id)).scalar()
        vendedores_ativos = session.query(func.count(Vendedor.id)).filter(Vendedor.ativo == True).scalar()
        logger.info(f"  Total de vendedores: {total_vendedores}")
        logger.info(f"  Vendedores ativos: {vendedores_ativos}")
        
        if total_vendedores > 0:
            vendedores_exemplo = session.query(Vendedor.codigo, Vendedor.nome).limit(5).all()
            logger.info(f"  Exemplos de vendedores (codigo, nome):")
            for codigo, nome in vendedores_exemplo:
                logger.info(f"    - {codigo}: {nome}")
        
        # 3. Verifica supervisores
        logger.info("\n3. SUPERVISORES:")
        total_supervisores = session.query(func.count(Supervisor.id)).scalar()
        logger.info(f"  Total de supervisores: {total_supervisores}")
        
        if total_supervisores > 0:
            supervisores_exemplo = session.query(Supervisor.codigo, Supervisor.nome).limit(5).all()
            logger.info(f"  Exemplos de supervisores (codigo, nome):")
            for codigo, nome in supervisores_exemplo:
                logger.info(f"    - {codigo}: {nome}")
        
        # 4. Verifica relacionamentos
        logger.info("\n4. RELACIONAMENTOS:")
        clientes_com_vendedor_id = session.query(func.count(Cliente.id)).filter(
            Cliente.ativo == True,
            Cliente.vendedor_id.isnot(None)
        ).scalar()
        logger.info(f"  Clientes ativos com vendedor_id: {clientes_com_vendedor_id}")
        
        # 5. Testa query de clientes sem compra
        logger.info("\n5. TESTE DA QUERY (clientes sem compra há 60 dias):")
        try:
            resultados = get_clientes_sem_compra_ha_dias(session, dias=60)
            logger.info(f"  Total de clientes retornados: {len(resultados)}")
            
            if resultados:
                primeiro = resultados[0]
                logger.info(f"  Primeiro resultado:")
                logger.info(f"    - Cliente: {primeiro.get('nome', 'N/A')}")
                logger.info(f"    - Rota: {primeiro.get('rota_id', 'N/A')}")
                logger.info(f"    - Vendedor nome: {primeiro.get('vendedor_nome', 'N/A')}")
                logger.info(f"    - Vendedor código: {primeiro.get('vendedor_codigo', 'N/A')}")
                logger.info(f"    - Supervisor nome: {primeiro.get('supervisor_nome', 'N/A')}")
                logger.info(f"    - Supervisor código: {primeiro.get('supervisor_codigo', 'N/A')}")
                logger.info(f"    - Dias sem compra: {primeiro.get('dias_sem_compra', 'N/A')}")
                
                # Conta quantos têm vendedor/supervisor preenchido
                com_vendedor = sum(1 for r in resultados if r.get('vendedor_nome') or r.get('vendedor_codigo'))
                com_supervisor = sum(1 for r in resultados if r.get('supervisor_nome') or r.get('supervisor_codigo'))
                logger.info(f"  Resultados COM vendedor: {com_vendedor}/{len(resultados)}")
                logger.info(f"  Resultados COM supervisor: {com_supervisor}/{len(resultados)}")
            else:
                logger.warning("  Nenhum resultado retornado pela query")
        except Exception as e:
            logger.error(f"  ERRO ao executar query: {str(e)}", exc_info=True)
        
        # 6. Verifica se há rotas que não têm vendedor correspondente
        logger.info("\n6. VERIFICAÇÃO DE ROTAS SEM VENDEDOR:")
        if clientes_com_rota > 0:
            rotas_distintas = session.query(distinct(Cliente.rota_rca)).filter(
                Cliente.ativo == True,
                Cliente.rota_rca.isnot(None),
                Cliente.rota_rca != ''
            ).all()
            
            rotas_sem_vendedor = []
            for (rota,) in rotas_distintas:
                if not rota or str(rota).strip() == '':
                    continue
                rota = str(rota).strip()
                vendedor = session.query(Vendedor).filter(Vendedor.codigo == rota).first()
                if not vendedor:
                    rotas_sem_vendedor.append(rota)
            
            logger.info(f"  Total de rotas distintas: {len(rotas_distintas)}")
            logger.info(f"  Rotas SEM vendedor correspondente: {len(rotas_sem_vendedor)}")
            if rotas_sem_vendedor:
                logger.info(f"  Exemplos de rotas sem vendedor: {rotas_sem_vendedor[:5]}")
        
        logger.info("\n" + "=" * 60)
        logger.info("DIAGNÓSTICO CONCLUÍDO")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Erro durante diagnóstico: {str(e)}", exc_info=True)
    finally:
        session.close()


if __name__ == "__main__":
    diagnostico_completo()

