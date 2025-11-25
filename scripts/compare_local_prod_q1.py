#!/usr/bin/env python3
"""
Script para comparar dados da Q1 entre ambiente local e produção.

Valida:
- Total de clientes (esperado: 932)
- Todos os clientes ativos
- Nenhuma duplicata
- % com vendedor/supervisor ≥ 97%
- Faixas idênticas entre local e produção
"""

import requests
import json
import sys
import os
from pathlib import Path
from collections import Counter

# Adiciona o diretório raiz ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Define SQLITE_PATH para o caminho local se não estiver definido
if not os.getenv("SQLITE_PATH"):
    sqlite_path = Path(project_root) / "data" / "dipam_dw.db"
    os.environ["SQLITE_PATH"] = str(sqlite_path)

from src.dw.connection import init_db, get_db_session
from src.dw.queries import get_clientes_sem_compra_ha_dias

PROD_URL = "https://dipam-ai-backend-642830139828.us-central1.run.app"
Q1_PERGUNTA = "Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?"

def get_local_q1_data():
    """Obtém dados da Q1 do ambiente local."""
    print("📊 Obtendo dados locais...")
    
    try:
        init_db()
        session_gen = get_db_session()
        session = next(session_gen)
        
        # Bypassa cache para garantir dados frescos
        dados = get_clientes_sem_compra_ha_dias(
            session=session,
            dias=60,
            data_referencia="2025-11-30",
            bypass_cache=True
        )
        
        session.close()
        
        return dados
    except Exception as e:
        print(f"❌ Erro ao obter dados locais: {e}")
        return []

def get_prod_q1_data():
    """Obtém dados da Q1 do ambiente de produção."""
    print("🌐 Obtendo dados de produção...")
    
    url = f"{PROD_URL}/ask"
    payload = {
        "pergunta": Q1_PERGUNTA,
        "papel": "diretor"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code != 200:
            print(f"❌ Erro na API: {response.status_code}")
            print(response.text[:500])
            return None
        
        data = response.json()
        structured = data.get("structured", {})
        json_tecnico = structured.get("jsonTecnico", {})
        tabela_principal = json_tecnico.get("tabela_principal", [])
        
        if not tabela_principal:
            print("❌ Tabela principal não encontrada na resposta")
            return None
        
        # Extrai dados da tabela
        tabela = tabela_principal[0] if isinstance(tabela_principal, list) else tabela_principal
        colunas = tabela.get("colunas", [])
        linhas = tabela.get("linhas", [])
        
        # Converte para formato similar ao local
        dados = []
        for linha in linhas:
            registro = {}
            for i, coluna in enumerate(colunas):
                registro[coluna] = linha[i] if i < len(linha) else None
            dados.append(registro)
        
        return dados
    except Exception as e:
        print(f"❌ Erro ao obter dados de produção: {e}")
        return None

def classificar_por_faixa(dias_sem_compra):
    """Classifica dias sem compra em faixas."""
    if dias_sem_compra is None:
        return None
    if 61 <= dias_sem_compra <= 120:
        return "61-120"
    elif 121 <= dias_sem_compra <= 180:
        return "121-180"
    elif 181 <= dias_sem_compra <= 300:
        return "181-300"
    elif dias_sem_compra > 300:
        return ">300"
    return None

def comparar_dados(local_data, prod_data):
    """Compara dados locais e de produção."""
    print("\n" + "=" * 80)
    print("COMPARAÇÃO DE DADOS")
    print("=" * 80)
    
    resultados = {
        "local": {},
        "producao": {},
        "comparacao": {}
    }
    
    # Análise local
    print("\n📊 DADOS LOCAIS:")
    total_local = len(local_data)
    resultados["local"]["total"] = total_local
    
    clientes_ids_local = set()
    vendedor_preenchido_local = 0
    supervisor_preenchido_local = 0
    faixas_local = Counter()
    
    for item in local_data:
        cliente_id = item.get("cliente_id") or item.get("Cliente ID")
        if cliente_id:
            clientes_ids_local.add(str(cliente_id))
        
        if item.get("vendedor_nome") or item.get("Vendedor"):
            vendedor_preenchido_local += 1
        if item.get("supervisor_nome") or item.get("Supervisor"):
            supervisor_preenchido_local += 1
        
        dias = item.get("dias_sem_compra") or item.get("Dias sem compra")
        faixa = classificar_por_faixa(dias)
        if faixa:
            faixas_local[faixa] += 1
    
    resultados["local"]["unicos"] = len(clientes_ids_local)
    resultados["local"]["vendedor_pct"] = (vendedor_preenchido_local / total_local * 100) if total_local > 0 else 0
    resultados["local"]["supervisor_pct"] = (supervisor_preenchido_local / total_local * 100) if total_local > 0 else 0
    resultados["local"]["faixas"] = dict(faixas_local)
    
    print(f"  Total: {total_local}")
    print(f"  Únicos: {len(clientes_ids_local)}")
    print(f"  Vendedor preenchido: {vendedor_preenchido_local} ({resultados['local']['vendedor_pct']:.1f}%)")
    print(f"  Supervisor preenchido: {supervisor_preenchido_local} ({resultados['local']['supervisor_pct']:.1f}%)")
    print(f"  Faixas: {dict(faixas_local)}")
    
    # Análise produção
    if prod_data is None:
        print("\n❌ Não foi possível obter dados de produção")
        return resultados
    
    print("\n🌐 DADOS PRODUÇÃO:")
    total_prod = len(prod_data)
    resultados["producao"]["total"] = total_prod
    
    clientes_ids_prod = set()
    vendedor_preenchido_prod = 0
    supervisor_preenchido_prod = 0
    faixas_prod = Counter()
    
    for item in prod_data:
        cliente_id = item.get("cliente_id") or item.get("Cliente ID") or item.get("Cliente ID")
        if cliente_id:
            clientes_ids_prod.add(str(cliente_id))
        
        vendedor = item.get("vendedor_nome") or item.get("Vendedor") or item.get("Vendedor")
        supervisor = item.get("supervisor_nome") or item.get("Supervisor") or item.get("Supervisor")
        
        if vendedor:
            vendedor_preenchido_prod += 1
        if supervisor:
            supervisor_preenchido_prod += 1
        
        dias = item.get("dias_sem_compra") or item.get("Dias sem compra") or item.get("Dias sem compra")
        if isinstance(dias, str):
            try:
                dias = int(dias.split()[0]) if dias.split()[0].isdigit() else None
            except:
                dias = None
        faixa = classificar_por_faixa(dias)
        if faixa:
            faixas_prod[faixa] += 1
    
    resultados["producao"]["unicos"] = len(clientes_ids_prod)
    resultados["producao"]["vendedor_pct"] = (vendedor_preenchido_prod / total_prod * 100) if total_prod > 0 else 0
    resultados["producao"]["supervisor_pct"] = (supervisor_preenchido_prod / total_prod * 100) if total_prod > 0 else 0
    resultados["producao"]["faixas"] = dict(faixas_prod)
    
    print(f"  Total: {total_prod}")
    print(f"  Únicos: {len(clientes_ids_prod)}")
    print(f"  Vendedor preenchido: {vendedor_preenchido_prod} ({resultados['producao']['vendedor_pct']:.1f}%)")
    print(f"  Supervisor preenchido: {supervisor_preenchido_prod} ({resultados['producao']['supervisor_pct']:.1f}%)")
    print(f"  Faixas: {dict(faixas_prod)}")
    
    # Comparação
    print("\n🔍 COMPARAÇÃO:")
    resultados["comparacao"] = {
        "total_igual": total_local == total_prod,
        "unicos_igual": len(clientes_ids_local) == len(clientes_ids_prod),
        "vendedor_ok": resultados["local"]["vendedor_pct"] >= 97 and resultados["producao"]["vendedor_pct"] >= 97,
        "supervisor_ok": resultados["local"]["supervisor_pct"] >= 97 and resultados["producao"]["supervisor_pct"] >= 97,
        "faixas_iguais": faixas_local == faixas_prod,
        "sem_duplicatas_local": len(clientes_ids_local) == total_local,
        "sem_duplicatas_prod": len(clientes_ids_prod) == total_prod
    }
    
    print(f"  Total igual: {'✅' if resultados['comparacao']['total_igual'] else '❌'} ({total_local} vs {total_prod})")
    print(f"  Únicos igual: {'✅' if resultados['comparacao']['unicos_igual'] else '❌'} ({len(clientes_ids_local)} vs {len(clientes_ids_prod)})")
    print(f"  Vendedor ≥97%: {'✅' if resultados['comparacao']['vendedor_ok'] else '❌'}")
    print(f"  Supervisor ≥97%: {'✅' if resultados['comparacao']['supervisor_ok'] else '❌'}")
    print(f"  Faixas iguais: {'✅' if resultados['comparacao']['faixas_iguais'] else '❌'}")
    print(f"  Sem duplicatas (local): {'✅' if resultados['comparacao']['sem_duplicatas_local'] else '❌'}")
    print(f"  Sem duplicatas (prod): {'✅' if resultados['comparacao']['sem_duplicatas_prod'] else '❌'}")
    
    return resultados


def main():
    """Executa comparação entre local e produção."""
    print("=" * 80)
    print("VALIDAÇÃO: COMPARAÇÃO LOCAL vs PRODUÇÃO - Q1")
    print("=" * 80)
    
    local_data = get_local_q1_data()
    prod_data = get_prod_q1_data()
    
    resultados = comparar_dados(local_data, prod_data)
    
    # Salva resultados
    output_file = "compare_local_prod_q1_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Resultados salvos em: {output_file}")
    
    return resultados


if __name__ == "__main__":
    main()

