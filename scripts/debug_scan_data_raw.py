#!/usr/bin/env python3
"""
Script de debug para escanear e listar todos os arquivos CSV em data_raw/.

Este script:
1. Escaneia o diretório data_raw/ (incluindo subpastas)
2. Detecta o tipo de cada arquivo CSV
3. Lista todos os arquivos com seus tipos e metadados
4. Imprime um resumo final

Uso:
    DB_TYPE=sqlite python -m scripts.debug_scan_data_raw
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from src.config import config
from src.ingestion_scan import scan_data_raw, detect_file_type

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


def get_relative_path(file_path: Path, base_dir: Path) -> str:
    """Retorna o caminho relativo do arquivo."""
    try:
        return str(file_path.relative_to(base_dir))
    except ValueError:
        return str(file_path)


def format_metadata(metadata: Dict) -> str:
    """Formata metadados para exibição."""
    if not metadata:
        return "(sem metadados)"
    
    parts = []
    for key, value in metadata.items():
        parts.append(f"{key}={value}")
    return ", ".join(parts)


def main():
    """Função principal."""
    print_header("Debug de Scan - Arquivos CSV em data_raw/")
    
    try:
        data_raw_dir = config.paths.data_raw_dir
        
        print_info(f"Diretório base: {data_raw_dir}")
        print_info(f"Diretório absoluto: {data_raw_dir.absolute()}")
        
        if not data_raw_dir.exists():
            print_error(f"Diretório data_raw não encontrado: {data_raw_dir}")
            return 1
        
        # Escaneia todos os arquivos CSV
        print_section("Escaneando Arquivos CSV")
        
        csv_files = list(data_raw_dir.rglob('*.csv'))
        
        if not csv_files:
            print_warning(f"Nenhum arquivo CSV encontrado em {data_raw_dir}")
            return 1
        
        print_success(f"Total de arquivos CSV encontrados: {len(csv_files)}")
        
        # Detecta tipo de cada arquivo
        files_by_type: Dict[str, List[Tuple[Path, Dict]]] = {
            'clientes': [],
            'vendas': [],
            'metas_vendedor': [],
            'metas_departamento': [],
            'unknown': []
        }
        
        print_section("Detalhamento por Tipo")
        
        for csv_file in sorted(csv_files):
            file_type, metadata = detect_file_type(csv_file.name)
            files_by_type[file_type].append((csv_file, metadata))
            
            # Imprime detalhes do arquivo
            relative_path = get_relative_path(csv_file, data_raw_dir)
            metadata_str = format_metadata(metadata)
            
            if file_type == 'unknown':
                print_warning(f"[{file_type.upper():20s}] {relative_path}")
                print(f"  {'':20s}   → Tipo não reconhecido")
            else:
                type_label = file_type.replace('_', ' ').title()
                print_success(f"[{type_label:20s}] {relative_path}")
                if metadata:
                    print(f"  {'':20s}   → {metadata_str}")
        
        # Resumo por tipo
        print_header("Resumo por Tipo")
        
        summary = {}
        for file_type, files in files_by_type.items():
            count = len(files)
            summary[file_type] = count
            
            if count == 0:
                print_warning(f"{file_type.replace('_', ' ').title()}: {count} arquivos")
            else:
                print_success(f"{file_type.replace('_', ' ').title()}: {count} arquivos")
        
        # Arquivos unknown
        if summary.get('unknown', 0) > 0:
            print_section("Arquivos Não Reconhecidos (unknown)")
            print_warning("Os seguintes arquivos não foram classificados:")
            for csv_file, metadata in files_by_type['unknown']:
                relative_path = get_relative_path(csv_file, data_raw_dir)
                print(f"  - {relative_path}")
            print()
            print_info("Dica: Verifique os nomes dos arquivos e ajuste a função detect_file_type() se necessário.")
        
        # Análise de problemas
        print_header("Análise de Problemas")
        
        has_issues = False
        
        if summary.get('metas_vendedor', 0) == 0:
            print_warning("⚠ Nenhum arquivo de metas_vendedor encontrado!")
            print_info("  Verifique se os arquivos contêm 'meta' e 'vendedor' no nome.")
            has_issues = True
        
        if summary.get('metas_departamento', 0) == 0:
            print_warning("⚠ Nenhum arquivo de metas_departamento encontrado!")
            print_info("  Verifique se os arquivos contêm 'meta' e 'departamento' no nome.")
            has_issues = True
        
        if not has_issues:
            print_success("✓ Todos os tipos esperados foram encontrados!")
        
        # Detalhes adicionais
        print_header("Detalhes Adicionais")
        
        print_info("Tipos esperados:")
        print("  - clientes: arquivos com 'cliente'/'clientes' e 'ativo'/'ativos' no nome")
        print("  - vendas: arquivos com 'venda'/'vendas' ou 'detalhe'/'detalhes' no nome")
        print("  - metas_vendedor: arquivos com 'meta'/'metas' e 'vendedor'/'vendedores' no nome")
        print("  - metas_departamento: arquivos com 'meta'/'metas' e 'departamento'/'depto' no nome")
        print()
        
        if summary.get('metas_vendedor', 0) > 0 or summary.get('metas_departamento', 0) > 0:
            print_section("Exemplos de Metas Encontradas")
            
            for file_type in ['metas_vendedor', 'metas_departamento']:
                if files_by_type[file_type]:
                    print_info(f"\n{file_type.replace('_', ' ').title()}:")
                    for csv_file, metadata in files_by_type[file_type][:3]:  # Primeiros 3
                        relative_path = get_relative_path(csv_file, data_raw_dir)
                        metadata_str = format_metadata(metadata)
                        print(f"  - {relative_path}")
                        if metadata:
                            print(f"    → {metadata_str}")
                    if len(files_by_type[file_type]) > 3:
                        print(f"  ... e mais {len(files_by_type[file_type]) - 3} arquivos")
        
        print_header("Scan Concluído")
        
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




