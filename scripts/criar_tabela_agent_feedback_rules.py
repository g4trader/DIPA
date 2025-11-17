#!/usr/bin/env python3
"""
Script para criar a tabela agent_feedback_rules no banco de dados.

Uso:
    python -m scripts.criar_tabela_agent_feedback_rules
"""

import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from src.dw.connection import init_db, get_db_engine, Base
from src.dw.models_agent import AgentFeedbackRule


def main():
    """Cria a tabela agent_feedback_rules."""
    print("=" * 60)
    print("Criando tabela agent_feedback_rules")
    print("=" * 60)
    
    # Inicializa banco
    init_db(create_tables_if_not_exists=False)
    
    # Cria apenas a tabela agent_feedback_rules
    engine = get_db_engine()
    AgentFeedbackRule.__table__.create(bind=engine, checkfirst=True)
    
    print("✅ Tabela agent_feedback_rules criada com sucesso!")
    print()
    print("Estrutura da tabela:")
    print("  - id: INTEGER PRIMARY KEY")
    print("  - owner_role: TEXT NOT NULL (ex.: 'diretor', 'supervisor')")
    print("  - owner_id: TEXT (opcional)")
    print("  - rule_scope: TEXT NOT NULL (ex.: 'meta', 'vendas')")
    print("  - condition_json: TEXT NOT NULL (JSON com condição)")
    print("  - action_json: TEXT NOT NULL (JSON com ação)")
    print("  - description: TEXT (descrição humana)")
    print("  - priority: INTEGER DEFAULT 10 (menor = maior prioridade)")
    print("  - active: INTEGER DEFAULT 1 (1=ativa, 0=desativada)")
    print("  - created_at: DATETIME")
    print("  - updated_at: DATETIME")


if __name__ == "__main__":
    main()

