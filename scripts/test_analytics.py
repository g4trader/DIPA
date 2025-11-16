#!/usr/bin/env python3
"""
Script de teste para validar tabelas de Analytics.

Este script:
1. Executa run_all_analytics para um mês específico
2. Imprime estatísticas de cada tabela analytics_*
3. Mostra top 5 vendedores, clientes e produtos

Uso:
    DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db python -m scripts.test_analytics --mes-ano 2025-08
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


def test_analytics(mes_ano: str = "2025-08"):
    """
    Testa as tabelas de analytics.
    
    Args:
        mes_ano: Mês/ano no formato "YYYY-MM"
    """
    print_section(f"TESTE DE ANALYTICS - {mes_ano}")
    
    # Inicializa banco
    init_db()
    
    # Executa build de analytics
    print(f"📊 Executando build de analytics para {mes_ano}...")
    try:
        stats = run_all_analytics(mes_ano=mes_ano)
        print(f"✅ Build concluído:")
        print(f"   - analytics_vendedor_mes: {stats['vendedor_mes']} registros")
        print(f"   - analytics_cliente_mes: {stats['cliente_mes']} registros")
        print(f"   - analytics_produto_mes: {stats['produto_mes']} registros")
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
        # 1. Contagem de registros por tabela
        print_section("CONTAGEM DE REGISTROS")
        
        count_vendedor = session.query(func.count(AnalyticsVendedorMes.id)).filter(
            AnalyticsVendedorMes.mes_ano == mes_ano
        ).scalar()
        print(f"📊 analytics_vendedor_mes: {count_vendedor} registros")
        
        count_cliente = session.query(func.count(AnalyticsClienteMes.id)).filter(
            AnalyticsClienteMes.mes_ano == mes_ano
        ).scalar()
        print(f"👥 analytics_cliente_mes: {count_cliente} registros")
        
        count_produto = session.query(func.count(AnalyticsProdutoMes.id)).filter(
            AnalyticsProdutoMes.mes_ano == mes_ano
        ).scalar()
        print(f"📦 analytics_produto_mes: {count_produto} registros")
        
        count_alertas = session.query(func.count(AnalyticsAlerta.id)).filter(
            AnalyticsAlerta.mes_ano == mes_ano
        ).scalar()
        print(f"🚨 analytics_alertas: {count_alertas} alertas")
        
        # 2. Top 5 vendedores com pior atingimento
        print_section("TOP 5 VENDEDORES COM PIOR ATINGIMENTO")
        
        piores = session.query(AnalyticsVendedorMes).filter(
            AnalyticsVendedorMes.mes_ano == mes_ano,
            AnalyticsVendedorMes.atingimento_pct.isnot(None)
        ).order_by(
            AnalyticsVendedorMes.atingimento_pct.asc()
        ).limit(5).all()
        
        if piores:
            for i, v in enumerate(piores, 1):
                print(f"{i}. {v.vendedor_nome}")
                print(f"   Atingimento: {v.atingimento_pct:.1f}%")
                print(f"   Meta: R$ {v.meta_total:,.2f} | Realizado: R$ {v.realizado_total:,.2f}")
                print(f"   Gap: R$ {v.gap_valor:,.2f}")
                print(f"   Rank: {v.rank_atingimento}")
                print()
        else:
            print("⚠️  Nenhum vendedor encontrado")
        
        # 3. Top 5 clientes por dias desde última compra
        print_section("TOP 5 CLIENTES POR DIAS DESDE ÚLTIMA COMPRA")
        
        clientes = session.query(AnalyticsClienteMes).filter(
            AnalyticsClienteMes.mes_ano == mes_ano,
            AnalyticsClienteMes.dias_desde_ultima_compra.isnot(None)
        ).order_by(
            AnalyticsClienteMes.dias_desde_ultima_compra.desc()
        ).limit(5).all()
        
        if clientes:
            for i, c in enumerate(clientes, 1):
                print(f"{i}. {c.cliente_nome}")
                print(f"   Dias sem comprar: {c.dias_desde_ultima_compra}")
                print(f"   Faturamento no mês: R$ {c.faturamento_total:,.2f}")
                print(f"   Qtd compras: {c.qtd_compras}")
                print()
        else:
            print("⚠️  Nenhum cliente encontrado")
        
        # 4. Top 5 produtos com menor faturamento
        print_section("TOP 5 PRODUTOS COM MENOR FATURAMENTO")
        
        produtos = session.query(AnalyticsProdutoMes).filter(
            AnalyticsProdutoMes.mes_ano == mes_ano
        ).order_by(
            AnalyticsProdutoMes.faturamento_total.asc()
        ).limit(5).all()
        
        if produtos:
            for i, p in enumerate(produtos, 1):
                print(f"{i}. {p.desc_produto or p.codigo_produto}")
                print(f"   Código: {p.codigo_produto}")
                print(f"   Faturamento: R$ {p.faturamento_total:,.2f}")
                print(f"   Qtd vendida: {p.qtd_vendida:,}")
                print(f"   Clientes ativos: {p.qtd_clientes_ativos}")
                if p.participacao_no_faturamento:
                    print(f"   Participação: {p.participacao_no_faturamento:.2f}%")
                print()
        else:
            print("⚠️  Nenhum produto encontrado")
        
        # 5. Alertas críticos
        print_section("ALERTAS CRÍTICOS")
        
        alertas_alto = session.query(AnalyticsAlerta).filter(
            AnalyticsAlerta.mes_ano == mes_ano,
            AnalyticsAlerta.nivel == "alto"
        ).limit(5).all()
        
        if alertas_alto:
            print("🔴 Alertas de Nível ALTO:")
            for a in alertas_alto:
                print(f"   - [{a.tipo_alerta}] {a.referencia_nome}")
                print(f"     {a.descricao}")
                print()
        else:
            print("✅ Nenhum alerta de nível alto")
        
        print_section("TESTE CONCLUÍDO")
        print("✅ Todas as tabelas analytics_* foram populadas e validadas")
        
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
        description="Testa tabelas de Analytics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Testa com mês padrão (2025-08)
  python -m scripts.test_analytics
  
  # Especifica mês/ano
  python -m scripts.test_analytics --mes-ano 2025-08
  
  # Com variáveis de ambiente
  DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db python -m scripts.test_analytics --mes-ano 2025-08
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
        exit_code = test_analytics(mes_ano=args.mes_ano)
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n❌ Erro: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    main()

