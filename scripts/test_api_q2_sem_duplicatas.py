#!/usr/bin/env python3
"""
Script para testar se a query Q2 retorna apenas 1 linha por cliente (sem duplicatas).

Q2: Clientes com queda de faturamento ano contra ano
Identificador único: cliente_id
"""

import requests
import json
import sys
import os
import argparse
from collections import Counter

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_q2_sem_duplicatas(environment="local"):
    """Testa se a query Q2 retorna apenas 1 linha por cliente."""
    
    # Define URL base conforme ambiente
    if environment == "prod":
        base_url = "https://dipam-ai-backend-6arhlm3mha-uc.a.run.app"
    elif environment == "local":
        base_url = "http://localhost:8000"
    else:
        base_url = os.getenv("API_URL", "http://localhost:8000")
    
    url = f"{base_url}/ask"
    
    # Pergunta Q2: Clientes com queda de faturamento
    pergunta = "Quais clientes tiveram queda de faturamento em 2025 comparado a 2024?"
    
    payload = {
        "pergunta": pergunta,
        "papel": "diretor"
    }
    
    print("=" * 80)
    print("TESTE: Query Q2 - Verificação de Duplicatas")
    print("=" * 80)
    print(f"\nURL: {url}")
    print(f"Pergunta: {pergunta}\n")
    
    try:
        # Faz a requisição
        response = requests.post(url, json=payload, timeout=120)
        
        print(f"Status Code: {response.status_code}\n")
        
        if response.status_code != 200:
            print(f"❌ ERRO: Status {response.status_code}")
            print(f"Resposta: {response.text}")
            return False
        
        # Parse da resposta
        data = response.json()
        
        # Extrai tabela principal
        structured = data.get("structured", {})
        json_tecnico = structured.get("jsonTecnico", {})
        tabela_principal = json_tecnico.get("tabela_principal", [])
        
        if not tabela_principal:
            print("\n❌ ERRO: tabela_principal não encontrada na resposta")
            return False
        
        # Pega a primeira tabela
        tabela = tabela_principal[0] if isinstance(tabela_principal, list) else tabela_principal
        colunas = tabela.get("colunas", [])
        linhas = tabela.get("linhas", [])
        
        print(f"Colunas: {colunas}")
        print(f"Total de linhas: {len(linhas)}")
        
        # Encontra índice da coluna Cliente ID
        idx_cliente_id = None
        for i, col in enumerate(colunas):
            col_lower = col.lower()
            if col_lower in ["cliente id", "cliente_id", "id", "codigo"]:
                idx_cliente_id = i
                break
        
        if idx_cliente_id is None:
            print("\n❌ ERRO: Coluna 'Cliente ID' não encontrada")
            return False
        
        print(f"\nÍndice coluna Cliente ID: {idx_cliente_id}")
        
        # ========================================================================
        # VALIDAÇÃO DE DUPLICATAS
        # ========================================================================
        print("\n" + "=" * 80)
        print("VALIDAÇÃO DE DUPLICATAS")
        print("=" * 80)
        
        # Extrai todos os IDs de clientes
        cliente_ids = []
        for linha in linhas:
            if idx_cliente_id < len(linha):
                cliente_id = linha[idx_cliente_id]
                cliente_id_str = str(cliente_id).strip() if cliente_id is not None else None
                if cliente_id_str:
                    cliente_ids.append(cliente_id_str)
        
        total_registros = len(linhas)
        clientes_unicos = len(set(cliente_ids))
        
        print(f"\nTotal de registros: {total_registros}")
        print(f"Clientes únicos: {clientes_unicos}")
        
        # Verifica duplicatas
        if total_registros != clientes_unicos:
            print(f"\n❌ ERRO: Foram encontrados clientes duplicados na resposta da Q2.")
            print(f"Total de registros: {total_registros} | Clientes distintos: {clientes_unicos}")
            
            # Identifica IDs duplicados
            contador_ids = Counter(cliente_ids)
            ids_duplicados = {id_val: count for id_val, count in contador_ids.items() if count > 1}
            
            if ids_duplicados:
                print(f"\nIDs de clientes duplicados (primeiros 20):")
                for cliente_id, count in list(ids_duplicados.items())[:20]:
                    print(f"  - Cliente ID {cliente_id}: aparece {count} vez(es)")
                if len(ids_duplicados) > 20:
                    print(f"  ... e mais {len(ids_duplicados) - 20} cliente(s) duplicado(s)")
            
            print("\n❌ FALHA: A query Q2 não deve retornar clientes duplicados!")
            return False
        else:
            print(f"\n✅ Validação Q2: nenhum cliente duplicado. Registros = {total_registros}, Clientes únicos = {clientes_unicos}.")
            return True
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ ERRO na requisição: {str(e)}")
        return False
    except Exception as e:
        print(f"\n❌ ERRO inesperado: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Testa query Q2 sem duplicatas")
    parser.add_argument("--local", action="store_true", help="Testa em localhost:8000")
    parser.add_argument("--prod", action="store_true", help="Testa em produção")
    
    args = parser.parse_args()
    
    if args.prod:
        env = "prod"
    elif args.local:
        env = "local"
    else:
        env = "auto"
    
    success = test_q2_sem_duplicatas(environment=env)
    sys.exit(0 if success else 1)

