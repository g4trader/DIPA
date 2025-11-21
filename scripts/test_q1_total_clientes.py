#!/usr/bin/env python3
"""
Script para testar a Q1 via API e verificar o total de clientes retornados.
"""

import sys
import os
import json
import requests
from pathlib import Path

# Adiciona o diretório raiz ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

def test_q1_api(api_url: str = None):
    """Testa a Q1 via API"""
    if not api_url:
        # Tenta detectar automaticamente
        api_url = os.getenv('API_URL', 'http://localhost:8000')
    
    print("=" * 80)
    print("TESTE: Q1 via API - Total de Clientes")
    print("=" * 80)
    print(f"API URL: {api_url}")
    
    pergunta = "Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?"
    
    try:
        response = requests.post(
            f"{api_url}/ask",
            json={"pergunta": pergunta},
            timeout=60
        )
        
        if response.status_code != 200:
            print(f"❌ ERRO: Status {response.status_code}")
            print(f"Resposta: {response.text}")
            return
        
        data = response.json()
        
        # Extrai o total de clientes
        total_clientes = 0
        tabela_principal = None
        
        # Tenta encontrar a tabela principal
        if 'dadosDw' in data:
            dados_dw = data['dadosDw']
            if isinstance(dados_dw, list):
                total_clientes = len(dados_dw)
            elif isinstance(dados_dw, dict) and 'dados' in dados_dw:
                total_clientes = len(dados_dw['dados'])
        
        if 'tabelaPrincipal' in data:
            tabela_principal = data['tabelaPrincipal']
            if isinstance(tabela_principal, dict) and 'rows' in tabela_principal:
                total_clientes = len(tabela_principal['rows'])
        
        if 'detalhe_tabela' in data:
            detalhe_tabela = data['detalhe_tabela']
            if isinstance(detalhe_tabela, dict) and 'linhas' in detalhe_tabela:
                total_clientes = len(detalhe_tabela['linhas'])
        
        print(f"\n✅ Total de clientes retornados pela API: {total_clientes}")
        
        # Verifica duplicatas
        if tabela_principal and 'rows' in tabela_principal:
            cliente_ids = []
            for row in tabela_principal['rows']:
                # Tenta encontrar o ID do cliente na primeira coluna ou em uma coluna específica
                if isinstance(row, list) and len(row) > 0:
                    cliente_ids.append(str(row[0]))  # Assume que o primeiro campo é o ID
                elif isinstance(row, dict):
                    cliente_ids.append(str(row.get('cliente_id', row.get('Cliente ID', ''))))
            
            clientes_unicos = set(cliente_ids)
            print(f"✅ Total de clientes únicos na tabela: {len(clientes_unicos)}")
            print(f"📊 Total de registros na tabela: {len(cliente_ids)}")
            
            if len(cliente_ids) != len(clientes_unicos):
                print(f"⚠️  DUPLICATAS ENCONTRADAS: {len(cliente_ids) - len(clientes_unicos)}")
            else:
                print("✅ Nenhuma duplicata encontrada")
        
        # Mostra estrutura da resposta
        print("\n" + "=" * 80)
        print("ESTRUTURA DA RESPOSTA")
        print("=" * 80)
        print(f"Campos disponíveis: {list(data.keys())}")
        
        if 'resumo_executivo' in data:
            print(f"\nResumo Executivo (primeiros 200 chars):")
            print(data['resumo_executivo'][:200] + "...")
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--api', type=str, help='URL da API (ex: http://localhost:8000)')
    parser.add_argument('--prod', action='store_true', help='Usa API de produção')
    args = parser.parse_args()
    
    if args.prod:
        api_url = "https://dipam-ai-backend-642830139828.us-central1.run.app"
    elif args.api:
        api_url = args.api
    else:
        api_url = "http://localhost:8000"
    
    test_q1_api(api_url)

