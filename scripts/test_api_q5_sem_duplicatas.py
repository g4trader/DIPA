#!/usr/bin/env python3
"""
Script para testar se a query Q5 retorna apenas 1 linha por produto (sem duplicatas).

Q5: Itens com baixa média mensal
Identificador único: produto_id
"""

import requests
import json
import sys
import os
import argparse
from collections import Counter

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_q5_sem_duplicatas(environment="local"):
    """Testa se a query Q5 retorna apenas 1 linha por produto."""
    
    # Define URL base conforme ambiente
    if environment == "prod":
        base_url = "https://dipam-ai-backend-6arhlm3mha-uc.a.run.app"
    elif environment == "local":
        base_url = "http://localhost:8000"
    else:
        base_url = os.getenv("API_URL", "http://localhost:8000")
    
    url = f"{base_url}/ask"
    
    # Pergunta Q5: Itens com baixa média mensal
    pergunta = "Quais itens têm média mensal de vendas menor que 10 caixas nos últimos 12 meses?"
    
    payload = {
        "pergunta": pergunta,
        "papel": "diretor"
    }
    
    print("=" * 80)
    print("TESTE: Query Q5 - Verificação de Duplicatas")
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
        
        # Encontra índice da coluna Produto ID (pode ser produto_id, sku, ou descricao)
        idx_produto_id = None
        for i, col in enumerate(colunas):
            col_lower = col.lower()
            if col_lower in ["produto id", "produto_id", "id", "sku", "codigo"]:
                idx_produto_id = i
                break
        
        if idx_produto_id is None:
            print("\n❌ ERRO: Coluna 'Produto ID' não encontrada")
            return False
        
        print(f"\nÍndice coluna Produto ID: {idx_produto_id}")
        
        # ========================================================================
        # VALIDAÇÃO DE DUPLICATAS
        # ========================================================================
        print("\n" + "=" * 80)
        print("VALIDAÇÃO DE DUPLICATAS")
        print("=" * 80)
        
        # Extrai todos os IDs de produtos
        produto_ids = []
        for linha in linhas:
            if idx_produto_id < len(linha):
                produto_id = linha[idx_produto_id]
                produto_id_str = str(produto_id).strip() if produto_id is not None else None
                if produto_id_str:
                    produto_ids.append(produto_id_str)
        
        total_registros = len(linhas)
        produtos_unicos = len(set(produto_ids))
        
        print(f"\nTotal de registros: {total_registros}")
        print(f"Produtos únicos: {produtos_unicos}")
        
        # Verifica duplicatas
        if total_registros != produtos_unicos:
            print(f"\n❌ ERRO: Foram encontrados produtos duplicados na resposta da Q5.")
            print(f"Total de registros: {total_registros} | Produtos distintos: {produtos_unicos}")
            
            # Identifica produtos duplicados
            contador_produtos = Counter(produto_ids)
            produtos_duplicados = {prod: count for prod, count in contador_produtos.items() if count > 1}
            
            if produtos_duplicados:
                print(f"\nProdutos duplicados (primeiros 20):")
                for produto_id, count in list(produtos_duplicados.items())[:20]:
                    print(f"  - Produto ID {produto_id}: aparece {count} vez(es)")
                if len(produtos_duplicados) > 20:
                    print(f"  ... e mais {len(produtos_duplicados) - 20} produto(s) duplicado(s)")
            
            print("\n❌ FALHA: A query Q5 não deve retornar produtos duplicados!")
            return False
        else:
            print(f"\n✅ Validação Q5: nenhum produto duplicado. Registros = {total_registros}, Produtos únicos = {produtos_unicos}.")
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
    parser = argparse.ArgumentParser(description="Testa query Q5 sem duplicatas")
    parser.add_argument("--local", action="store_true", help="Testa em localhost:8000")
    parser.add_argument("--prod", action="store_true", help="Testa em produção")
    
    args = parser.parse_args()
    
    if args.prod:
        env = "prod"
    elif args.local:
        env = "local"
    else:
        env = "auto"
    
    success = test_q5_sem_duplicatas(environment=env)
    sys.exit(0 if success else 1)

