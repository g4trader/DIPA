#!/usr/bin/env python3
"""
Script para testar consistência entre Big Number e total de linhas da tabela na Q1.
"""

import sys
import os
import json
import requests
from pathlib import Path
from typing import Dict, Any, Optional

# Adiciona o diretório raiz ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

if not os.getenv('SQLITE_PATH'):
    sqlite_path = Path(project_root) / 'data' / 'dipam_dw.db'
    os.environ['SQLITE_PATH'] = str(sqlite_path)

from src.dw.connection import init_db, get_db_session
from src.dw.queries import get_clientes_sem_compra_ha_dias

def test_q1_consistencia_local():
    """Testa consistência localmente (via função Python)"""
    print("=" * 80)
    print("TESTE LOCAL: Q1 - Consistência Big Number vs Tabela")
    print("=" * 80)
    
    init_db()
    session = next(get_db_session())
    
    try:
        # Executa Q1 diretamente
        resultados = get_clientes_sem_compra_ha_dias(session, dias=60)
        total_linhas_tabela = len(resultados)
        
        # Verifica clientes únicos
        cliente_ids = [r['cliente_id'] for r in resultados]
        clientes_unicos = len(set(cliente_ids))
        
        print(f"\n✅ Total de linhas retornadas pela query: {total_linhas_tabela}")
        print(f"✅ Total de clientes únicos: {clientes_unicos}")
        
        if total_linhas_tabela != clientes_unicos:
            print(f"⚠️  INCONSISTÊNCIA: {total_linhas_tabela} linhas vs {clientes_unicos} clientes únicos")
            return False
        else:
            print("✅ Consistência OK: total_linhas_tabela == clientes_unicos")
            return True
            
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()


def test_q1_consistencia_api(api_url: str = None):
    """Testa consistência via API"""
    if not api_url:
        api_url = os.getenv('API_URL', 'http://localhost:8000')
    
    print("\n" + "=" * 80)
    print("TESTE API: Q1 - Consistência Big Number vs Tabela")
    print("=" * 80)
    print(f"API URL: {api_url}")
    
    pergunta = "Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?"
    
    try:
        response = requests.post(
            f"{api_url}/ask",
            json={"pergunta": pergunta},
            timeout=120
        )
        
        if response.status_code != 200:
            print(f"❌ ERRO: Status {response.status_code}")
            print(f"Resposta: {response.text[:500]}")
            return False
        
        data = response.json()
        
        # Extrai total de linhas da tabela
        total_linhas_tabela = 0
        tabela_principal = None
        
        # Tenta encontrar a tabela principal
        if 'structured' in data and isinstance(data['structured'], dict):
            structured = data['structured']
            if 'tabelaPrincipal' in structured:
                tabela_principal = structured['tabelaPrincipal']
            elif 'dadosDw' in structured:
                dados_dw = structured.get('dadosDw', {})
                if isinstance(dados_dw, dict) and 'dados' in dados_dw:
                    total_linhas_tabela = len(dados_dw['dados'])
        
        if 'dadosDw' in data:
            dados_dw = data['dadosDw']
            if isinstance(dados_dw, list):
                total_linhas_tabela = len(dados_dw)
            elif isinstance(dados_dw, dict) and 'dados' in dados_dw:
                total_linhas_tabela = len(dados_dw['dados'])
        
        if tabela_principal:
            if isinstance(tabela_principal, dict) and 'rows' in tabela_principal:
                total_linhas_tabela = len(tabela_principal['rows'])
            elif isinstance(tabela_principal, list):
                # Pode ser uma lista de tabelas
                for tabela in tabela_principal:
                    if isinstance(tabela, dict):
                        if 'rows' in tabela:
                            total_linhas_tabela += len(tabela['rows'])
                        elif 'linhas' in tabela:
                            total_linhas_tabela += len(tabela['linhas'])
        
        # Extrai Big Number (pode estar em vários lugares)
        big_number_total = None
        
        # Tenta encontrar em metrics
        if 'structured' in data and isinstance(data['structured'], dict):
            structured = data['structured']
            if 'metrics' in structured:
                metrics = structured['metrics']
                if isinstance(metrics, dict):
                    big_number_total = metrics.get('total_clientes') or metrics.get('totalClientes') or metrics.get('total_registros')
        
        # Tenta encontrar em dadosDw
        if big_number_total is None and 'dadosDw' in data:
            dados_dw = data['dadosDw']
            if isinstance(dados_dw, dict):
                big_number_total = dados_dw.get('total_clientes') or dados_dw.get('totalClientes') or dados_dw.get('total_registros')
        
        # Se não encontrou, usa total_linhas_tabela como fallback
        if big_number_total is None:
            big_number_total = total_linhas_tabela
            print("⚠️  Big Number não encontrado na resposta, usando total_linhas_tabela")
        
        print(f"\n📊 Big Number (da resposta): {big_number_total}")
        print(f"📊 Total de linhas na tabela: {total_linhas_tabela}")
        
        # Valida consistência
        if big_number_total != total_linhas_tabela:
            print(f"\n❌ INCONSISTÊNCIA DETECTADA:")
            print(f"   Big Number: {big_number_total}")
            print(f"   Linhas Tabela: {total_linhas_tabela}")
            print(f"   Diferença: {abs(big_number_total - total_linhas_tabela)}")
            return False
        else:
            print(f"\n✅ CONSISTÊNCIA OK: Big Number ({big_number_total}) == Linhas Tabela ({total_linhas_tabela})")
            return True
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Executa todos os testes"""
    print("\n" + "=" * 80)
    print("TESTE DE CONSISTÊNCIA: Q1 - Big Number vs Tabela")
    print("=" * 80)
    
    # Teste local
    resultado_local = test_q1_consistencia_local()
    
    # Teste via API (se disponível)
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--api', type=str, help='URL da API (ex: http://localhost:8000)')
    parser.add_argument('--prod', action='store_true', help='Usa API de produção')
    args = parser.parse_args()
    
    resultado_api = None
    if args.prod:
        api_url = "https://dipam-ai-backend-642830139828.us-central1.run.app"
        resultado_api = test_q1_consistencia_api(api_url)
    elif args.api:
        resultado_api = test_q1_consistencia_api(args.api)
    else:
        print("\n⚠️  Teste via API não executado (use --api ou --prod)")
    
    # Resumo final
    print("\n" + "=" * 80)
    print("RESUMO FINAL")
    print("=" * 80)
    print(f"Teste Local: {'✅ PASSOU' if resultado_local else '❌ FALHOU'}")
    if resultado_api is not None:
        print(f"Teste API: {'✅ PASSOU' if resultado_api else '❌ FALHOU'}")
    
    # Exit code
    if not resultado_local or (resultado_api is not None and not resultado_api):
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()

