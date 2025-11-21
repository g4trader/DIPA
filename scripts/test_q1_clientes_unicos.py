#!/usr/bin/env python3
"""
Script para testar se a Q1 retorna apenas clientes únicos
e verificar se há clientes com múltiplos vendedores/supervisores.
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
from collections import Counter

def main():
    print("=" * 80)
    print("TESTE: Q1 - Clientes Únicos e Múltiplos Vendedores/Supervisores")
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
            # Mostra alguns clientes duplicados
            duplicados = [cid for cid, count in Counter(cliente_ids).items() if count > 1]
            print(f'Exemplos de clientes duplicados: {duplicados[:10]}')
            for cid in duplicados[:5]:
                registros = [r for r in resultados if r['cliente_id'] == cid]
                print(f'\n  Cliente {cid} ({len(registros)} registros):')
                for r in registros:
                    print(f'    - Vendedor: {r.get("vendedor_nome", "N/A")}, Supervisor: {r.get("supervisor_nome", "N/A")}')
        else:
            print('✅ Nenhuma duplicata encontrada')
        
        # Verifica se há clientes com múltiplos vendedores/supervisores na base
        # (mesmo que apareçam apenas 1 vez no resultado devido ao ROW_NUMBER)
        print('\n' + "=" * 80)
        print("VERIFICANDO: Clientes com múltiplos vendedores/supervisores na base")
        print("=" * 80)
        
        from src.dw.models import Cliente, Vendedor, Supervisor
        from sqlalchemy.orm import aliased
        
        # Busca clientes que têm múltiplas rotas/vendedores associados
        clientes_com_multiplos = {}
        
        # Para cada cliente no resultado, verifica quantos vendedores/supervisores existem na base
        for r in resultados[:100]:  # Limita a 100 para não demorar muito
            cid = r['cliente_id']
            cliente = session.query(Cliente).filter(Cliente.id == cid).first()
            
            if cliente:
                # Busca todos os vendedores que podem estar associados a este cliente
                # (via rota_rca ou outras formas)
                vendedores_associados = set()
                supervisores_associados = set()
                
                # Se cliente tem rota_rca, busca vendedor por nome da rota
                if cliente.rota_rca:
                    vendedores = session.query(Vendedor).filter(Vendedor.nome == cliente.rota_rca).all()
                    for v in vendedores:
                        vendedores_associados.add(v.nome)
                        if v.supervisor:
                            supervisores_associados.add(v.supervisor.nome)
                
                # Se cliente tem supervisor direto
                if cliente.supervisor:
                    supervisores_associados.add(cliente.supervisor.nome)
                
                if len(vendedores_associados) > 1 or len(supervisores_associados) > 1:
                    clientes_com_multiplos[cid] = {
                        'vendedores': list(vendedores_associados),
                        'supervisores': list(supervisores_associados),
                        'nome': cliente.nome
                    }
        
        if clientes_com_multiplos:
            print(f'\n⚠️  Encontrados {len(clientes_com_multiplos)} clientes com múltiplos vendedores/supervisores:')
            for cid, info in list(clientes_com_multiplos.items())[:5]:
                print(f'\n  Cliente {cid} ({info["nome"]}):')
                if len(info['vendedores']) > 1:
                    print(f'    Vendedores: {info["vendedores"]}')
                if len(info['supervisores']) > 1:
                    print(f'    Supervisores: {info["supervisores"]}')
        else:
            print('\n✅ Nenhum cliente com múltiplos vendedores/supervisores encontrado nos primeiros 100')
        
        print('\n' + "=" * 80)
        print("RESUMO")
        print("=" * 80)
        print(f"Total de registros: {len(resultados)}")
        print(f"Total de clientes únicos: {len(clientes_unicos)}")
        print(f"Duplicatas: {'SIM' if len(cliente_ids) != len(clientes_unicos) else 'NÃO'}")
        print(f"Clientes com múltiplos vendedores/supervisores: {len(clientes_com_multiplos)}")
        
    finally:
        session.close()

if __name__ == "__main__":
    main()

