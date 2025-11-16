#!/usr/bin/env python3
"""
Script de teste para validar pipeline de ML Baseline.

Este script:
1. Executa run_all_analytics para um mês específico
2. Imprime top 10 clientes com maior churn_score
3. Imprime top 10 vendedores com maior meta_risk_score
4. Imprime top 10 produtos com maior queda_score
5. Imprime total de alertas por tipo_alerta

Uso:
    DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db python -m scripts.test_ml_baseline --mes-ano 2025-08
"""

import sys
import argparse
from pathlib import Path
from sqlalchemy import func, desc

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from src.config import config
from src.dw.connection import init_db, get_db_session
from src.dw.models_analytics import (
    AnalyticsVendedorMes, AnalyticsClienteMes,
    AnalyticsProdutoMes, AnalyticsAlerta
)
from scripts.build_analytics import run_all_analytics


def print_section(title: str):
    """Imprime seção formatada."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def test_ml_baseline(mes_ano: str = "2025-08"):
    """
    Testa o pipeline completo de ML baseline.
    
    Args:
        mes_ano: Mês/ano no formato "YYYY-MM"
    """
    print_section(f"TESTE DE ML BASELINE - {mes_ano}")
    
    # Inicializa banco
    init_db()
    
    # Executa build completo de analytics (incluindo scores)
    print(f"📊 Executando build completo de analytics para {mes_ano}...")
    try:
        stats = run_all_analytics(mes_ano=mes_ano)
        print(f"✅ Build concluído:")
        print(f"   - analytics_vendedor_mes: {stats['vendedor_mes']} registros")
        print(f"   - analytics_cliente_mes: {stats['cliente_mes']} registros")
        print(f"   - analytics_produto_mes: {stats['produto_mes']} registros")
        print(f"   - Scores aplicados: {stats['scores_clientes']} clientes, {stats['scores_vendedores']} vendedores, {stats['scores_produtos']} produtos")
        print(f"   - analytics_alertas: {stats['alertas']} alertas")
    except Exception as e:
        print(f"❌ Erro ao executar build: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Cria sessão para consultas
    session_gen = get_db_session()
    session = next(session_gen)
    
    try:
        # 1. Top 10 clientes com maior churn_score
        print_section("TOP 10 CLIENTES COM MAIOR CHURN_SCORE")
        
        clientes_churn = session.query(AnalyticsClienteMes).filter(
            AnalyticsClienteMes.mes_ano == mes_ano,
            AnalyticsClienteMes.churn_score.isnot(None)
        ).order_by(
            AnalyticsClienteMes.churn_score.desc()
        ).limit(10).all()
        
        if clientes_churn:
            for i, c in enumerate(clientes_churn, 1):
                print(f"{i}. {c.cliente_nome}")
                print(f"   Churn Score: {c.churn_score:.2f}")
                print(f"   Churn Flag: {'🔴 SIM' if c.churn_flag else '🟢 NÃO'}")
                print(f"   Faturamento atual: R$ {c.faturamento_total:,.2f}")
                if c.faturamento_media_3m:
                    print(f"   Faturamento média 3m: R$ {c.faturamento_media_3m:,.2f}")
                if c.variacao_pct_vs_3m:
                    print(f"   Variação vs 3m: {c.variacao_pct_vs_3m:.1f}%")
                if c.dias_desde_ultima_compra:
                    print(f"   Dias sem comprar: {c.dias_desde_ultima_compra}")
                print()
        else:
            print("⚠️  Nenhum cliente com churn_score encontrado")
        
        # 2. Top 10 vendedores com maior meta_risk_score
        print_section("TOP 10 VENDEDORES COM MAIOR META_RISK_SCORE")
        
        vendedores_risco = session.query(AnalyticsVendedorMes).filter(
            AnalyticsVendedorMes.mes_ano == mes_ano,
            AnalyticsVendedorMes.meta_risk_score.isnot(None)
        ).order_by(
            AnalyticsVendedorMes.meta_risk_score.desc()
        ).limit(10).all()
        
        if vendedores_risco:
            for i, v in enumerate(vendedores_risco, 1):
                print(f"{i}. {v.vendedor_nome}")
                print(f"   Meta Risk Score: {v.meta_risk_score:.2f}")
                print(f"   Meta Risk Flag: {'🔴 SIM' if v.meta_risk_flag else '🟢 NÃO'}")
                if v.atingimento_pct:
                    print(f"   Atingimento: {v.atingimento_pct:.1f}%")
                if v.gap_valor:
                    print(f"   Gap: R$ {v.gap_valor:,.2f}")
                print(f"   Meta: R$ {v.meta_total:,.2f} | Realizado: R$ {v.realizado_total:,.2f}")
                print()
        else:
            print("⚠️  Nenhum vendedor com meta_risk_score encontrado")
        
        # 3. Top 10 produtos com maior queda_score
        print_section("TOP 10 PRODUTOS COM MAIOR QUEDA_SCORE")
        
        produtos_queda = session.query(AnalyticsProdutoMes).filter(
            AnalyticsProdutoMes.mes_ano == mes_ano,
            AnalyticsProdutoMes.queda_score.isnot(None)
        ).order_by(
            AnalyticsProdutoMes.queda_score.desc()
        ).limit(10).all()
        
        if produtos_queda:
            for i, p in enumerate(produtos_queda, 1):
                print(f"{i}. {p.desc_produto or p.codigo_produto}")
                print(f"   Código: {p.codigo_produto}")
                print(f"   Queda Score: {p.queda_score:.2f}")
                print(f"   Queda Flag: {'🔴 SIM' if p.queda_flag else '🟢 NÃO'}")
                if p.variacao_pct_vs_3m:
                    print(f"   Variação vs 3m: {p.variacao_pct_vs_3m:.1f}%")
                print(f"   Faturamento: R$ {p.faturamento_total:,.2f}")
                print(f"   Qtd vendida: {p.qtd_vendida:,}")
                print()
        else:
            print("⚠️  Nenhum produto com queda_score encontrado")
        
        # 4. Total de alertas por tipo_alerta
        print_section("TOTAL DE ALERTAS POR TIPO")
        
        alertas_por_tipo = session.query(
            AnalyticsAlerta.tipo_alerta,
            func.count(AnalyticsAlerta.id).label('total'),
            func.sum(func.case((AnalyticsAlerta.nivel == 'alto', 1), else_=0)).label('alto'),
            func.sum(func.case((AnalyticsAlerta.nivel == 'medio', 1), else_=0)).label('medio'),
            func.sum(func.case((AnalyticsAlerta.nivel == 'baixo', 1), else_=0)).label('baixo')
        ).filter(
            AnalyticsAlerta.mes_ano == mes_ano
        ).group_by(
            AnalyticsAlerta.tipo_alerta
        ).all()
        
        if alertas_por_tipo:
            for tipo, total, alto, medio, baixo in alertas_por_tipo:
                print(f"📊 {tipo}:")
                print(f"   Total: {total}")
                print(f"   🔴 Alto: {alto or 0} | 🟡 Médio: {medio or 0} | 🟢 Baixo: {baixo or 0}")
                print()
        else:
            print("⚠️  Nenhum alerta encontrado")
        
        # 5. Resumo de flags
        print_section("RESUMO DE FLAGS")
        
        total_clientes_churn = session.query(func.count(AnalyticsClienteMes.id)).filter(
            AnalyticsClienteMes.mes_ano == mes_ano,
            AnalyticsClienteMes.churn_flag == True
        ).scalar()
        
        total_vendedores_risco = session.query(func.count(AnalyticsVendedorMes.id)).filter(
            AnalyticsVendedorMes.mes_ano == mes_ano,
            AnalyticsVendedorMes.meta_risk_flag == True
        ).scalar()
        
        total_produtos_queda = session.query(func.count(AnalyticsProdutoMes.id)).filter(
            AnalyticsProdutoMes.mes_ano == mes_ano,
            AnalyticsProdutoMes.queda_flag == True
        ).scalar()
        
        print(f"🔴 Clientes em risco de churn: {total_clientes_churn}")
        print(f"🔴 Vendedores em risco de meta: {total_vendedores_risco}")
        print(f"🔴 Produtos em queda: {total_produtos_queda}")
        
        print_section("TESTE CONCLUÍDO")
        print("✅ Pipeline de ML baseline validado com sucesso")
        
        return 0
    
    except Exception as e:
        print(f"❌ Erro durante teste: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        session.close()


def main():
    """Entry point para CLI."""
    parser = argparse.ArgumentParser(
        description="Testa pipeline de ML Baseline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Testa com mês padrão (2025-08)
  python -m scripts.test_ml_baseline
  
  # Especifica mês/ano
  python -m scripts.test_ml_baseline --mes-ano 2025-08
  
  # Com variáveis de ambiente
  DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db python -m scripts.test_ml_baseline --mes-ano 2025-08
        """
    )
    
    parser.add_argument(
        '--mes-ano',
        type=str,
        default="2025-08",
        help='Mês/ano no formato YYYY-MM (padrão: 2025-08)'
    )
    
    args = parser.parse_args()
    
    try:
        exit_code = test_ml_baseline(mes_ano=args.mes_ano)
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n❌ Erro: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    main()

