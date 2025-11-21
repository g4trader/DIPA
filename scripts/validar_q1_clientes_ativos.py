#!/usr/bin/env python3
"""
Script para validar que a Q1 retorna APENAS clientes ATIVOS.

Este script:
1. Executa a query Q1
2. Verifica se TODOS os clientes retornados têm ativo=True
3. Se encontrar qualquer cliente inativo, levanta Exception
4. Exibe estatísticas completas

Uso:
    python scripts/validar_q1_clientes_ativos.py
"""

import sys
import os
from pathlib import Path

# Adiciona o diretório raiz ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Configura SQLITE_PATH se não estiver definido
if not os.getenv("SQLITE_PATH"):
    sqlite_path = Path(project_root) / "data" / "dipam_dw.db"
    if sqlite_path.exists():
        os.environ["SQLITE_PATH"] = str(sqlite_path)

from src.dw.connection import init_db, get_db_session
from src.dw.queries import get_clientes_sem_compra_ha_dias
from src.dw.models import Cliente
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def validar_q1_clientes_ativos():
    """
    Valida que a Q1 retorna apenas clientes ativos.
    
    Raises:
        Exception: Se encontrar qualquer cliente inativo nos resultados
    """
    logger.info("=" * 80)
    logger.info("VALIDAÇÃO Q1: APENAS CLIENTES ATIVOS")
    logger.info("=" * 80)
    
    try:
        # Inicializa banco
        init_db()
        session = next(get_db_session())
        
        # Executa Q1
        logger.info("Executando Q1 (get_clientes_sem_compra_ha_dias)...")
        resultados = get_clientes_sem_compra_ha_dias(session, dias=60)
        
        total_resultados = len(resultados)
        logger.info(f"✅ Q1 retornou {total_resultados} registros")
        
        if total_resultados == 0:
            logger.warning("⚠️  Q1 não retornou nenhum registro. Verifique os dados.")
            return
        
        # Extrai IDs dos clientes retornados
        clientes_ids = [r['cliente_id'] for r in resultados]
        
        # Verifica status de ativo para cada cliente
        logger.info("Verificando status 'ativo' de cada cliente retornado...")
        
        # Query para verificar clientes inativos nos resultados
        clientes_inativos = (
            session.query(Cliente.id, Cliente.nome, Cliente.ativo)
            .filter(
                Cliente.id.in_(clientes_ids),
                Cliente.ativo == False
            )
            .all()
        )
        
        # Query para verificar clientes ativos nos resultados
        clientes_ativos = (
            session.query(Cliente.id, Cliente.nome, Cliente.ativo)
            .filter(
                Cliente.id.in_(clientes_ids),
                Cliente.ativo == True
            )
            .all()
        )
        
        # Estatísticas
        total_inativos = len(clientes_inativos)
        total_ativos = len(clientes_ativos)
        
        logger.info("")
        logger.info("-" * 80)
        logger.info("ESTATÍSTICAS:")
        logger.info("-" * 80)
        logger.info(f"  Total de registros retornados pela Q1: {total_resultados}")
        logger.info(f"  Clientes ATIVOS nos resultados: {total_ativos}")
        logger.info(f"  Clientes INATIVOS nos resultados: {total_inativos}")
        logger.info("")
        
        # ✅ VALIDAÇÃO CRÍTICA: Se houver qualquer cliente inativo, levanta exceção
        if total_inativos > 0:
            logger.error("=" * 80)
            logger.error("❌ ERRO CRÍTICO: Q1 RETORNOU CLIENTES INATIVOS!")
            logger.error("=" * 80)
            logger.error(f"Encontrados {total_inativos} cliente(s) INATIVO(S) nos resultados:")
            logger.error("")
            
            for cliente in clientes_inativos[:20]:  # Mostra até 20
                logger.error(f"  - ID: {cliente.id}, Nome: {cliente.nome}, Ativo: {cliente.ativo}")
            
            if total_inativos > 20:
                logger.error(f"  ... e mais {total_inativos - 20} cliente(s) inativo(s)")
            
            logger.error("")
            logger.error("🔧 AÇÃO NECESSÁRIA:")
            logger.error("  1. Verificar a query Q1 em src/dw/queries.py")
            logger.error("  2. Garantir que o filtro Cliente.ativo == True está aplicado")
            logger.error("  3. Verificar se o filtro está na CTE base (ANTES do ROW_NUMBER)")
            logger.error("")
            
            raise Exception(
                f"Q1 retornou {total_inativos} cliente(s) INATIVO(S). "
                f"A query deve retornar APENAS clientes ativos (ativo=True)."
            )
        
        # ✅ SUCESSO: Todos os clientes são ativos
        logger.info("=" * 80)
        logger.info("✅ VALIDAÇÃO PASSOU: Todos os clientes retornados pela Q1 são ATIVOS")
        logger.info("=" * 80)
        logger.info(f"  - Total de registros: {total_resultados}")
        logger.info(f"  - Clientes ativos: {total_ativos} (100%)")
        logger.info(f"  - Clientes inativos: {total_inativos} (0%)")
        logger.info("")
        logger.info("✅ Q1 está funcionando corretamente: apenas clientes ativos são retornados.")
        
    except Exception as e:
        logger.error(f"❌ Erro durante validação: {str(e)}")
        raise


if __name__ == "__main__":
    try:
        validar_q1_clientes_ativos()
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Validação falhou: {str(e)}")
        sys.exit(1)

