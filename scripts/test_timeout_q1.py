#!/usr/bin/env python3
"""
Script de teste para validar timeout controlado do endpoint /ask (Q1).

Este script:
1. Faz uma chamada controlada à /ask com a pergunta Q1
2. Mede tempo total de resposta
3. Valida se timeout controlado retorna JSON estruturado com CORS
4. Gera relatório de teste
"""

import requests
import time
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional

# Configurações
PROD_URL = "https://dipam-ai-backend-642830139828.us-central1.run.app"
LOCAL_URL = "http://localhost:8000"
ORIGIN = "https://dipam.smartiasolutions.com.br"

# Pergunta Q1
Q1_PERGUNTA = "Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?"


def test_ask_timeout(base_url: str, use_prod: bool = True) -> Dict[str, Any]:
    """
    Testa o endpoint /ask com Q1 e valida timeout controlado.
    
    Args:
        base_url: URL base da API
        use_prod: Se True, usa origin de produção
        
    Returns:
        dict com resultados do teste
    """
    url = f"{base_url}/ask"
    headers = {
        "Content-Type": "application/json",
    }
    
    if use_prod:
        headers["Origin"] = ORIGIN
    
    payload = {
        "pergunta": Q1_PERGUNTA,
        "papel": "diretor"
    }
    
    print(f"\n{'='*60}")
    print(f"Teste de Timeout Q1 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    print(f"URL: {url}")
    print(f"Origin: {headers.get('Origin', 'N/A')}")
    print(f"Pergunta: {Q1_PERGUNTA[:50]}...")
    print()
    
    start_time = time.perf_counter()
    
    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=25  # Timeout do cliente maior que timeout do servidor (18s)
        )
        
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        # Extrai headers CORS
        cors_headers = {
            "Access-Control-Allow-Origin": response.headers.get("Access-Control-Allow-Origin"),
            "Access-Control-Allow-Credentials": response.headers.get("Access-Control-Allow-Credentials"),
            "Access-Control-Allow-Methods": response.headers.get("Access-Control-Allow-Methods"),
            "Access-Control-Allow-Headers": response.headers.get("Access-Control-Allow-Headers"),
            "Vary": response.headers.get("Vary"),
        }
        
        # Tenta parsear JSON
        try:
            body = response.json()
        except:
            body = {"raw": response.text[:500]}
        
        result = {
            "status_code": response.status_code,
            "elapsed_ms": int(elapsed_ms),
            "cors_headers": cors_headers,
            "body": body,
            "success": False,
            "timeout_controlled": False,
            "cors_present": False,
            "errors": []
        }
        
        # Validações
        if response.status_code == 503:
            if isinstance(body, dict) and body.get("codigo") == "ASK_TIMEOUT":
                result["timeout_controlled"] = True
                result["success"] = True
                print("✅ Timeout controlado detectado (503 com ASK_TIMEOUT)")
            else:
                result["errors"].append("503 sem código ASK_TIMEOUT")
                print("⚠️  503 sem código ASK_TIMEOUT")
        elif response.status_code == 200:
            if isinstance(body, dict) and "resumoExecutivo" in body:
                result["success"] = True
                print("✅ Resposta OK (200) com dados")
            else:
                result["errors"].append("200 sem dados esperados")
                print("⚠️  200 sem dados esperados")
        else:
            result["errors"].append(f"Status code inesperado: {response.status_code}")
            print(f"⚠️  Status code inesperado: {response.status_code}")
        
        # Valida CORS
        if cors_headers.get("Access-Control-Allow-Origin") == ORIGIN:
            result["cors_present"] = True
            print("✅ Headers CORS presentes")
        else:
            result["errors"].append("CORS headers ausentes ou incorretos")
            print("❌ Headers CORS ausentes ou incorretos")
        
        # Valida formato JSON
        if isinstance(body, dict):
            print("✅ Resposta é JSON válido")
        else:
            result["errors"].append("Resposta não é JSON válido")
            print("❌ Resposta não é JSON válido")
        
        return result
        
    except requests.exceptions.Timeout:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        print(f"❌ Timeout do cliente (após {elapsed_ms:.0f}ms)")
        return {
            "status_code": None,
            "elapsed_ms": int(elapsed_ms),
            "cors_headers": {},
            "body": None,
            "success": False,
            "timeout_controlled": False,
            "cors_present": False,
            "errors": ["Timeout do cliente (não controlado pela aplicação)"]
        }
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        print(f"❌ Erro: {str(e)}")
        return {
            "status_code": None,
            "elapsed_ms": int(elapsed_ms),
            "cors_headers": {},
            "body": None,
            "success": False,
            "timeout_controlled": False,
            "cors_present": False,
            "errors": [str(e)]
        }


def generate_report(result: Dict[str, Any]) -> str:
    """Gera relatório markdown do teste"""
    report = f"""# Relatório de Teste - Timeout Q1

**Data:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**URL Testada:** {PROD_URL}/ask
**Pergunta:** {Q1_PERGUNTA}

## Resultados

### Status HTTP
- **Código:** {result['status_code'] or 'N/A'}
- **Tempo Total:** {result['elapsed_ms']}ms

### Validações

| Validação | Status |
|-----------|--------|
| Timeout Controlado | {'✅' if result['timeout_controlled'] else '❌'} |
| CORS Presente | {'✅' if result['cors_present'] else '❌'} |
| JSON Válido | {'✅' if isinstance(result['body'], dict) else '❌'} |
| Sucesso Geral | {'✅' if result['success'] else '❌'} |

### Headers CORS

```json
{json.dumps(result['cors_headers'], indent=2, ensure_ascii=False)}
```

### Corpo da Resposta

```json
{json.dumps(result['body'], indent=2, ensure_ascii=False) if result['body'] else 'N/A'}
```

### Erros

"""
    
    if result['errors']:
        for error in result['errors']:
            report += f"- ❌ {error}\n"
    else:
        report += "- ✅ Nenhum erro\n"
    
    report += f"""
## Conclusão

"""
    
    if result['success']:
        if result['timeout_controlled']:
            report += "✅ **Timeout controlado funcionando corretamente**\n"
            report += "- Aplicação retornou erro estruturado com CORS\n"
            report += "- Não houve timeout de infra (503 sem JSON)\n"
        else:
            report += "✅ **Resposta OK**\n"
            report += "- Endpoint respondeu corretamente\n"
            report += "- Headers CORS presentes\n"
    else:
        report += "❌ **Falha no teste**\n"
        report += "- Verifique os erros acima\n"
    
    return report


def main():
    """Função principal"""
    use_prod = "--prod" in sys.argv or "-p" in sys.argv
    base_url = PROD_URL if use_prod else LOCAL_URL
    
    print(f"Testando {'PRODUÇÃO' if use_prod else 'LOCAL'}: {base_url}")
    
    result = test_ask_timeout(base_url, use_prod=use_prod)
    
    # Gera relatório
    report = generate_report(result)
    
    # Salva relatório
    report_file = "RELATORIO_TESTE_TIMEOUT_Q1.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"\n{'='*60}")
    print(f"Relatório salvo em: {report_file}")
    print(f"{'='*60}\n")
    
    # Print resumo
    print("RESUMO:")
    print(f"  Status: {result['status_code']}")
    print(f"  Tempo: {result['elapsed_ms']}ms")
    print(f"  Timeout Controlado: {'✅' if result['timeout_controlled'] else '❌'}")
    print(f"  CORS: {'✅' if result['cors_present'] else '❌'}")
    print(f"  Sucesso: {'✅' if result['success'] else '❌'}")
    
    if result['errors']:
        print("\nERROS:")
        for error in result['errors']:
            print(f"  - {error}")
    
    return 0 if result['success'] else 1


if __name__ == "__main__":
    sys.exit(main())

