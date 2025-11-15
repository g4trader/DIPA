#!/usr/bin/env python3
"""
Script de verificação do banco de dados em produção.

Este script conecta no banco de dados usando a mesma configuração
do aplicativo e verifica se os dados de metas e vendas estão presentes.

Uso:
    python scripts/check_db_prod.py

Variáveis de ambiente:
    - DB_TYPE: Tipo de banco (sqlite ou postgresql)
    - SQLITE_PATH: Caminho do arquivo SQLite (se DB_TYPE=sqlite)
    - DB_URL: URL completa de conexão (opcional, sobrescreve outras configs)
"""

import sys
import os
from pathlib import Path

# Adiciona o diretório raiz ao path para importar módulos do projeto
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from src.config import config
from src.dw.connection import get_db_engine, init_db
from sqlalchemy import text

def check_database():
    """Verifica se o banco de dados tem dados de metas e vendas."""
    
    print("=" * 60)
    print("Verificação do Banco de Dados - DIPAM COPILOT™")
    print("=" * 60)
    print()
    
    # Mostra configuração atual
    print(f"Tipo de banco: {config.database.db_type}")
    print(f"String de conexão: {config.database.connection_string}")
    print()
    
    try:
        # Inicializa conexão
        init_db()
        engine = get_db_engine()
        
        print("✅ Conexão com o banco estabelecida com sucesso!")
        print()
        
        # Testa conexão com uma query simples
        with engine.connect() as conn:
            # Verifica se tabelas existem e contam registros
            # Nota: Verifica tanto 'venda' quanto 'vendas' pois pode variar
            tables_to_check = [
                ("metas_vendedor", "metas_vendedor"),
                ("metas_departamento", "metas_departamento"),
                ("vendas", "vendas"),  # Tabela de vendas (plural)
                ("vendas (venda)", "venda"),  # Alternativa caso seja singular
            ]
            
            results = {}
            
            for table_label, table_name in tables_to_check:
                try:
                    # Tenta contar registros (funciona para SQLite e PostgreSQL)
                    if config.database.db_type == "sqlite":
                        query = text(f'SELECT COUNT(*) as count FROM {table_name}')
                    else:
                        query = text(f'SELECT COUNT(*) as count FROM {table_name}')
                    
                    result = conn.execute(query)
                    count = result.scalar()
                    results[table_label] = count
                    status = "✅" if count > 0 else "⚠️ "
                    print(f"{status} {table_label}: {count:,} registros")
                    
                except Exception as e:
                    print(f"❌ {table_label}: Erro ao verificar - {e}")
                    results[table_label] = None
            
            print()
            
            # Verifica meses disponíveis em metas_vendedor
            try:
                if config.database.db_type == "sqlite":
                    query = text("""
                        SELECT DISTINCT mes_ano 
                        FROM metas_vendedor 
                        ORDER BY mes_ano DESC 
                        LIMIT 10
                    """)
                else:
                    query = text("""
                        SELECT DISTINCT mes_ano 
                        FROM metas_vendedor 
                        ORDER BY mes_ano DESC 
                        LIMIT 10
                    """)
                
                result = conn.execute(query)
                meses = [row[0] for row in result]
                
                if meses:
                    print(f"📅 Meses disponíveis em metas_vendedor: {', '.join(meses)}")
                else:
                    print("⚠️  Nenhum mês encontrado em metas_vendedor")
                    
            except Exception as e:
                print(f"⚠️  Não foi possível listar meses: {e}")
            
            print()
            
            # Verifica meses disponíveis em vendas
            # Tenta 'vendas' primeiro, depois 'venda' como fallback
            for table_name in ["vendas", "venda"]:
                try:
                    if config.database.db_type == "sqlite":
                        # Para SQLite, usa strftime para extrair ano-mês
                        query = text(f"""
                            SELECT DISTINCT strftime('%Y-%m', data_venda) as mes_ano
                            FROM {table_name}
                            ORDER BY mes_ano DESC
                            LIMIT 10
                        """)
                    else:
                        query = text(f"""
                            SELECT DISTINCT TO_CHAR(data_venda, 'YYYY-MM') as mes_ano
                            FROM {table_name}
                            ORDER BY mes_ano DESC
                            LIMIT 10
                        """)
                    
                    result = conn.execute(query)
                    meses = [row[0] for row in result]
                    
                    if meses:
                    print(f"📅 Meses disponíveis em venda: {', '.join(meses)}")
                else:
                    print("⚠️  Nenhum mês encontrado em venda")
                    
            except Exception as e:
                print(f"⚠️  Não foi possível listar meses de vendas: {e}")
            
            print()
            
            # Resumo final
            total_records = sum(v for v in results.values() if v is not None and v > 0)
            
            if total_records > 0:
                print("=" * 60)
                print("✅ BANCO DE DADOS OK - Dados encontrados!")
                print(f"   Total de registros verificados: {total_records:,}")
                print("=" * 60)
                return 0
            else:
                print("=" * 60)
                print("❌ BANCO DE DADOS VAZIO - Nenhum dado encontrado!")
                print("=" * 60)
                print()
                print("Possíveis causas:")
                print("  1. O arquivo SQLite não foi copiado para o container")
                print("  2. O caminho do SQLite está incorreto")
                print("  3. O ETL não foi executado para popular o banco")
                print()
                print("Soluções:")
                print("  - Verifique se data/dipam_dw.db existe e está no Dockerfile")
                print("  - Verifique se SQLITE_PATH está configurado corretamente")
                print("  - Execute o ETL para popular o banco com dados")
                return 1
        
    except Exception as e:
        print("=" * 60)
        print(f"❌ ERRO ao conectar no banco de dados: {e}")
        print("=" * 60)
        print()
        print("Verifique:")
        print(f"  - String de conexão: {config.database.connection_string}")
        print(f"  - Tipo de banco: {config.database.db_type}")
        if config.database.db_type == "sqlite":
            print(f"  - Arquivo SQLite existe? {os.path.exists(config.database.sqlite_path)}")
            print(f"  - Caminho do SQLite: {config.database.sqlite_path}")
        return 1


if __name__ == "__main__":
    exit_code = check_database()
    sys.exit(exit_code)

