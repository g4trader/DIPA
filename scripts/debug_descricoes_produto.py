#!/usr/bin/env python3
"""
Script de debug para descobrir como produtos Nissin aparecem no banco de dados.

Executa queries para encontrar produtos relacionados a NISSIN, MIOJO e GALINHA
e exibe os resultados formatados.

Uso:
    python -m scripts.debug_descricoes_produto
"""

import os
import sys
import traceback
from datetime import datetime

# Garante que o diretório raiz está no path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Define DB_TYPE=sqlite antes de importar módulos do banco
os.environ.setdefault('DB_TYPE', 'sqlite')

from src.dw.connection import get_db_session
from src.dw.models import Venda
from sqlalchemy import func, distinct
from sqlalchemy.orm import aliased


def formatar_tabela(resultados, titulo, termo_busca):
    """Formata resultados em uma tabela legível."""
    print("=" * 100)
    print(f"{titulo} (termo: '{termo_busca}')")
    print("=" * 100)
    
    if not resultados:
        print("⚠️  Nenhum resultado encontrado.")
        print()
        return
    
    # Cabeçalho da tabela
    print(f"{'Código':<20} {'Descrição':<70}")
    print("-" * 100)
    
    # Imprime resultados
    for i, row in enumerate(resultados, 1):
        codigo = str(row.codigo_produto) if row.codigo_produto else "N/A"
        descricao = str(row.desc_produto) if row.desc_produto else "N/A"
        
        # Trunca se muito longo
        codigo = codigo[:20]
        descricao = descricao[:70]
        
        print(f"{codigo:<20} {descricao:<70}")
    
    print(f"\nTotal de produtos encontrados: {len(resultados)}")
    print()


def main():
    """Função principal para buscar produtos no banco."""
    print("=" * 100)
    print("DEBUG: Buscando produtos relacionados a NISSIN, MIOJO e GALINHA")
    print("=" * 100)
    print()
    
    # Abre sessão de banco
    print("Abrindo sessão de banco de dados...")
    session_context = get_db_session()
    session = next(session_context)
    
    try:
        # 1. Calcula data_base (max data_venda)
        print("Calculando data_base (max data_venda)...")
        data_base = session.query(func.max(Venda.data_venda)).scalar()
        
        print()
        print("=" * 100)
        print("INFORMAÇÕES DO BANCO")
        print("=" * 100)
        if data_base:
            print(f"Data base (última venda): {data_base.strftime('%Y-%m-%d')}")
        else:
            print("⚠️  Nenhuma venda encontrada no banco de dados.")
        print()
        
        # 2. Query a) Produtos contendo "NISS"
        print("Executando query a) Produtos contendo 'NISS'...")
        query_niss = (
            session.query(
                Venda.codigo_produto,
                Venda.desc_produto
            )
            .filter(func.lower(Venda.desc_produto).like('%niss%'))
            .distinct()
            .order_by(Venda.desc_produto)
            .limit(50)
        )
        resultados_niss = query_niss.all()
        
        formatar_tabela(resultados_niss, "a) PRODUTOS CONTENDO 'NISS'", "NISS")
        
        # 3. Query b) Produtos contendo "MIOJO"
        print("Executando query b) Produtos contendo 'MIOJO'...")
        query_miojo = (
            session.query(
                Venda.codigo_produto,
                Venda.desc_produto
            )
            .filter(func.lower(Venda.desc_produto).like('%miojo%'))
            .distinct()
            .order_by(Venda.desc_produto)
            .limit(50)
        )
        resultados_miojo = query_miojo.all()
        
        formatar_tabela(resultados_miojo, "b) PRODUTOS CONTENDO 'MIOJO'", "MIOJO")
        
        # 4. Query c) Produtos contendo "GALINHA"
        print("Executando query c) Produtos contendo 'GALINHA'...")
        query_galinha = (
            session.query(
                Venda.codigo_produto,
                Venda.desc_produto
            )
            .filter(func.lower(Venda.desc_produto).like('%galinha%'))
            .distinct()
            .order_by(Venda.desc_produto)
            .limit(50)
        )
        resultados_galinha = query_galinha.all()
        
        formatar_tabela(resultados_galinha, "c) PRODUTOS CONTENDO 'GALINHA'", "GALINHA")
        
        # 5. Estatísticas adicionais
        print("=" * 100)
        print("ESTATÍSTICAS")
        print("=" * 100)
        
        total_vendas_niss = session.query(func.count(Venda.id)).filter(
            func.lower(Venda.desc_produto).like('%niss%')
        ).scalar()
        
        total_vendas_miojo = session.query(func.count(Venda.id)).filter(
            func.lower(Venda.desc_produto).like('%miojo%')
        ).scalar()
        
        total_vendas_galinha = session.query(func.count(Venda.id)).filter(
            func.lower(Venda.desc_produto).like('%galinha%')
        ).scalar()
        
        print(f"Total de vendas com produtos contendo 'NISS': {total_vendas_niss}")
        print(f"Total de vendas com produtos contendo 'MIOJO': {total_vendas_miojo}")
        print(f"Total de vendas com produtos contendo 'GALINHA': {total_vendas_galinha}")
        print()
        
        # Busca por departamento/seção como alternativa
        print("=" * 100)
        print("ALTERNATIVA: Produtos agrupados por departamento/seção")
        print("=" * 100)
        print()
        
        query_dept = (
            session.query(
                Venda.departamento,
                Venda.secao,
                func.count(distinct(Venda.desc_produto)).label('qtd_produtos'),
                func.count(Venda.id).label('qtd_vendas')
            )
            .filter(
                (func.lower(Venda.departamento).like('%niss%')) |
                (func.lower(Venda.secao).like('%niss%')) |
                (func.lower(Venda.desc_produto).like('%niss%')) |
                (func.lower(Venda.departamento).like('%miojo%')) |
                (func.lower(Venda.secao).like('%miojo%')) |
                (func.lower(Venda.desc_produto).like('%miojo%'))
            )
            .group_by(Venda.departamento, Venda.secao)
            .order_by(Venda.departamento, Venda.secao)
            .limit(20)
        )
        
        resultados_dept = query_dept.all()
        
        if resultados_dept:
            print(f"{'Departamento':<30} {'Seção':<30} {'Produtos':<12} {'Vendas':<12}")
            print("-" * 100)
            for row in resultados_dept:
                dept = str(row.departamento or 'N/A')[:30]
                secao = str(row.secao or 'N/A')[:30]
                qtd_prod = row.qtd_produtos or 0
                qtd_vendas = row.qtd_vendas or 0
                print(f"{dept:<30} {secao:<30} {qtd_prod:<12} {qtd_vendas:<12}")
        else:
            print("⚠️  Nenhum resultado encontrado por departamento/seção.")
        
        print()
        print("=" * 100)
        print("✅ Teste concluído com sucesso!")
        print("=" * 100)
        
    except Exception as e:
        print()
        print("=" * 100)
        print("❌ ERRO durante a execução")
        print("=" * 100)
        print(f"Erro: {str(e)}")
        print()
        print("Stack trace completo:")
        print("-" * 100)
        traceback.print_exc()
        print("-" * 100)
        
        return 1
    
    finally:
        # Fecha sessão
        session.close()
        print(f"\nSessão de banco de dados fechada.")
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

