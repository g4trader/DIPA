#!/usr/bin/env python3
"""
Script para testar performance e cache da Q1 em produção.

Executa duas chamadas consecutivas e valida:
- Primeira chamada (sem cache): 12-21 segundos
- Segunda chamada (cache hit): < 100 ms
- Headers de compressão gzip
- Cache hit na segunda execução
"""

import requests
import json
import sys
import os
import time
import argparse
from datetime import datetime

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROD_URL = "https://dipam-ai-backend-642830139828.us-central1.run.app"
Q1_PERGUNTA = "Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?"

def test_q1_performance(environment="prod", verbose=True):
    """Testa performance e cache da Q1."""
    
    base_url = PROD_URL if environment == "prod" else "http://localhost:8000"
    url = f"{base_url}/ask"
    
    payload = {
        "pergunta": Q1_PERGUNTA,
        "papel": "diretor"
    }
    
    results = {
        "primeira_chamada": {},
        "segunda_chamada": {},
        "comparacao": {}
    }
    
    print("=" * 80)
    print("TESTE DE PERFORMANCE E CACHE - Q1")
    print("=" * 80)
    print(f"\nURL: {url}")
    print(f"Pergunta: {Q1_PERGUNTA}\n")
    
    # PRIMEIRA CHAMADA (sem cache)
    print("=" * 80)
    print("PRIMEIRA CHAMADA (sem cache)")
    print("=" * 80)
    
    try:
        start_time = time.time()
        response = requests.post(
            url,
            json=payload,
            timeout=60,
            headers={"Accept-Encoding": "gzip"}
        )
        elapsed_time = time.time() - start_time
        
        results["primeira_chamada"] = {
            "status_code": response.status_code,
            "elapsed_time": elapsed_time,
            "size_bytes": len(response.content),
            "headers": dict(response.headers),
            "has_gzip": "gzip" in response.headers.get("Content-Encoding", "").lower(),
            "cache_control": response.headers.get("Cache-Control", ""),
            "timestamp": datetime.now().isoformat()
        }
        
        if response.status_code == 200:
            data = response.json()
            structured = data.get("structured", {})
            metrics = structured.get("metrics", {})
            
            results["primeira_chamada"]["total_clientes"] = metrics.get("total_clientes", 0)
            results["primeira_chamada"]["cache_hit"] = False
            
            print(f"✅ Status: {response.status_code}")
            print(f"⏱️  Tempo: {elapsed_time:.2f}s")
            print(f"📦 Tamanho: {len(response.content):,} bytes")
            print(f"🗜️  Gzip: {'✅' if results['primeira_chamada']['has_gzip'] else '❌'}")
            print(f"👥 Total Clientes: {results['primeira_chamada']['total_clientes']}")
            print(f"💾 Cache Hit: {results['primeira_chamada']['cache_hit']}")
        else:
            print(f"❌ Erro: Status {response.status_code}")
            print(f"Resposta: {response.text[:500]}")
            return results
            
    except Exception as e:
        print(f"❌ Erro na primeira chamada: {e}")
        return results
    
    # Aguarda 2 segundos antes da segunda chamada
    print("\n⏳ Aguardando 2 segundos antes da segunda chamada...\n")
    time.sleep(2)
    
    # SEGUNDA CHAMADA (com cache)
    print("=" * 80)
    print("SEGUNDA CHAMADA (com cache)")
    print("=" * 80)
    
    try:
        start_time = time.time()
        response = requests.post(
            url,
            json=payload,
            timeout=10,
            headers={"Accept-Encoding": "gzip"}
        )
        elapsed_time = time.time() - start_time
        
        results["segunda_chamada"] = {
            "status_code": response.status_code,
            "elapsed_time": elapsed_time,
            "size_bytes": len(response.content),
            "headers": dict(response.headers),
            "has_gzip": "gzip" in response.headers.get("Content-Encoding", "").lower(),
            "cache_control": response.headers.get("Cache-Control", ""),
            "timestamp": datetime.now().isoformat()
        }
        
        if response.status_code == 200:
            data = response.json()
            structured = data.get("structured", {})
            metrics = structured.get("metrics", {})
            
            results["segunda_chamada"]["total_clientes"] = metrics.get("total_clientes", 0)
            # Verifica se há indicação de cache hit na resposta
            results["segunda_chamada"]["cache_hit"] = "cache" in str(data).lower() or elapsed_time < 0.5
            
            print(f"✅ Status: {response.status_code}")
            print(f"⏱️  Tempo: {elapsed_time:.3f}s ({elapsed_time*1000:.0f}ms)")
            print(f"📦 Tamanho: {len(response.content):,} bytes")
            print(f"🗜️  Gzip: {'✅' if results['segunda_chamada']['has_gzip'] else '❌'}")
            print(f"👥 Total Clientes: {results['segunda_chamada']['total_clientes']}")
            print(f"💾 Cache Hit: {'✅' if results['segunda_chamada']['cache_hit'] else '❌'}")
        else:
            print(f"❌ Erro: Status {response.status_code}")
            print(f"Resposta: {response.text[:500]}")
            
    except Exception as e:
        print(f"❌ Erro na segunda chamada: {e}")
    
    # COMPARAÇÃO
    print("\n" + "=" * 80)
    print("COMPARAÇÃO")
    print("=" * 80)
    
    if results["primeira_chamada"].get("status_code") == 200 and results["segunda_chamada"].get("status_code") == 200:
        time_diff = results["segunda_chamada"]["elapsed_time"] - results["primeira_chamada"]["elapsed_time"]
        speedup = results["primeira_chamada"]["elapsed_time"] / results["segunda_chamada"]["elapsed_time"] if results["segunda_chamada"]["elapsed_time"] > 0 else 0
        
        results["comparacao"] = {
            "time_diff": time_diff,
            "speedup": speedup,
            "primeira_ok": 12 <= results["primeira_chamada"]["elapsed_time"] <= 21,
            "segunda_ok": results["segunda_chamada"]["elapsed_time"] < 0.1,
            "gzip_ok": results["primeira_chamada"]["has_gzip"] and results["segunda_chamada"]["has_gzip"],
            "cache_ok": results["segunda_chamada"]["cache_hit"]
        }
        
        print(f"⏱️  Diferença de tempo: {time_diff:.3f}s")
        print(f"🚀 Speedup: {speedup:.1f}x")
        print(f"✅ Primeira chamada OK (12-21s): {'✅' if results['comparacao']['primeira_ok'] else '❌'} ({results['primeira_chamada']['elapsed_time']:.2f}s)")
        print(f"✅ Segunda chamada OK (<100ms): {'✅' if results['comparacao']['segunda_ok'] else '❌'} ({results['segunda_chamada']['elapsed_time']*1000:.0f}ms)")
        print(f"✅ Gzip ativo: {'✅' if results['comparacao']['gzip_ok'] else '❌'}")
        print(f"✅ Cache funcionando: {'✅' if results['comparacao']['cache_ok'] else '❌'}")
    
    # Salva resultados
    output_file = "test_q1_perf_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Resultados salvos em: {output_file}")
    
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Testa performance e cache da Q1")
    parser.add_argument("--prod", action="store_true", help="Testa produção")
    parser.add_argument("--local", action="store_true", help="Testa local")
    
    args = parser.parse_args()
    
    env = "prod" if args.prod else ("local" if args.local else "prod")
    test_q1_performance(env)

