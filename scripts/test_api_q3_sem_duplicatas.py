#!/usr/bin/env python3
"""
Script para testar se a query Q3 retorna apenas 1 linha por indústria (sem duplicatas).

Q3: Indústrias com mais vendedores fora da meta
Identificador único: industria
"""

import requests
import json
import sys
import os
import argparse
from collections import Counter

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_q3_sem_duplicatas(environment="local"):
    """Testa se a query Q3 retorna apenas 1 linha por indústria."""
    
    # Define URL base conforme ambiente
    if environment == "prod":
        base_url = "https://dipam-ai-backend-6arhlm3mha-uc.a.run.app"
    elif environment == "local":
        base_url = "http://localhost:8000"
    else:
        base_url = os.getenv("API_URL", "http://localhost:8000")
    
    url = f"{base_url}/ask"
    
    # Pergunta Q3: Indústrias com mais vendedores fora da meta
    pergunta = "Quais indústrias têm mais vendedores fora da meta em outubro de 2025?"
    
    payload = {
        "pergunta": pergunta,
        "papel": "diretor"
    }
    
    print("=" * 80)
    print("TESTE: Query Q3 - Verificação de Duplicatas")
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
        
        # Encontra índice da coluna Indústria
        idx_industria = None
        for i, col in enumerate(colunas):
            col_lower = col.lower()
            if col_lower in ["industria", "indústria", "industria_nome"]:
                idx_industria = i
                break
        
        if idx_industria is None:
            print("\n❌ ERRO: Coluna 'Indústria' não encontrada")
            return False
        
        print(f"\nÍndice coluna Indústria: {idx_industria}")
        
        # ========================================================================
        # VALIDAÇÃO DE DUPLICATAS
        # ========================================================================
        print("\n" + "=" * 80)
        print("VALIDAÇÃO DE DUPLICATAS")
        print("=" * 80)
        
        # Extrai todos os nomes de indústrias
        industrias = []
        for linha in linhas:
            if idx_industria < len(linha):
                industria = linha[idx_industria]
                industria_str = str(industria).strip() if industria is not None else None
                if industria_str:
                    industrias.append(industria_str)
        
        total_registros = len(linhas)
        industrias_unicas = len(set(industrias))
        
        print(f"\nTotal de registros: {total_registros}")
        print(f"Indústrias únicas: {industrias_unicas}")
        
        # Verifica duplicatas
        if total_registros != industrias_unicas:
            print(f"\n❌ ERRO: Foram encontradas indústrias duplicadas na resposta da Q3.")
            print(f"Total de registros: {total_registros} | Indústrias distintas: {industrias_unicas}")
            
            # Identifica indústrias duplicadas
            contador_industrias = Counter(industrias)
            industrias_duplicadas = {ind: count for ind, count in contador_industrias.items() if count > 1}
            
            if industrias_duplicadas:
                print(f"\nIndústrias duplicadas (primeiras 20):")
                for industria, count in list(industrias_duplicadas.items())[:20]:
                    print(f"  - {industria}: aparece {count} vez(es)")
                if len(industrias_duplicadas) > 20:
                    print(f"  ... e mais {len(industrias_duplicadas) - 20} indústria(s) duplicada(s)")
            
            print("\n❌ FALHA: A query Q3 não deve retornar indústrias duplicadas!")
            return False
        else:
            print(f"\n✅ Validação Q3: nenhuma indústria duplicada. Registros = {total_registros}, Indústrias únicas = {industrias_unicas}.")
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
    parser = argparse.ArgumentParser(description="Testa query Q3 sem duplicatas")
    parser.add_argument("--local", action="store_true", help="Testa em localhost:8000")
    parser.add_argument("--prod", action="store_true", help="Testa em produção")
    
    args = parser.parse_args()
    
    if args.prod:
        env = "prod"
    elif args.local:
        env = "local"
    else:
        env = "auto"
    
    success = test_q3_sem_duplicatas(environment=env)
    sys.exit(0 if success else 1)

