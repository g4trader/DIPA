#!/usr/bin/env python3
"""
Script para testar o endpoint /ask com a pergunta Q1 e validar
que os campos Vendedor e Supervisor estão preenchidos corretamente.

Uso:
    python scripts/test_api_ask_q1.py --local    # Testa localhost:8000
    python scripts/test_api_ask_q1.py --prod     # Testa produção
    python scripts/test_api_ask_q1.py            # Usa API_URL env var
"""

import requests
import json
import sys
import os
import argparse

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_ask_endpoint(environment="local"):
    """Testa o endpoint /ask com a pergunta Q1."""
    
    # Define URL base conforme ambiente
    if environment == "prod":
        base_url = "https://dipam-ai-backend-6arhlm3mha-uc.a.run.app"
    elif environment == "local":
        base_url = "http://localhost:8000"
    else:
        base_url = os.getenv("API_URL", "http://localhost:8000")
    
    url = f"{base_url}/ask"
    
    # Pergunta Q1
    pergunta = "Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?"
    
    payload = {
        "pergunta": pergunta,
        "papel": "diretor"
    }
    
    print("=" * 80)
    print("TESTE: Endpoint /ask - Pergunta Q1")
    print("=" * 80)
    print(f"\nURL: {url}")
    print(f"Pergunta: {pergunta}\n")
    
    try:
        # Faz a requisição
        response = requests.post(url, json=payload, timeout=60)
        
        print(f"Status Code: {response.status_code}\n")
        
        if response.status_code != 200:
            print(f"❌ ERRO: Status {response.status_code}")
            print(f"Resposta: {response.text}")
            return False
        
        # Parse da resposta
        data = response.json()
        
        # Salva resposta completa para análise
        with open("test_ask_response.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("✅ Resposta salva em: test_ask_response.json\n")
        
        # Valida estrutura
        print("=" * 80)
        print("VALIDAÇÃO DOS DADOS")
        print("=" * 80)
        
        # Verifica intent
        intent = data.get("intent", "")
        intent_label = data.get("intentLabel", "")
        print(f"\nIntent: {intent}")
        print(f"Intent Label: {intent_label}")
        
        # Verifica structured response
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
        
        print(f"\nColunas: {colunas}")
        print(f"Total de linhas: {len(linhas)}")
        
        # Encontra índices das colunas
        idx_cliente_id = None
        idx_vendedor = None
        idx_supervisor = None
        
        for i, col in enumerate(colunas):
            col_lower = col.lower()
            if col_lower in ["cliente id", "cliente_id", "id", "codigo"]:
                idx_cliente_id = i
            elif col_lower in ["vendedor", "vendedor_nome"]:
                idx_vendedor = i
            elif col_lower in ["supervisor", "supervisor_nome"]:
                idx_supervisor = i
        
        if idx_cliente_id is None:
            print("\n❌ ERRO: Coluna 'Cliente ID' não encontrada")
            return False
        
        if idx_vendedor is None:
            print("\n❌ ERRO: Coluna 'Vendedor' não encontrada")
            return False
        
        if idx_supervisor is None:
            print("\n❌ ERRO: Coluna 'Supervisor' não encontrada")
            return False
        
        print(f"\nÍndice coluna Cliente ID: {idx_cliente_id}")
        print(f"Índice coluna Vendedor: {idx_vendedor}")
        print(f"Índice coluna Supervisor: {idx_supervisor}")
        
        # ========================================================================
        # VALIDAÇÃO DE DUPLICATAS (CRÍTICO)
        # ========================================================================
        print("\n" + "=" * 80)
        print("VALIDAÇÃO DE DUPLICATAS")
        print("=" * 80)
        
        # Extrai todos os IDs de clientes
        cliente_ids = []
        for linha in linhas:
            if idx_cliente_id < len(linha):
                cliente_id = linha[idx_cliente_id]
                # Converte para string para comparação consistente
                cliente_id_str = str(cliente_id).strip() if cliente_id is not None else None
                if cliente_id_str:
                    cliente_ids.append(cliente_id_str)
        
        total_registros = len(linhas)
        clientes_unicos = len(set(cliente_ids))
        
        print(f"\nTotal de registros: {total_registros}")
        print(f"Clientes únicos: {clientes_unicos}")
        
        # Verifica duplicatas
        if total_registros != clientes_unicos:
            print(f"\n❌ ERRO: Foram encontrados clientes duplicados na resposta da Q1.")
            print(f"Total de registros: {total_registros} | Clientes distintos: {clientes_unicos}")
            
            # Identifica IDs duplicados
            from collections import Counter
            contador_ids = Counter(cliente_ids)
            ids_duplicados = {id_val: count for id_val, count in contador_ids.items() if count > 1}
            
            if ids_duplicados:
                print(f"\nIDs de clientes duplicados (primeiros 20):")
                for cliente_id, count in list(ids_duplicados.items())[:20]:
                    print(f"  - Cliente ID {cliente_id}: aparece {count} vez(es)")
                if len(ids_duplicados) > 20:
                    print(f"  ... e mais {len(ids_duplicados) - 20} cliente(s) duplicado(s)")
            
            print("\n❌ FALHA: A query Q1 não deve retornar clientes duplicados!")
            return False
        else:
            print(f"\n✅ Validação Q1: nenhum cliente duplicado. Registros = {total_registros}, Clientes únicos = {clientes_unicos}.")
        
        # Valida dados (total_registros já foi definido acima)
        com_vendedor = 0
        com_supervisor = 0
        vazios_vendedor = []
        vazios_supervisor = []
        
        print("\n" + "=" * 80)
        print("ANÁLISE DOS REGISTROS")
        print("=" * 80)
        
        # Analisa primeiros 10 registros
        print("\nPrimeiros 10 registros:")
        for i, linha in enumerate(linhas[:10]):
            vendedor = linha[idx_vendedor] if idx_vendedor < len(linha) else ""
            supervisor = linha[idx_supervisor] if idx_supervisor < len(linha) else ""
            
            vendedor_preenchido = vendedor and str(vendedor).strip() and str(vendedor).strip() != "—"
            supervisor_preenchido = supervisor and str(supervisor).strip() and str(supervisor).strip() != "—"
            
            if vendedor_preenchido:
                com_vendedor += 1
            else:
                vazios_vendedor.append(i + 1)
            
            if supervisor_preenchido:
                com_supervisor += 1
            else:
                vazios_supervisor.append(i + 1)
            
            print(f"\n  Registro {i + 1}:")
            print(f"    Cliente ID: {linha[0] if len(linha) > 0 else 'N/A'}")
            print(f"    Nome: {linha[1] if len(linha) > 1 else 'N/A'}")
            print(f"    Vendedor: {vendedor} {'✅' if vendedor_preenchido else '❌'}")
            print(f"    Supervisor: {supervisor} {'✅' if supervisor_preenchido else '❌'}")
        
        # Analisa todos os registros
        print("\n" + "=" * 80)
        print("ESTATÍSTICAS COMPLETAS")
        print("=" * 80)
        
        for linha in linhas:
            vendedor = linha[idx_vendedor] if idx_vendedor < len(linha) else ""
            supervisor = linha[idx_supervisor] if idx_supervisor < len(linha) else ""
            
            vendedor_preenchido = vendedor and str(vendedor).strip() and str(vendedor).strip() != "—"
            supervisor_preenchido = supervisor and str(supervisor).strip() and str(supervisor).strip() != "—"
            
            if vendedor_preenchido:
                com_vendedor += 1
            else:
                vazios_vendedor.append(len(vazios_vendedor) + 1)
            
            if supervisor_preenchido:
                com_supervisor += 1
            else:
                vazios_supervisor.append(len(vazios_supervisor) + 1)
        
        pct_vendedor = (com_vendedor / total_registros * 100) if total_registros > 0 else 0
        pct_supervisor = (com_supervisor / total_registros * 100) if total_registros > 0 else 0
        
        print(f"\nTotal de registros: {total_registros}")
        print(f"Com vendedor: {com_vendedor} ({pct_vendedor:.1f}%)")
        print(f"Com supervisor: {com_supervisor} ({pct_supervisor:.1f}%)")
        print(f"Sem vendedor: {total_registros - com_vendedor} ({100 - pct_vendedor:.1f}%)")
        print(f"Sem supervisor: {total_registros - com_supervisor} ({100 - pct_supervisor:.1f}%)")
        
        # Validação final
        print("\n" + "=" * 80)
        print("RESULTADO FINAL")
        print("=" * 80)
        
        sucesso = True
        
        if pct_vendedor >= 85:
            print(f"✅ SUCESSO: {pct_vendedor:.1f}% dos clientes têm vendedor (meta: ≥85%)")
        else:
            print(f"❌ FALHA: {pct_vendedor:.1f}% dos clientes têm vendedor (meta: ≥85%)")
            sucesso = False
        
        if pct_supervisor >= 70:
            print(f"✅ SUCESSO: {pct_supervisor:.1f}% dos clientes têm supervisor (meta: ≥70%)")
        else:
            print(f"❌ FALHA: {pct_supervisor:.1f}% dos clientes têm supervisor (meta: ≥70%)")
            sucesso = False
        
        if len(vazios_vendedor) > 0 and len(vazios_vendedor) <= 10:
            print(f"\n⚠️  Registros sem vendedor (primeiros 10): {vazios_vendedor[:10]}")
        
        if len(vazios_supervisor) > 0 and len(vazios_supervisor) <= 10:
            print(f"⚠️  Registros sem supervisor (primeiros 10): {vazios_supervisor[:10]}")
        
        return sucesso
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ ERRO na requisição: {str(e)}")
        return False
    except Exception as e:
        print(f"\n❌ ERRO inesperado: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Testa endpoint /ask com pergunta Q1")
    parser.add_argument("--local", action="store_true", help="Testa em localhost:8000")
    parser.add_argument("--prod", action="store_true", help="Testa em produção")
    
    args = parser.parse_args()
    
    if args.prod:
        env = "prod"
    elif args.local:
        env = "local"
    else:
        env = "auto"
    
    success = test_ask_endpoint(environment=env)
    sys.exit(0 if success else 1)

