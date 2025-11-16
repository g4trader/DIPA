#!/usr/bin/env python3
"""
Script de teste de CORS para o backend DIPAM COPILOT™.

Testa se o backend está respondendo corretamente às requisições CORS,
incluindo preflight (OPTIONS) e requisições reais (POST).

Uso:
    export API_BASE_URL=https://dipam-ai-backend-6arhlm3mha-uc.a.run.app
    python scripts/test_cors_cloud.py

Ou com URL local:
    export API_BASE_URL=http://localhost:8080
    python scripts/test_cors_cloud.py
"""

import os
import sys
import requests
from typing import List, Tuple, Optional

# Cores para output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def test_cors_preflight(base_url: str, origin: str) -> Tuple[bool, str, dict]:
    """
    Testa requisição CORS preflight (OPTIONS).
    
    Args:
        base_url: URL base da API (ex: https://dipam-ai-backend-6arhlm3mha-uc.a.run.app)
        origin: Origem a testar (ex: https://dipam.smartiasolutions.com.br)
        
    Returns:
        (sucesso, mensagem, headers)
    """
    url = f"{base_url.rstrip('/')}/ask"
    
    headers = {
        "Origin": origin,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type",
    }
    
    try:
        response = requests.options(url, headers=headers, timeout=10)
        response_headers = dict(response.headers)
        
        # Verifica status code
        if response.status_code not in [200, 204]:
            return False, f"Status code {response.status_code} (esperado 200 ou 204)", response_headers
        
        # Verifica header Access-Control-Allow-Origin
        allow_origin = response_headers.get("Access-Control-Allow-Origin")
        if not allow_origin:
            return False, "Header Access-Control-Allow-Origin ausente", response_headers
        
        if allow_origin != origin and allow_origin != "*":
            return False, f"Access-Control-Allow-Origin: {allow_origin} (esperado {origin})", response_headers
        
        # Verifica outros headers importantes
        allow_methods = response_headers.get("Access-Control-Allow-Methods", "")
        if "POST" not in allow_methods:
            return False, f"Access-Control-Allow-Methods não inclui POST: {allow_methods}", response_headers
        
        return True, f"OPTIONS {url} - CORS preflight OK", response_headers
        
    except requests.exceptions.RequestException as e:
        return False, f"Erro na requisição: {str(e)}", {}


def test_cors_post(base_url: str, origin: str) -> Tuple[bool, str, dict]:
    """
    Testa requisição CORS real (POST).
    
    Args:
        base_url: URL base da API
        origin: Origem a testar
        
    Returns:
        (sucesso, mensagem, headers)
    """
    url = f"{base_url.rstrip('/')}/ask"
    
    headers = {
        "Origin": origin,
        "Content-Type": "application/json",
    }
    
    payload = {
        "pergunta": "teste de cors",
        "papel": "diretor"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response_headers = dict(response.headers)
        
        # Verifica header Access-Control-Allow-Origin (deve estar presente mesmo em 503, 500, etc)
        allow_origin = response_headers.get("Access-Control-Allow-Origin")
        if not allow_origin:
            return False, f"Header Access-Control-Allow-Origin ausente (status {response.status_code})", response_headers
        
        if allow_origin != origin and allow_origin != "*":
            return False, f"Access-Control-Allow-Origin: {allow_origin} (esperado {origin}, status {response.status_code})", response_headers
        
        # Status code pode ser 200, 503, 500, etc - o importante é ter o header CORS
        status_msg = f"Status {response.status_code}"
        if response.status_code == 200:
            status_msg += " (OK)"
        elif response.status_code == 503:
            status_msg += " (Service Unavailable - mas CORS OK)"
        elif response.status_code >= 500:
            status_msg += " (Erro do servidor - mas CORS OK)"
        
        return True, f"POST {url} - {status_msg}, CORS OK", response_headers
        
    except requests.exceptions.RequestException as e:
        return False, f"Erro na requisição: {str(e)}", {}


def run_tests(base_url: str, origins: List[str]) -> int:
    """
    Executa todos os testes de CORS.
    
    Returns:
        Código de saída (0 = sucesso, 1 = falha)
    """
    print(f"\n{YELLOW}🧪 Testando CORS para: {base_url}{RESET}\n")
    
    all_passed = True
    
    for origin in origins:
        print(f"\n{YELLOW}📍 Testando origem: {origin}{RESET}")
        print("-" * 80)
        
        # Teste 1: Preflight OPTIONS
        success, message, headers = test_cors_preflight(base_url, origin)
        if success:
            print(f"{GREEN}✅ {message}{RESET}")
        else:
            print(f"{RED}❌ {message}{RESET}")
            print(f"{RED}   Headers: {headers}{RESET}")
            all_passed = False
        
        # Teste 2: POST real
        success, message, headers = test_cors_post(base_url, origin)
        if success:
            print(f"{GREEN}✅ {message}{RESET}")
        else:
            print(f"{RED}❌ {message}{RESET}")
            print(f"{RED}   Headers: {headers}{RESET}")
            all_passed = False
    
    print("\n" + "=" * 80)
    if all_passed:
        print(f"{GREEN}✅ Todos os testes de CORS passaram!{RESET}\n")
        return 0
    else:
        print(f"{RED}❌ Alguns testes de CORS falharam.{RESET}\n")
        return 1


def main():
    """Função principal."""
    # Lê URL base da variável de ambiente
    base_url = os.getenv("API_BASE_URL", "https://dipam-ai-backend-6arhlm3mha-uc.a.run.app")
    
    # Remove barra no final se houver
    base_url = base_url.rstrip("/")
    
    # Origens a testar (apenas as de produção para o script)
    origins = [
        "https://dipam.smartiasolutions.com.br",
        "https://dipam-copilot-frontend-6arhlm3mha-uc.a.run.app",
    ]
    
    print(f"{YELLOW}🌐 API Base URL: {base_url}{RESET}")
    print(f"{YELLOW}📋 Origens a testar: {', '.join(origins)}{RESET}")
    
    exit_code = run_tests(base_url, origins)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

