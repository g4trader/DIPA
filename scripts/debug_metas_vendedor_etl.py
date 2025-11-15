#!/usr/bin/env python3
"""
Script de debug para o ETL de metas por vendedor.

Este script:
1. Escaneia arquivos CSV classificados como metas_vendedor
2. Seleciona os primeiros arquivos da lista
3. Para cada arquivo:
   - Imprime informações do arquivo
   - Carrega o CSV usando load_metas_vendedor()
   - Exibe informações detalhadas do DataFrame
   - Verifica valores NaN em colunas-chave
   - Carrega no banco usando load_metas_vendedor_to_db()
   - Verifica contagem de registros no banco

Uso:
    DB_TYPE=sqlite python -m scripts.debug_metas_vendedor_etl
"""

import sys
from pathlib import Path
import pandas as pd

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from src.config import config
from src.ingestion_scan import scan_data_raw
from src.ingestion import load_metas_vendedor
from src.load_to_db import load_metas_vendedor_to_db
from src.dw import connection as dw_connection
from src.dw.connection import init_db
from src.dw.models import MetaVendedor

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
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{text}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'=' * 70}{Colors.ENDC}\n")


def print_section(text: str):
    """Imprime seção formatada."""
    print(f"\n{Colors.OKCYAN}{'─' * 70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKCYAN}{text}{Colors.ENDC}")
    print(f"{Colors.OKCYAN}{'─' * 70}{Colors.ENDC}\n")


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


def main():
    """Função principal."""
    print_header("Debug ETL - Metas por Vendedor")
    
    try:
        # Inicializa banco de dados
        print_section("Inicializando Banco de Dados")
        try:
            init_db()
            print_success("Banco de dados inicializado")
        except Exception as e:
            print_error(f"Erro ao inicializar banco de dados: {str(e)}")
            return 1
        
        # Escaneia arquivos
        print_section("Escaneando Arquivos CSV")
        files_by_type = scan_data_raw()
        
        if 'metas_vendedor' not in files_by_type or not files_by_type['metas_vendedor']:
            print_error("Nenhum arquivo de metas_vendedor encontrado!")
            return 1
        
        metas_files = files_by_type['metas_vendedor']
        print_success(f"Encontrados {len(metas_files)} arquivos de metas_vendedor")
        
        # Seleciona os primeiros 2 arquivos (ou menos se houver menos)
        num_files_to_process = min(2, len(metas_files))
        files_to_process = metas_files[:num_files_to_process]
        
        print_info(f"Processando {num_files_to_process} arquivo(s)...")
        
        # Processa cada arquivo
        for idx, (csv_file, metadata) in enumerate(files_to_process, 1):
            print_header(f"Arquivo {idx}/{num_files_to_process}: {csv_file.name}")
            
            # 1) Imprime informações do arquivo
            print_section("Informações do Arquivo")
            print(f"Caminho completo: {csv_file.absolute()}")
            print(f"Nome do arquivo: {csv_file.name}")
            mes_ano = metadata.get('mes_ano', 'N/A')
            print(f"Mês/Ano detectado: {mes_ano}")
            
            # 2) Carrega o CSV
            print_section("Carregando CSV")
            try:
                df = load_metas_vendedor(str(csv_file), mes_ano=mes_ano)
                print_success(f"CSV carregado com sucesso")
            except Exception as e:
                print_error(f"Erro ao carregar CSV: {str(e)}")
                import traceback
                traceback.print_exc()
                continue
            
            # 3) Imprime informações do DataFrame
            print_section("Informações do DataFrame")
            print(f"Shape: {df.shape} (linhas, colunas)")
            print(f"\nTipos de dados:")
            print(df.dtypes)
            
            print(f"\nPrimeiras 10 linhas (todas as colunas):")
            # Configura pandas para mostrar todas as colunas e linhas
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', None)
            pd.set_option('display.max_colwidth', 50)
            print(df.head(10).to_string())
            
            # 4) Verifica valores NaN em colunas-chave
            print_section("Verificação de Valores NaN")
            key_columns = [
                'vendedor_nome', 'valor_meta', 'valor_faturado', 
                'realizado_valor', 'meta_valor', 'valor_parado',
                'meta_volume', 'realizado_volume', 'perc_ating_valor'
            ]
            
            for col in key_columns:
                if col in df.columns:
                    nan_count = df[col].isna().sum()
                    total_count = len(df)
                    if nan_count > 0:
                        print_warning(f"{col}: {nan_count}/{total_count} valores NaN ({nan_count/total_count*100:.1f}%)")
                    else:
                        print_success(f"{col}: sem valores NaN")
                else:
                    print_info(f"{col}: coluna não encontrada no DataFrame")
            
            # 5) Verifica se DataFrame está vazio
            print_section("Verificação de Dados")
            if df.shape[0] == 0:
                print_error("⚠ load_metas_vendedor retornou DataFrame vazio para este arquivo.")
                continue
            
            print_success(f"DataFrame contém {df.shape[0]} linhas")
            
            # 6) Carrega no banco e verifica contagem
            print_section("Carregando no Banco de Dados")
            
            # Conta registros antes da inserção
            session = dw_connection.SessionLocal()
            try:
                count_before = session.query(MetaVendedor).count()
                print_info(f"Registros em metas_vendedor antes da inserção: {count_before}")
            finally:
                session.close()
            
            try:
                records_inserted = load_metas_vendedor_to_db(df)
                print_success(f"Registros inseridos nesta execução: {records_inserted}")
            except Exception as e:
                print_error(f"Erro ao carregar no banco: {str(e)}")
                import traceback
                traceback.print_exc()
                continue
            
            # Conta registros depois da inserção
            session = dw_connection.SessionLocal()
            try:
                count_after = session.query(MetaVendedor).count()
                print_info(f"Total de registros em metas_vendedor após inserção: {count_after}")
            finally:
                session.close()
            
            # Verifica se houve incremento
            if count_after > count_before:
                increment = count_after - count_before
                print_success(f"Incremento de registros: {increment}")
            else:
                print_warning(f"Nenhum novo registro foi inserido (pode ser atualização de registros existentes)")
        
        print_header("Debug Concluído")
        return 0
        
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

