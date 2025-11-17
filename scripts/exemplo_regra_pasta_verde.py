#!/usr/bin/env python3
"""
Script de exemplo para criar a regra de exclusão da pasta verde.

Este script demonstra como registrar uma regra de feedback do Diretor:
"Para análises de meta, exclua sempre a pasta verde."

Uso:
    python -m scripts.exemplo_regra_pasta_verde
"""

import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from src.dw.connection import get_db_session
from src.agent.rules import salvar_regra_feedback


def main():
    """Cria a regra de exemplo para excluir pasta verde em análises de meta."""
    print("=" * 60)
    print("Criando regra de exemplo: Excluir pasta verde em análises de meta")
    print("=" * 60)
    
    with get_db_session() as session:
        # Regra: Excluir pasta verde de todas as análises de meta
        regra = salvar_regra_feedback(
            session=session,
            owner_role="diretor",
            rule_scope="meta",
            condition_json={
                "carteira": "pasta_verde"
            },
            action_json={
                "excluir_dos_filtros": True,
                "excluir_carteira": ["pasta_verde"]
            },
            description="Excluir pasta verde de todas as análises de meta, exceto se o diretor pedir explicitamente o contrário.",
            priority=10,
            active=True
        )
        
        print(f"✅ Regra criada com sucesso!")
        print(f"   ID: {regra.id}")
        print(f"   Owner Role: {regra.owner_role}")
        print(f"   Rule Scope: {regra.rule_scope}")
        print(f"   Description: {regra.description}")
        print()
        print("A partir de agora, todas as consultas de meta excluirão")
        print("automaticamente a pasta verde, a menos que o Diretor")
        print("solicite explicitamente o contrário na pergunta.")


if __name__ == "__main__":
    main()

