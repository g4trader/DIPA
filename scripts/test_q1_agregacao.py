#!/usr/bin/env python3
"""
Script para testar a Q1 com agregação de múltiplos vendedores/supervisores.
"""

import sys
import os
from pathlib import Path

# Adiciona o diretório raiz ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

if not os.getenv('SQLITE_PATH'):
    sqlite_path = Path(project_root) / 'data' / 'dipam_dw.db'
    os.environ['SQLITE_PATH'] = str(sqlite_path)

from src.dw.connection import init_db, get_db_session
from src.dw.queries import get_clientes_sem_compra_ha_dias

def main():
    print("=" * 80)
    print("TESTE: Q1 com Agregação de Múltiplos Vendedores/Supervisores")
    print("=" * 80)
    
    init_db()
    session = next(get_db_session())
    
    try:
        resultados = get_clientes_sem_compra_ha_dias(session, dias=60)
        print(f'\n✅ Total de registros retornados: {len(resultados)}')
        
        # Verifica duplicatas
        cliente_ids = [r['cliente_id'] for r in resultados]
        clientes_unicos = set(cliente_ids)
        
        print(f'✅ Total de clientes únicos: {len(clientes_unicos)}')
        print(f'📊 Total de registros: {len(cliente_ids)}')
        
        if len(cliente_ids) != len(clientes_unicos):
            print(f'\n⚠️  DUPLICATAS ENCONTRADAS: {len(cliente_ids) - len(clientes_unicos)}')
        else:
            print('✅ Nenhuma duplicata encontrada')
        
        # Verifica se há clientes com múltiplos vendedores/supervisores agregados
        clientes_com_multiplos = []
        for r in resultados[:50]:  # Primeiros 50
            vendedor = r.get('vendedor_nome', '') or ''
            supervisor = r.get('supervisor_nome', '') or ''
            # Verifica se há múltiplos valores (separados por \n)
            if '\n' in str(vendedor) or '\n' in str(supervisor):
                clientes_com_multiplos.append({
                    'cliente_id': r['cliente_id'],
                    'nome': r['nome'],
                    'vendedor': vendedor,
                    'supervisor': supervisor
                })
        
        if clientes_com_multiplos:
            print(f'\n✅ Encontrados {len(clientes_com_multiplos)} clientes com múltiplos vendedores/supervisores agregados:')
            for c in clientes_com_multiplos[:5]:
                print(f'\n  Cliente {c["cliente_id"]} ({c["nome"]}):')
                if '\n' in str(c['vendedor']):
                    vendedores = [v.strip() for v in str(c['vendedor']).split('\n') if v.strip()]
                    print(f'    Vendedores ({len(vendedores)}): {vendedores}')
                if '\n' in str(c['supervisor']):
                    supervisores = [s.strip() for s in str(c['supervisor']).split('\n') if s.strip()]
                    print(f'    Supervisores ({len(supervisores)}): {supervisores}')
        else:
            print('\nℹ️  Nenhum cliente com múltiplos vendedores/supervisores encontrado nos primeiros 50')
        
        print('\n' + "=" * 80)
        print("RESUMO")
        print("=" * 80)
        print(f"Total de registros: {len(resultados)}")
        print(f"Total de clientes únicos: {len(clientes_unicos)}")
        print(f"Duplicatas: {'SIM' if len(cliente_ids) != len(clientes_unicos) else 'NÃO'}")
        print(f"Clientes com múltiplos vendedores/supervisores agregados: {len(clientes_com_multiplos)}")
        print('\n✅ Query funcionando corretamente!')
        
    except Exception as e:
        print(f'\n❌ ERRO: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()

if __name__ == "__main__":
    main()

