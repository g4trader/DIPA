#!/usr/bin/env python3
"""
Script de diagnóstico para Q2: Queda de Faturamento (set/25 x out/25)

Este script analisa os dados disponíveis para responder à pergunta:
"Quais os clientes com maior queda de faturamento de setembro 2025 x outubro 2025?"

Valida:
1. Total de clientes com faturamento em set/25
2. Total de clientes com queda de faturamento de set → out/25
3. Top 10 clientes com maior queda absoluta
4. Top 10 clientes com maior queda percentual
"""

import sys
import os
from pathlib import Path
from datetime import date, datetime
from decimal import Decimal

# Adiciona o diretório raiz ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Define SQLITE_PATH para o caminho local se não estiver definido
if not os.getenv("SQLITE_PATH"):
    sqlite_path = Path(project_root) / "data" / "dipam_dw.db"
    os.environ["SQLITE_PATH"] = str(sqlite_path)

# Importa diretamente dos arquivos para evitar problema com ETL/pandas
import importlib.util

# Carrega connection.py diretamente
conn_path = os.path.join(project_root, "src", "dw", "connection.py")
spec_conn = importlib.util.spec_from_file_location("dw_connection", conn_path)
dw_conn = importlib.util.module_from_spec(spec_conn)
sys.modules['src.dw.connection'] = dw_conn  # Mock para evitar import circular
spec_conn.loader.exec_module(dw_conn)

# Carrega models.py diretamente
models_path = os.path.join(project_root, "src", "dw", "models.py")
spec_models = importlib.util.spec_from_file_location("dw_models", models_path)
dw_models = importlib.util.module_from_spec(spec_models)
sys.modules['src.dw.models'] = dw_models
spec_models.loader.exec_module(dw_models)

# Extrai classes e funções necessárias
Cliente = dw_models.Cliente
Venda = dw_models.Venda
Vendedor = dw_models.Vendedor
Supervisor = dw_models.Supervisor
init_db = dw_conn.init_db
get_db_engine = dw_conn.get_db_engine
from sqlalchemy import func, and_, or_, case
from sqlalchemy.orm import aliased, sessionmaker
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Executa diagnóstico de queda de faturamento."""
    logger.info("=" * 80)
    logger.info("DIAGNÓSTICO Q2: QUEDA DE FATURAMENTO (SET/25 x OUT/25)")
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
    
    # Períodos definidos
    data_ini_set = date(2025, 9, 1)
    data_fim_set = date(2025, 9, 30)
    data_ini_out = date(2025, 10, 1)
    data_fim_out = date(2025, 10, 31)
    
    logger.info(f"\n📅 Períodos analisados:")
    logger.info(f"   Setembro 2025: {data_ini_set} a {data_fim_set}")
    logger.info(f"   Outubro 2025: {data_ini_out} a {data_fim_out}")
    
    session = SessionLocal()
    
    try:
        # Query base: faturamento por cliente em cada mês
        # Subquery para setembro
        faturamento_set = (
            session.query(
                Venda.cliente_id,
                func.sum(Venda.valor_total_liquido).label('faturamento_setembro')
            )
            .filter(
                and_(
                    Venda.data_venda >= data_ini_set,
                    Venda.data_venda <= data_fim_set
                )
            )
            .group_by(Venda.cliente_id)
            .subquery()
        )
        
        # Subquery para outubro
        faturamento_out = (
            session.query(
                Venda.cliente_id,
                func.sum(Venda.valor_total_liquido).label('faturamento_outubro')
            )
            .filter(
                and_(
                    Venda.data_venda >= data_ini_out,
                    Venda.data_venda <= data_fim_out
                )
            )
            .group_by(Venda.cliente_id)
            .subquery()
        )
        
        # Query principal: join com Cliente para filtrar apenas ativos
        query = (
            session.query(
                Cliente.id.label('cliente_id'),
                Cliente.nome.label('cliente_nome'),
                func.coalesce(faturamento_set.c.faturamento_setembro, 0).label('faturamento_setembro'),
                func.coalesce(faturamento_out.c.faturamento_outubro, 0).label('faturamento_outubro'),
                (
                    func.coalesce(faturamento_set.c.faturamento_setembro, 0) - 
                    func.coalesce(faturamento_out.c.faturamento_outubro, 0)
                ).label('queda_absoluta'),
                case(
                    (
                        func.coalesce(faturamento_set.c.faturamento_setembro, 0) > 0,
                        (
                            (func.coalesce(faturamento_set.c.faturamento_setembro, 0) - 
                             func.coalesce(faturamento_out.c.faturamento_outubro, 0)) /
                            func.coalesce(faturamento_set.c.faturamento_setembro, 1) * 100
                        )
                    ),
                    else_=0
                ).label('queda_percentual')
            )
            .outerjoin(faturamento_set, Cliente.id == faturamento_set.c.cliente_id)
            .outerjoin(faturamento_out, Cliente.id == faturamento_out.c.cliente_id)
            .filter(Cliente.ativo == True)
        )
        
        # Executa query base
        resultados_base = query.all()
        
        # Filtros aplicados
        # 1. Apenas clientes com faturamento em setembro > 0
        # 2. Apenas clientes com queda (faturamento_setembro > faturamento_outubro)
        resultados_filtrados = [
            r for r in resultados_base
            if r.faturamento_setembro > 0 and r.queda_absoluta > 0
        ]
        
        # Estatísticas gerais
        total_com_faturamento_set = len([r for r in resultados_base if r.faturamento_setembro > 0])
        total_com_queda = len(resultados_filtrados)
        
        logger.info(f"\n📊 ESTATÍSTICAS GERAIS:")
        logger.info(f"   Total de clientes ativos com faturamento em set/25: {total_com_faturamento_set}")
        logger.info(f"   Total de clientes com queda de faturamento (set → out/25): {total_com_queda}")
        
        if total_com_queda == 0:
            logger.warning("⚠️  Nenhum cliente com queda de faturamento encontrado!")
            return 0
        
        # Top 10 por queda absoluta
        top_queda_absoluta = sorted(
            resultados_filtrados,
            key=lambda x: x.queda_absoluta,
            reverse=True
        )[:10]
        
        logger.info(f"\n💰 TOP 10 CLIENTES POR QUEDA ABSOLUTA (R$):")
        logger.info("-" * 80)
        for i, cliente in enumerate(top_queda_absoluta, 1):
            logger.info(
                f"{i:2d}. ID: {cliente.cliente_id:6d} | "
                f"Nome: {cliente.cliente_nome[:40]:40s} | "
                f"Queda: R$ {cliente.queda_absoluta:>12,.2f} | "
                f"Queda %: {cliente.queda_percentual:>6.2f}%"
            )
        
        # Top 10 por queda percentual (com filtro de faturamento mínimo)
        min_faturamento_set = 200.0
        resultados_com_min = [
            r for r in resultados_filtrados
            if r.faturamento_setembro >= min_faturamento_set
        ]
        
        top_queda_percentual = sorted(
            resultados_com_min,
            key=lambda x: x.queda_percentual,
            reverse=True
        )[:10]
        
        logger.info(f"\n📉 TOP 10 CLIENTES POR QUEDA PERCENTUAL (faturamento set/25 >= R$ {min_faturamento_set:.2f}):")
        logger.info("-" * 80)
        for i, cliente in enumerate(top_queda_percentual, 1):
            logger.info(
                f"{i:2d}. ID: {cliente.cliente_id:6d} | "
                f"Nome: {cliente.cliente_nome[:40]:40s} | "
                f"Set/25: R$ {cliente.faturamento_setembro:>12,.2f} | "
                f"Out/25: R$ {cliente.faturamento_outubro:>12,.2f} | "
                f"Queda: {cliente.queda_percentual:>6.2f}%"
            )
        
        # Análise de distribuição por rotas/vendedores
        logger.info(f"\n🔍 ANÁLISE DE DISTRIBUIÇÃO:")
        
        # Busca informações de vendedor/supervisor para os top clientes
        top_ids = [c.cliente_id for c in top_queda_absoluta[:5]]
        clientes_com_info = (
            session.query(
                Cliente.id,
                Cliente.nome,
                Cliente.rota_rca,
                Vendedor.nome.label('vendedor_nome'),
                Supervisor.nome.label('supervisor_nome')
            )
            .outerjoin(Vendedor, Cliente.rota_rca == Vendedor.codigo)
            .outerjoin(Supervisor, Cliente.supervisor_id == Supervisor.id)
            .filter(Cliente.id.in_(top_ids))
            .all()
        )
        
        rotas_afetadas = {}
        for cliente in clientes_com_info:
            rota = cliente.rota_rca or "N/A"
            if rota not in rotas_afetadas:
                rotas_afetadas[rota] = 0
            rotas_afetadas[rota] += 1
        
        logger.info(f"   Rotas mais afetadas (top 5 clientes): {len(rotas_afetadas)} rotas distintas")
        for rota, count in sorted(rotas_afetadas.items(), key=lambda x: x[1], reverse=True)[:5]:
            logger.info(f"      - {rota}: {count} cliente(s)")
        
        # Resumo final
        logger.info(f"\n✅ RESUMO:")
        logger.info(f"   ✓ Dados suportam bem a análise Q2")
        logger.info(f"   ✓ {total_com_queda} clientes com queda relevante identificados")
        logger.info(f"   ✓ Maior queda absoluta: R$ {top_queda_absoluta[0].queda_absoluta:,.2f}")
        logger.info(f"   ✓ Maior queda percentual: {top_queda_percentual[0].queda_percentual:.2f}%")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Erro durante diagnóstico: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())

