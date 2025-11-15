#!/usr/bin/env python3
"""
Script para inicializar o banco de dados.

Cria todas as tabelas necessárias, incluindo as novas tabelas de interações e embeddings.
"""

import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

import os
import logging

# Força uso de SQLite se não especificado
os.environ.setdefault("DB_TYPE", "sqlite")

from src.dw.connection import init_db, create_tables, get_db_engine
from sqlalchemy import inspect

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Função principal do script."""
    print("=" * 80)
    print("INICIALIZAÇÃO DO BANCO DE DADOS")
    print("=" * 80)
    print()
    
    try:
        # Inicializa conexão
        init_db()
        logger.info("Conexão com banco de dados inicializada")
        
        # Importa modelos para garantir que estejam registrados
        print("Importando modelos...")
        import src.dw.models  # noqa: F401
        print("✅ Modelos importados com sucesso")
        print()
        
        # Verifica modelos registrados
        from src.dw.connection import Base
        tabelas_esperadas = [table.name for table in Base.metadata.tables.values()]
        print(f"Modelos registrados ({len(tabelas_esperadas)}):")
        for tabela in sorted(tabelas_esperadas):
            print(f"  - {tabela}")
        print()
        
        # Cria todas as tabelas
        print("Criando tabelas...")
        create_tables()
        print("✅ Tabelas criadas com sucesso")
        print()
        
        # Lista tabelas existentes no banco
        engine = get_db_engine()
        inspector = inspect(engine)
        tabelas_existentes = inspector.get_table_names()
        
        print("-" * 80)
        print("TABELAS NO BANCO DE DADOS:")
        print("-" * 80)
        if tabelas_existentes:
            for tabela in sorted(tabelas_existentes):
                print(f"  ✓ {tabela}")
            
            print()
            print(f"Total: {len(tabelas_existentes)} tabela(s)")
            
            # Verifica se as tabelas principais existem
            tabelas_importantes = [
                "interacoes_agent",
                "interacoes_embedding",
                "vendas",
                "vendedores",
                "supervisores",
                "metas_vendedor",
                "metas_departamento"
            ]
            
            print()
            print("Verificação de tabelas importantes:")
            for tabela in tabelas_importantes:
                if tabela in tabelas_existentes:
                    print(f"  ✅ {tabela}")
                else:
                    print(f"  ❌ {tabela} (NÃO ENCONTRADA)")
        else:
            print("  ❌ Nenhuma tabela encontrada no banco!")
        
        print()
        print("=" * 80)
        print("✅ Inicialização concluída com sucesso!")
        print("=" * 80)
        
    except Exception as e:
        logger.error(f"Erro ao inicializar banco: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
