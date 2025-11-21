#!/usr/bin/env python3
"""
Script de validação pós-ETL para verificar preenchimento de vendedor e supervisor.

Este script verifica:
1. Total de clientes ativos
2. Quantos têm vendedor_codigo não nulo
3. Quantos têm rota_rca não nulo
4. Quantos têm supervisor_id não nulo
5. Na query "clientes com cadastro ativo sem compra há +60 dias":
   - Total de clientes
   - Quantos têm vendedor_nome
   - Quantos têm supervisor_nome
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
from src.dw.models import Cliente, Vendedor, Supervisor
from src.dw.queries import get_clientes_sem_compra_ha_dias
from sqlalchemy import func, and_
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Executa validação pós-ETL."""
    logger.info("=" * 80)
    logger.info("VALIDAÇÃO PÓS-ETL: VENDEDOR E SUPERVISOR")
    logger.info("=" * 80)
    
    # Inicializa banco
    try:
        init_db()
    except Exception as e:
        logger.error(f"Erro ao inicializar banco: {e}")
        logger.info("Tentando continuar mesmo assim...")
    
    # Garante que SessionLocal foi criado
    session_gen = get_db_session()
    session = next(session_gen)
    
    try:
        # ========================================================================
        # 1. ESTATÍSTICAS GERAIS DE CLIENTES
        # ========================================================================
        logger.info("\n1. ESTATÍSTICAS GERAIS DE CLIENTES")
        logger.info("-" * 80)
        
        total_clientes = session.query(func.count(Cliente.id)).scalar()
        clientes_ativos = session.query(func.count(Cliente.id)).filter(Cliente.ativo == True).scalar()
        
        # REGRA PM: Quantos têm vendedor_codigo (inferido pela presença de rota_rca ou vendedor_id)
        # Como não há campo vendedor_codigo direto, inferimos pela rota_rca
        clientes_com_rota_rca = session.query(func.count(Cliente.id)).filter(
            and_(
                Cliente.ativo == True,
                Cliente.rota_rca.isnot(None),
                Cliente.rota_rca != ''
            )
        ).scalar()
        
        # REGRA PM: Quantos têm supervisor_id
        clientes_com_supervisor_id = session.query(func.count(Cliente.id)).filter(
            and_(
                Cliente.ativo == True,
                Cliente.supervisor_id.isnot(None)
            )
        ).scalar()
        
        # Clientes com vendedor_id (se o campo existir)
        try:
            clientes_com_vendedor_id = session.query(func.count(Cliente.id)).filter(
                and_(
                    Cliente.ativo == True,
                    Cliente.vendedor_id.isnot(None)
                )
            ).scalar()
        except Exception:
            clientes_com_vendedor_id = 0
        
        logger.info(f"Total de clientes: {total_clientes}")
        logger.info(f"Clientes ativos: {clientes_ativos}")
        logger.info(f"Clientes ativos com vendedor_codigo (inferido por rota_rca): {clientes_com_rota_rca} ({clientes_com_rota_rca/clientes_ativos*100:.1f}%)")
        logger.info(f"Clientes ativos com rota_rca: {clientes_com_rota_rca} ({clientes_com_rota_rca/clientes_ativos*100:.1f}%)")
        logger.info(f"Clientes ativos com supervisor_id: {clientes_com_supervisor_id} ({clientes_com_supervisor_id/clientes_ativos*100:.1f}%)")
        if clientes_com_vendedor_id > 0:
            logger.info(f"Clientes ativos com vendedor_id: {clientes_com_vendedor_id} ({clientes_com_vendedor_id/clientes_ativos*100:.1f}%)")
        
        # ========================================================================
        # 2. ESTATÍSTICAS DE VENDEDORES E SUPERVISORES
        # ========================================================================
        logger.info("\n2. ESTATÍSTICAS DE VENDEDORES E SUPERVISORES")
        logger.info("-" * 80)
        
        total_vendedores = session.query(func.count(Vendedor.id)).scalar()
        vendedores_ativos = session.query(func.count(Vendedor.id)).filter(Vendedor.ativo == True).scalar()
        vendedores_com_supervisor = session.query(func.count(Vendedor.id)).filter(
            Vendedor.supervisor_id.isnot(None)
        ).scalar()
        
        total_supervisores = session.query(func.count(Supervisor.id)).scalar()
        supervisores_ativos = session.query(func.count(Supervisor.id)).filter(Supervisor.ativo == True).scalar()
        
        logger.info(f"Total de vendedores: {total_vendedores}")
        logger.info(f"Vendedores ativos: {vendedores_ativos}")
        logger.info(f"Vendedores com supervisor_id: {vendedores_com_supervisor} ({vendedores_com_supervisor/vendedores_ativos*100:.1f}%)")
        logger.info(f"Total de supervisores: {total_supervisores}")
        logger.info(f"Supervisores ativos: {supervisores_ativos}")
        
        # ========================================================================
        # 3. QUERY "CLIENTES SEM COMPRA HÁ +60 DIAS"
        # ========================================================================
        logger.info("\n3. QUERY: CLIENTES SEM COMPRA HÁ +60 DIAS")
        logger.info("-" * 80)
        
        resultados_query = get_clientes_sem_compra_ha_dias(session, dias=60)
        total_resultados = len(resultados_query)
        
        logger.info(f"Total de clientes sem compra há mais de 60 dias: {total_resultados}")
        
        if total_resultados == 0:
            logger.warning("⚠️  NENHUM CLIENTE ENCONTRADO COM +60 DIAS SEM COMPRA!")
            return
        
        # ========================================================================
        # 3.1. VALIDAÇÃO DE DUPLICATAS NA Q1 (CRÍTICO)
        # ========================================================================
        logger.info("\n3.1. VALIDAÇÃO DE DUPLICATAS NA Q1")
        logger.info("-" * 80)
        
        # Extrai todos os IDs de clientes
        cliente_ids = []
        for resultado in resultados_query:
            cliente_id = resultado.get('cliente_id')
            if cliente_id is not None:
                cliente_id_str = str(cliente_id).strip()
                if cliente_id_str:
                    cliente_ids.append(cliente_id_str)
        
        clientes_unicos = len(set(cliente_ids))
        total_registros = len(resultados_query)
        
        logger.info(f"Q1 - Clientes distintos: {clientes_unicos} | Registros totais: {total_registros}")
        
        # Verifica duplicatas
        if total_registros != clientes_unicos:
            logger.error("❌ ALERTA CRÍTICO: Foram encontrados clientes duplicados na resposta da Q1!")
            logger.error(f"   Total de registros: {total_registros} | Clientes distintos: {clientes_unicos}")
            logger.error(f"   Diferença: {total_registros - clientes_unicos} cliente(s) duplicado(s)")
            
            # Identifica IDs duplicados
            from collections import Counter
            contador_ids = Counter(cliente_ids)
            ids_duplicados = {id_val: count for id_val, count in contador_ids.items() if count > 1}
            
            if ids_duplicados:
                logger.error(f"   IDs duplicados (primeiros 10):")
                for cliente_id, count in list(ids_duplicados.items())[:10]:
                    logger.error(f"     - Cliente ID {cliente_id}: aparece {count} vez(es)")
                if len(ids_duplicados) > 10:
                    logger.error(f"     ... e mais {len(ids_duplicados) - 10} cliente(s) duplicado(s)")
            
            logger.error("   ⚠️  ALERTA: A query Q1 não deve retornar clientes duplicados!")
            tem_duplicatas = True
        else:
            logger.info(f"✅ Validação Q1: nenhum cliente duplicado. Registros = {total_registros}, Clientes únicos = {clientes_unicos}.")
            tem_duplicatas = False
        
        # Conta quantos têm vendedor_nome
        com_vendedor_nome = sum(1 for r in resultados_query if r.get('vendedor_nome'))
        com_vendedor_codigo = sum(1 for r in resultados_query if r.get('vendedor_codigo'))
        com_vendedor_qualquer = sum(1 for r in resultados_query if r.get('vendedor_nome') or r.get('vendedor_codigo') or r.get('rota_id'))
        
        # Conta quantos têm supervisor_nome
        com_supervisor_nome = sum(1 for r in resultados_query if r.get('supervisor_nome'))
        com_supervisor_codigo = sum(1 for r in resultados_query if r.get('supervisor_codigo'))
        com_supervisor_qualquer = sum(1 for r in resultados_query if r.get('supervisor_nome') or r.get('supervisor_codigo'))
        
        logger.info(f"Clientes com vendedor_nome: {com_vendedor_nome} ({com_vendedor_nome/total_resultados*100:.1f}%)")
        logger.info(f"Clientes com vendedor_codigo: {com_vendedor_codigo} ({com_vendedor_codigo/total_resultados*100:.1f}%)")
        logger.info(f"Clientes com vendedor (qualquer): {com_vendedor_qualquer} ({com_vendedor_qualquer/total_resultados*100:.1f}%)")
        logger.info(f"Clientes com supervisor_nome: {com_supervisor_nome} ({com_supervisor_nome/total_resultados*100:.1f}%)")
        logger.info(f"Clientes com supervisor_codigo: {com_supervisor_codigo} ({com_supervisor_codigo/total_resultados*100:.1f}%)")
        logger.info(f"Clientes com supervisor (qualquer): {com_supervisor_qualquer} ({com_supervisor_qualquer/total_resultados*100:.1f}%)")
        
        # ========================================================================
        # 4. EXEMPLOS DE DADOS
        # ========================================================================
        logger.info("\n4. EXEMPLOS DE DADOS (primeiros 5 clientes)")
        logger.info("-" * 80)
        
        for i, cliente in enumerate(resultados_query[:5], 1):
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
        # 5. RESUMO E CONCLUSÕES
        # ========================================================================
        logger.info("\n5. RESUMO E CONCLUSÕES")
        logger.info("=" * 80)
        
        logger.info(f"\n✅ ESTATÍSTICAS GERAIS:")
        logger.info(f"   - Clientes ativos: {clientes_ativos}")
        logger.info(f"   - Clientes com rota_rca: {clientes_com_rota_rca} ({clientes_com_rota_rca/clientes_ativos*100:.1f}%)")
        logger.info(f"   - Clientes com supervisor_id: {clientes_com_supervisor_id} ({clientes_com_supervisor_id/clientes_ativos*100:.1f}%)")
        logger.info(f"   - Vendedores ativos: {vendedores_ativos}")
        logger.info(f"   - Vendedores com supervisor: {vendedores_com_supervisor} ({vendedores_com_supervisor/vendedores_ativos*100:.1f}%)")
        logger.info(f"   - Supervisores ativos: {supervisores_ativos}")
        
        logger.info(f"\n✅ RESULTADOS DA QUERY (+60 dias sem compra):")
        logger.info(f"   - Total: {total_resultados}")
        logger.info(f"   - Clientes distintos: {clientes_unicos}")
        logger.info(f"   - Com vendedor: {com_vendedor_qualquer} ({com_vendedor_qualquer/total_resultados*100:.1f}%)")
        logger.info(f"   - Com vendedor_nome: {com_vendedor_nome} ({com_vendedor_nome/total_resultados*100:.1f}%)")
        logger.info(f"   - Com supervisor: {com_supervisor_qualquer} ({com_supervisor_qualquer/total_resultados*100:.1f}%)")
        logger.info(f"   - Com supervisor_nome: {com_supervisor_nome} ({com_supervisor_nome/total_resultados*100:.1f}%)")
        
        # Alerta sobre duplicatas no resumo final
        if tem_duplicatas:
            logger.error("\n❌ ALERTA: A query Q1 contém clientes duplicados. Revisar implementação da query!")
        
        # REGRA PM: Objetivo final >85%
        if com_vendedor_nome / total_resultados >= 0.85:
            logger.info("\n✅ SUCESSO: Mais de 85% dos clientes têm vendedor! (Objetivo atingido)")
        elif com_vendedor_nome / total_resultados >= 0.8:
            logger.info("\n✅ BOM: Mais de 80% dos clientes têm vendedor. (Próximo do objetivo)")
        elif com_vendedor_nome / total_resultados >= 0.5:
            logger.warning("\n⚠️  PARCIAL: Entre 50-80% dos clientes têm vendedor. Melhorias necessárias no ETL.")
        else:
            logger.warning("\n⚠️  ATENÇÃO: Menos de 50% dos clientes têm vendedor. Revisar ETL.")
        
        if com_supervisor_nome / total_resultados >= 0.85:
            logger.info("✅ SUCESSO: Mais de 85% dos clientes têm supervisor! (Objetivo atingido)")
        elif com_supervisor_nome / total_resultados >= 0.8:
            logger.info("✅ BOM: Mais de 80% dos clientes têm supervisor. (Próximo do objetivo)")
        elif com_supervisor_nome / total_resultados >= 0.5:
            logger.warning("⚠️  PARCIAL: Entre 50-80% dos clientes têm supervisor. Melhorias necessárias no ETL.")
        else:
            logger.warning("⚠️  ATENÇÃO: Menos de 50% dos clientes têm supervisor. Revisar ETL.")
        
        # ========================================================================
        # 6. VALIDAÇÃO GLOBAL DE DUPLICATAS (TODAS AS QUERIES)
        # ========================================================================
        logger.info("\n6. VALIDAÇÃO GLOBAL DE DUPLICATAS")
        logger.info("=" * 80)
        
        # Importa funções de teste
        import subprocess
        import sys as sys_module
        
        resultados_validacao = {}
        
        # Lista de queries para validar
        queries_validacao = [
            ("Q1", "scripts/test_q1_sem_duplicatas.py", "cliente_id"),
            ("Q2", "scripts/test_api_q2_sem_duplicatas.py", "cliente_id"),
            ("Q3", "scripts/test_api_q3_sem_duplicatas.py", "industria"),
            ("Q4", "scripts/test_api_q4_sem_duplicatas.py", "rota_id"),
            ("Q5", "scripts/test_api_q5_sem_duplicatas.py", "produto_id"),
        ]
        
        logger.info("\nExecutando validação de duplicatas para todas as queries...")
        logger.info("-" * 80)
        
        for query_nome, script_path, identificador in queries_validacao:
            script_full_path = os.path.join(project_root, script_path)
            
            if not os.path.exists(script_full_path):
                logger.warning(f"⚠️  {query_nome}: Script não encontrado ({script_path})")
                resultados_validacao[query_nome] = {"status": "SKIP", "erro": "Script não encontrado"}
                continue
            
            try:
                logger.info(f"\nExecutando validação para {query_nome}...")
                
                # Executa script de validação
                # Para Q1, usa validação direta (sem API)
                # Para Q2-Q5, tenta API mas pode falhar se servidor não estiver rodando
                if query_nome == "Q1":
                    # Q1 usa validação direta no banco
                    resultado = subprocess.run(
                        [sys_module.executable, script_full_path],
                        capture_output=True,
                        text=True,
                        timeout=60,
                        cwd=project_root
                    )
                else:
                    # Q2-Q5 tentam API (pode falhar se servidor não estiver rodando)
                    resultado = subprocess.run(
                        [sys_module.executable, script_full_path, "--local"],
                        capture_output=True,
                        text=True,
                        timeout=120,
                        cwd=project_root
                    )
                
                if resultado.returncode == 0:
                    resultados_validacao[query_nome] = {"status": "OK", "identificador": identificador}
                    logger.info(f"✅ {query_nome}: OK (sem duplicatas)")
                else:
                    # Verifica se é erro de conexão (servidor não rodando) ou erro real de duplicatas
                    output = resultado.stdout + resultado.stderr
                    if "Connection refused" in output or "Max retries exceeded" in output:
                        resultados_validacao[query_nome] = {"status": "SKIP", "erro": "Servidor não disponível"}
                        logger.warning(f"⚠️  {query_nome}: SKIP (servidor não disponível para teste via API)")
                    else:
                        resultados_validacao[query_nome] = {"status": "FALHA", "identificador": identificador, "erro": output}
                        logger.error(f"❌ {query_nome}: FALHA (duplicatas encontradas ou erro)")
                        
            except subprocess.TimeoutExpired:
                resultados_validacao[query_nome] = {"status": "FALHA", "erro": "Timeout"}
                logger.error(f"❌ {query_nome}: FALHA (timeout)")
            except Exception as e:
                resultados_validacao[query_nome] = {"status": "FALHA", "erro": str(e)}
                logger.error(f"❌ {query_nome}: FALHA (erro: {str(e)})")
        
        # ========================================================================
        # 7. RELATÓRIO CONSOLIDADO DE VALIDAÇÃO
        # ========================================================================
        logger.info("\n7. RELATÓRIO CONSOLIDADO DE VALIDAÇÃO")
        logger.info("=" * 80)
        
        logger.info("\n📊 RESULTADO DA VALIDAÇÃO GLOBAL DE DUPLICATAS:")
        logger.info("-" * 80)
        
        total_ok = sum(1 for r in resultados_validacao.values() if r.get("status") == "OK")
        total_falha = sum(1 for r in resultados_validacao.values() if r.get("status") == "FALHA")
        total_skip = sum(1 for r in resultados_validacao.values() if r.get("status") == "SKIP")
        
        for query_nome, resultado in resultados_validacao.items():
            status = resultado.get("status")
            identificador = resultado.get("identificador", "N/A")
            
            if status == "OK":
                logger.info(f"✅ {query_nome}: OK (identificador: {identificador})")
            elif status == "FALHA":
                logger.error(f"❌ {query_nome}: FALHA (identificador: {identificador})")
                erro = resultado.get("erro", "")
                if erro and len(erro) < 200:
                    logger.error(f"   Erro: {erro[:200]}")
            elif status == "SKIP":
                logger.warning(f"⚠️  {query_nome}: SKIP ({resultado.get('erro', 'N/A')})")
        
        logger.info("\n" + "-" * 80)
        logger.info(f"Resumo: {total_ok} OK | {total_falha} FALHA | {total_skip} SKIP")
        
        if total_falha > 0:
            logger.error("\n❌ ALERTA CRÍTICO: Uma ou mais queries contêm duplicatas!")
            logger.error("   Revisar implementação das queries com falha.")
        elif total_ok == len(queries_validacao):
            logger.info("\n✅ SUCESSO: Todas as queries validadas estão sem duplicatas!")
        else:
            logger.warning("\n⚠️  ATENÇÃO: Algumas queries não puderam ser validadas (servidor não disponível).")
        
    except Exception as e:
        logger.error(f"Erro durante validação: {str(e)}", exc_info=True)
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
    main()

