#!/usr/bin/env python3
"""
Script de teste manual da API do Agente Comercial.

Este script testa os principais endpoints da API e valida
as respostas do agente comercial.

Uso:
    python -m scripts.manual_test_api
"""

import sys
import json
import requests
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Configuração
API_BASE_URL = "http://localhost:8000"
TIMEOUT = 30


def print_header(title: str):
    """Imprime cabeçalho formatado."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_section(title: str):
    """Imprime seção formatada."""
    print(f"\n{'─' * 80}")
    print(f"  {title}")
    print(f"{'─' * 80}")


def test_health_check() -> bool:
    """Testa endpoint de health check."""
    print_section("Teste: Health Check")
    
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        print(f"✓ Status: {data.get('status')}")
        print(f"✓ Database: {data.get('database')}")
        print(f"✓ Version: {data.get('version')}")
        print(f"✓ Timestamp: {data.get('timestamp')}")
        
        return True
    except Exception as e:
        print(f"✗ Erro: {str(e)}")
        return False


def test_ask_question(pergunta: str, expected_intent: str = None) -> Dict[str, Any]:
    """Testa endpoint /ask com uma pergunta."""
    print_section(f"Pergunta: {pergunta}")
    
    try:
        payload = {"pergunta": pergunta}
        response = requests.post(
            f"{API_BASE_URL}/ask",
            json=payload,
            timeout=TIMEOUT
        )
        response.raise_for_status()
        
        data = response.json()
        
        print(f"✓ Intent detectada: {data.get('intent')}")
        if expected_intent and data.get('intent') != expected_intent:
            print(f"  ⚠ Esperado: {expected_intent}, mas recebeu: {data.get('intent')}")
        
        print(f"✓ Confiança: {data.get('confianca', 0):.2f}")
        print(f"✓ Timestamp: {data.get('timestamp')}")
        
        resposta = data.get('resposta', '')
        print(f"\n📝 Resposta ({len(resposta)} caracteres):")
        print("-" * 80)
        # Mostra primeiras linhas da resposta
        resposta_lines = resposta.split('\n')[:15]
        for line in resposta_lines:
            print(line)
        if len(resposta.split('\n')) > 15:
            print("...")
        print("-" * 80)
        
        contexto = data.get('contexto', {})
        if 'erro' in contexto:
            print(f"⚠ Erro no contexto: {contexto['erro']}")
        else:
            print(f"✓ Contexto válido (keys: {list(contexto.keys())[:5]}...)")
        
        return data
    
    except Exception as e:
        print(f"✗ Erro: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                print(f"  Detalhes: {json.dumps(error_data, indent=2)}")
            except:
                print(f"  Response: {e.response.text[:200]}")
        return {}


def test_preview_vendedor(vendedor: str, mes_ano: str) -> Dict[str, Any]:
    """Testa endpoint /preview/vendedor."""
    print_section(f"Preview: {vendedor} - {mes_ano}")
    
    try:
        url = f"{API_BASE_URL}/preview/vendedor/{vendedor}/{mes_ano}"
        response = requests.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        
        print(f"✓ Vendedor: {data.get('vendedor')}")
        print(f"✓ Mês/Ano: {data.get('mes_ano')}")
        
        dados = data.get('dados', {})
        if 'erro' in dados:
            print(f"⚠ Erro: {dados['erro']}")
        else:
            print(f"✓ Meta: R$ {dados.get('meta_valor', 0):,.2f}")
            print(f"✓ Realizado: R$ {dados.get('realizado_valor', 0):,.2f}")
            print(f"✓ % Atingido: {dados.get('perc_atingido', 0):.2f}%")
        
        return data
    
    except Exception as e:
        print(f"✗ Erro: {str(e)}")
        return {}


def main():
    """Função principal."""
    print_header("Teste Manual da API - Dipam AI Agent")
    print(f"\nAPI Base URL: {API_BASE_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Lista de testes
    testes = []
    
    # 1. Health Check
    print_header("1. Health Check")
    if not test_health_check():
        print("\n⚠ API não está respondendo. Verifique se o servidor está rodando.")
        print("  Execute: DB_TYPE=sqlite python -m src.run_api")
        return
    
    # 2. Testes de perguntas
    print_header("2. Testes de Perguntas (/ask)")
    
    perguntas_teste = [
        {
            "pergunta": "Por que o vendedor ROTA 77 não bateu a meta em novembro de 2025?",
            "expected_intent": "motivo_nao_bateu_meta"
        },
        {
            "pergunta": "Quais são os clientes em risco de churn do vendedor ROTA 77?",
            "expected_intent": "clientes_risco_churn"
        },
        {
            "pergunta": "Qual a meta do vendedor ROTA 1 em setembro de 2025?",
            "expected_intent": "meta_vendedor"
        },
        {
            "pergunta": "Qual a probabilidade do vendedor ROTA 1 bater a meta em outubro?",
            "expected_intent": "previsao_bater_meta"
        },
        {
            "pergunta": "Mostre os clientes em risco de churn",
            "expected_intent": "clientes_risco_churn"
        },
    ]
    
    resultados = []
    for i, teste in enumerate(perguntas_teste, 1):
        print(f"\n{'=' * 80}")
        print(f"Teste {i}/{len(perguntas_teste)}")
        resultado = test_ask_question(
            teste["pergunta"],
            teste.get("expected_intent")
        )
        resultados.append({
            "teste": i,
            "pergunta": teste["pergunta"],
            "sucesso": bool(resultado),
            "intent": resultado.get("intent") if resultado else None,
            "confianca": resultado.get("confianca", 0) if resultado else 0
        })
    
    # 3. Teste de preview
    print_header("3. Teste de Preview (/preview/vendedor)")
    test_preview_vendedor("ROTA 77", "2025-11")
    
    # 4. Resumo
    print_header("4. Resumo dos Testes")
    
    total = len(resultados)
    sucessos = sum(1 for r in resultados if r["sucesso"])
    confianca_media = sum(r["confianca"] for r in resultados) / total if total > 0 else 0
    
    print(f"\nTotal de testes: {total}")
    print(f"Sucessos: {sucessos}")
    print(f"Falhas: {total - sucessos}")
    print(f"Confiança média: {confianca_media:.2f}")
    
    print("\nDetalhes por teste:")
    for r in resultados:
        status = "✓" if r["sucesso"] else "✗"
        print(f"  {status} Teste {r['teste']}: {r['intent']} (confiança: {r['confianca']:.2f})")
        print(f"      Pergunta: {r['pergunta'][:60]}...")
    
    print("\n" + "=" * 80)
    print("Teste concluído!")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Teste interrompido pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Erro fatal: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)




