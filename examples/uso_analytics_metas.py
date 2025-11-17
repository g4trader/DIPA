"""
Exemplo de uso da camada analítica de metas (src/dw/analytics_metas.py).

Este script demonstra como usar as funções de consulta reutilizáveis
para acessar dados do Data Warehouse.
"""

from src.dw.connection import get_db_session
from src.dw.analytics_metas import (
    listar_metas_por_mes,
    listar_vendas_por_mes,
    listar_metas_realizado_por_supervisor,
    listar_clientes_criticos
)


def exemplo_metas_por_mes():
    """Exemplo: Listar metas por mês no período."""
    session = next(get_db_session())
    
    # Lista metas de nov/2024 a out/2025
    metas = listar_metas_por_mes(
        session,
        periodo_inicio="2024-11",
        periodo_fim="2025-10"
    )
    
    print(f"\n📊 Metas por Mês ({len(metas)} meses encontrados):")
    print("-" * 80)
    for meta in metas:
        print(
            f"  {meta.mes_ano}: "
            f"Meta R$ {meta.meta_total:,.2f} | "
            f"Realizado R$ {meta.realizado_total:,.2f} | "
            f"Atingimento {meta.atingimento_medio:.1f}% | "
            f"Vendedores: {meta.total_vendedores}"
        )
    
    session.close()


def exemplo_vendas_por_mes():
    """Exemplo: Listar vendas por mês no período."""
    session = next(get_db_session())
    
    vendas = listar_vendas_por_mes(
        session,
        periodo_inicio="2024-11",
        periodo_fim="2025-10"
    )
    
    print(f"\n💰 Vendas por Mês ({len(vendas)} meses encontrados):")
    print("-" * 80)
    for venda in vendas:
        print(
            f"  {venda.mes_ano}: "
            f"Faturamento R$ {venda.faturamento_total:,.2f} | "
            f"Vendas: {venda.quantidade_vendas} | "
            f"Clientes: {venda.quantidade_clientes} | "
            f"Ticket Médio R$ {venda.ticket_medio:,.2f}"
        )
    
    session.close()


def exemplo_metas_por_supervisor():
    """Exemplo: Listar metas por supervisor em um mês."""
    session = next(get_db_session())
    
    supervisores = listar_metas_realizado_por_supervisor(
        session,
        mes="2025-08"
    )
    
    print(f"\n👥 Metas por Supervisor - Agosto 2025 ({len(supervisores)} supervisores):")
    print("-" * 80)
    for sup in supervisores:
        print(
            f"  {sup.supervisor_nome}: "
            f"Meta R$ {sup.meta_total:,.2f} | "
            f"Realizado R$ {sup.realizado_total:,.2f} | "
            f"Atingimento {sup.atingimento_pct:.1f}% | "
            f"Gap R$ {sup.gap_total:,.2f} | "
            f"RCAs: {sup.quantidade_vendedores}"
        )
    
    session.close()


def exemplo_clientes_criticos():
    """Exemplo: Listar clientes críticos (em risco de churn)."""
    session = next(get_db_session())
    
    clientes = listar_clientes_criticos(
        session,
        periodo_inicio="2025-08",
        periodo_fim="2025-08",
        limite=20
    )
    
    print(f"\n⚠️  Clientes Críticos - Agosto 2025 ({len(clientes)} clientes):")
    print("-" * 80)
    for cliente in clientes[:10]:  # Mostra apenas top 10
        risco = "🔴 ALTO" if cliente.churn_score >= 70 else "🟡 MÉDIO"
        print(
            f"  {cliente.cliente_nome} ({risco}): "
            f"Churn Score {cliente.churn_score:.1f} | "
            f"Dias sem compra: {cliente.dias_sem_compra} | "
            f"Faturamento R$ {cliente.faturamento_total:,.2f}"
        )
    
    session.close()


if __name__ == "__main__":
    print("=" * 80)
    print("EXEMPLOS DE USO - Camada Analítica de Metas")
    print("=" * 80)
    
    try:
        exemplo_metas_por_mes()
        exemplo_vendas_por_mes()
        exemplo_metas_por_supervisor()
        exemplo_clientes_criticos()
    except Exception as e:
        print(f"\n❌ Erro ao executar exemplos: {e}")
        import traceback
        traceback.print_exc()

