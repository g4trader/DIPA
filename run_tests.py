#!/usr/bin/env python3
"""
Script para executar testes do projeto Dipam AI.

Executa pytest com opções configuradas para mostrar output detalhado.
"""

import sys
import subprocess
from pathlib import Path

# Diretório raiz do projeto
root_dir = Path(__file__).parent


def main():
    """Função principal."""
    print("=" * 60)
    print("Executando Testes - Dipam AI")
    print("=" * 60)
    print()
    
    # Comando pytest
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-sv",  # Verbose + print statements
        "--tb=short",  # Traceback curto
        "--disable-warnings",  # Ignora warnings
        "--color=yes",  # Cores no output
        "tests/"  # Diretório de testes
    ]
    
    # Executa pytest
    try:
        result = subprocess.run(cmd, cwd=root_dir)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n\nTestes interrompidos pelo usuário")
        sys.exit(130)
    except Exception as e:
        print(f"\nErro ao executar testes: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()



