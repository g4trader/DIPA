#!/usr/bin/env python3
"""
Script de debug para validar KPIs de agosto/2025.

Mostra os valores corretos calculados pela função única de agregação.
"""

import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from src.dw.connection import get_db_session
from src.agent.queries_analytics import get_metas_realizado_por_mes

def main():
    """Valida KPIs de agosto/2025."""
    session = next(get_db_session())
    mes_ano = "2025-08"
    
    print("="*80)
    print(f"VALIDAÇÃO DE KPIs PARA {mes_ano}")
    print("="*80)
    print()
    
    # Calcula KPIs usando função única
    kpis = get_metas_realizado_por_mes(session, mes_ano, excluir_totais=True)
    
    print("RESULTADOS (excluindo linha Totais):")
    print("-"*80)
    print(f"Meta total:        R$ {kpis['meta_total']:,.2f}")
    print(f"Realizado total:   R$ {kpis['realizado_total']:,.2f}")
    print(f"Gap total:         R$ {kpis['gap_total']:,.2f}")
    print(f"Atingimento médio:  {kpis['atingimento_medio']:.2f}%")
    print(f"Total vendedores:  {kpis['total_vendedores']}")
    print()
    
    # Compara com valores esperados
    print("="*80)
    print("COMPARAÇÃO COM VALORES ESPERADOS:")
    print("="*80)
    print(f"Esperado (banco):   Meta R$ 17.833.054,85 | Realizado R$ 17.254.142,15 | Atingimento 96,75%")
    print(f"Calculado:          Meta R$ {kpis['meta_total']:,.2f} | Realizado R$ {kpis['realizado_total']:,.2f} | Atingimento {kpis['atingimento_medio']:.2f}%")
    print()
    
    # Verifica se está dentro da tolerância
    meta_esperada = 17_833_054.85
    realizado_esperado = 17_254_142.15
    atingimento_esperado = 96.75
    
    diff_meta = abs(kpis['meta_total'] - meta_esperada) / meta_esperada * 100
    diff_realizado = abs(kpis['realizado_total'] - realizado_esperado) / realizado_esperado * 100
    diff_atingimento = abs(kpis['atingimento_medio'] - atingimento_esperado)
    
    print("="*80)
    print("VALIDAÇÃO:")
    print("="*80)
    
    if diff_meta < 1.0:
        print(f"✅ Meta total: Diferença de {diff_meta:.2f}% (dentro da tolerância)")
    else:
        print(f"❌ Meta total: Diferença de {diff_meta:.2f}% (FORA da tolerância)")
    
    if diff_realizado < 1.0:
        print(f"✅ Realizado total: Diferença de {diff_realizado:.2f}% (dentro da tolerância)")
    else:
        print(f"❌ Realizado total: Diferença de {diff_realizado:.2f}% (FORA da tolerância)")
    
    if diff_atingimento < 1.0:
        print(f"✅ Atingimento médio: Diferença de {diff_atingimento:.2f}% (dentro da tolerância)")
    else:
        print(f"❌ Atingimento médio: Diferença de {diff_atingimento:.2f}% (FORA da tolerância)")
    
    print()
    print("="*80)
    print("QUERY SQL USADA (via SQLAlchemy):")
    print("="*80)
    print("""
SELECT * FROM analytics_vendedor_mes
WHERE mes_ano = '2025-08'
  AND LOWER(vendedor_nome) NOT LIKE '%total%'
  AND vendedor_nome != 'Totais'
  AND vendedor_id IS NOT NULL;

-- Depois soma:
-- meta_total = SUM(meta_total)
-- realizado_total = SUM(realizado_total)
-- atingimento_medio = (realizado_total / meta_total) * 100
    """)
    
    session.close()

if __name__ == "__main__":
    main()

