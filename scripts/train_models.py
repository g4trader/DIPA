#!/usr/bin/env python3
"""
Script para treinar modelos de ML.

Este script:
1. Carrega features do banco de dados
2. Treina modelos de bater meta e churn
3. Avalia modelos com métricas
4. Salva modelos treinados
5. Imprime feature importance
"""

import sys
from pathlib import Path
import logging

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from src.config import config
from src.dw.connection import init_db
from src.features import build_features_vendedor_mes, build_features_cliente_mes
from src.models_ml import (
    train_model_bater_meta,
    train_model_churn,
    print_metrics,
    plot_feature_importance
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Função principal."""
    print("=" * 60)
    print("Treinamento de Modelos de ML - Dipam AI")
    print("=" * 60)
    print()
    
    # Inicializa banco de dados
    logger.info("Inicializando banco de dados...")
    init_db()
    
    # 1. Treina modelo de bater meta
    print("=" * 60)
    print("1. Treinando Modelo de Bater Meta")
    print("=" * 60)
    print()
    
    try:
        # Constrói features
        logger.info("Construindo features de vendedor/mês...")
        df_meta = build_features_vendedor_mes()
        
        print(f"Features carregadas: {len(df_meta)} registros")
        print(f"Distribuição de classes:")
        print(df_meta['bateu_meta'].value_counts())
        print()
        
        # Treina baseline (Logistic Regression)
        print("-" * 60)
        print("Modelo Baseline: Logistic Regression")
        print("-" * 60)
        model_lr, metrics_lr = train_model_bater_meta(
            df_meta,
            model_type='logistic_regression',
            test_size=0.2,
            temporal_split=True
        )
        print_metrics(metrics_lr, "Logistic Regression (Baseline)")
        
        # Salva modelo baseline
        model_lr.save()
        
        # Treina modelo forte (Gradient Boosting)
        print("-" * 60)
        print("Modelo Forte: Gradient Boosting")
        print("-" * 60)
        model_gb, metrics_gb = train_model_bater_meta(
            df_meta,
            model_type='gradient_boosting',
            test_size=0.2,
            temporal_split=True
        )
        print_metrics(metrics_gb, "Gradient Boosting")
        
        # Salva modelo forte
        model_gb.save()
        
        # Feature importance
        print("-" * 60)
        print("Feature Importance - Gradient Boosting")
        print("-" * 60)
        df_importance = model_gb.get_feature_importance()
        print("\nTop 10 Features:")
        print(df_importance.head(10).to_string(index=False))
        print()
        
        # Plota feature importance
        plot_feature_importance(model_gb, top_n=20)
        
    except Exception as e:
        logger.error(f"Erro ao treinar modelo de bater meta: {str(e)}")
        import traceback
        traceback.print_exc()
        print()
    
    # 2. Treina modelo de churn
    print("=" * 60)
    print("2. Treinando Modelo de Churn")
    print("=" * 60)
    print()
    
    try:
        # Constrói features
        logger.info("Construindo features de cliente/mês...")
        df_churn = build_features_cliente_mes(dias_churn=90)
        
        print(f"Features carregadas: {len(df_churn)} registros")
        print(f"Distribuição de classes:")
        print(df_churn['churn_provavel'].value_counts())
        print()
        
        # Treina baseline (Logistic Regression)
        print("-" * 60)
        print("Modelo Baseline: Logistic Regression")
        print("-" * 60)
        model_lr_churn, metrics_lr_churn = train_model_churn(
            df_churn,
            model_type='logistic_regression',
            test_size=0.2,
            temporal_split=True
        )
        print_metrics(metrics_lr_churn, "Logistic Regression (Baseline)")
        
        # Salva modelo baseline
        model_lr_churn.save()
        
        # Treina modelo forte (Gradient Boosting)
        print("-" * 60)
        print("Modelo Forte: Gradient Boosting")
        print("-" * 60)
        model_gb_churn, metrics_gb_churn = train_model_churn(
            df_churn,
            model_type='gradient_boosting',
            test_size=0.2,
            temporal_split=True
        )
        print_metrics(metrics_gb_churn, "Gradient Boosting")
        
        # Salva modelo forte
        model_gb_churn.save()
        
        # Feature importance
        print("-" * 60)
        print("Feature Importance - Gradient Boosting")
        print("-" * 60)
        df_importance_churn = model_gb_churn.get_feature_importance()
        print("\nTop 10 Features:")
        print(df_importance_churn.head(10).to_string(index=False))
        print()
        
        # Plota feature importance
        plot_feature_importance(model_gb_churn, top_n=20)
        
    except Exception as e:
        logger.error(f"Erro ao treinar modelo de churn: {str(e)}")
        import traceback
        traceback.print_exc()
        print()
    
    print("=" * 60)
    print("Treinamento concluído!")
    print("=" * 60)
    print()
    print("Modelos salvos em:")
    print(f"  - {config.ml.models_dir}/meta_model_logistic_regression.joblib")
    print(f"  - {config.ml.models_dir}/meta_model_gradient_boosting.joblib")
    print(f"  - {config.ml.models_dir}/churn_model_logistic_regression.joblib")
    print(f"  - {config.ml.models_dir}/churn_model_gradient_boosting.joblib")
    print()


if __name__ == "__main__":
    main()
