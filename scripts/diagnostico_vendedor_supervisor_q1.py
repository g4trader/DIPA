#!/usr/bin/env python3
"""
Script de diagnóstico para verificar dados de vendedor e supervisor
na pergunta Q1 (clientes sem compra há mais de 60 dias).

Este script verifica:
1. Se existem dados de vendedor/supervisor no banco
2. Se os modelos suportam o relacionamento
3. Se a query retorna vendedor e supervisor corretamente
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
    print(f"[DIAGNÓSTICO] Usando SQLite em: {sqlite_path}")

from src.dw.connection import init_db, get_db_session
from src.dw.models import Cliente, Vendedor, Supervisor, Venda
from src.dw.queries import get_clientes_sem_compra_ha_dias
from sqlalchemy import func, distinct, and_
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Executa diagnóstico completo."""
    logger.info("=" * 80)
    logger.info("DIAGNÓSTICO: VENDEDOR E SUPERVISOR NA PERGUNTA Q1 (+60 DIAS SEM COMPRA)")
    logger.info("=" * 80)
    
    # Inicializa banco
    try:
        init_db()
    except Exception as e:
        logger.error(f"Erro ao inicializar banco: {e}")
        logger.info("Tentando continuar mesmo assim...")
    
    # Usa get_db_session que é um generator, então precisamos iterar
    session_gen = get_db_session()
    session = next(session_gen)
    
    try:
        # ========================================================================
        # 1. VERIFICAR DADOS NO BANCO
        # ========================================================================
        logger.info("\n1. VERIFICANDO DADOS NO BANCO")
        logger.info("-" * 80)
        
        # 1.1. Estatísticas gerais
        total_clientes = session.query(func.count(Cliente.id)).scalar()
        clientes_ativos = session.query(func.count(Cliente.id)).filter(Cliente.ativo == True).scalar()
        clientes_com_rota = session.query(func.count(Cliente.id)).filter(
            and_(
                Cliente.ativo == True,
                Cliente.rota_rca.isnot(None),
                Cliente.rota_rca != ''
            )
        ).scalar()
        
        logger.info(f"Total de clientes: {total_clientes}")
        logger.info(f"Clientes ativos: {clientes_ativos}")
        logger.info(f"Clientes ativos com rota_rca: {clientes_com_rota}")
        
        # 1.2. Verificar vendedor_id (pode não existir)
        try:
            clientes_com_vendedor_id = session.query(func.count(Cliente.id)).filter(
                and_(
                    Cliente.ativo == True,
                    Cliente.vendedor_id.isnot(None)
                )
            ).scalar()
            logger.info(f"Clientes ativos com vendedor_id: {clientes_com_vendedor_id}")
        except Exception as e:
            logger.warning(f"Coluna vendedor_id pode não existir: {e}")
            clientes_com_vendedor_id = 0
        
        # 1.3. Estatísticas de vendedores
        total_vendedores = session.query(func.count(Vendedor.id)).scalar()
        vendedores_ativos = session.query(func.count(Vendedor.id)).filter(Vendedor.ativo == True).scalar()
        vendedores_com_supervisor = session.query(func.count(Vendedor.id)).filter(
            Vendedor.supervisor_id.isnot(None)
        ).scalar()
        
        logger.info(f"\nTotal de vendedores: {total_vendedores}")
        logger.info(f"Vendedores ativos: {vendedores_ativos}")
        logger.info(f"Vendedores com supervisor_id: {vendedores_com_supervisor}")
        
        # 1.4. Estatísticas de supervisores
        total_supervisores = session.query(func.count(Supervisor.id)).scalar()
        supervisores_ativos = session.query(func.count(Supervisor.id)).filter(Supervisor.ativo == True).scalar()
        
        logger.info(f"\nTotal de supervisores: {total_supervisores}")
        logger.info(f"Supervisores ativos: {supervisores_ativos}")
        
        # 1.5. Verificar match entre Cliente.rota_rca e Vendedor.codigo
        rotas_distintas = session.query(distinct(Cliente.rota_rca)).filter(
            and_(
                Cliente.ativo == True,
                Cliente.rota_rca.isnot(None),
                Cliente.rota_rca != ''
            )
        ).all()
        rotas_list = [r[0] for r in rotas_distintas]
        
        vendedores_codigos = session.query(Vendedor.codigo).filter(Vendedor.ativo == True).all()
        vendedores_codigos_list = [v[0] for v in vendedores_codigos]
        
        rotas_com_match = [r for r in rotas_list if r in vendedores_codigos_list]
        
        logger.info(f"\nRotas distintas nos clientes: {len(rotas_list)}")
        logger.info(f"Códigos de vendedores ativos: {len(vendedores_codigos_list)}")
        logger.info(f"Rotas com match em vendedores: {len(rotas_com_match)} ({len(rotas_com_match)/len(rotas_list)*100:.1f}%)")
        
        if rotas_list and len(rotas_list) <= 10:
            logger.info(f"Exemplos de rotas: {rotas_list[:5]}")
        if vendedores_codigos_list and len(vendedores_codigos_list) <= 10:
            logger.info(f"Exemplos de códigos vendedores: {vendedores_codigos_list[:5]}")
        
        # ========================================================================
        # 2. VERIFICAR CLIENTES COM +60 DIAS SEM COMPRA
        # ========================================================================
        logger.info("\n2. VERIFICANDO CLIENTES COM +60 DIAS SEM COMPRA")
        logger.info("-" * 80)
        
        # 2.1. Buscar clientes sem compra há 60 dias
        resultados_query = get_clientes_sem_compra_ha_dias(session, dias=60)
        total_resultados = len(resultados_query)
        
        logger.info(f"Total de clientes sem compra há mais de 60 dias: {total_resultados}")
        
        if total_resultados == 0:
            logger.warning("⚠️  NENHUM CLIENTE ENCONTRADO COM +60 DIAS SEM COMPRA!")
            logger.warning("   Isso pode indicar que não há dados de vendas no banco ou que todos os clientes compraram recentemente.")
            return
        
        # 2.2. Verificar quantos têm vendedor
        com_vendedor_nome = sum(1 for r in resultados_query if r.get('vendedor_nome'))
        com_vendedor_codigo = sum(1 for r in resultados_query if r.get('vendedor_codigo'))
        com_vendedor_qualquer = sum(1 for r in resultados_query if r.get('vendedor_nome') or r.get('vendedor_codigo') or r.get('rota_id'))
        
        logger.info(f"Clientes com vendedor_nome: {com_vendedor_nome} ({com_vendedor_nome/total_resultados*100:.1f}%)")
        logger.info(f"Clientes com vendedor_codigo: {com_vendedor_codigo} ({com_vendedor_codigo/total_resultados*100:.1f}%)")
        logger.info(f"Clientes com vendedor (qualquer): {com_vendedor_qualquer} ({com_vendedor_qualquer/total_resultados*100:.1f}%)")
        
        # 2.3. Verificar quantos têm supervisor
        com_supervisor_nome = sum(1 for r in resultados_query if r.get('supervisor_nome'))
        com_supervisor_codigo = sum(1 for r in resultados_query if r.get('supervisor_codigo'))
        com_supervisor_qualquer = sum(1 for r in resultados_query if r.get('supervisor_nome') or r.get('supervisor_codigo'))
        
        logger.info(f"Clientes com supervisor_nome: {com_supervisor_nome} ({com_supervisor_nome/total_resultados*100:.1f}%)")
        logger.info(f"Clientes com supervisor_codigo: {com_supervisor_codigo} ({com_supervisor_codigo/total_resultados*100:.1f}%)")
        logger.info(f"Clientes com supervisor (qualquer): {com_supervisor_qualquer} ({com_supervisor_qualquer/total_resultados*100:.1f}%)")
        
        # ========================================================================
        # 3. EXEMPLOS DE DADOS
        # ========================================================================
        logger.info("\n3. EXEMPLOS DE DADOS (primeiros 10 clientes)")
        logger.info("-" * 80)
        
        for i, cliente in enumerate(resultados_query[:10], 1):
            logger.info(f"\nCliente {i}:")
            logger.info(f"  - ID: {cliente.get('cliente_id')}")
            logger.info(f"  - Nome: {cliente.get('nome', 'N/A')}")
            logger.info(f"  - Dias sem compra: {cliente.get('dias_sem_compra', 'N/A')}")
            logger.info(f"  - Rota RCA: {cliente.get('rota_id', 'N/A')}")
            logger.info(f"  - Vendedor nome: {cliente.get('vendedor_nome', '—')}")
            logger.info(f"  - Vendedor código: {cliente.get('vendedor_codigo', '—')}")
            logger.info(f"  - Supervisor nome: {cliente.get('supervisor_nome', '—')}")
            logger.info(f"  - Supervisor código: {cliente.get('supervisor_codigo', '—')}")
        
        # ========================================================================
        # 4. VERIFICAR RELACIONAMENTOS DIRETAMENTE NO BANCO
        # ========================================================================
        logger.info("\n4. VERIFICANDO RELACIONAMENTOS DIRETAMENTE NO BANCO")
        logger.info("-" * 80)
        
        # 4.1. Pegar alguns clientes da query
        if resultados_query:
            exemplo_cliente_id = resultados_query[0].get('cliente_id')
            exemplo_rota = resultados_query[0].get('rota_id')
            
            if exemplo_cliente_id:
                cliente_obj = session.query(Cliente).filter(Cliente.id == exemplo_cliente_id).first()
                if cliente_obj:
                    logger.info(f"\nCliente ID {exemplo_cliente_id} (direto do banco):")
                    logger.info(f"  - Nome: {cliente_obj.nome}")
                    logger.info(f"  - Rota RCA: {cliente_obj.rota_rca}")
                    logger.info(f"  - Vendedor ID: {cliente_obj.vendedor_id}")
                    
                    # Tentar encontrar vendedor pela rota_rca
                    if cliente_obj.rota_rca:
                        vendedor_obj = session.query(Vendedor).filter(
                            Vendedor.codigo == cliente_obj.rota_rca
                        ).first()
                        if vendedor_obj:
                            logger.info(f"  - Vendedor encontrado (por rota_rca): {vendedor_obj.nome} (ID: {vendedor_obj.id})")
                            logger.info(f"  - Supervisor ID do vendedor: {vendedor_obj.supervisor_id}")
                            if vendedor_obj.supervisor:
                                logger.info(f"  - Supervisor: {vendedor_obj.supervisor.nome}")
                            else:
                                logger.info(f"  - Supervisor: — (não encontrado)")
                        else:
                            logger.warning(f"  - ⚠️  Vendedor NÃO encontrado para rota_rca '{cliente_obj.rota_rca}'")
                    
                    # Tentar encontrar vendedor por vendedor_id
                    if cliente_obj.vendedor_id:
                        vendedor_obj = session.query(Vendedor).filter(
                            Vendedor.id == cliente_obj.vendedor_id
                        ).first()
                        if vendedor_obj:
                            logger.info(f"  - Vendedor encontrado (por vendedor_id): {vendedor_obj.nome} (ID: {vendedor_obj.id})")
                        else:
                            logger.warning(f"  - ⚠️  Vendedor NÃO encontrado para vendedor_id {cliente_obj.vendedor_id}")
                    
                    # Verificar supervisor direto do cliente
                    if cliente_obj.supervisor_id:
                        supervisor_obj = session.query(Supervisor).filter(
                            Supervisor.id == cliente_obj.supervisor_id
                        ).first()
                        if supervisor_obj:
                            logger.info(f"  - Supervisor direto do cliente: {supervisor_obj.nome}")
        
        # ========================================================================
        # 5. RESUMO E CONCLUSÕES
        # ========================================================================
        logger.info("\n5. RESUMO E CONCLUSÕES")
        logger.info("=" * 80)
        
        logger.info(f"\n✅ DADOS NO BANCO:")
        logger.info(f"   - Clientes ativos: {clientes_ativos}")
        logger.info(f"   - Clientes com rota_rca: {clientes_com_rota}")
        logger.info(f"   - Vendedores ativos: {vendedores_ativos}")
        logger.info(f"   - Supervisores ativos: {supervisores_ativos}")
        logger.info(f"   - Match rota_rca ↔ vendedor.codigo: {len(rotas_com_match)}/{len(rotas_list) if rotas_list else 0}")
        
        logger.info(f"\n✅ RESULTADOS DA QUERY (+60 dias sem compra):")
        logger.info(f"   - Total: {total_resultados}")
        logger.info(f"   - Com vendedor: {com_vendedor_qualquer} ({com_vendedor_qualquer/total_resultados*100:.1f}%)")
        logger.info(f"   - Com supervisor: {com_supervisor_qualquer} ({com_supervisor_qualquer/total_resultados*100:.1f}%)")
        
        if com_vendedor_qualquer == 0:
            logger.warning("\n⚠️  PROBLEMA: Nenhum cliente tem vendedor associado!")
            logger.warning("   Possíveis causas:")
            logger.warning("   1. Cliente.rota_rca não corresponde a Vendedor.codigo")
            logger.warning("   2. Vendedores não foram criados no banco")
            logger.warning("   3. Dados de rota_rca estão vazios ou incorretos")
        
        if com_supervisor_qualquer == 0:
            logger.warning("\n⚠️  PROBLEMA: Nenhum cliente tem supervisor associado!")
            logger.warning("   Possíveis causas:")
            logger.warning("   1. Vendedor.supervisor_id não está preenchido")
            logger.warning("   2. Cliente.supervisor_id não está preenchido")
            logger.warning("   3. Supervisores não foram criados no banco")
        
        if com_vendedor_qualquer > 0 and com_supervisor_qualquer > 0:
            logger.info("\n✅ SUCESSO: Dados de vendedor e supervisor estão disponíveis!")
            logger.info("   A query está funcionando corretamente.")
            logger.info("   Se o frontend não exibe, verifique o mapper_handler_refatorado.py")
        
    except Exception as e:
        logger.error(f"Erro durante diagnóstico: {str(e)}", exc_info=True)
        raise
    
    finally:
        try:
            session.close()
        except:
            pass
        try:
            next(session_gen, None)  # Finaliza o generator
        except:
            pass


if __name__ == "__main__":
    main()

