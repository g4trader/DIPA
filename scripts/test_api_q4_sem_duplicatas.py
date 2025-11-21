#!/usr/bin/env python3
"""
Script para testar se a query Q4 retorna apenas 1 linha por rota (sem duplicatas).

Q4: Rotas com positivação de indústria
Identificador único: rota_id
"""

import requests
import json
import sys
import os
import argparse
from collections import Counter

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_q4_sem_duplicatas(environment="local"):
    """Testa se a query Q4 retorna apenas 1 linha por rota."""
    
    # Define URL base conforme ambiente
    if environment == "prod":
        base_url = "https://dipam-ai-backend-6arhlm3mha-uc.a.run.app"
    elif environment == "local":
        base_url = "http://localhost:8000"
    else:
        base_url = os.getenv("API_URL", "http://localhost:8000")
    
    url = f"{base_url}/ask"
    
    # Pergunta Q4: Rotas com positivação de indústria
    pergunta = "Quais rotas têm melhor desempenho em positivação de clientes da indústria Mars no período de janeiro a outubro de 2025?"
    
    payload = {
        "pergunta": pergunta,
        "papel": "diretor"
    }
    
    print("=" * 80)
    print("TESTE: Query Q4 - Verificação de Duplicatas")
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
        
        # Encontra índice da coluna Rota ID
        idx_rota_id = None
        for i, col in enumerate(colunas):
            col_lower = col.lower()
            if col_lower in ["rota", "rota_id", "rota rca", "vendedor", "rota_nome"]:
                idx_rota_id = i
                break
        
        if idx_rota_id is None:
            print("\n❌ ERRO: Coluna 'Rota ID' não encontrada")
            return False
        
        print(f"\nÍndice coluna Rota ID: {idx_rota_id}")
        
        # ========================================================================
        # VALIDAÇÃO DE DUPLICATAS
        # ========================================================================
        print("\n" + "=" * 80)
        print("VALIDAÇÃO DE DUPLICATAS")
        print("=" * 80)
        
        # Extrai todos os IDs de rotas
        rota_ids = []
        for linha in linhas:
            if idx_rota_id < len(linha):
                rota_id = linha[idx_rota_id]
                rota_id_str = str(rota_id).strip() if rota_id is not None else None
                if rota_id_str:
                    rota_ids.append(rota_id_str)
        
        total_registros = len(linhas)
        rotas_unicas = len(set(rota_ids))
        
        print(f"\nTotal de registros: {total_registros}")
        print(f"Rotas únicas: {rotas_unicas}")
        
        # Verifica duplicatas
        if total_registros != rotas_unicas:
            print(f"\n❌ ERRO: Foram encontradas rotas duplicadas na resposta da Q4.")
            print(f"Total de registros: {total_registros} | Rotas distintas: {rotas_unicas}")
            
            # Identifica rotas duplicadas
            contador_rotas = Counter(rota_ids)
            rotas_duplicadas = {rota: count for rota, count in contador_rotas.items() if count > 1}
            
            if rotas_duplicadas:
                print(f"\nRotas duplicadas (primeiras 20):")
                for rota_id, count in list(rotas_duplicadas.items())[:20]:
                    print(f"  - Rota {rota_id}: aparece {count} vez(es)")
                if len(rotas_duplicadas) > 20:
                    print(f"  ... e mais {len(rotas_duplicadas) - 20} rota(s) duplicada(s)")
            
            print("\n❌ FALHA: A query Q4 não deve retornar rotas duplicadas!")
            return False
        else:
            print(f"\n✅ Validação Q4: nenhuma rota duplicada. Registros = {total_registros}, Rotas únicas = {rotas_unicas}.")
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
    parser = argparse.ArgumentParser(description="Testa query Q4 sem duplicatas")
    parser.add_argument("--local", action="store_true", help="Testa em localhost:8000")
    parser.add_argument("--prod", action="store_true", help="Testa em produção")
    
    args = parser.parse_args()
    
    if args.prod:
        env = "prod"
    elif args.local:
        env = "local"
    else:
        env = "auto"
    
    success = test_q4_sem_duplicatas(environment=env)
    sys.exit(0 if success else 1)

