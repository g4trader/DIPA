#!/usr/bin/env python3
"""
Script CLI para construir features para ML a partir do banco de dados.

Este script:
1. Carrega tabelas do banco de dados
2. Chama build_features_vendedor_mes() e build_features_cliente_mes()
3. Salva os DataFrames resultantes em CSV
4. Exibe resumo no console

Uso:
    python -m src.run_build_features
"""

import sys
from pathlib import Path
import logging
from typing import Optional
import pandas as pd

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from src.config import config
from src.dw.connection import init_db, get_db_session
# Importa diretamente do arquivo features.py usando importlib para evitar conflito com diretório features/
import importlib.util
from pathlib import Path
features_file = Path(__file__).parent / "features.py"
spec = importlib.util.spec_from_file_location("features_module", features_file)
features_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(features_module)
build_features_vendedor_mes = features_module.build_features_vendedor_mes
build_features_cliente_mes = features_module.build_features_cliente_mes
save_features_to_csv = features_module.save_features_to_csv
from sqlalchemy.orm import Session

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


def print_dataframe_summary(df: pd.DataFrame, title: str, n_rows: int = 10):
    """
    Imprime resumo de um DataFrame.
    
    Args:
        df: DataFrame para resumir
        title: Título do resumo
        n_rows: Número de linhas para mostrar
    """
    print(f"\n{Colors.BOLD}{title}{Colors.ENDC}")
    print(f"  Total de registros: {len(df):,}")
    print(f"  Total de colunas: {len(df.columns)}")
    
    if len(df) > 0:
        print(f"\n  {Colors.BOLD}Primeiras {min(n_rows, len(df))} linhas:{Colors.ENDC}")
        print()
        
        # Seleciona colunas principais para exibição
        # Prioriza colunas mais importantes
        priority_cols = ['mes_ano', 'vendedor', 'id_cliente', 'nome_cliente', 
                         'meta_valor', 'realizado_valor', 'perc_ating_valor',
                         'bateu_meta', 'churn_provavel', 'valor_total_mes',
                         'qtd_pedidos_mes', 'dias_desde_ultima_compra']
        
        # Seleciona até 8 colunas para exibição
        display_cols = []
        for col in priority_cols:
            if col in df.columns and len(display_cols) < 8:
                display_cols.append(col)
        
        # Preenche com outras colunas se necessário
        for col in df.columns:
            if col not in display_cols and len(display_cols) < 8:
                display_cols.append(col)
        
        # Formata como tabela simples
        df_display = df[display_cols].head(n_rows)
        
        # Imprime cabeçalho
        header = " | ".join([f"{col[:12]:>12}" for col in display_cols])
        print(f"  {header}")
        print(f"  {'─' * len(header)}")
        
        # Imprime linhas
        for idx, row in df_display.iterrows():
            values = []
            for col in display_cols:
                value = row[col]
                # Formata valor
                if pd.isna(value):
                    value_str = "NaN"
                elif isinstance(value, (int, float)):
                    if abs(value) >= 1000:
                        value_str = f"{value:,.0f}"
                    elif isinstance(value, float):
                        value_str = f"{value:.2f}"
                    else:
                        value_str = str(value)
                else:
                    value_str = str(value)
                    if len(value_str) > 12:
                        value_str = value_str[:9] + "..."
                
                values.append(f"{value_str:>12}")
            
            print(f"  {' | '.join(values)}")
        
        if len(df.columns) > len(display_cols):
            print(f"\n  ... e mais {len(df.columns) - len(display_cols)} colunas")


def build_vendedor_features(
    session: Session,
    start_mes_ano: Optional[str] = None,
    end_mes_ano: Optional[str] = None
) -> pd.DataFrame:
    """
    Constrói features de vendedor/mês.
    
    Args:
        session: Sessão SQLAlchemy
        start_mes_ano: Mês/ano inicial (opcional)
        end_mes_ano: Mês/ano final (opcional)
        
    Returns:
        pd.DataFrame: Features de vendedor/mês
    """
    print_section("Construindo Features de Vendedor/Mês")
    
    try:
        print_info(f"Carregando features de vendedor/mês...")
        if start_mes_ano or end_mes_ano:
            print_info(f"Período: {start_mes_ano or 'início'} até {end_mes_ano or 'fim'}")
        
        df = build_features_vendedor_mes(
            session=session,
            start_mes_ano=start_mes_ano,
            end_mes_ano=end_mes_ano
        )
        
        if len(df) == 0:
            print_warning("Nenhuma feature de vendedor/mês encontrada")
            return df
        
        print_success(f"Features carregadas: {len(df):,} registros")
        print_info(f"Colunas: {len(df.columns)}")
        
        # Estatísticas
        if 'vendedor' in df.columns:
            unique_vendedores = df['vendedor'].nunique()
            print_info(f"Vendedores únicos: {unique_vendedores}")
        
        if 'mes_ano' in df.columns:
            unique_meses = df['mes_ano'].nunique()
            print_info(f"Meses únicos: {unique_meses}")
            if unique_meses > 0:
                print_info(f"Período: {df['mes_ano'].min()} até {df['mes_ano'].max()}")
        
        if 'bateu_meta' in df.columns:
            bateu_meta = df['bateu_meta'].sum()
            perc_bateu = (bateu_meta / len(df)) * 100 if len(df) > 0 else 0
            print_info(f"Vendedores que bateram meta: {bateu_meta} ({perc_bateu:.1f}%)")
        
        return df
    
    except Exception as e:
        print_error(f"Erro ao construir features de vendedor/mês: {str(e)}")
        logger.exception("Erro detalhado ao construir features de vendedor/mês")
        raise


def build_cliente_features(
    session: Session,
    start_mes_ano: Optional[str] = None,
    end_mes_ano: Optional[str] = None,
    dias_churn: int = 90
) -> pd.DataFrame:
    """
    Constrói features de cliente/mês.
    
    Args:
        session: Sessão SQLAlchemy
        start_mes_ano: Mês/ano inicial (opcional)
        end_mes_ano: Mês/ano final (opcional)
        dias_churn: Número de dias sem compra para considerar churn
        
    Returns:
        pd.DataFrame: Features de cliente/mês
    """
    print_section("Construindo Features de Cliente/Mês (Churn)")
    
    try:
        print_info(f"Carregando features de cliente/mês (churn: {dias_churn} dias)...")
        if start_mes_ano or end_mes_ano:
            print_info(f"Período: {start_mes_ano or 'início'} até {end_mes_ano or 'fim'}")
        
        df = build_features_cliente_mes(
            session=session,
            start_mes_ano=start_mes_ano,
            end_mes_ano=end_mes_ano,
            dias_churn=dias_churn
        )
        
        if len(df) == 0:
            print_warning("Nenhuma feature de cliente/mês encontrada")
            return df
        
        print_success(f"Features carregadas: {len(df):,} registros")
        print_info(f"Colunas: {len(df.columns)}")
        
        # Estatísticas
        if 'id_cliente' in df.columns:
            unique_clientes = df['id_cliente'].nunique()
            print_info(f"Clientes únicos: {unique_clientes:,}")
        
        if 'mes_ano' in df.columns:
            unique_meses = df['mes_ano'].nunique()
            print_info(f"Meses únicos: {unique_meses}")
            if unique_meses > 0:
                print_info(f"Período: {df['mes_ano'].min()} até {df['mes_ano'].max()}")
        
        if 'churn_provavel' in df.columns:
            churn_provavel = df['churn_provavel'].sum()
            perc_churn = (churn_provavel / len(df)) * 100 if len(df) > 0 else 0
            print_info(f"Clientes com churn provável: {churn_provavel:,} ({perc_churn:.1f}%)")
        
        return df
    
    except Exception as e:
        print_error(f"Erro ao construir features de cliente/mês: {str(e)}")
        logger.exception("Erro detalhado ao construir features de cliente/mês")
        raise


def save_features(df: pd.DataFrame, filename: str, output_dir: Optional[Path] = None):
    """
    Salva DataFrame de features em CSV.
    
    Args:
        df: DataFrame com features
        filename: Nome do arquivo
        output_dir: Diretório de saída (None = usa config.paths.data_processed_dir)
    """
    if output_dir is None:
        output_dir = config.paths.data_processed_dir
    
    # Garante que o diretório existe
    output_dir.mkdir(parents=True, exist_ok=True)
    
    filepath = output_dir / filename
    
    try:
        print_info(f"Salvando features em: {filepath}")
        df.to_csv(filepath, index=False)
        
        # Verifica tamanho do arquivo
        file_size = filepath.stat().st_size / (1024 * 1024)  # MB
        print_success(f"Features salvas: {len(df):,} registros ({file_size:.2f} MB)")
    
    except Exception as e:
        print_error(f"Erro ao salvar features: {str(e)}")
        raise


def run_build_features_pipeline(
    start_mes_ano: Optional[str] = None,
    end_mes_ano: Optional[str] = None,
    dias_churn: int = 90,
    save_files: bool = True
):
    """
    Executa o pipeline completo de construção de features.
    
    Args:
        start_mes_ano: Mês/ano inicial (opcional)
        end_mes_ano: Mês/ano final (opcional)
        dias_churn: Número de dias sem compra para considerar churn
        save_files: Se True, salva arquivos CSV
        
    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: (features_vendedor, features_cliente)
    """
    print_header("Construção de Features para ML - Dipam AI")
    
    stats = {
        'vendedor': {'registros': 0, 'vendedores': 0, 'meses': 0},
        'cliente': {'registros': 0, 'clientes': 0, 'meses': 0},
    }
    
    try:
        # Inicializa banco de dados
        print_section("Inicializando Banco de Dados")
        try:
            init_db()
            print_success("Banco de dados inicializado")
        except Exception as e:
            print_error(f"Erro ao inicializar banco de dados: {str(e)}")
            raise
        
        # Abre sessão com o banco
        session_context = get_db_session()
        session = next(session_context)
        
        try:
            # Constrói features de vendedor/mês
            df_vendedor = None
            try:
                df_vendedor = build_vendedor_features(
                    session=session,
                    start_mes_ano=start_mes_ano,
                    end_mes_ano=end_mes_ano
                )
                
                if df_vendedor is not None and len(df_vendedor) > 0:
                    stats['vendedor']['registros'] = len(df_vendedor)
                    
                    if 'vendedor' in df_vendedor.columns:
                        stats['vendedor']['vendedores'] = df_vendedor['vendedor'].nunique()
                    
                    if 'mes_ano' in df_vendedor.columns:
                        stats['vendedor']['meses'] = df_vendedor['mes_ano'].nunique()
                    
                    # Salva arquivo
                    if save_files:
                        save_features(df_vendedor, "features_vendedor.csv")
            except Exception as e:
                print_error(f"Erro ao processar features de vendedor: {str(e)}")
                logger.exception("Erro detalhado")
            
            # Constrói features de cliente/mês
            df_cliente = None
            try:
                df_cliente = build_cliente_features(
                    session=session,
                    start_mes_ano=start_mes_ano,
                    end_mes_ano=end_mes_ano,
                    dias_churn=dias_churn
                )
                
                if df_cliente is not None and len(df_cliente) > 0:
                    stats['cliente']['registros'] = len(df_cliente)
                    
                    if 'id_cliente' in df_cliente.columns:
                        stats['cliente']['clientes'] = df_cliente['id_cliente'].nunique()
                    
                    if 'mes_ano' in df_cliente.columns:
                        stats['cliente']['meses'] = df_cliente['mes_ano'].nunique()
                    
                    # Salva arquivo
                    if save_files:
                        save_features(df_cliente, "features_cliente.csv")
            except Exception as e:
                print_error(f"Erro ao processar features de cliente: {str(e)}")
                logger.exception("Erro detalhado")
        finally:
            session.close()
        
        # Resumo final
        print_header("Resumo Final")
        
        print(f"{Colors.BOLD}Features de Vendedor/Mês:{Colors.ENDC}")
        print(f"  Total de registros: {stats['vendedor']['registros']:,}")
        print(f"  Vendedores únicos: {stats['vendedor']['vendedores']}")
        print(f"  Meses únicos: {stats['vendedor']['meses']}")
        
        print(f"\n{Colors.BOLD}Features de Cliente/Mês:{Colors.ENDC}")
        print(f"  Total de registros: {stats['cliente']['registros']:,}")
        print(f"  Clientes únicos: {stats['cliente']['clientes']:,}")
        print(f"  Meses únicos: {stats['cliente']['meses']}")
        
        # Exibe exemplos
        if df_vendedor is not None and len(df_vendedor) > 0:
            print_section("Exemplo - Features de Vendedor/Mês")
            print(f"  Shape: {df_vendedor.shape[0]} linhas x {df_vendedor.shape[1]} colunas")
            print(f"\n  Primeiras 5 linhas:")
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', None)
            pd.set_option('display.max_colwidth', 50)
            print(df_vendedor.head(5).to_string())
        
        if df_cliente is not None and len(df_cliente) > 0:
            print_section("Exemplo - Features de Cliente/Mês")
            print(f"  Shape: {df_cliente.shape[0]} linhas x {df_cliente.shape[1]} colunas")
            print(f"\n  Primeiras 5 linhas:")
            print(df_cliente.head(5).to_string())
        
        # Informa sobre arquivos salvos
        if save_files:
            print_section("Arquivos Salvos")
            output_dir = config.paths.data_processed_dir
            print_info(f"Diretório: {output_dir}")
            print_success(f"features_vendedor.csv - {stats['vendedor']['registros']:,} registros")
            print_success(f"features_cliente.csv - {stats['cliente']['registros']:,} registros")
        
        print_header("Construção de Features Concluída!")
        
        return df_vendedor, df_cliente
    
    except KeyboardInterrupt:
        print("\n\n" + Colors.WARNING + "Pipeline interrompido pelo usuário." + Colors.ENDC)
        return None, None
    except Exception as e:
        print_error(f"Erro fatal no pipeline: {str(e)}")
        logger.exception("Erro fatal detalhado")
        return None, None


def main():
    """Função principal."""
    try:
        # Por padrão, processa todos os dados
        # Pode ser estendido para aceitar argumentos de linha de comando
        df_vendedor, df_cliente = run_build_features_pipeline(
            start_mes_ano=None,  # Processa todos os dados
            end_mes_ano=None,    # Processa todos os dados
            dias_churn=90,       # Padrão: 90 dias para churn
            save_files=True      # Salva arquivos CSV
        )
        
        # Exit code baseado no resultado
        if df_vendedor is None and df_cliente is None:
            return 1
        elif df_vendedor is not None and len(df_vendedor) == 0 and \
             df_cliente is not None and len(df_cliente) == 0:
            print_warning("Nenhuma feature foi gerada. Verifique se há dados no banco.")
            return 1
        else:
            return 0
    
    except Exception as e:
        print_error(f"Erro inesperado: {str(e)}")
        logger.exception("Erro inesperado detalhado")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

