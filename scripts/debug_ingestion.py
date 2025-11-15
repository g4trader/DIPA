#!/usr/bin/env python3
"""
Script de debug para validar se o pipeline de ingestão carregou os dados no banco.

Este script:
1. Conecta ao banco de dados
2. Verifica a contagem de registros em cada tabela principal
3. Imprime um relatório com os totais
4. Alerta se alguma tabela está vazia

Uso:
    python -m scripts.debug_ingestion
"""

import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from src.config import config as app_config
from src.dw.connection import init_db, get_db_session
from src.dw.models import (
    Cliente, Venda, MetaVendedor, MetaDepartamento
)

# Cores ANSI para output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text: str):
    """Imprime cabeçalho formatado."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{text}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'=' * 60}{Colors.ENDC}\n")


def print_success(text: str):
    """Imprime mensagem de sucesso."""
    print(f"{Colors.OKGREEN}✓{Colors.ENDC} {text}")


def print_warning(text: str):
    """Imprime mensagem de aviso."""
    print(f"{Colors.WARNING}⚠{Colors.ENDC} {text}")


def print_info(text: str):
    """Imprime mensagem informativa."""
    print(f"{Colors.OKBLUE}ℹ{Colors.ENDC} {text}")


def print_error(text: str):
    """Imprime mensagem de erro."""
    print(f"{Colors.FAIL}✗{Colors.ENDC} {text}")


def count_table_records(session, model, table_name: str) -> int:
    """
    Conta registros em uma tabela.
    
    Args:
        session: Sessão SQLAlchemy
        model: Modelo SQLAlchemy
        table_name: Nome da tabela (para exibição)
        
    Returns:
        int: Número de registros
    """
    try:
        count = session.query(model).count()
        return count
    except Exception as e:
        print_error(f"Erro ao contar registros em {table_name}: {str(e)}")
        return -1


def main():
    """Função principal."""
    print_header("Debug de Ingestão - Validação de Dados")
    
    try:
        # Inicializa banco de dados
        print_info("Conectando ao banco de dados...")
        init_db()
        print_success(f"Conectado ao banco: {app_config.database.db_type}")
        print_info(f"Connection string: {app_config.database.connection_string}")
        
        # Obtém sessão
        session = next(get_db_session())
        
        print_header("Contagem de Registros por Tabela")
        
        # Conta registros em cada tabela
        tables_data = [
            ("clientes", Cliente, "Clientes"),
            ("vendas", Venda, "Vendas"),
            ("metas_vendedor", MetaVendedor, "Metas por Vendedor"),
            ("metas_departamento", MetaDepartamento, "Metas por Departamento"),
        ]
        
        results = {}
        has_empty = False
        
        for table_key, model, table_display in tables_data:
            count = count_table_records(session, model, table_key)
            results[table_key] = count
            
            if count < 0:
                print_error(f"{table_display}: Erro ao contar registros")
                has_empty = True
            elif count == 0:
                print_warning(f"{table_display}: {count} registros")
                has_empty = True
            else:
                print_success(f"{table_display}: {count:,} registros")
        
        # Resumo
        print_header("Resumo")
        
        total_records = sum(count for count in results.values() if count > 0)
        print_info(f"Total de registros no banco: {total_records:,}")
        
        if has_empty:
            print_warning("\n⚠ ATENÇÃO: Algumas tabelas estão vazias ou com erro!")
            print_info("Execute o pipeline de ingestão:")
            print_info("  python -m src.run_ingestion")
        else:
            print_success("\n✓ Todas as tabelas contêm dados!")
        
        # Detalhes adicionais
        print_header("Detalhes")
        for table_key, model, table_display in tables_data:
            count = results[table_key]
            if count > 0:
                # Mostra exemplo de dados (primeiro registro)
                try:
                    first_record = session.query(model).first()
                    if first_record:
                        print_info(f"\n{table_display} - Primeiro registro:")
                        if hasattr(first_record, 'codigo'):
                            print_info(f"  Código: {first_record.codigo}")
                        if hasattr(first_record, 'nome'):
                            print_info(f"  Nome: {first_record.nome}")
                        if hasattr(first_record, 'mes'):
                            print_info(f"  Mês: {first_record.mes}/{first_record.ano}")
                        if hasattr(first_record, 'data_venda'):
                            print_info(f"  Data: {first_record.data_venda}")
                except Exception as e:
                    print_warning(f"  Não foi possível exibir exemplo: {str(e)}")
        
        session.close()
        
        print_header("Validação Concluída")
        
        return 0 if not has_empty else 1
        
    except Exception as e:
        print_error(f"Erro fatal: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n" + Colors.WARNING + "Script interrompido pelo usuário." + Colors.ENDC)
        sys.exit(130)
    except Exception as e:
        print_error(f"Erro inesperado: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

