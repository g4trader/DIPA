#!/usr/bin/env python3
"""
Script CLI para executar pipeline completo de ingestão de dados.

Este script:
1. Escaneia a pasta data_raw/ em busca de CSVs
2. Detecta o tipo de arquivo pelo nome
3. Executa a função de ingestão apropriada
4. Carrega os dados no banco de dados via SQLAlchemy
5. Imprime contagens e logs limpos

Uso:
    python -m src.run_ingestion
"""

import sys
from pathlib import Path
import logging
from typing import Dict, List, Tuple, Optional

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from src.config import config
from src.dw.connection import init_db, create_tables
from src.ingestion import (
    load_clientes,
    load_vendas,
    load_metas_vendedor,
    load_metas_departamento
)
from src.ingestion_scan import scan_data_raw, detect_file_type
from src.load_to_db import (
    load_clientes_to_db,
    load_vendas_to_db,
    load_metas_vendedor_to_db,
    load_metas_departamento_to_db
)

# Configuração de logging (mais limpo para console)
logging.basicConfig(
    level=logging.WARNING,  # Apenas warnings e erros no console
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


class Colors:
    """Cores ANSI para output do console."""
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


def print_section(text: str):
    """Imprime seção formatada."""
    print(f"\n{Colors.OKCYAN}{'─' * 60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKCYAN}{text}{Colors.ENDC}")
    print(f"{Colors.OKCYAN}{'─' * 60}{Colors.ENDC}\n")


def print_success(text: str):
    """Imprime mensagem de sucesso."""
    print(f"{Colors.OKGREEN}✓{Colors.ENDC} {text}")


def print_error(text: str):
    """Imprime mensagem de erro."""
    print(f"{Colors.FAIL}✗{Colors.ENDC} {text}")


def print_warning(text: str):
    """Imprime mensagem de aviso."""
    print(f"{Colors.WARNING}⚠{Colors.ENDC} {text}")


def print_info(text: str):
    """Imprime mensagem informativa."""
    print(f"{Colors.OKBLUE}ℹ{Colors.ENDC} {text}")




def run_ingestion_pipeline():
    """
    Executa o pipeline completo de ingestão de dados.
    """
    print_header("Pipeline de Ingestão de Dados - Dipam AI")
    
    # Estatísticas
    stats = {
        'clientes': {'arquivos': 0, 'registros': 0, 'erros': 0},
        'vendas': {'arquivos': 0, 'registros': 0, 'erros': 0},
        'metas_vendedor': {'arquivos': 0, 'registros': 0, 'erros': 0},
        'metas_departamento': {'arquivos': 0, 'registros': 0, 'erros': 0},
        'unknown': {'arquivos': 0, 'registros': 0, 'erros': 0},
    }
    
    try:
        # Inicializa banco de dados
        print_section("Inicializando Banco de Dados")
        try:
            init_db()
            create_tables()  # Cria as tabelas se não existirem
            print_success("Banco de dados inicializado e tabelas criadas")
        except Exception as e:
            print_error(f"Erro ao inicializar banco de dados: {str(e)}")
            raise
        
        # Escaneia arquivos
        print_section("Escaneando Arquivos")
        data_raw_dir = config.paths.data_raw_dir
        
        if not data_raw_dir.exists():
            print_error(f"Diretório data_raw não encontrado: {data_raw_dir}")
            return
        
        csv_files = list(data_raw_dir.rglob('*.csv'))
        if not csv_files:
            print_warning(f"Nenhum arquivo CSV encontrado em {data_raw_dir}")
            return
        
        print_info(f"Encontrados {len(csv_files)} arquivos CSV em {data_raw_dir}")
        
        files_by_type = scan_data_raw()
        
        if not files_by_type:
            print_warning("Nenhum arquivo encontrado para processar")
            return
        
        # Resumo de arquivos encontrados
        print_section("Resumo de Arquivos Encontrados")
        for file_type, files in sorted(files_by_type.items()):
            count = len(files)
            if file_type == 'unknown':
                print_warning(f"{file_type.capitalize()}: {count} arquivos")
            else:
                print_info(f"{file_type.replace('_', ' ').title()}: {count} arquivos")
        
        # Processa clientes
        if files_by_type.get('clientes'):
            print_section("Processando Clientes")
            for csv_file, metadata in files_by_type['clientes']:
                stats['clientes']['arquivos'] += 1
                try:
                    print(f"  Processando: {csv_file.name}...", end=' ', flush=True)
                    df = load_clientes(str(csv_file))
                    count = load_clientes_to_db(df)
                    stats['clientes']['registros'] += count
                    print_success(f"{count} registros processados")
                except Exception as e:
                    stats['clientes']['erros'] += 1
                    print_error(f"Erro: {str(e)}")
                    logger.exception(f"Erro detalhado ao processar {csv_file.name}")
        
        # Processa vendas
        if files_by_type.get('vendas'):
            print_section("Processando Vendas")
            for csv_file, metadata in files_by_type['vendas']:
                stats['vendas']['arquivos'] += 1
                try:
                    periodo = metadata.get('periodo_referencia', 'N/A')
                    print(f"  Processando: {csv_file.name} (período: {periodo})...", end=' ', flush=True)
                    df = load_vendas(str(csv_file), periodo_referencia=periodo)
                    count = load_vendas_to_db(df)
                    stats['vendas']['registros'] += count
                    print_success(f"{count} registros processados")
                except Exception as e:
                    stats['vendas']['erros'] += 1
                    print_error(f"Erro: {str(e)}")
                    logger.exception(f"Erro detalhado ao processar {csv_file.name}")
        
        # Processa metas vendedor
        if files_by_type.get('metas_vendedor'):
            print_section("Processando Metas por Vendedor")
            for csv_file, metadata in files_by_type['metas_vendedor']:
                stats['metas_vendedor']['arquivos'] += 1
                try:
                    mes_ano = metadata.get('mes_ano', 'N/A')
                    print(f"  Processando: {csv_file.name} (mês/ano: {mes_ano})...", end=' ', flush=True)
                    df = load_metas_vendedor(str(csv_file), mes_ano=mes_ano)
                    count = load_metas_vendedor_to_db(df)
                    stats['metas_vendedor']['registros'] += count
                    print_success(f"{count} registros processados")
                except Exception as e:
                    stats['metas_vendedor']['erros'] += 1
                    print_error(f"Erro: {str(e)}")
                    logger.exception(f"Erro detalhado ao processar {csv_file.name}")
        
        # Processa metas departamento
        if files_by_type.get('metas_departamento'):
            print_section("Processando Metas por Departamento")
            for csv_file, metadata in files_by_type['metas_departamento']:
                stats['metas_departamento']['arquivos'] += 1
                try:
                    mes_ano = metadata.get('mes_ano', 'N/A')
                    print(f"  Processando: {csv_file.name} (mês/ano: {mes_ano})...", end=' ', flush=True)
                    df = load_metas_departamento(str(csv_file), mes_ano=mes_ano)
                    count = load_metas_departamento_to_db(df)
                    stats['metas_departamento']['registros'] += count
                    print_success(f"{count} registros processados")
                except Exception as e:
                    stats['metas_departamento']['erros'] += 1
                    print_error(f"Erro: {str(e)}")
                    logger.exception(f"Erro detalhado ao processar {csv_file.name}")
        
        # Arquivos desconhecidos
        if files_by_type.get('unknown'):
            print_section("Arquivos Não Reconhecidos")
            for csv_file, metadata in files_by_type['unknown']:
                stats['unknown']['arquivos'] += 1
                print_warning(f"  {csv_file.name} - Tipo não identificado")
        
        # Build de Analytics (opcional, após carga de dados)
        mes_anos_processados = set()
        for file_type in ['metas_vendedor', 'metas_departamento', 'vendas']:
            if files_by_type.get(file_type):
                for csv_file, metadata in files_by_type[file_type]:
                    mes_ano = metadata.get('mes_ano')
                    if mes_ano and mes_ano != 'N/A':
                        mes_anos_processados.add(mes_ano)
        
        if mes_anos_processados:
            print_section("Construindo Tabelas de Analytics")
            try:
                from scripts.build_analytics import run_all_analytics
                
                # Processa analytics para cada mes_ano único encontrado
                for mes_ano in sorted(mes_anos_processados):
                    print(f"  Construindo analytics para {mes_ano}...", end=' ', flush=True)
                    try:
                        stats_analytics = run_all_analytics(mes_ano=mes_ano)
                        total = sum(stats_analytics.values())
                        print_success(f"{total} registros de analytics criados")
                    except Exception as e:
                        print_error(f"Erro: {str(e)}")
                        logger.exception(f"Erro ao construir analytics para {mes_ano}")
            except ImportError:
                print_warning("Módulo build_analytics não encontrado - pulando construção de analytics")
            except Exception as e:
                print_warning(f"Erro ao construir analytics: {str(e)}")
                logger.exception("Erro ao construir analytics")
        
        # Resumo final
        print_header("Resumo Final")
        
        total_arquivos = sum(s['arquivos'] for s in stats.values())
        total_registros = sum(s['registros'] for s in stats.values())
        total_erros = sum(s['erros'] for s in stats.values())
        
        print(f"{Colors.BOLD}Total de arquivos processados:{Colors.ENDC} {total_arquivos}")
        print(f"{Colors.BOLD}Total de registros carregados:{Colors.ENDC} {total_registros:,}")
        if total_erros > 0:
            print(f"{Colors.BOLD}{Colors.FAIL}Total de erros:{Colors.ENDC} {total_erros}")
        print()
        
        # Estatísticas por tipo
        for tipo, dados in stats.items():
            if dados['arquivos'] > 0:
                tipo_label = tipo.replace('_', ' ').title()
                print(f"  {tipo_label}:")
                print(f"    Arquivos: {dados['arquivos']}")
                print(f"    Registros: {dados['registros']:,}")
                if dados['erros'] > 0:
                    print(f"    {Colors.FAIL}Erros: {dados['erros']}{Colors.ENDC}")
        
        print_header("Pipeline Concluído com Sucesso!")
        
        if total_erros > 0:
            print_warning(f"Alguns erros ocorreram durante o processamento. Verifique os logs acima.")
            return 1
        else:
            return 0
    
    except KeyboardInterrupt:
        print("\n\n" + Colors.WARNING + "Pipeline interrompido pelo usuário." + Colors.ENDC)
        return 130
    except Exception as e:
        print_error(f"Erro fatal no pipeline: {str(e)}")
        logger.exception("Erro fatal detalhado")
        return 1


def main():
    """Função principal."""
    try:
        exit_code = run_ingestion_pipeline()
        sys.exit(exit_code)
    except Exception as e:
        print_error(f"Erro inesperado: {str(e)}")
        logger.exception("Erro inesperado detalhado")
        sys.exit(1)


if __name__ == "__main__":
    main()
