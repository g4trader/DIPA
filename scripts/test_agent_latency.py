#!/usr/bin/env python3
"""
Script de teste para medir latência do agente.

Testa o tempo de resposta do agente para diferentes tipos de perguntas.

Uso:
    python -m scripts.test_agent_latency
    python -m scripts.test_agent_latency "qual a meta de agosto de 2025?"
"""

import os
import sys
import time

# Garante que o diretório raiz está no path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Define DB_TYPE=sqlite antes de importar módulos do banco
os.environ.setdefault('DB_TYPE', 'sqlite')

from src.agent.service import get_agent_service
from src.dw.connection import get_db_session


def main():
    """Função principal para testar latência do agente."""
    # Obtém pergunta da linha de comando ou usa padrão
    pergunta = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "teste rapido"
    print(f"Pergunta: {pergunta!r}")
    
    # Obtém sessão de banco de dados
    session_context = get_db_session()
    session = next(session_context)
    
    try:
        # Obtém instância do agente
        agent = get_agent_service()
        
        # Mede o tempo da chamada
        start = time.perf_counter()
        result = agent.process_question(pergunta=pergunta, session=session)
        elapsed = time.perf_counter() - start
        
        print("\nResultado bruto:")
        print(result)
        print(f"\nTempo total: {elapsed:.3f} segundos")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        # Fecha sessão
        session.close()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
