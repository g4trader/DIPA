#!/usr/bin/env python3
"""
Script para testar os endpoints de diagnóstico do banco.
"""

import sys
import os
from pathlib import Path

# Adiciona o diretório raiz ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

if not os.getenv('SQLITE_PATH'):
    sqlite_path = Path(project_root) / 'data' / 'dipam_dw.db'
    os.environ['SQLITE_PATH'] = str(sqlite_path)

from src.dw.connection import init_db, get_db_session
from src.dw.diagnostico_db import get_db_fingerprint, get_q1_contagem

def main():
    print("=" * 80)
    print("TESTE: Diagnóstico do Banco de Dados")
    print("=" * 80)
    
    init_db()
    session = next(get_db_session())
    
    try:
        print("\n1. Fingerprint do banco:")
        fingerprint = get_db_fingerprint(session)
        for key, value in fingerprint.items():
            print(f"   {key}: {value}")
        
        print("\n2. Contagem Q1:")
        q1_result = get_q1_contagem(session, dias=60)
        for key, value in q1_result.items():
            if key != 'amostra_ids':
                print(f"   {key}: {value}")
        print(f"   amostra_ids (primeiros 5): {q1_result['amostra_ids'][:5]}")
        
        print("\n✅ Testes concluídos com sucesso!")
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()

if __name__ == "__main__":
    main()

