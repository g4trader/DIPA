#!/usr/bin/env python3
"""
Script de debug para testar a função clientes_positivados_sem_compra_produto.

Testa diretamente a busca de clientes que já compraram um produto específico
mas não compram há mais de X dias.

Uso:
    python -m scripts.debug_clientes_nissin
"""

import os
import sys
import time
import traceback
from datetime import datetime

# Garante que o diretório raiz está no path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Define DB_TYPE=sqlite antes de importar módulos do banco
os.environ.setdefault('DB_TYPE', 'sqlite')

from src.dw.connection import get_db_session
from src.analysis.clientes import clientes_positivados_sem_compra_produto


def formatar_data(data):
    """Formata data para exibição."""
    if data:
        if isinstance(data, str):
            return data
        return data.strftime('%Y-%m-%d')
    return "N/A"


def main():
    """Função principal para testar a busca de clientes."""
    print("=" * 80)
    print("DEBUG: Testando clientes_positivados_sem_compra_produto")
    print("=" * 80)
    print()
    
    # Parâmetros de teste
    termo_produto = "NISSIN"
    dias_sem_compra = 60
    limite = 50
    
    print(f"Parâmetros:")
    print(f"  - Produto: {termo_produto}")
    print(f"  - Dias sem compra: {dias_sem_compra}")
    print(f"  - Limite: {limite}")
    print()
    
    # Abre sessão de banco
    print("Abrindo sessão de banco de dados...")
    session_context = get_db_session()
    session = next(session_context)
    
    try:
        # Mede tempo de execução
        t_start = time.perf_counter()
        print(f"Iniciando busca às {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
        print()
        
        # Chama a função
        resultados = clientes_positivados_sem_compra_produto(
            session=session,
            termo_produto=termo_produto,
            dias_sem_compra=dias_sem_compra,
            limite=limite,
        )
        
        t_end = time.perf_counter()
        tempo_execucao = t_end - t_start
        
        # Imprime resultados
        print("=" * 80)
        print("RESULTADOS")
        print("=" * 80)
        print(f"Tempo total de execução: {tempo_execucao:.3f} segundos")
        print(f"Quantidade de clientes retornados: {len(resultados)}")
        print()
        
        if len(resultados) == 0:
            print("⚠️  Nenhum cliente encontrado que atenda aos critérios.")
            print()
            print("Isso pode indicar:")
            print("  - Não há clientes que compraram este produto")
            print("  - Todos os clientes compraram recentemente (menos de 60 dias)")
            print("  - Problema na query ou dados do banco")
        else:
            print("=" * 80)
            print("PRIMEIROS 5 REGISTROS:")
            print("=" * 80)
            print()
            
            # Imprime cabeçalho da tabela
            print(f"{'#':<4} {'Código':<12} {'Nome':<40} {'Cidade':<20} {'Dias sem':<10} {'Última Compra':<12} {'Faturamento':<15}")
            print("-" * 130)
            
            # Imprime os 5 primeiros registros
            for i, cliente in enumerate(resultados[:5], 1):
                codigo = cliente.get("codigo_cliente", "N/A")[:12]
                nome = cliente.get("nome_cliente", "N/A")[:40]
                cidade = cliente.get("cidade", "N/A")[:20]
                dias = cliente.get("dias_sem_compra", 0)
                ultima_compra = formatar_data(cliente.get("ultima_compra_produto"))
                faturamento = cliente.get("total_historico_faturamento", 0)
                
                # Formata faturamento
                faturamento_str = f"R$ {faturamento:,.2f}" if faturamento else "R$ 0,00"
                
                print(f"{i:<4} {codigo:<12} {nome:<40} {cidade:<20} {dias:<10} {ultima_compra:<12} {faturamento_str:<15}")
            
            print()
            
            if len(resultados) > 5:
                print(f"... e mais {len(resultados) - 5} cliente(s)")
                print()
            
            # Estatísticas adicionais
            print("=" * 80)
            print("ESTATÍSTICAS:")
            print("=" * 80)
            
            if resultados:
                dias_list = [c.get("dias_sem_compra", 0) for c in resultados]
                faturamento_list = [c.get("total_historico_faturamento", 0) for c in resultados]
                
                print(f"  - Maior tempo sem compra: {max(dias_list)} dias")
                print(f"  - Menor tempo sem compra: {min(dias_list)} dias")
                print(f"  - Tempo médio sem compra: {sum(dias_list) / len(dias_list):.1f} dias")
                print(f"  - Faturamento histórico total: R$ {sum(faturamento_list):,.2f}")
                print(f"  - Faturamento histórico médio por cliente: R$ {sum(faturamento_list) / len(faturamento_list):,.2f}")
        
        print()
        print("=" * 80)
        print("✅ Teste concluído com sucesso!")
        print("=" * 80)
        
    except Exception as e:
        t_error = time.perf_counter()
        tempo_ate_erro = t_error - t_start
        
        print()
        print("=" * 80)
        print("❌ ERRO durante a execução")
        print("=" * 80)
        print(f"Tempo até o erro: {tempo_ate_erro:.3f} segundos")
        print(f"Erro: {str(e)}")
        print()
        print("Stack trace completo:")
        print("-" * 80)
        traceback.print_exc()
        print("-" * 80)
        
        return 1
    
    finally:
        # Fecha sessão
        session.close()
        print(f"\nSessão de banco de dados fechada.")
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)




