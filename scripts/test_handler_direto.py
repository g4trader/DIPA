#!/usr/bin/env python3
"""Teste direto do handler refatorado."""

import sys
import os
from pathlib import Path

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Importa diretamente para evitar problemas de import
import importlib.util

# Importa connection diretamente
connection_path = os.path.join(root_dir, "src", "dw", "connection.py")
spec_connection = importlib.util.spec_from_file_location("connection", connection_path)
connection = importlib.util.module_from_spec(spec_connection)
spec_connection.loader.exec_module(connection)

get_db_session = connection.get_db_session
init_db = connection.init_db

# Importa handler
from src.agent.handler_dw_refatorado import processar_pergunta_com_dw

# Inicializa banco
init_db(create_tables_if_not_exists=True)

# Testa
with get_db_session() as session:
    try:
        resposta = processar_pergunta_com_dw(
            pergunta="Liste as metas por mês de todo o período que você tem.",
            session=session,
            papel="diretor"
        )
        print("✅ Handler funcionou!")
        print(f"Resumo: {resposta.get('resumo_executivo', 'N/A')[:200]}")
        print(f"Intent: {resposta.get('intent_spec', {}).tipo if resposta.get('intent_spec') else 'N/A'}")
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

