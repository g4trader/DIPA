"""
Modelos de Machine Learning para Dipam AI.

Este módulo contém funções para treinar, avaliar e usar modelos de ML
para probabilidade de bater meta e risco de churn.
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report,
    roc_curve, auc
)
import joblib
import logging
from typing import Dict, Tuple, Any, Optional
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns

from src.config import config

logger = logging.getLogger(__name__)


class MetaModel:
    """
    Modelo de ML para probabilidade de bater meta.
    
    Wrapper para modelos de classificação binária que prevê se um vendedor
    vai bater a meta em um determinado mês.
    """
    
    def __init__(self, model_type: str = 'gradient_boosting'):
        """
        Inicializa o modelo.
        
        Args:
            model_type: Tipo de modelo ('logistic_regression' ou 'gradient_boosting')
        """
        self.model_type = model_type
        self.model = None
        self.scaler = None
        self.label_encoders = {}
        self.feature_columns = None
        self.is_trained = False
        
        if model_type == 'logistic_regression':
            self.model = LogisticRegression(
                max_iter=1000,
                random_state=42,
                class_weight='balanced'  # Para lidar com desbalanceamento
            )
        elif model_type == 'gradient_boosting':
            self.model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=42,
                subsample=0.8
            )
        else:
            raise ValueError(f"Tipo de modelo não suportado: {model_type}")
        
        self.scaler = StandardScaler()
    
    def prepare_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepara features e target para treinamento.
        
        Remove colunas não numéricas e não features, separa target.
        
        Args:
            df: DataFrame com features e target
            
        Returns:
            Tuple[pd.DataFrame, pd.Series]: Features e target preparados
        """
        # Colunas a excluir (identificadores, targets, etc.)
        exclude_cols = [
            'mes_ano', 'ano', 'mes',
            'vendedor_id', 'vendedor', 'vendedor_nome',
            'supervisor', 'pasta',
            'bateu_meta',  # Target
        ]
        
        # Seleciona features numéricas
        feature_cols = [col for col in df.columns if col not in exclude_cols]
        
        # Remove colunas com muitos valores faltantes
        feature_cols = [col for col in feature_cols if df[col].notna().sum() / len(df) > 0.5]
        
        # Features e target
        X = df[feature_cols].copy()
        y = df['bateu_meta'].copy()
        
        # Preenche valores faltantes com 0
        X = X.fillna(0)
        
        # Substitui infinitos e valores muito grandes por NaN e depois por 0 (apenas em colunas numéricas)
        numeric_cols = X.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            X[col] = X[col].replace([np.inf, -np.inf], np.nan)
            # Substitui valores muito grandes (> 1e10) por NaN
            X.loc[X[col].abs() > 1e10, col] = np.nan
        X = X.fillna(0)
        
        # Codifica variáveis categóricas se houver
        categorical_cols = X.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            if col not in self.label_encoders:
                self.label_encoders[col] = LabelEncoder()
                X[col] = self.label_encoders[col].fit_transform(X[col].astype(str))
            else:
                X[col] = self.label_encoders[col].transform(X[col].astype(str))
        
        self.feature_columns = X.columns.tolist()
        
        return X, y
    
    def train(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        df_original: Optional[pd.DataFrame] = None,
        test_size: float = 0.2,
        temporal_split: bool = True,
        cv_folds: int = 5
    ) -> Dict[str, Any]:
        """
        Treina o modelo.
        
        Args:
            X: Features
            y: Target
            df_original: DataFrame original com mes_ano para split temporal
            test_size: Proporção de dados de teste
            temporal_split: Se True, usa split temporal (por mes_ano)
            cv_folds: Número de folds para cross-validation
            
        Returns:
            dict: Métricas de avaliação
        """
        try:
            if temporal_split and df_original is not None:
                # Split temporal: ordena por mes_ano e usa últimos meses como validação
                df_original = df_original.sort_values('mes_ano').reset_index(drop=True)
                split_idx = int(len(df_original) * (1 - test_size))
                train_indices = df_original.index[:split_idx]
                test_indices = df_original.index[split_idx:]
                
                X_train = X.iloc[train_indices].reset_index(drop=True)
                X_test = X.iloc[test_indices].reset_index(drop=True)
                y_train = y.iloc[train_indices].reset_index(drop=True)
                y_test = y.iloc[test_indices].reset_index(drop=True)
                
                logger.info(f"Split temporal: treino até {df_original.iloc[split_idx-1]['mes_ano']}, teste a partir de {df_original.iloc[split_idx]['mes_ano']}")
            elif temporal_split:
                # Fallback: assume que X já está ordenado por tempo
                split_idx = int(len(X) * (1 - test_size))
                X_train = X.iloc[:split_idx]
                X_test = X.iloc[split_idx:]
                y_train = y.iloc[:split_idx]
                y_test = y.iloc[split_idx:]
            else:
                # Split aleatório
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=test_size, random_state=42, stratify=y
                )
            
            logger.info(f"Treino: {len(X_train)} registros, Teste: {len(X_test)} registros")
            logger.info(f"Distribuição de classes no treino: {y_train.value_counts().to_dict()}")
            
            # Normaliza features (apenas para Logistic Regression)
            if self.model_type == 'logistic_regression':
                X_train_scaled = self.scaler.fit_transform(X_train)
                X_test_scaled = self.scaler.transform(X_test)
            else:
                # Gradient Boosting não precisa normalização
                X_train_scaled = X_train
                X_test_scaled = X_test
            
            # Treina modelo
            logger.info(f"Treinando modelo {self.model_type}...")
            self.model.fit(X_train_scaled, y_train)
            
            # Predições
            y_pred = self.model.predict(X_test_scaled)
            y_pred_proba = self.model.predict_proba(X_test_scaled)[:, 1]
            
            # Métricas
            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred)
            recall = recall_score(y_test, y_pred)
            f1 = f1_score(y_test, y_pred)
            roc_auc = roc_auc_score(y_test, y_pred_proba)
            
            # Cross-validation
            cv_scores = cross_val_score(
                self.model,
                X_train_scaled,
                y_train,
                cv=cv_folds,
                scoring='roc_auc'
            )
            
            # Matriz de confusão
            cm = confusion_matrix(y_test, y_pred)
            
            metrics = {
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall,
                'f1': f1,
                'roc_auc': roc_auc,
                'cv_mean': cv_scores.mean(),
                'cv_std': cv_scores.std(),
                'confusion_matrix': cm.tolist(),
                'y_test': y_test.values,
                'y_pred': y_pred,
                'y_pred_proba': y_pred_proba,
            }
            
            logger.info(f"Métricas - Accuracy: {accuracy:.4f}, ROC-AUC: {roc_auc:.4f}")
            
            self.is_trained = True
            
            return metrics
        
        except Exception as e:
            logger.error(f"Erro ao treinar modelo: {str(e)}")
            raise
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Faz predições.
        
        Args:
            X: Features
            
        Returns:
            np.ndarray: Probabilidades de bater meta (0-1)
        """
        if not self.is_trained:
            raise ValueError("Modelo não foi treinado ainda")
        
        # Seleciona features
        X_features = X[self.feature_columns].copy()
        
        # Preenche valores faltantes
        X_features = X_features.fillna(0)
        
        # Codifica variáveis categóricas
        for col, encoder in self.label_encoders.items():
            if col in X_features.columns:
                X_features[col] = encoder.transform(X_features[col].astype(str))
        
        # Normaliza se necessário
        if self.model_type == 'logistic_regression':
            X_scaled = self.scaler.transform(X_features)
        else:
            X_scaled = X_features
        
        # Predições
        y_proba = self.model.predict_proba(X_scaled)[:, 1]
        
        return y_proba
    
    def get_feature_importance(self) -> pd.DataFrame:
        """
        Retorna importância das features.
        
        Returns:
            pd.DataFrame: DataFrame com features e importância
        """
        if not self.is_trained:
            raise ValueError("Modelo não foi treinado ainda")
        
        if hasattr(self.model, 'feature_importances_'):
            importance = self.model.feature_importances_
        elif hasattr(self.model, 'coef_'):
            # Para Logistic Regression, usa valores absolutos dos coeficientes
            importance = np.abs(self.model.coef_[0])
        else:
            return pd.DataFrame()
        
        df_importance = pd.DataFrame({
            'feature': self.feature_columns,
            'importance': importance
        }).sort_values('importance', ascending=False)
        
        return df_importance
    
    def save(self, filepath: Optional[str] = None):
        """
        Salva o modelo.
        
        Args:
            filepath: Caminho para salvar (None = usa path padrão)
        """
        if filepath is None:
            filepath = config.ml.models_dir / f"meta_model_{self.model_type}.joblib"
        
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        joblib.dump(
            {
                'model': self.model,
                'scaler': self.scaler,
                'label_encoders': self.label_encoders,
                'feature_columns': self.feature_columns,
                'model_type': self.model_type,
            },
            filepath
        )
        
        logger.info(f"Modelo salvo em: {filepath}")
    
    def load(self, filepath: Optional[str] = None):
        """
        Carrega o modelo.
        
        Args:
            filepath: Caminho para carregar (None = usa path padrão)
        """
        if filepath is None:
            filepath = config.ml.models_dir / f"meta_model_{self.model_type}.joblib"
        
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"Modelo não encontrado: {filepath}")
        
        data = joblib.load(filepath)
        
        self.model = data['model']
        self.scaler = data['scaler']
        self.label_encoders = data['label_encoders']
        self.feature_columns = data['feature_columns']
        self.model_type = data['model_type']
        self.is_trained = True
        
        logger.info(f"Modelo carregado de: {filepath}")


class ChurnModel:
    """
    Modelo de ML para risco de churn.
    
    Wrapper para modelos de classificação binária que prevê risco de churn
    de clientes.
    """
    
    def __init__(self, model_type: str = 'gradient_boosting'):
        """
        Inicializa o modelo.
        
        Args:
            model_type: Tipo de modelo ('logistic_regression' ou 'gradient_boosting')
        """
        self.model_type = model_type
        self.model = None
        self.scaler = None
        self.label_encoders = {}
        self.feature_columns = None
        self.is_trained = False
        
        if model_type == 'logistic_regression':
            self.model = LogisticRegression(
                max_iter=1000,
                random_state=42,
                class_weight='balanced'
            )
        elif model_type == 'gradient_boosting':
            self.model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=42,
                subsample=0.8
            )
        else:
            raise ValueError(f"Tipo de modelo não suportado: {model_type}")
        
        self.scaler = StandardScaler()
    
    def prepare_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepara features e target para treinamento.
        
        Args:
            df: DataFrame com features e target
            
        Returns:
            Tuple[pd.DataFrame, pd.Series]: Features e target preparados
        """
        # Colunas a excluir
        exclude_cols = [
            'mes_ano', 'ano', 'mes',
            'id_cliente', 'codigo_cliente', 'nome_cliente',
            'vendedor_id', 'vendedor', 'supervisor', 'pasta', 'rota',
            'churn_provavel',  # Target
            'churn_risk_category',  # Categoria derivada
        ]
        
        # Seleciona features numéricas
        feature_cols = [col for col in df.columns if col not in exclude_cols]
        
        # Remove colunas com muitos valores faltantes
        feature_cols = [col for col in feature_cols if df[col].notna().sum() / len(df) > 0.5]
        
        # Features e target
        X = df[feature_cols].copy()
        y = df['churn_provavel'].copy()
        
        # Preenche valores faltantes
        X = X.fillna(0)
        
        # Substitui infinitos e valores muito grandes por NaN e depois por 0 (apenas em colunas numéricas)
        numeric_cols = X.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            X[col] = X[col].replace([np.inf, -np.inf], np.nan)
            # Substitui valores muito grandes (> 1e10) por NaN
            X.loc[X[col].abs() > 1e10, col] = np.nan
        X = X.fillna(0)
        
        # Codifica variáveis categóricas
        categorical_cols = X.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            if col not in self.label_encoders:
                self.label_encoders[col] = LabelEncoder()
                X[col] = self.label_encoders[col].fit_transform(X[col].astype(str))
            else:
                X[col] = self.label_encoders[col].transform(X[col].astype(str))
        
        self.feature_columns = X.columns.tolist()
        
        return X, y
    
    def train(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        df_original: Optional[pd.DataFrame] = None,
        test_size: float = 0.2,
        temporal_split: bool = True,
        cv_folds: int = 5
    ) -> Dict[str, Any]:
        """
        Treina o modelo.
        
        Args:
            X: Features
            y: Target
            df_original: DataFrame original com mes_ano para split temporal
            test_size: Proporção de dados de teste
            temporal_split: Se True, usa split temporal
            cv_folds: Número de folds para cross-validation
            
        Returns:
            dict: Métricas de avaliação
        """
        try:
            if temporal_split and df_original is not None:
                # Split temporal: ordena por mes_ano e usa últimos meses como validação
                df_original = df_original.sort_values('mes_ano').reset_index(drop=True)
                split_idx = int(len(df_original) * (1 - test_size))
                train_indices = df_original.index[:split_idx]
                test_indices = df_original.index[split_idx:]
                
                X_train = X.iloc[train_indices].reset_index(drop=True)
                X_test = X.iloc[test_indices].reset_index(drop=True)
                y_train = y.iloc[train_indices].reset_index(drop=True)
                y_test = y.iloc[test_indices].reset_index(drop=True)
                
                logger.info(f"Split temporal: treino até {df_original.iloc[split_idx-1]['mes_ano']}, teste a partir de {df_original.iloc[split_idx]['mes_ano']}")
            elif temporal_split:
                # Fallback: assume que X já está ordenado por tempo
                split_idx = int(len(X) * (1 - test_size))
                X_train = X.iloc[:split_idx]
                X_test = X.iloc[split_idx:]
                y_train = y.iloc[:split_idx]
                y_test = y.iloc[split_idx:]
            else:
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=test_size, random_state=42, stratify=y
                )
            
            logger.info(f"Treino: {len(X_train)} registros, Teste: {len(X_test)} registros")
            logger.info(f"Distribuição de classes no treino: {y_train.value_counts().to_dict()}")
            
            # Normaliza se necessário
            if self.model_type == 'logistic_regression':
                X_train_scaled = self.scaler.fit_transform(X_train)
                X_test_scaled = self.scaler.transform(X_test)
            else:
                X_train_scaled = X_train
                X_test_scaled = X_test
            
            # Treina modelo
            logger.info(f"Treinando modelo {self.model_type}...")
            self.model.fit(X_train_scaled, y_train)
            
            # Predições
            y_pred = self.model.predict(X_test_scaled)
            y_pred_proba = self.model.predict_proba(X_test_scaled)[:, 1]
            
            # Métricas
            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred)
            recall = recall_score(y_test, y_pred)
            f1 = f1_score(y_test, y_pred)
            roc_auc = roc_auc_score(y_test, y_pred_proba)
            
            # Cross-validation
            cv_scores = cross_val_score(
                self.model,
                X_train_scaled,
                y_train,
                cv=cv_folds,
                scoring='roc_auc'
            )
            
            # Matriz de confusão
            cm = confusion_matrix(y_test, y_pred)
            
            metrics = {
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall,
                'f1': f1,
                'roc_auc': roc_auc,
                'cv_mean': cv_scores.mean(),
                'cv_std': cv_scores.std(),
                'confusion_matrix': cm.tolist(),
                'y_test': y_test.values,
                'y_pred': y_pred,
                'y_pred_proba': y_pred_proba,
            }
            
            logger.info(f"Métricas - Accuracy: {accuracy:.4f}, ROC-AUC: {roc_auc:.4f}")
            
            self.is_trained = True
            
            return metrics
        
        except Exception as e:
            logger.error(f"Erro ao treinar modelo: {str(e)}")
            raise
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Faz predições.
        
        Args:
            X: Features
            
        Returns:
            np.ndarray: Probabilidades de churn (0-1)
        """
        if not self.is_trained:
            raise ValueError("Modelo não foi treinado ainda")
        
        # Seleciona features
        X_features = X[self.feature_columns].copy()
        X_features = X_features.fillna(0)
        
        # Codifica variáveis categóricas
        for col, encoder in self.label_encoders.items():
            if col in X_features.columns:
                X_features[col] = encoder.transform(X_features[col].astype(str))
        
        # Normaliza se necessário
        if self.model_type == 'logistic_regression':
            X_scaled = self.scaler.transform(X_features)
        else:
            X_scaled = X_features
        
        # Predições
        y_proba = self.model.predict_proba(X_scaled)[:, 1]
        
        return y_proba
    
    def predict_risk_score(self, proba: float) -> str:
        """
        Converte probabilidade em score de risco.
        
        Args:
            proba: Probabilidade de churn (0-1)
            
        Returns:
            str: Score de risco ('baixo', 'medio', 'alto')
        """
        if proba < 0.3:
            return 'baixo'
        elif proba < 0.7:
            return 'medio'
        else:
            return 'alto'
    
    def get_feature_importance(self) -> pd.DataFrame:
        """
        Retorna importância das features.
        
        Returns:
            pd.DataFrame: DataFrame com features e importância
        """
        if not self.is_trained:
            raise ValueError("Modelo não foi treinado ainda")
        
        if hasattr(self.model, 'feature_importances_'):
            importance = self.model.feature_importances_
        elif hasattr(self.model, 'coef_'):
            importance = np.abs(self.model.coef_[0])
        else:
            return pd.DataFrame()
        
        df_importance = pd.DataFrame({
            'feature': self.feature_columns,
            'importance': importance
        }).sort_values('importance', ascending=False)
        
        return df_importance
    
    def save(self, filepath: Optional[str] = None):
        """
        Salva o modelo.
        
        Args:
            filepath: Caminho para salvar (None = usa path padrão)
        """
        if filepath is None:
            filepath = config.ml.models_dir / f"churn_model_{self.model_type}.joblib"
        
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        joblib.dump(
            {
                'model': self.model,
                'scaler': self.scaler,
                'label_encoders': self.label_encoders,
                'feature_columns': self.feature_columns,
                'model_type': self.model_type,
            },
            filepath
        )
        
        logger.info(f"Modelo salvo em: {filepath}")
    
    def load(self, filepath: Optional[str] = None):
        """
        Carrega o modelo.
        
        Args:
            filepath: Caminho para carregar (None = usa path padrão)
        """
        if filepath is None:
            filepath = config.ml.models_dir / f"churn_model_{self.model_type}.joblib"
        
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"Modelo não encontrado: {filepath}")
        
        data = joblib.load(filepath)
        
        self.model = data['model']
        self.scaler = data['scaler']
        self.label_encoders = data['label_encoders']
        self.feature_columns = data['feature_columns']
        self.model_type = data['model_type']
        self.is_trained = True
        
        logger.info(f"Modelo carregado de: {filepath}")


def train_model_bater_meta(
    df_features: pd.DataFrame,
    model_type: str = 'gradient_boosting',
    test_size: float = 0.2,
    temporal_split: bool = True
) -> Tuple[MetaModel, Dict[str, Any]]:
    """
    Treina modelo para probabilidade de bater meta.
    
    Args:
        df_features: DataFrame com features de vendedor/mês
        model_type: Tipo de modelo ('logistic_regression' ou 'gradient_boosting')
        test_size: Proporção de dados de teste
        temporal_split: Se True, usa split temporal
        
    Returns:
        Tuple[MetaModel, Dict]: Modelo treinado e métricas
    """
    logger.info("Treinando modelo de bater meta...")
    
    # Cria modelo
    model = MetaModel(model_type=model_type)
    
    # Prepara features
    X, y = model.prepare_features(df_features)
    
    # Treina com split temporal usando mes_ano
    metrics = model.train(X, y, df_original=df_features, test_size=test_size, temporal_split=temporal_split)
    
    return model, metrics


def train_model_churn(
    df_features: pd.DataFrame,
    model_type: str = 'gradient_boosting',
    test_size: float = 0.2,
    temporal_split: bool = True
) -> Tuple[ChurnModel, Dict[str, Any]]:
    """
    Treina modelo para risco de churn.
    
    Args:
        df_features: DataFrame com features de cliente/mês
        model_type: Tipo de modelo ('logistic_regression' ou 'gradient_boosting')
        test_size: Proporção de dados de teste
        temporal_split: Se True, usa split temporal
        
    Returns:
        Tuple[ChurnModel, Dict]: Modelo treinado e métricas
    """
    logger.info("Treinando modelo de churn...")
    
    # Cria modelo
    model = ChurnModel(model_type=model_type)
    
    # Prepara features
    X, y = model.prepare_features(df_features)
    
    # Treina com split temporal usando mes_ano
    metrics = model.train(X, y, df_original=df_features, test_size=test_size, temporal_split=temporal_split)
    
    return model, metrics


def print_metrics(metrics: Dict[str, Any], model_name: str = "Modelo"):
    """
    Imprime métricas de avaliação formatadas.
    
    Args:
        metrics: Dicionário com métricas
        model_name: Nome do modelo
    """
    print(f"\n{'='*60}")
    print(f"Métricas de Avaliação - {model_name}")
    print(f"{'='*60}")
    print(f"Accuracy:  {metrics['accuracy']:.4f}")
    print(f"Precision: {metrics['precision']:.4f}")
    print(f"Recall:    {metrics['recall']:.4f}")
    print(f"F1-Score:  {metrics['f1']:.4f}")
    print(f"ROC-AUC:   {metrics['roc_auc']:.4f}")
    print(f"CV Mean:   {metrics['cv_mean']:.4f} (+/- {metrics['cv_std']:.4f})")
    print()
    print("Matriz de Confusão:")
    cm = np.array(metrics['confusion_matrix'])
    print(f"                Predito")
    print(f"              Não  Sim")
    print(f"Real  Não  {cm[0,0]:5d} {cm[0,1]:5d}")
    print(f"      Sim   {cm[1,0]:5d} {cm[1,1]:5d}")
    print()


def plot_feature_importance(model: Any, top_n: int = 20, figsize: Tuple[int, int] = (10, 8)):
    """
    Plota importância das features.
    
    Args:
        model: Modelo treinado (MetaModel ou ChurnModel)
        top_n: Número de features top para mostrar
        figsize: Tamanho da figura
    """
    df_importance = model.get_feature_importance()
    
    if df_importance.empty:
        logger.warning("Modelo não possui feature importance")
        return
    
    # Top N features
    df_top = df_importance.head(top_n)
    
    # Cria plot
    plt.figure(figsize=figsize)
    plt.barh(range(len(df_top)), df_top['importance'].values)
    plt.yticks(range(len(df_top)), df_top['feature'].values)
    plt.xlabel('Importância')
    plt.title(f'Top {top_n} Features Mais Importantes')
    plt.gca().invert_yaxis()
    plt.tight_layout()
    
    # Salva figura
    fig_path = config.ml.models_dir / f"feature_importance_{model.model_type}.png"
    plt.savefig(fig_path)
    logger.info(f"Feature importance salva em: {fig_path}")
    plt.close()

