#!/usr/bin/env python3
"""
Script para testar e exibir produtos menos vendidos.
"""

import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

import os
# Força uso de SQLite
os.environ.setdefault("DB_TYPE", "sqlite")
os.environ.setdefault("DATABASE_TYPE", "sqlite")

from src.dw.connection import get_db_session, init_db
from src.analysis.produtos import get_produtos_menos_vendidos

def main():
    """Executa a função e exibe resultados em formato de tabela."""
    print("=" * 100)
    print("PRODUTOS MENOS VENDIDOS - ÚLTIMOS 90 DIAS")
    print("=" * 100)
    print()
    
    # Inicializa banco de dados
    init_db()
    
    # Cria sessão do banco de dados
    session_gen = get_db_session()
    session = next(session_gen)
    
    try:
        # Executa a função
        produtos = get_produtos_menos_vendidos(session, dias=90, limite=20)
        
        if not produtos:
            print("❌ Nenhum produto encontrado no período especificado.")
            return
        
        # Formata valores para exibição em tabela
        def format_currency(value: float) -> str:
            """Formata valor monetário no padrão brasileiro."""
            parte_int = int(value)
            parte_dec = int(round((value - parte_int) * 100))
            parte_int_str = f"{parte_int:,}".replace(",", ".")
            return f"R$ {parte_int_str},{parte_dec:02d}"
        
        # Cabeçalho da tabela
        print(f"Total de produtos encontrados: {len(produtos)}\n")
        print("-" * 120)
        print(f"{'#':<4} {'Código':<15} {'Produto':<40} {'Unidades':<12} {'Caixas':<10} {'Faturamento':<20}")
        print("-" * 120)
        
        # Linhas da tabela
        for i, produto in enumerate(produtos, 1):
            codigo = produto['codigo'][:14] if len(produto['codigo']) > 14 else produto['codigo']
            nome = produto['produto'][:38] if len(produto['produto']) > 38 else produto['produto']
            unidades = produto['unidades']
            caixas = f"{produto['caixas']:.1f}"
            faturamento = format_currency(produto['faturamento'])
            
            print(f"{i:<4} {codigo:<15} {nome:<40} {unidades:<12} {caixas:<10} {faturamento:<20}")
        
        print("-" * 120)
        print()
        
        # Estatísticas resumidas
        print("-" * 100)
        print("RESUMO ESTATÍSTICO:")
        print("-" * 100)
        print(f"Total de produtos analisados: {len(produtos)}")
        print(f"Faturamento total (menos vendidos): R$ {sum(p['faturamento'] for p in produtos):,.2f}")
        print(f"Faturamento médio por produto: R$ {sum(p['faturamento'] for p in produtos) / len(produtos):,.2f}")
        print(f"Total de unidades vendidas: {sum(p['unidades'] for p in produtos)}")
        print(f"Total de caixas vendidas: {sum(p['caixas'] for p in produtos):.1f}")
        
        # Produto com menor faturamento
        pior = min(produtos, key=lambda x: x['faturamento'])
        print(f"\nProduto com MENOR faturamento:")
        print(f"  - Nome: {pior['produto']}")
        print(f"  - Código: {pior['codigo']}")
        print(f"  - Faturamento: R$ {pior['faturamento']:,.2f}")
        print(f"  - Unidades: {pior['unidades']} | Caixas: {pior['caixas']:.1f}")
        
    except Exception as e:
        print(f"❌ Erro ao executar análise: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    main()

