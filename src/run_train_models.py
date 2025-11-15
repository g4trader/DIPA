#!/usr/bin/env python3
"""
Script CLI para treinar modelos de ML a partir das features construídas.

Este script:
1. Carrega features de vendedor/mês e cliente/mês
2. Treina modelo de bater meta (vendedor/mês)
3. Treina modelo de churn (cliente/mês)
4. Salva modelos treinados em models/artefacts/
5. Exibe métricas e resumo no console

Uso:
    python -m src.run_train_models
"""

import sys
from pathlib import Path
import logging
from typing import Optional, Tuple, Dict, Any
from datetime import datetime
import json

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

import pandas as pd
from src.config import config
from src.models_ml import (
    train_model_bater_meta,
    train_model_churn,
    print_metrics,
    plot_feature_importance
)
from src.models_ml import MetaModel, ChurnModel

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


def get_model_version() -> str:
    """
    Gera versão do modelo baseada em timestamp.
    
    Returns:
        str: Versão do modelo no formato YYYYMMDD_HHMMSS
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def save_model_metadata(
    model_type: str,
    model_name: str,
    version: str,
    metrics: Dict[str, Any],
    artifacts_dir: Path,
    features_used: Optional[list] = None
):
    """
    Salva metadados do modelo (métricas, versão, etc.).
    
    Args:
        model_type: Tipo do modelo ('meta' ou 'churn')
        model_name: Nome do modelo
        version: Versão do modelo
        metrics: Métricas de avaliação
        artifacts_dir: Diretório para salvar metadados
        features_used: Lista de features usadas no modelo
    """
    metadata = {
        'model_type': model_type,
        'model_name': model_name,
        'version': version,
        'timestamp': datetime.now().isoformat(),
        'features_used': features_used or [],
        'metrics': {
            'accuracy': float(metrics.get('accuracy', 0)),
            'precision': float(metrics.get('precision', 0)),
            'recall': float(metrics.get('recall', 0)),
            'f1_score': float(metrics.get('f1', 0)),
            'roc_auc': float(metrics.get('roc_auc', 0)),
            'cv_mean': float(metrics.get('cv_mean', 0)),
            'cv_std': float(metrics.get('cv_std', 0)),
        },
        'confusion_matrix': metrics.get('confusion_matrix', [])
    }
    
    metadata_file = artifacts_dir / f"{model_type}_model_{version}_metadata.json"
    
    try:
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"Metadados salvos em: {metadata_file}")
    except Exception as e:
        logger.warning(f"Erro ao salvar metadados: {str(e)}")


def print_model_metrics(metrics: Dict[str, Any], model_name: str):
    """
    Imprime métricas do modelo formatadas.
    
    Args:
        metrics: Dicionário com métricas
        model_name: Nome do modelo
    """
    print_section(f"Métricas - {model_name}")
    
    print(f"{Colors.BOLD}Accuracy:{Colors.ENDC}  {metrics['accuracy']:.4f}")
    print(f"{Colors.BOLD}Precision:{Colors.ENDC} {metrics['precision']:.4f}")
    print(f"{Colors.BOLD}Recall:{Colors.ENDC}    {metrics['recall']:.4f}")
    print(f"{Colors.BOLD}F1-Score:{Colors.ENDC}  {metrics['f1']:.4f}")
    print(f"{Colors.BOLD}ROC-AUC:{Colors.ENDC}   {metrics['roc_auc']:.4f}")
    print(f"{Colors.BOLD}CV Mean:{Colors.ENDC}   {metrics['cv_mean']:.4f} (+/- {metrics['cv_std']:.4f})")
    
    # Matriz de confusão
    print(f"\n{Colors.BOLD}Matriz de Confusão:{Colors.ENDC}")
    import numpy as np
    cm = np.array(metrics['confusion_matrix'])
    print(f"                    Predito")
    print(f"                  Não  Sim")
    print(f"Real  Não  {cm[0,0]:8d} {cm[0,1]:8d}")
    print(f"      Sim   {cm[1,0]:8d} {cm[1,1]:8d}")
    print()


def train_meta_model(
    df_features: pd.DataFrame,
    model_type: str = 'gradient_boosting',
    test_size: float = 0.2,
    temporal_split: bool = True,
    artifacts_dir: Optional[Path] = None
) -> Tuple[MetaModel, Dict[str, Any], str]:
    """
    Treina modelo para probabilidade de bater meta.
    
    Args:
        df_features: DataFrame com features de vendedor/mês
        model_type: Tipo de modelo ('logistic_regression' ou 'gradient_boosting')
        test_size: Proporção de dados de teste
        temporal_split: Se True, usa split temporal
        artifacts_dir: Diretório para salvar modelos
        
    Returns:
        Tuple[MetaModel, Dict, str]: (modelo, métricas, versão)
    """
    print_section(f"Treinando Modelo de Bater Meta - {model_type}")
    
    version = get_model_version()
    print_info(f"Versão do modelo: {version}")
    
    try:
        if len(df_features) == 0:
            raise ValueError("Nenhuma feature de vendedor/mês encontrada")
        
        print_info(f"Features carregadas: {len(df_features):,} registros")
        print_info(f"Distribuição de classes:")
        
        if 'bateu_meta' in df_features.columns:
            class_dist = df_features['bateu_meta'].value_counts()
            for class_val, count in class_dist.items():
                perc = (count / len(df_features)) * 100
                print(f"  {'Bateu meta' if class_val == 1 else 'Não bateu meta'}: {count:,} ({perc:.1f}%)")
        
        # Treina modelo
        print_info(f"Treinando modelo {model_type}...")
        model, metrics = train_model_bater_meta(
            df_features,
            model_type=model_type,
            test_size=test_size,
            temporal_split=temporal_split
        )
        
        # Exibe número de exemplos
        n_train = int(len(df_features) * (1 - test_size))
        n_test = len(df_features) - n_train
        print_info(f"Exemplos de treino: {n_train:,}")
        print_info(f"Exemplos de validação: {n_test:,}")
        
        # Exibe métricas
        print_model_metrics(metrics, f"Bater Meta ({model_type})")
        
        # Feature importance
        try:
            df_importance = model.get_feature_importance()
            if not df_importance.empty:
                print_info(f"Top 5 features mais importantes:")
                for idx, row in df_importance.head(5).iterrows():
                    print(f"  {idx + 1}. {row['feature']}: {row['importance']:.4f}")
        except Exception as e:
            logger.warning(f"Erro ao obter feature importance: {str(e)}")
        
        # Salva modelo
        if artifacts_dir is None:
            artifacts_dir = Path(config.ml.models_dir) / "artefacts"
        
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        # Salva como _latest.joblib
        model_file = artifacts_dir / f"meta_model_latest.joblib"
        print_info(f"Salvando modelo em: {model_file}")
        model.save(str(model_file))
        print_success(f"Modelo salvo: {model_file.name}")
        
        # Salva metadados como _latest_metadata.json
        save_model_metadata('meta', model_type, 'latest', metrics, artifacts_dir, features_used=model.feature_columns)
        
        # Salva feature importance
        try:
            plot_feature_importance(model, top_n=20)
        except Exception as e:
            logger.warning(f"Erro ao plotar feature importance: {str(e)}")
        
        return model, metrics, version
    
    except Exception as e:
        print_error(f"Erro ao treinar modelo de meta: {str(e)}")
        logger.exception("Erro detalhado ao treinar modelo de meta")
        raise


def train_churn_model(
    df_features: pd.DataFrame,
    model_type: str = 'gradient_boosting',
    test_size: float = 0.2,
    temporal_split: bool = True,
    artifacts_dir: Optional[Path] = None
) -> Tuple[ChurnModel, Dict[str, Any], str]:
    """
    Treina modelo para risco de churn.
    
    Args:
        df_features: DataFrame com features de cliente/mês
        model_type: Tipo de modelo ('logistic_regression' ou 'gradient_boosting')
        test_size: Proporção de dados de teste
        temporal_split: Se True, usa split temporal
        artifacts_dir: Diretório para salvar modelos
        
    Returns:
        Tuple[ChurnModel, Dict, str]: (modelo, métricas, versão)
    """
    print_section(f"Treinando Modelo de Churn - {model_type}")
    
    version = get_model_version()
    print_info(f"Versão do modelo: {version}")
    
    try:
        if len(df_features) == 0:
            raise ValueError("Nenhuma feature de cliente/mês encontrada")
        
        print_info(f"Features carregadas: {len(df_features):,} registros")
        print_info(f"Distribuição de classes:")
        
        if 'churn_provavel' in df_features.columns:
            class_dist = df_features['churn_provavel'].value_counts()
            for class_val, count in class_dist.items():
                perc = (count / len(df_features)) * 100
                print(f"  {'Churn provável' if class_val == 1 else 'Sem churn'}: {count:,} ({perc:.1f}%)")
        
        # Treina modelo
        print_info(f"Treinando modelo {model_type}...")
        model, metrics = train_model_churn(
            df_features,
            model_type=model_type,
            test_size=test_size,
            temporal_split=temporal_split
        )
        
        # Exibe número de exemplos
        n_train = int(len(df_features) * (1 - test_size))
        n_test = len(df_features) - n_train
        print_info(f"Exemplos de treino: {n_train:,}")
        print_info(f"Exemplos de validação: {n_test:,}")
        
        # Exibe métricas
        print_model_metrics(metrics, f"Churn ({model_type})")
        
        # Feature importance
        try:
            df_importance = model.get_feature_importance()
            if not df_importance.empty:
                print_info(f"Top 5 features mais importantes:")
                for idx, row in df_importance.head(5).iterrows():
                    print(f"  {idx + 1}. {row['feature']}: {row['importance']:.4f}")
        except Exception as e:
            logger.warning(f"Erro ao obter feature importance: {str(e)}")
        
        # Salva modelo
        if artifacts_dir is None:
            artifacts_dir = Path(config.ml.models_dir) / "artefacts"
        
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        # Salva como _latest.joblib
        model_file = artifacts_dir / f"churn_model_latest.joblib"
        print_info(f"Salvando modelo em: {model_file}")
        model.save(str(model_file))
        print_success(f"Modelo salvo: {model_file.name}")
        
        # Salva metadados como _latest_metadata.json
        save_model_metadata('churn', model_type, 'latest', metrics, artifacts_dir, features_used=model.feature_columns)
        
        # Salva feature importance
        try:
            plot_feature_importance(model, top_n=20)
        except Exception as e:
            logger.warning(f"Erro ao plotar feature importance: {str(e)}")
        
        return model, metrics, version
    
    except Exception as e:
        print_error(f"Erro ao treinar modelo de churn: {str(e)}")
        logger.exception("Erro detalhado ao treinar modelo de churn")
        raise


def run_train_models_pipeline(
    test_size: float = 0.2,
    temporal_split: bool = True
):
    """
    Executa o pipeline completo de treinamento de modelos.
    
    Treina modelos baseline (LogisticRegression) e ensemble (GradientBoosting)
    para ambos os problemas (meta e churn).
    
    Args:
        test_size: Proporção de dados de teste
        temporal_split: Se True, usa split temporal
        
    Returns:
        int: Exit code (0 = sucesso, 1 = erro)
    """
    print_header("Treinamento de Modelos de ML - Dipam AI")
    
    stats = {
        'meta': {'trained': False, 'metrics_baseline': None, 'metrics_ensemble': None},
        'churn': {'trained': False, 'metrics_baseline': None, 'metrics_ensemble': None},
    }
    
    artifacts_dir = Path(config.ml.models_dir) / "artefacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Carrega features dos CSVs
        print_section("Carregando Features")
        
        features_vendedor_path = config.paths.data_processed_dir / "features_vendedor.csv"
        features_cliente_path = config.paths.data_processed_dir / "features_cliente.csv"
        
        if not features_vendedor_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {features_vendedor_path}")
        if not features_cliente_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {features_cliente_path}")
        
        print_info(f"Carregando features de vendedor: {features_vendedor_path}")
        df_vendedor = pd.read_csv(features_vendedor_path)
        print_success(f"Features de vendedor carregadas: {len(df_vendedor):,} registros")
        
        print_info(f"Carregando features de cliente: {features_cliente_path}")
        df_cliente = pd.read_csv(features_cliente_path)
        print_success(f"Features de cliente carregadas: {len(df_cliente):,} registros")
        
        # Treina modelos de meta (baseline e ensemble)
        print_section("Treinando Modelos de Bater Meta")
        
        try:
            # Baseline: LogisticRegression
            print_info("Treinando modelo baseline (LogisticRegression)...")
            model_meta_baseline, metrics_meta_baseline, _ = train_meta_model(
                df_features=df_vendedor,
                model_type='logistic_regression',
                test_size=test_size,
                temporal_split=temporal_split,
                artifacts_dir=artifacts_dir
            )
            stats['meta']['metrics_baseline'] = metrics_meta_baseline
            
            # Ensemble: GradientBoosting (modelo final)
            print_info("Treinando modelo ensemble (GradientBoosting)...")
            model_meta_ensemble, metrics_meta_ensemble, _ = train_meta_model(
                df_features=df_vendedor,
                model_type='gradient_boosting',
                test_size=test_size,
                temporal_split=temporal_split,
                artifacts_dir=artifacts_dir
            )
            stats['meta']['metrics_ensemble'] = metrics_meta_ensemble
            stats['meta']['trained'] = True
            
            print_success("Modelos de meta treinados com sucesso")
        
        except Exception as e:
            print_error(f"Erro ao treinar modelos de meta: {str(e)}")
            logger.exception("Erro detalhado")
        
        # Treina modelos de churn (baseline e ensemble)
        print_section("Treinando Modelos de Churn")
        
        try:
            # Baseline: LogisticRegression
            print_info("Treinando modelo baseline (LogisticRegression)...")
            model_churn_baseline, metrics_churn_baseline, _ = train_churn_model(
                df_features=df_cliente,
                model_type='logistic_regression',
                test_size=test_size,
                temporal_split=temporal_split,
                artifacts_dir=artifacts_dir
            )
            stats['churn']['metrics_baseline'] = metrics_churn_baseline
            
            # Ensemble: GradientBoosting (modelo final)
            print_info("Treinando modelo ensemble (GradientBoosting)...")
            model_churn_ensemble, metrics_churn_ensemble, _ = train_churn_model(
                df_features=df_cliente,
                model_type='gradient_boosting',
                test_size=test_size,
                temporal_split=temporal_split,
                artifacts_dir=artifacts_dir
            )
            stats['churn']['metrics_ensemble'] = metrics_churn_ensemble
            stats['churn']['trained'] = True
            
            print_success("Modelos de churn treinados com sucesso")
        
        except Exception as e:
            print_error(f"Erro ao treinar modelos de churn: {str(e)}")
            logger.exception("Erro detalhado")
        
        # Resumo final
        print_header("Resumo Final")
        
        print(f"{Colors.BOLD}Modelos Treinados:{Colors.ENDC}")
        
        if stats['meta']['trained']:
            print(f"\n  {Colors.BOLD}Modelo de Bater Meta:{Colors.ENDC}")
            if stats['meta']['metrics_baseline']:
                m = stats['meta']['metrics_baseline']
                print(f"    Baseline (LogisticRegression):")
                print(f"      ROC-AUC: {m['roc_auc']:.4f}, Accuracy: {m['accuracy']:.4f}, Recall: {m['recall']:.4f}")
            if stats['meta']['metrics_ensemble']:
                m = stats['meta']['metrics_ensemble']
                print(f"    Ensemble (GradientBoosting) - Modelo Final:")
                print(f"      ROC-AUC: {m['roc_auc']:.4f}, Accuracy: {m['accuracy']:.4f}, Recall: {m['recall']:.4f}")
            print(f"    Arquivo: meta_model_latest.joblib")
        else:
            print_warning("Modelo de meta não foi treinado")
        
        if stats['churn']['trained']:
            print(f"\n  {Colors.BOLD}Modelo de Churn:{Colors.ENDC}")
            if stats['churn']['metrics_baseline']:
                m = stats['churn']['metrics_baseline']
                print(f"    Baseline (LogisticRegression):")
                print(f"      ROC-AUC: {m['roc_auc']:.4f}, Accuracy: {m['accuracy']:.4f}, Recall: {m['recall']:.4f}")
            if stats['churn']['metrics_ensemble']:
                m = stats['churn']['metrics_ensemble']
                print(f"    Ensemble (GradientBoosting) - Modelo Final:")
                print(f"      ROC-AUC: {m['roc_auc']:.4f}, Accuracy: {m['accuracy']:.4f}, Recall: {m['recall']:.4f}")
            print(f"    Arquivo: churn_model_latest.joblib")
        else:
            print_warning("Modelo de churn não foi treinado")
        
        print_section("Artefatos Salvos")
        print_info(f"Diretório: {artifacts_dir}")
        
        if stats['meta']['trained']:
            print_success("meta_model_latest.joblib")
            print_success("meta_model_latest_metadata.json")
        
        if stats['churn']['trained']:
            print_success("churn_model_latest.joblib")
            print_success("churn_model_latest_metadata.json")
        
        print_header("Treinamento Concluído!")
        
        if not stats['meta']['trained'] and not stats['churn']['trained']:
            print_error("Nenhum modelo foi treinado com sucesso")
            return 1
        else:
            return 0
    
    except KeyboardInterrupt:
        print("\n\n" + Colors.WARNING + "Treinamento interrompido pelo usuário." + Colors.ENDC)
        return 130
    except Exception as e:
        print_error(f"Erro fatal no pipeline: {str(e)}")
        logger.exception("Erro fatal detalhado")
        return 1


def main():
    """Função principal."""
    try:
        # Treina modelos baseline e ensemble para ambos os problemas
        exit_code = run_train_models_pipeline(
            test_size=0.2,
            temporal_split=True
        )
        
        return exit_code
    
    except Exception as e:
        print_error(f"Erro inesperado: {str(e)}")
        logger.exception("Erro inesperado detalhado")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

