"""
Testes para módulo de modelos de ML.

Testa funções de treinamento, predição e salvamento de modelos.
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path
import tempfile
import os
import joblib
from unittest.mock import Mock, patch, MagicMock
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier

# Adiciona diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models_ml import (
    MetaModel,
    ChurnModel,
    train_model_bater_meta,
    train_model_churn
)


@pytest.fixture
def sample_features_vendedor():
    """Fixture com features sintéticas de vendedor/mês."""
    return pd.DataFrame({
        'mes_ano': ['2024-01', '2024-01', '2024-02', '2024-02', '2024-03', '2024-03'] * 5,
        'ano': [2024] * 30,
        'mes': [1, 1, 2, 2, 3, 3] * 5,
        'vendedor_id': [1, 2, 1, 2, 1, 2] * 5,
        'vendedor': ['ROTA 77', 'ROTA 78', 'ROTA 77', 'ROTA 78', 'ROTA 77', 'ROTA 78'] * 5,
        'vendedor_nome': ['Vendedor 1', 'Vendedor 2'] * 15,
        'supervisor': ['Supervisor A', 'Supervisor B'] * 15,
        'meta_valor': [100000.0, 120000.0] * 15,
        'realizado_valor': [85000.0, 135000.0, 110000.0, 115000.0, 90000.0, 140000.0] * 5,
        'gap_valor': [-15000.0, 15000.0, 10000.0, -5000.0, -10000.0, 20000.0] * 5,
        'perc_ating_valor': [85.0, 112.5, 110.0, 95.83, 90.0, 116.67] * 5,
        'meta_volume': [1000, 1200] * 15,
        'realizado_volume': [850, 1350, 1100, 1150, 900, 1400] * 5,
        'perc_ating_volume': [85.0, 112.5, 110.0, 95.83, 90.0, 116.67] * 5,
        'meta_positivacao': [50, 60] * 15,
        'clientes_positivados': [42, 68, 55, 58, 45, 70] * 5,
        'perc_ating_positivacao': [84.0, 113.33, 110.0, 96.67, 90.0, 116.67] * 5,
        'ticket_medio': [1700.0, 1800.0] * 15,
        'desconto_medio': [100.0, 120.0] * 15,
        'num_produtos_diferentes_vendidos': [25, 30] * 15,
        'participacao_departamento_chave': [0.3, 0.35] * 15,
        'bateu_meta': [0, 1, 1, 0, 0, 1] * 5  # Target
    })


@pytest.fixture
def sample_features_cliente():
    """Fixture com features sintéticas de cliente/mês."""
    return pd.DataFrame({
        'mes_ano': ['2024-01', '2024-01', '2024-02', '2024-02'] * 10,
        'ano': [2024] * 40,
        'mes': [1, 1, 2, 2] * 10,
        'id_cliente': list(range(1, 41)),
        'codigo_cliente': [f'C{i:03d}' for i in range(1, 41)],
        'nome_cliente': [f'Cliente {i}' for i in range(1, 41)],
        'vendedor': ['ROTA 77', 'ROTA 78'] * 20,
        'supervisor': ['Supervisor A', 'Supervisor B'] * 20,
        'valor_total_mes': [5000.0 + i * 100 for i in range(40)],
        'qtd_pedidos_mes': [5 + (i % 10) for i in range(40)],
        'qtd_departamentos_diferentes': [2 + (i % 3) for i in range(40)],
        'qtd_produtos_diferentes': [10 + (i % 5) for i in range(40)],
        'ticket_medio_mes': [1000.0 + i * 10 for i in range(40)],
        'desconto_medio_mes': [50.0 + i * 2 for i in range(40)],
        'qtd_compras_90d_anteriores': [10 + (i % 5) for i in range(40)],
        'valor_total_90d_anteriores': [10000.0 + i * 200 for i in range(40)],
        'dias_desde_ultima_compra': [15, 45, 90, 120] * 10,
        'recencia_score': [5, 4, 3, 2] * 10,
        'frequencia_score': [3, 4, 5, 2] * 10,
        'valor_score': [4, 5, 3, 2] * 10,
        'rfv_score': [12, 13, 11, 6] * 10,
        'estado': ['SP', 'RJ', 'MG', 'RS'] * 10,
        'municipio': ['São Paulo', 'Rio de Janeiro', 'Belo Horizonte', 'Porto Alegre'] * 10,
        'churn_provavel': [0, 0, 1, 1] * 10  # Target
    })


@pytest.mark.unit
@pytest.mark.ml
class TestModelTraining:
    """Testes para treinamento de modelos."""
    
    def test_train_model_bater_meta_returns_valid_model(self, sample_features_vendedor):
        """Testa que train_model_bater_meta() retorna um modelo sklearn válido."""
        model, metrics = train_model_bater_meta(
            sample_features_vendedor,
            model_type='logistic_regression',
            test_size=0.3,
            temporal_split=True
        )
        
        # Verifica que retorna tupla
        assert isinstance(model, MetaModel), "Deveria retornar MetaModel"
        assert isinstance(metrics, dict), "Deveria retornar dicionário de métricas"
        
        # Verifica que modelo é sklearn válido
        assert model.model is not None, "Modelo sklearn não deveria ser None"
        assert hasattr(model.model, 'predict'), "Modelo deveria ter método predict"
        assert hasattr(model.model, 'predict_proba'), "Modelo deveria ter método predict_proba"
        assert model.is_trained, "Modelo deveria estar marcado como treinado"
        
        # Verifica que métricas têm valores esperados
        assert 'accuracy' in metrics
        assert 'precision' in metrics
        assert 'recall' in metrics
        assert 'roc_auc' in metrics
        assert 'confusion_matrix' in metrics
        
        # Verifica que métricas são valores numéricos válidos
        assert 0 <= metrics['accuracy'] <= 1, "Accuracy deve estar entre 0 e 1"
        assert 0 <= metrics['roc_auc'] <= 1, "ROC-AUC deve estar entre 0 e 1"
        assert isinstance(metrics['confusion_matrix'], list)
    
    def test_train_model_churn_returns_valid_model(self, sample_features_cliente):
        """Testa que train_model_churn() retorna um modelo sklearn válido."""
        model, metrics = train_model_churn(
            sample_features_cliente,
            model_type='logistic_regression',
            test_size=0.3,
            temporal_split=True
        )
        
        # Verifica que retorna tupla
        assert isinstance(model, ChurnModel), "Deveria retornar ChurnModel"
        assert isinstance(metrics, dict), "Deveria retornar dicionário de métricas"
        
        # Verifica que modelo é sklearn válido
        assert model.model is not None, "Modelo sklearn não deveria ser None"
        assert hasattr(model.model, 'predict'), "Modelo deveria ter método predict"
        assert hasattr(model.model, 'predict_proba'), "Modelo deveria ter método predict_proba"
        assert model.is_trained, "Modelo deveria estar marcado como treinado"
        
        # Verifica que métricas têm valores esperados
        assert 'accuracy' in metrics
        assert 'precision' in metrics
        assert 'recall' in metrics
        assert 'roc_auc' in metrics
        assert 'confusion_matrix' in metrics
    
    def test_train_model_bater_meta_gradient_boosting(self, sample_features_vendedor):
        """Testa treinamento de modelo de meta com Gradient Boosting."""
        model, metrics = train_model_bater_meta(
            sample_features_vendedor,
            model_type='gradient_boosting',
            test_size=0.3,
            temporal_split=True
        )
        
        assert isinstance(model, MetaModel)
        assert model.model_type == 'gradient_boosting'
        assert isinstance(model.model, GradientBoostingClassifier)
        assert model.is_trained
        
        # Verifica métricas
        assert metrics['accuracy'] >= 0
        assert metrics['roc_auc'] >= 0
    
    def test_train_model_churn_gradient_boosting(self, sample_features_cliente):
        """Testa treinamento de modelo de churn com Gradient Boosting."""
        model, metrics = train_model_churn(
            sample_features_cliente,
            model_type='gradient_boosting',
            test_size=0.3,
            temporal_split=True
        )
        
        assert isinstance(model, ChurnModel)
        assert model.model_type == 'gradient_boosting'
        assert isinstance(model.model, GradientBoostingClassifier)
        assert model.is_trained


@pytest.mark.unit
@pytest.mark.ml
class TestModelPredictions:
    """Testes para predições de modelos."""
    
    def test_meta_model_predictions_with_mock_features(self, sample_features_vendedor):
        """Testa predições do modelo de meta com features mock."""
        # Treina modelo
        model, _ = train_model_bater_meta(
            sample_features_vendedor,
            model_type='logistic_regression',
            test_size=0.3,
            temporal_split=True
        )
        
        # Cria features mock para predição
        # Usa as mesmas colunas que o modelo espera
        X_test = model.prepare_features(sample_features_vendedor)[0]
        mock_features = X_test.head(5)
        
        # Faz predições
        predictions = model.predict(mock_features)
        
        # Verifica que predições são válidas
        assert isinstance(predictions, np.ndarray), "Predições deveriam ser array numpy"
        assert len(predictions) == len(mock_features), "Número de predições deveria corresponder ao número de amostras"
        assert all(0 <= p <= 1 for p in predictions), "Probabilidades deveriam estar entre 0 e 1"
        
        # Verifica que pode fazer predições de classe também
        classes = model.model.predict(mock_features.values if hasattr(mock_features, 'values') else mock_features)
        assert len(classes) == len(mock_features)
        assert all(c in [0, 1] for c in classes), "Classes deveriam ser 0 ou 1"
    
    def test_churn_model_predictions_with_mock_features(self, sample_features_cliente):
        """Testa predições do modelo de churn com features mock."""
        # Treina modelo
        model, _ = train_model_churn(
            sample_features_cliente,
            model_type='logistic_regression',
            test_size=0.3,
            temporal_split=True
        )
        
        # Cria features mock para predição
        X_test = model.prepare_features(sample_features_cliente)[0]
        mock_features = X_test.head(5)
        
        # Faz predições
        predictions = model.predict(mock_features)
        
        # Verifica que predições são válidas
        assert isinstance(predictions, np.ndarray), "Predições deveriam ser array numpy"
        assert len(predictions) == len(mock_features), "Número de predições deveria corresponder ao número de amostras"
        assert all(0 <= p <= 1 for p in predictions), "Probabilidades deveriam estar entre 0 e 1"
        
        # Testa conversão para score de risco
        for prob in predictions:
            risk_score = model.predict_risk_score(prob)
            assert risk_score in ['baixo', 'medio', 'alto'], \
                f"Risk score deveria ser 'baixo', 'medio' ou 'alto', encontrado: {risk_score}"
    
    def test_meta_model_predictions_shape(self, sample_features_vendedor):
        """Testa que predições têm shape correto."""
        model, _ = train_model_bater_meta(
            sample_features_vendedor,
            model_type='logistic_regression',
            test_size=0.3,
            temporal_split=True
        )
        
        # Prepara features
        X, _ = model.prepare_features(sample_features_vendedor)
        
        # Testa com uma amostra
        single_sample = X.head(1)
        predictions = model.predict(single_sample)
        
        assert predictions.shape == (1,), "Predição de uma amostra deveria ter shape (1,)"
        
        # Testa com múltiplas amostras
        multiple_samples = X.head(10)
        predictions = model.predict(multiple_samples)
        
        assert predictions.shape == (10,), "Predições de 10 amostras deveriam ter shape (10,)"


@pytest.mark.unit
@pytest.mark.ml
class TestModelSaving:
    """Testes para salvamento de modelos."""
    
    def test_meta_model_save_and_load(self, sample_features_vendedor):
        """Testa que modelo de meta é salvo e carregado corretamente."""
        # Treina modelo
        model, _ = train_model_bater_meta(
            sample_features_vendedor,
            model_type='logistic_regression',
            test_size=0.3,
            temporal_split=True
        )
        
        # Salva em arquivo temporário
        with tempfile.NamedTemporaryFile(suffix='.joblib', delete=False) as f:
            temp_path = f.name
        
        try:
            # Salva modelo
            model.save(temp_path)
            
            # Verifica que arquivo foi criado
            assert os.path.exists(temp_path), "Arquivo de modelo deveria ser criado"
            assert os.path.getsize(temp_path) > 0, "Arquivo de modelo não deveria estar vazio"
            
            # Carrega modelo
            loaded_model = MetaModel(model_type='logistic_regression')
            loaded_model.load(temp_path)
            
            # Verifica que modelo carregado é válido
            assert loaded_model.is_trained, "Modelo carregado deveria estar marcado como treinado"
            assert loaded_model.model is not None, "Modelo sklearn não deveria ser None"
            assert loaded_model.model_type == model.model_type, "Tipo de modelo deveria ser o mesmo"
            
            # Verifica que pode fazer predições
            X_test = model.prepare_features(sample_features_vendedor)[0]
            original_predictions = model.predict(X_test.head(5))
            loaded_predictions = loaded_model.predict(X_test.head(5))
            
            # Predições deveriam ser similares (com tolerância)
            np.testing.assert_array_almost_equal(
                original_predictions,
                loaded_predictions,
                decimal=4,
                err_msg="Predições do modelo carregado deveriam ser similares às originais"
            )
        
        finally:
            # Limpa arquivo temporário
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_churn_model_save_and_load(self, sample_features_cliente):
        """Testa que modelo de churn é salvo e carregado corretamente."""
        # Treina modelo
        model, _ = train_model_churn(
            sample_features_cliente,
            model_type='logistic_regression',
            test_size=0.3,
            temporal_split=True
        )
        
        # Salva em arquivo temporário
        with tempfile.NamedTemporaryFile(suffix='.joblib', delete=False) as f:
            temp_path = f.name
        
        try:
            # Salva modelo
            model.save(temp_path)
            
            # Verifica que arquivo foi criado
            assert os.path.exists(temp_path), "Arquivo de modelo deveria ser criado"
            
            # Carrega modelo
            loaded_model = ChurnModel(model_type='logistic_regression')
            loaded_model.load(temp_path)
            
            # Verifica que modelo carregado é válido
            assert loaded_model.is_trained, "Modelo carregado deveria estar marcado como treinado"
            assert loaded_model.model is not None, "Modelo sklearn não deveria ser None"
            
            # Verifica que pode fazer predições
            X_test = model.prepare_features(sample_features_cliente)[0]
            original_predictions = model.predict(X_test.head(5))
            loaded_predictions = loaded_model.predict(X_test.head(5))
            
            np.testing.assert_array_almost_equal(
                original_predictions,
                loaded_predictions,
                decimal=4,
                err_msg="Predições do modelo carregado deveriam ser similares às originais"
            )
        
        finally:
            # Limpa arquivo temporário
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_model_save_creates_directory(self, sample_features_vendedor):
        """Testa que salvamento cria diretório se não existir."""
        # Treina modelo
        model, _ = train_model_bater_meta(
            sample_features_vendedor,
            model_type='logistic_regression',
            test_size=0.3,
            temporal_split=True
        )
        
        # Cria caminho para diretório que não existe
        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts_dir = Path(temp_dir) / "artefacts" / "subdir"
            model_file = artifacts_dir / "test_model.joblib"
            
            # Salva modelo (deveria criar diretório)
            model.save(str(model_file))
            
            # Verifica que diretório foi criado
            assert artifacts_dir.exists(), "Diretório deveria ser criado automaticamente"
            assert model_file.exists(), "Arquivo de modelo deveria ser criado"


@pytest.mark.unit
@pytest.mark.ml
class TestModelFeatureImportance:
    """Testes para feature importance."""
    
    def test_meta_model_feature_importance(self, sample_features_vendedor):
        """Testa que modelo de meta retorna feature importance."""
        model, _ = train_model_bater_meta(
            sample_features_vendedor,
            model_type='gradient_boosting',
            test_size=0.3,
            temporal_split=True
        )
        
        # Obtém feature importance
        df_importance = model.get_feature_importance()
        
        # Verifica estrutura
        assert isinstance(df_importance, pd.DataFrame), "Feature importance deveria ser DataFrame"
        assert 'feature' in df_importance.columns, "DataFrame deveria ter coluna 'feature'"
        assert 'importance' in df_importance.columns, "DataFrame deveria ter coluna 'importance'"
        assert len(df_importance) > 0, "Deveria ter pelo menos uma feature"
        
        # Verifica que importâncias são válidas
        assert all(df_importance['importance'] >= 0), "Importâncias deveriam ser >= 0"
        
        # Verifica que está ordenado
        importances_sorted = df_importance['importance'].values
        assert all(importances_sorted[i] >= importances_sorted[i+1] 
                  for i in range(len(importances_sorted)-1)), \
            "Importâncias deveriam estar ordenadas (decrescente)"
    
    def test_churn_model_feature_importance(self, sample_features_cliente):
        """Testa que modelo de churn retorna feature importance."""
        model, _ = train_model_churn(
            sample_features_cliente,
            model_type='gradient_boosting',
            test_size=0.3,
            temporal_split=True
        )
        
        # Obtém feature importance
        df_importance = model.get_feature_importance()
        
        # Verifica estrutura
        assert isinstance(df_importance, pd.DataFrame), "Feature importance deveria ser DataFrame"
        assert len(df_importance) > 0, "Deveria ter pelo menos uma feature"


@pytest.mark.unit
@pytest.mark.ml
class TestModelEdgeCases:
    """Testes para casos extremos dos modelos."""
    
    def test_meta_model_minimum_features(self, sample_features_vendedor):
        """Testa predição com número mínimo de features."""
        model, _ = train_model_bater_meta(
            sample_features_vendedor,
            model_type='logistic_regression',
            test_size=0.3,
            temporal_split=True
        )
        
        # Prepara features
        X, _ = model.prepare_features(sample_features_vendedor)
        
        # Testa com apenas uma linha
        single_row = X.head(1)
        predictions = model.predict(single_row)
        
        assert len(predictions) == 1, "Deveria retornar uma predição"
        assert 0 <= predictions[0] <= 1, "Probabilidade deveria estar entre 0 e 1"
    
    def test_churn_model_minimum_features(self, sample_features_cliente):
        """Testa predição com número mínimo de features."""
        model, _ = train_model_churn(
            sample_features_cliente,
            model_type='logistic_regression',
            test_size=0.3,
            temporal_split=True
        )
        
        # Prepara features
        X, _ = model.prepare_features(sample_features_cliente)
        
        # Testa com apenas uma linha
        single_row = X.head(1)
        predictions = model.predict(single_row)
        
        assert len(predictions) == 1, "Deveria retornar uma predição"
        assert 0 <= predictions[0] <= 1, "Probabilidade deveria estar entre 0 e 1"
    
    def test_model_untrained_predict_raises_error(self):
        """Testa que predição sem treinamento levanta erro."""
        model = MetaModel(model_type='logistic_regression')
        
        # Não treinou o modelo, deveria levantar erro
        with pytest.raises(ValueError, match="não foi treinado"):
            model.predict(pd.DataFrame({'feature1': [1.0], 'feature2': [2.0]}))
    
    def test_churn_model_risk_score_conversion(self):
        """Testa conversão de probabilidade em score de risco."""
        model = ChurnModel(model_type='gradient_boosting')
        
        # Testa diferentes probabilidades
        test_cases = [
            (0.2, 'baixo'),
            (0.3, 'medio'),
            (0.5, 'medio'),
            (0.7, 'medio'),
            (0.8, 'alto'),
        ]
        
        for prob, expected_score in test_cases:
            score = model.predict_risk_score(prob)
            assert score == expected_score, \
                f"Para probabilidade {prob}, esperado {expected_score}, obtido {score}"
