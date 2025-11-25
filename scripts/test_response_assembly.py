#!/usr/bin/env python3
"""
Script para testar montagem e serialização de resposta Q1.

Simula apenas a montagem JSON para identificar se há problema de serialização.
"""

import json
import sys
import os
import time
from pathlib import Path

# Adiciona o diretório raiz ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

def test_json_serialization(data, use_orjson=False):
    """Testa serialização JSON com json padrão ou orjson."""
    start = time.perf_counter()
    
    if use_orjson:
        try:
            import orjson
            result = orjson.dumps(data, option=orjson.OPT_SERIALIZE_NUMPY)
            duration = (time.perf_counter() - start) * 1000
            return result, duration, len(result)
        except ImportError:
            print("⚠️  orjson não instalado, usando json padrão")
            use_orjson = False
    
    if not use_orjson:
        result = json.dumps(data, ensure_ascii=False, indent=None)
        duration = (time.perf_counter() - start) * 1000
        return result, duration, len(result)


def create_mock_q1_response():
    """Cria resposta mock da Q1 com 932 clientes."""
    # Simula estrutura real da resposta Q1
    dados_clientes = []
    for i in range(932):
        dados_clientes.append({
            "cliente_id": f"CLI{i:04d}",
            "nome": f"Cliente {i}",
            "dias_sem_compra": 60 + (i % 300),
            "vendedor_nome": f"Vendedor {i % 50}",
            "vendedor_codigo": f"VEND{i % 50:03d}",
            "supervisor_nome": f"Supervisor {i % 10}",
            "supervisor_codigo": f"SUP{i % 10:02d}",
            "rota_id": f"ROTA {i % 50:02d}",
            "segmento_venda": f"Segmento {i % 5}"
        })
    
    resposta = {
        "resumo_executivo": "Análise executiva detalhada..." * 10,
        "tabela_principal": [{
            "colunas": ["Cliente ID", "Nome", "Dias sem Compra", "Vendedor", "Supervisor"],
            "linhas": [
                [
                    c["cliente_id"],
                    c["nome"],
                    c["dias_sem_compra"],
                    c["vendedor_nome"],
                    c["supervisor_nome"]
                ]
                for c in dados_clientes
            ]
        }],
        "insights": ["Insight 1", "Insight 2", "Insight 3"] * 10,
        "diagnostico_comercial": {
            "riscos": "Análise de riscos..." * 20,
            "oportunidades": "Análise de oportunidades..." * 20,
            "tendencias": "Análise de tendências..." * 20
        },
        "recomendacoes_estrategicas": {
            "prioridade_1": "Recomendação 1" * 50,
            "prioridade_2": "Recomendação 2" * 50,
            "nao_priorizar": "Recomendação 3" * 50
        },
        "intent_spec": {
            "tipo": "clientes_sem_compra",
            "periodo_inicio": "2024-11-01",
            "periodo_fim": "2025-10-31"
        },
        "dados_dw": {
            "dados": dados_clientes,
            "total": 932,
            "classificacao_faixas": {
                "faixa_61_120": 300,
                "faixa_121_180": 250,
                "faixa_181_300": 200,
                "faixa_mais_300": 182
            }
        },
        "contexto": {
            "performance_metrics": {
                "intent_spec_ms": 500,
                "dw_query_ms": 5000,
                "llm_resposta_ms": 8000,
                "total_ms": 13500
            }
        }
    }
    
    return resposta


def main():
    """Testa montagem e serialização de resposta Q1."""
    print("=" * 80)
    print("TESTE: Montagem e Serialização de Resposta Q1")
    print("=" * 80)
    
    # Cria resposta mock
    print("\n📊 Criando resposta mock (932 clientes)...")
    resposta = create_mock_q1_response()
    
    # Testa serialização com json padrão
    print("\n🔄 Testando serialização com json padrão...")
    try:
        result_json, duration_json, size_json = test_json_serialization(resposta, use_orjson=False)
        print(f"✅ JSON padrão: {duration_json:.2f}ms, tamanho: {size_json:,} bytes ({size_json/1024/1024:.2f} MB)")
    except Exception as e:
        print(f"❌ Erro na serialização JSON: {e}")
        return
    
    # Testa serialização com orjson (se disponível)
    print("\n🔄 Testando serialização com orjson...")
    try:
        result_orjson, duration_orjson, size_orjson = test_json_serialization(resposta, use_orjson=True)
        speedup = duration_json / duration_orjson if duration_orjson > 0 else 0
        print(f"✅ orjson: {duration_orjson:.2f}ms, tamanho: {size_orjson:,} bytes ({size_orjson/1024/1024:.2f} MB)")
        print(f"🚀 Speedup: {speedup:.1f}x")
    except ImportError:
        print("⚠️  orjson não instalado (pip install orjson)")
    except Exception as e:
        print(f"❌ Erro na serialização orjson: {e}")
    
    # Verifica se tamanho excede 32MB (limite HTTP GFE)
    size_mb = size_json / 1024 / 1024
    if size_mb > 32:
        print(f"\n⚠️  AVISO: Resposta excede 32MB ({size_mb:.2f} MB) - pode causar timeout do Google Frontend")
    else:
        print(f"\n✅ Tamanho OK: {size_mb:.2f} MB (limite: 32 MB)")
    
    # Testa compressão gzip
    print("\n🗜️  Testando compressão gzip...")
    try:
        import gzip
        compressed = gzip.compress(result_json.encode('utf-8'))
        compression_ratio = len(compressed) / len(result_json) * 100
        print(f"✅ Gzip: {len(compressed):,} bytes ({len(compressed)/1024/1024:.2f} MB), ratio: {compression_ratio:.1f}%")
    except Exception as e:
        print(f"❌ Erro na compressão: {e}")
    
    print("\n" + "=" * 80)
    print("CONCLUSÃO")
    print("=" * 80)
    print(f"Tempo de serialização (json padrão): {duration_json:.2f}ms")
    print(f"Tamanho da resposta: {size_mb:.2f} MB")
    if size_mb > 32:
        print("⚠️  RECOMENDAÇÃO: Reduzir tamanho da resposta ou usar paginação")
    if duration_json > 1000:
        print("⚠️  RECOMENDAÇÃO: Considerar usar orjson para serialização mais rápida")


if __name__ == "__main__":
    main()

