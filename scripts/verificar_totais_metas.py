#!/usr/bin/env python3
"""
Script para verificar se há linhas de totalizador na tabela metas_vendedor.
"""
import os
import sys

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
import os

def main():
    """Verifica se há linhas de totalizador na tabela metas_vendedor."""
    # Cria engine diretamente
    db_type = os.getenv("DB_TYPE", "sqlite")
    sqlite_path = os.getenv("SQLITE_PATH", "data/dipam_dw.db")
    
    if db_type == "sqlite":
        engine = create_engine(f"sqlite:///{sqlite_path}")
    else:
        raise ValueError(f"DB_TYPE {db_type} não suportado neste script")
    
    with engine.connect() as conn:
        # 1. Verifica vendedores distintos em agosto/2025
        print("=" * 60)
        print("Vendedores distintos em agosto/2025:")
        print("=" * 60)
        result = conn.execute(text("""
            SELECT DISTINCT vendedor_nome, COUNT(*) as count
            FROM metas_vendedor 
            WHERE mes_ano = '2025-08'
            GROUP BY vendedor_nome
            ORDER BY vendedor_nome
        """)).fetchall()
        
        for row in result:
            print(f"  {row[0]}: {row[1]} registros")
        
        # 2. Verifica se há 'Totais' ou 'Total'
        print("\n" + "=" * 60)
        print("Linhas de totalizador encontradas:")
        print("=" * 60)
        totais = conn.execute(text("""
            SELECT vendedor_nome, COUNT(*) as count, 
                   SUM(valor_meta) as meta_total,
                   SUM(valor_faturado) as realizado_total
            FROM metas_vendedor 
            WHERE mes_ano = '2025-08' 
              AND (LOWER(vendedor_nome) LIKE '%total%' OR vendedor_nome = 'Totais')
            GROUP BY vendedor_nome
        """)).fetchall()
        
        if totais:
            for row in totais:
                print(f"  {row[0]}: {row[1]} registros")
                print(f"    Meta: R$ {row[2]:,.2f}")
                print(f"    Realizado: R$ {row[3]:,.2f}")
        else:
            print("  Nenhuma linha de totalizador encontrada")
        
        # 3. Calcula totais COM e SEM totalizador
        print("\n" + "=" * 60)
        print("Totais para agosto/2025:")
        print("=" * 60)
        
        # COM totalizador
        total_com = conn.execute(text("""
            SELECT 
                SUM(valor_meta) as meta_total,
                SUM(valor_faturado) as realizado_total,
                COUNT(DISTINCT vendedor_nome) as num_vendedores
            FROM metas_vendedor 
            WHERE mes_ano = '2025-08'
        """)).fetchone()
        
        print(f"\nCOM totalizador:")
        print(f"  Meta total: R$ {total_com[0]:,.2f}")
        print(f"  Realizado total: R$ {total_com[1]:,.2f}")
        print(f"  Número de vendedores: {total_com[2]}")
        
        # SEM totalizador
        total_sem = conn.execute(text("""
            SELECT 
                SUM(valor_meta) as meta_total,
                SUM(valor_faturado) as realizado_total,
                COUNT(DISTINCT vendedor_nome) as num_vendedores
            FROM metas_vendedor 
            WHERE mes_ano = '2025-08'
              AND LOWER(vendedor_nome) NOT LIKE '%total%'
              AND vendedor_nome != 'Totais'
              AND vendedor_id IS NOT NULL
        """)).fetchone()
        
        print(f"\nSEM totalizador:")
        print(f"  Meta total: R$ {total_sem[0]:,.2f}")
        print(f"  Realizado total: R$ {total_sem[1]:,.2f}")
        print(f"  Número de vendedores: {total_sem[2]}")
        
        # Diferença
        if total_com[0] and total_sem[0]:
            diff_meta = total_com[0] - total_sem[0]
            diff_realizado = total_com[1] - total_sem[1]
            print(f"\nDiferença (totalizador):")
            print(f"  Meta: R$ {diff_meta:,.2f}")
            print(f"  Realizado: R$ {diff_realizado:,.2f}")

if __name__ == "__main__":
    main()

