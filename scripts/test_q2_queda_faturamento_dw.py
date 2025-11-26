#!/usr/bin/env python3
"""
Script de teste para Q2: Queda de Faturamento (set/25 x out/25)

Valida a função get_clientes_queda_faturamento_periodo() com os parâmetros:
- setembro 2025: 2025-09-01 a 2025-09-30
- outubro 2025: 2025-10-01 a 2025-10-31
- min_faturamento_mes_anterior: 500.0
- min_queda_percentual: 10.0
- limit: 100
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

# Importa diretamente dos arquivos para evitar problema com ETL
import importlib.util

# Carrega connection.py diretamente
conn_path = os.path.join(project_root, "src", "dw", "connection.py")
spec_conn = importlib.util.spec_from_file_location("dw_connection", conn_path)
dw_conn = importlib.util.module_from_spec(spec_conn)
sys.modules['src.dw.connection'] = dw_conn  # Mock para evitar import circular
spec_conn.loader.exec_module(dw_conn)

# Carrega models.py primeiro (necessário para queries)
models_path = os.path.join(project_root, "src", "dw", "models.py")
spec_models = importlib.util.spec_from_file_location("dw_models", models_path)
dw_models = importlib.util.module_from_spec(spec_models)
sys.modules['src.dw.models'] = dw_models
sys.modules['src.dw.connection'] = dw_conn  # Já carregado
spec_models.loader.exec_module(dw_models)

# Carrega queries.py diretamente
queries_path = os.path.join(project_root, "src", "dw", "queries.py")
spec_queries = importlib.util.spec_from_file_location("dw_queries", queries_path)
dw_queries = importlib.util.module_from_spec(spec_queries)
sys.modules['src.dw.queries'] = dw_queries
spec_queries.loader.exec_module(dw_queries)

get_clientes_queda_faturamento_periodo = dw_queries.get_clientes_queda_faturamento_periodo
init_db = dw_conn.init_db
get_db_engine = dw_conn.get_db_engine

from sqlalchemy.orm import sessionmaker
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Executa teste da query Q2."""
    logger.info("=" * 80)
    logger.info("TESTE Q2: QUEDA DE FATURAMENTO (SET/25 x OUT/25)")
    logger.info("=" * 80)
    
    # Inicializa banco
    try:
        init_db()
        engine = get_db_engine()
        SessionLocal = sessionmaker(bind=engine)
    except Exception as e:
        logger.error(f"Erro ao inicializar banco: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
    
    session = SessionLocal()
    
    try:
        # Parâmetros do teste
        data_ini_mes_anterior = "2025-09-01"
        data_fim_mes_anterior = "2025-09-30"
        data_ini_mes_atual = "2025-10-01"
        data_fim_mes_atual = "2025-10-31"
        min_faturamento_mes_anterior = 500.0
        min_queda_percentual = 10.0
        limit = 100
        
        logger.info(f"\n📋 Parâmetros do teste:")
        logger.info(f"   Mês anterior: {data_ini_mes_anterior} a {data_fim_mes_anterior}")
        logger.info(f"   Mês atual: {data_ini_mes_atual} a {data_fim_mes_atual}")
        logger.info(f"   Faturamento mínimo (mês anterior): R$ {min_faturamento_mes_anterior:.2f}")
        logger.info(f"   Queda percentual mínima: {min_queda_percentual}%")
        logger.info(f"   Limit: {limit}")
        
        # Executa query
        import time
        start_time = time.perf_counter()
        
        resultados = get_clientes_queda_faturamento_periodo(
            session=session,
            data_ini_mes_anterior=data_ini_mes_anterior,
            data_fim_mes_anterior=data_fim_mes_anterior,
            data_ini_mes_atual=data_ini_mes_atual,
            data_fim_mes_atual=data_fim_mes_atual,
            min_faturamento_mes_anterior=min_faturamento_mes_anterior,
            min_queda_percentual=min_queda_percentual,
            limit=limit,
            query_id="Q2_TEST"
        )
        
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        
        logger.info(f"\n⏱️  Tempo de execução: {duration_ms}ms")
        logger.info(f"📊 Total de registros retornados: {len(resultados)}")
        
        if len(resultados) == 0:
            logger.warning("⚠️  Nenhum resultado retornado!")
            return 0
        
        # Validações
        logger.info(f"\n✅ VALIDAÇÕES:")
        
        # 1. Nenhum cliente com faturamento_mes_atual > faturamento_mes_anterior
        clientes_com_aumento = [
            r for r in resultados
            if r['faturamento_mes_atual'] > r['faturamento_mes_anterior']
        ]
        if clientes_com_aumento:
            logger.error(f"   ❌ {len(clientes_com_aumento)} clientes com aumento (deveria ser 0)")
            return 1
        else:
            logger.info(f"   ✓ Nenhum cliente com aumento (todos têm queda)")
        
        # 2. queda_absoluta > 0 para todos
        clientes_sem_queda = [
            r for r in resultados
            if r['queda_absoluta'] <= 0
        ]
        if clientes_sem_queda:
            logger.error(f"   ❌ {len(clientes_sem_queda)} clientes sem queda absoluta (deveria ser 0)")
            return 1
        else:
            logger.info(f"   ✓ Todos os clientes têm queda_absoluta > 0")
        
        # 3. queda_percentual >= 10 para todos
        clientes_abaixo_min = [
            r for r in resultados
            if r['queda_percentual'] < min_queda_percentual
        ]
        if clientes_abaixo_min:
            logger.error(f"   ❌ {len(clientes_abaixo_min)} clientes com queda < {min_queda_percentual}% (deveria ser 0)")
            return 1
        else:
            logger.info(f"   ✓ Todos os clientes têm queda_percentual >= {min_queda_percentual}%")
        
        # 4. Não há duplicatas de cliente_id
        cliente_ids = [r['cliente_id'] for r in resultados]
        duplicatas = len(cliente_ids) - len(set(cliente_ids))
        if duplicatas > 0:
            logger.error(f"   ❌ {duplicatas} duplicatas de cliente_id encontradas")
            return 1
        else:
            logger.info(f"   ✓ Nenhuma duplicata de cliente_id")
        
        # 5. Ordenação correta (queda_absoluta DESC)
        ordenacao_correta = True
        for i in range(len(resultados) - 1):
            if resultados[i]['queda_absoluta'] < resultados[i + 1]['queda_absoluta']:
                ordenacao_correta = False
                break
        if not ordenacao_correta:
            logger.error(f"   ❌ Ordenação incorreta (não está por queda_absoluta DESC)")
            return 1
        else:
            logger.info(f"   ✓ Ordenação correta (queda_absoluta DESC)")
        
        # Amostra de 5 clientes
        logger.info(f"\n📋 AMOSTRA DE 5 CLIENTES COM MAIOR QUEDA:")
        logger.info("-" * 80)
        for i, cliente in enumerate(resultados[:5], 1):
            logger.info(
                f"{i}. ID: {cliente['cliente_id']:6d} | "
                f"Nome: {cliente['cliente_nome'][:35]:35s} | "
                f"Set/25: R$ {cliente['faturamento_mes_anterior']:>12,.2f} | "
                f"Out/25: R$ {cliente['faturamento_mes_atual']:>12,.2f} | "
                f"Queda: R$ {cliente['queda_absoluta']:>12,.2f} ({cliente['queda_percentual']:>6.2f}%)"
            )
        
        # Estatísticas
        queda_media_absoluta = sum(r['queda_absoluta'] for r in resultados) / len(resultados)
        queda_media_percentual = sum(r['queda_percentual'] for r in resultados) / len(resultados)
        queda_maxima_absoluta = max(r['queda_absoluta'] for r in resultados)
        queda_maxima_percentual = max(r['queda_percentual'] for r in resultados)
        
        logger.info(f"\n📊 ESTATÍSTICAS:")
        logger.info(f"   Queda média absoluta: R$ {queda_media_absoluta:,.2f}")
        logger.info(f"   Queda média percentual: {queda_media_percentual:.2f}%")
        logger.info(f"   Queda máxima absoluta: R$ {queda_maxima_absoluta:,.2f}")
        logger.info(f"   Queda máxima percentual: {queda_maxima_percentual:.2f}%")
        
        logger.info(f"\n✅ TESTE CONCLUÍDO COM SUCESSO!")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Erro durante teste: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())

