#!/usr/bin/env python3
"""
Pipeline de recálculo automático de Analytics e Scores (FASE 4).

Este script orquestra o recálculo de analytics_* e scores para um ou mais meses,
sendo usado em jobs agendados (cron, Cloud Scheduler, etc.).

Uso:
    # Recalcular apenas o mês corrente (último mês fechado)
    DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db python -m scripts.run_analytics_job
    
    # Recalcular um mês específico
    DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db python -m scripts.run_analytics_job --mes_ano=2025-08
    
    # Recalcular últimos N meses
    DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db python -m scripts.run_analytics_job --ultimos_n_meses=6
"""

import sys
import argparse
import logging
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.config import config
from src.dw.connection import init_db, get_db_session
from src.dw.models import Venda, MetaVendedor
from scripts.build_analytics import (
    run_all_analytics,
    get_mes_anterior,
    parse_mes_ano
)

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_meses_disponiveis(session: Session, limite: int = 12) -> List[str]:
    """
    Retorna lista de meses disponíveis no banco (baseado em vendas e metas).
    
    Args:
        session: Sessão SQLAlchemy
        limite: Número máximo de meses a retornar
        
    Returns:
        Lista de mes_ano no formato "YYYY-MM" ordenada do mais recente para o mais antigo
    """
    meses = set()
    
    # Busca meses de vendas
    vendas_meses = session.query(
        func.strftime('%Y-%m', Venda.data_venda).label('mes_ano')
    ).distinct().all()
    
    for row in vendas_meses:
        if row.mes_ano:
            meses.add(row.mes_ano)
    
    # Busca meses de metas
    metas_meses = session.query(
        func.strftime('%Y-%m', MetaVendedor.mes_ano).label('mes_ano')
    ).distinct().all()
    
    for row in metas_meses:
        if row.mes_ano:
            meses.add(row.mes_ano)
    
    # Converte para lista e ordena (mais recente primeiro)
    meses_lista = sorted(list(meses), reverse=True)
    
    return meses_lista[:limite]


def determinar_meses_processar(
    mes_ano: str = None,
    ultimos_n_meses: int = None
) -> List[str]:
    """
    Determina quais meses devem ser processados baseado nos argumentos.
    
    Args:
        mes_ano: Mês específico no formato "YYYY-MM" (opcional)
        ultimos_n_meses: Número de meses a processar a partir do mais recente (opcional)
        
    Returns:
        Lista de mes_ano no formato "YYYY-MM"
    """
    if mes_ano:
        # Valida formato
        try:
            parse_mes_ano(mes_ano)
            return [mes_ano]
        except ValueError as e:
            logger.error(f"❌ Formato inválido de mes_ano: {e}")
            sys.exit(1)
    
    if ultimos_n_meses:
        if ultimos_n_meses < 1:
            logger.error("❌ ultimos_n_meses deve ser >= 1")
            sys.exit(1)
        
        # Inicializa banco para buscar meses disponíveis
        init_db()
        session_gen = get_db_session()
        session = next(session_gen)
        
        try:
            meses_disponiveis = get_meses_disponiveis(session, limite=ultimos_n_meses)
            if not meses_disponiveis:
                logger.warning("⚠️  Nenhum mês encontrado no banco")
                return []
            
            return meses_disponiveis[:ultimos_n_meses]
        finally:
            session.close()
    
    # Padrão: mês anterior (último mês fechado)
    mes_anterior = get_mes_anterior()
    logger.info(f"📅 Nenhum argumento fornecido, usando mês anterior: {mes_anterior}")
    return [mes_anterior]


def processar_mes(mes_ano: str) -> Dict[str, Any]:
    """
    Processa um mês específico: recalcula analytics + scores.
    
    Args:
        mes_ano: Mês/ano no formato "YYYY-MM"
        
    Returns:
        Dict com estatísticas do processamento
    """
    inicio = time.perf_counter()
    logger.info(f"🔄 Processando {mes_ano}...")
    
    try:
        # Executa pipeline completo
        stats = run_all_analytics(mes_ano=mes_ano)
        
        tempo_decorrido = int((time.perf_counter() - inicio) * 1000)
        
        logger.info(f"✅ {mes_ano} processado com sucesso em {tempo_decorrido}ms")
        logger.info(f"   Estatísticas: {stats}")
        
        return {
            "mes_ano": mes_ano,
            "sucesso": True,
            "tempo_ms": tempo_decorrido,
            "estatisticas": stats
        }
    
    except Exception as e:
        tempo_decorrido = int((time.perf_counter() - inicio) * 1000)
        logger.error(f"❌ Erro ao processar {mes_ano}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        return {
            "mes_ano": mes_ano,
            "sucesso": False,
            "tempo_ms": tempo_decorrido,
            "erro": str(e)
        }


def main():
    """Função principal do script."""
    parser = argparse.ArgumentParser(
        description="Pipeline de recálculo automático de Analytics e Scores (FASE 4)"
    )
    parser.add_argument(
        "--mes_ano",
        type=str,
        help="Mês/ano específico a processar (formato: YYYY-MM, ex.: 2025-08)"
    )
    parser.add_argument(
        "--ultimos_n_meses",
        type=int,
        help="Número de meses a processar a partir do mais recente (ex.: 6)"
    )
    
    args = parser.parse_args()
    
    # Valida que apenas um argumento foi fornecido
    if args.mes_ano and args.ultimos_n_meses:
        logger.error("❌ Não é possível usar --mes_ano e --ultimos_n_meses simultaneamente")
        sys.exit(1)
    
    logger.info("=" * 80)
    logger.info("🚀 DIPAM COPILOT - Pipeline de Recálculo de Analytics (FASE 4)")
    logger.info("=" * 80)
    
    # Determina meses a processar
    meses = determinar_meses_processar(
        mes_ano=args.mes_ano,
        ultimos_n_meses=args.ultimos_n_meses
    )
    
    if not meses:
        logger.warning("⚠️  Nenhum mês para processar")
        sys.exit(0)
    
    logger.info(f"📋 Meses a processar: {', '.join(meses)}")
    logger.info("")
    
    # Processa cada mês
    resultados = []
    inicio_total = time.perf_counter()
    
    for mes_ano in meses:
        resultado = processar_mes(mes_ano)
        resultados.append(resultado)
        logger.info("")  # Linha em branco entre meses
    
    tempo_total = int((time.perf_counter() - inicio_total) * 1000)
    
    # Resumo final
    logger.info("=" * 80)
    logger.info("📊 RESUMO DO PROCESSAMENTO")
    logger.info("=" * 80)
    logger.info(f"Total de meses processados: {len(meses)}")
    logger.info(f"Tempo total: {tempo_total}ms ({tempo_total/1000:.2f}s)")
    logger.info("")
    
    sucessos = sum(1 for r in resultados if r["sucesso"])
    falhas = len(resultados) - sucessos
    
    logger.info(f"✅ Sucessos: {sucessos}")
    if falhas > 0:
        logger.warning(f"❌ Falhas: {falhas}")
    
    logger.info("")
    logger.info("Detalhes por mês:")
    for resultado in resultados:
        status = "✅" if resultado["sucesso"] else "❌"
        logger.info(f"  {status} {resultado['mes_ano']}: {resultado['tempo_ms']}ms")
        
        if resultado["sucesso"]:
            stats = resultado.get("estatisticas", {})
            logger.info(f"     - analytics_vendedor_mes: {stats.get('vendedor', 0)} registros")
            logger.info(f"     - analytics_cliente_mes: {stats.get('cliente', 0)} registros")
            logger.info(f"     - analytics_produto_mes: {stats.get('produto', 0)} registros")
            logger.info(f"     - analytics_alertas: {stats.get('alertas', 0)} alertas")
        else:
            logger.error(f"     - Erro: {resultado.get('erro', 'Desconhecido')}")
    
    logger.info("=" * 80)
    
    # Exit code baseado em sucesso
    if falhas > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()

