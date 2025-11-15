#!/usr/bin/env python3
"""
Script de Demonstração Ponta a Ponta - PoC Dipam AI v1.0

Este script demonstra o pipeline completo:
1. Validação de dados no banco
2. Construção de features
3. Treinamento de modelos
4. Resumo em linguagem natural

Uso:
    DB_TYPE=sqlite python -m scripts.demo_pipeline_v1
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import pandas as pd

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from src.config import config
from src.dw.connection import init_db, get_db_session
from src.dw.models import (
    Cliente, Venda, MetaVendedor, MetaDepartamento, Vendedor
)
import importlib.util

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
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{text:^80}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'=' * 80}{Colors.ENDC}\n")


def print_section(text: str):
    """Imprime seção formatada."""
    print(f"\n{Colors.OKCYAN}{'─' * 80}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKCYAN}{text}{Colors.ENDC}")
    print(f"{Colors.OKCYAN}{'─' * 80}{Colors.ENDC}\n")


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


def ensure_sqlite():
    """Garante que o banco está configurado para SQLite."""
    print_section("Configuração do Banco de Dados")
    
    db_type = os.getenv("DB_TYPE", "sqlite")
    
    if db_type != "sqlite":
        print_warning(f"DB_TYPE está configurado como '{db_type}', mas este script requer SQLite.")
        print_info("Definindo DB_TYPE=sqlite para este script...")
        os.environ["DB_TYPE"] = "sqlite"
    
    print_success(f"Banco de dados: SQLite")
    print_info(f"Connection string: {config.database.connection_string}")
    
    return True


def count_table_records(session, model, table_name: str) -> int:
    """Conta registros em uma tabela."""
    try:
        count = session.query(model).count()
        return count
    except Exception as e:
        print_error(f"Erro ao contar registros em {table_name}: {str(e)}")
        return -1


def get_database_summary() -> Dict[str, Any]:
    """Obtém resumo das contagens das tabelas."""
    print_section("Resumo do Banco de Dados")
    
    try:
        init_db()
        session = next(get_db_session())
        
        stats = {}
        
        # Conta registros em cada tabela
        stats['clientes'] = count_table_records(session, Cliente, "clientes")
        stats['vendas'] = count_table_records(session, Venda, "vendas")
        stats['metas_vendedor'] = count_table_records(session, MetaVendedor, "metas_vendedor")
        stats['metas_departamento'] = count_table_records(session, MetaDepartamento, "metas_departamento")
        
        # Conta vendedores únicos
        stats['vendedores'] = session.query(Vendedor).count()
        
        # Conta meses únicos em metas_vendedor
        if stats['metas_vendedor'] > 0:
            meses_unicos = session.query(MetaVendedor.mes_ano).distinct().count()
            stats['meses_unicos'] = meses_unicos
        else:
            stats['meses_unicos'] = 0
        
        session.close()
        
        # Imprime resumo
        print_success(f"Clientes: {stats['clientes']:,}")
        print_success(f"Vendas: {stats['vendas']:,}")
        print_success(f"Metas de Vendedor: {stats['metas_vendedor']:,}")
        print_success(f"Metas de Departamento: {stats['metas_departamento']:,}")
        print_success(f"Vendedores: {stats['vendedores']}")
        print_success(f"Meses únicos: {stats['meses_unicos']}")
        
        return stats
    
    except Exception as e:
        print_error(f"Erro ao obter resumo do banco: {str(e)}")
        return {}


def build_features() -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """Constrói features de vendedor e cliente."""
    print_section("Construção de Features")
    
    try:
        # Importa funções de features usando importlib
        features_file = Path(__file__).parent.parent / "src" / "features.py"
        spec = importlib.util.spec_from_file_location("features_module", features_file)
        features_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(features_module)
        build_features_vendedor_mes = features_module.build_features_vendedor_mes
        build_features_cliente_mes = features_module.build_features_cliente_mes
        
        session = next(get_db_session())
        
        try:
            # Constrói features de vendedor
            print_info("Construindo features de vendedor/mês...")
            df_vendedor = build_features_vendedor_mes(session)
            
            if len(df_vendedor) > 0:
                print_success(f"Features de vendedor: {len(df_vendedor):,} linhas x {len(df_vendedor.columns)} colunas")
                
                # Salva CSV
                output_dir = config.paths.data_processed_dir
                output_dir.mkdir(parents=True, exist_ok=True)
                csv_path = output_dir / "features_vendedor.csv"
                df_vendedor.to_csv(csv_path, index=False)
                print_success(f"Salvo em: {csv_path}")
            else:
                print_warning("Nenhuma feature de vendedor gerada")
            
            # Constrói features de cliente
            print_info("Construindo features de cliente/mês...")
            df_cliente = build_features_cliente_mes(session)
            
            if len(df_cliente) > 0:
                print_success(f"Features de cliente: {len(df_cliente):,} linhas x {len(df_cliente.columns)} colunas")
                
                # Salva CSV
                csv_path = output_dir / "features_cliente.csv"
                df_cliente.to_csv(csv_path, index=False)
                print_success(f"Salvo em: {csv_path}")
            else:
                print_warning("Nenhuma feature de cliente gerada")
            
            return df_vendedor, df_cliente
        
        finally:
            session.close()
    
    except Exception as e:
        print_error(f"Erro ao construir features: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None


def train_models() -> Dict[str, Any]:
    """Treina modelos de ML."""
    print_section("Treinamento de Modelos")
    
    try:
        from src.models_ml import train_model_bater_meta, train_model_churn
        
        metrics = {}
        
        # Carrega features
        features_vendedor_path = config.paths.data_processed_dir / "features_vendedor.csv"
        features_cliente_path = config.paths.data_processed_dir / "features_cliente.csv"
        
        if not features_vendedor_path.exists():
            print_error(f"Arquivo não encontrado: {features_vendedor_path}")
            return {}
        
        if not features_cliente_path.exists():
            print_error(f"Arquivo não encontrado: {features_cliente_path}")
            return {}
        
        print_info("Carregando features...")
        df_vendedor = pd.read_csv(features_vendedor_path)
        df_cliente = pd.read_csv(features_cliente_path)
        
        print_success(f"Features de vendedor carregadas: {len(df_vendedor):,} registros")
        print_success(f"Features de cliente carregadas: {len(df_cliente):,} registros")
        
        # Treina modelo de meta (baseline e ensemble)
        print_info("Treinando modelo de bater meta (baseline)...")
        try:
            model_meta_baseline, metrics_meta_baseline = train_model_bater_meta(
                df_vendedor,
                model_type='logistic_regression',
                test_size=0.2,
                temporal_split=True
            )
            metrics['meta_baseline'] = metrics_meta_baseline
            print_success(f"Modelo baseline treinado - AUC: {metrics_meta_baseline.get('roc_auc', 0):.4f}")
        except Exception as e:
            print_error(f"Erro ao treinar modelo baseline: {str(e)}")
            metrics['meta_baseline'] = {}
        
        print_info("Treinando modelo de bater meta (ensemble)...")
        try:
            model_meta_ensemble, metrics_meta_ensemble = train_model_bater_meta(
                df_vendedor,
                model_type='gradient_boosting',
                test_size=0.2,
                temporal_split=True
            )
            metrics['meta_ensemble'] = metrics_meta_ensemble
            
            # Salva modelo final
            artifacts_dir = Path(config.ml.models_dir) / "artefacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            model_meta_ensemble.save(str(artifacts_dir / "meta_model_latest.joblib"))
            
            # Salva metadata
            metadata = {
                'date': datetime.now().isoformat(),
                'model_type': 'gradient_boosting',
                'features_used': model_meta_ensemble.feature_columns,
                'metrics': {
                    'accuracy': float(metrics_meta_ensemble.get('accuracy', 0)),
                    'precision': float(metrics_meta_ensemble.get('precision', 0)),
                    'recall': float(metrics_meta_ensemble.get('recall', 0)),
                    'f1': float(metrics_meta_ensemble.get('f1', 0)),
                    'roc_auc': float(metrics_meta_ensemble.get('roc_auc', 0)),
                }
            }
            with open(artifacts_dir / "meta_model_latest_metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)
            
            print_success(f"Modelo ensemble treinado - AUC: {metrics_meta_ensemble.get('roc_auc', 0):.4f}")
        except Exception as e:
            print_error(f"Erro ao treinar modelo ensemble: {str(e)}")
            metrics['meta_ensemble'] = {}
        
        # Treina modelo de churn (baseline e ensemble)
        print_info("Treinando modelo de churn (baseline)...")
        try:
            model_churn_baseline, metrics_churn_baseline = train_model_churn(
                df_cliente,
                model_type='logistic_regression',
                test_size=0.2,
                temporal_split=True
            )
            metrics['churn_baseline'] = metrics_churn_baseline
            print_success(f"Modelo baseline treinado - AUC: {metrics_churn_baseline.get('roc_auc', 0):.4f}")
        except Exception as e:
            print_error(f"Erro ao treinar modelo baseline: {str(e)}")
            metrics['churn_baseline'] = {}
        
        print_info("Treinando modelo de churn (ensemble)...")
        try:
            model_churn_ensemble, metrics_churn_ensemble = train_model_churn(
                df_cliente,
                model_type='gradient_boosting',
                test_size=0.2,
                temporal_split=True
            )
            metrics['churn_ensemble'] = metrics_churn_ensemble
            
            # Salva modelo final
            model_churn_ensemble.save(str(artifacts_dir / "churn_model_latest.joblib"))
            
            # Salva metadata
            metadata = {
                'date': datetime.now().isoformat(),
                'model_type': 'gradient_boosting',
                'features_used': model_churn_ensemble.feature_columns,
                'metrics': {
                    'accuracy': float(metrics_churn_ensemble.get('accuracy', 0)),
                    'precision': float(metrics_churn_ensemble.get('precision', 0)),
                    'recall': float(metrics_churn_ensemble.get('recall', 0)),
                    'f1': float(metrics_churn_ensemble.get('f1', 0)),
                    'roc_auc': float(metrics_churn_ensemble.get('roc_auc', 0)),
                }
            }
            with open(artifacts_dir / "churn_model_latest_metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)
            
            print_success(f"Modelo ensemble treinado - AUC: {metrics_churn_ensemble.get('roc_auc', 0):.4f}")
        except Exception as e:
            print_error(f"Erro ao treinar modelo ensemble: {str(e)}")
            metrics['churn_ensemble'] = {}
        
        return metrics
    
    except Exception as e:
        print_error(f"Erro ao treinar modelos: {str(e)}")
        import traceback
        traceback.print_exc()
        return {}


def generate_natural_language_summary(
    db_stats: Dict[str, Any],
    df_vendedor: Optional[pd.DataFrame],
    df_cliente: Optional[pd.DataFrame],
    metrics: Dict[str, Any]
) -> str:
    """Gera resumo em linguagem natural."""
    print_section("Resumo em Linguagem Natural")
    
    summary_parts = []
    
    # Resumo de dados
    vendedores = db_stats.get('vendedores', 0)
    meses = db_stats.get('meses_unicos', 0)
    metas = db_stats.get('metas_vendedor', 0)
    
    summary_parts.append(
        f"📊 **Dados no Banco:** Hoje temos {vendedores} vendedores com {metas:,} metas cadastradas "
        f"em {meses} meses diferentes."
    )
    
    # Resumo de features
    if df_vendedor is not None and len(df_vendedor) > 0:
        vendedores_unicos = df_vendedor['vendedor'].nunique() if 'vendedor' in df_vendedor.columns else 0
        meses_features = df_vendedor['mes_ano'].nunique() if 'mes_ano' in df_vendedor.columns else 0
        summary_parts.append(
            f"📈 **Features de Vendedor:** Foram geradas {len(df_vendedor):,} features para "
            f"{vendedores_unicos} vendedores em {meses_features} meses."
        )
    
    if df_cliente is not None and len(df_cliente) > 0:
        clientes_unicos = df_cliente['id_cliente'].nunique() if 'id_cliente' in df_cliente.columns else 0
        summary_parts.append(
            f"👥 **Features de Cliente:** Foram geradas {len(df_cliente):,} features para "
            f"{clientes_unicos:,} clientes únicos."
        )
    
    # Resumo de modelos
    meta_ensemble = metrics.get('meta_ensemble', {})
    if meta_ensemble:
        auc = meta_ensemble.get('roc_auc', 0) * 100
        recall = meta_ensemble.get('recall', 0) * 100
        accuracy = meta_ensemble.get('accuracy', 0) * 100
        summary_parts.append(
            f"🎯 **Modelo de Bater Meta:** O modelo de bater meta alcançou {auc:.1f}% de AUC, "
            f"{recall:.1f}% de recall e {accuracy:.1f}% de acurácia."
        )
    
    churn_ensemble = metrics.get('churn_ensemble', {})
    if churn_ensemble:
        auc = churn_ensemble.get('roc_auc', 0) * 100
        recall = churn_ensemble.get('recall', 0) * 100
        summary_parts.append(
            f"⚠️  **Modelo de Churn:** O modelo de churn alcançou {auc:.1f}% de AUC e "
            f"{recall:.1f}% de recall."
        )
        
        # Conta clientes em risco alto
        if df_cliente is not None and len(df_cliente) > 0 and 'churn_provavel' in df_cliente.columns:
            # Usa o modelo para calcular probabilidades
            try:
                from src.models_ml import ChurnModel
                from pathlib import Path
                
                artifacts_dir = Path(config.ml.models_dir) / "artefacts"
                churn_model_path = artifacts_dir / "churn_model_latest.joblib"
                
                if churn_model_path.exists():
                    model = ChurnModel(model_type='gradient_boosting')
                    model.load(str(churn_model_path))
                    
                    # Calcula probabilidades para últimos registros de cada cliente
                    df_cliente_latest = df_cliente.sort_values('mes_ano').groupby('id_cliente').tail(1)
                    probas = model.predict(df_cliente_latest)
                    
                    # Conta clientes com risco alto (>70%)
                    risco_alto = (probas > 0.7).sum()
                    summary_parts.append(
                        f"🚨 **Clientes em Risco:** Existem {risco_alto:,} clientes em risco alto de churn "
                        f"(probabilidade > 70%) segundo o modelo."
                    )
            except Exception as e:
                print_warning(f"Não foi possível calcular clientes em risco: {str(e)}")
    
    # Junta todas as partes
    summary = "\n\n".join(summary_parts)
    
    print(f"\n{Colors.BOLD}{summary}{Colors.ENDC}\n")
    
    return summary


def main():
    """Função principal."""
    print_header("Demonstração Ponta a Ponta - PoC Dipam AI v1.0")
    print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    try:
        # 1. Garante SQLite
        ensure_sqlite()
        
        # 2. Resumo do banco
        db_stats = get_database_summary()
        
        if not db_stats or db_stats.get('metas_vendedor', 0) == 0:
            print_error("Nenhum dado encontrado no banco. Execute o pipeline de ingestão primeiro.")
            return 1
        
        # 3. Construção de features
        df_vendedor, df_cliente = build_features()
        
        if df_vendedor is None or len(df_vendedor) == 0:
            print_error("Não foi possível construir features de vendedor.")
            return 1
        
        if df_cliente is None or len(df_cliente) == 0:
            print_error("Não foi possível construir features de cliente.")
            return 1
        
        # 4. Treinamento de modelos
        metrics = train_models()
        
        if not metrics:
            print_error("Não foi possível treinar modelos.")
            return 1
        
        # 5. Resumo em linguagem natural
        summary = generate_natural_language_summary(db_stats, df_vendedor, df_cliente, metrics)
        
        # 6. Resumo final
        print_header("Demonstração Concluída!")
        print_success("Pipeline executado com sucesso!")
        print_info("Artefatos gerados:")
        print_info(f"  - Features: {config.paths.data_processed_dir}")
        print_info(f"  - Modelos: {config.ml.models_dir}/artefacts")
        
        return 0
    
    except KeyboardInterrupt:
        print("\n\n" + Colors.WARNING + "Demonstração interrompida pelo usuário." + Colors.ENDC)
        return 1
    except Exception as e:
        print_error(f"Erro fatal: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

