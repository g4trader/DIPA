"""
Modelo de ML para risco de churn.

Este módulo contém o modelo de machine learning para prever o
risco de churn de clientes.
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)
import joblib
import logging
from typing import Optional, Dict, List, Tuple
from pathlib import Path

from src.config import config
from src.features.churn_features import create_churn_features

logger = logging.getLogger(__name__)


class ChurnModel:
    """
    Modelo de ML para prever risco de churn.
    
    Usa Random Forest ou Gradient Boosting para classificação binária
    (churn = 1, não churn = 0).
    """
    
    def __init__(
        self,
        model_type: str = "random_forest",
        random_seed: Optional[int] = None
    ):
        """
        Inicializa o modelo.
        
        Args:
            model_type: Tipo de modelo ('random_forest' ou 'gradient_boosting')
            random_seed: Seed para reprodutibilidade
        """
        self.model_type = model_type
        self.random_seed = random_seed or config.ml.random_seed
        
        if model_type == "random_forest":
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=self.random_seed,
                n_jobs=-1
            )
        elif model_type == "gradient_boosting":
            self.model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                random_state=self.random_seed
            )
        else:
            raise ValueError(
                f"Tipo de modelo não suportado: {model_type}"
            )
        
        self.scaler = StandardScaler()
        self.label_encoders: Dict[str, LabelEncoder] = {}
        self.feature_columns: Optional[List[str]] = None
        self.is_trained = False
    
    def prepare_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepara features e target para treinamento.
        
        Args:
            df: DataFrame com features
            
        Returns:
            Tuple[pd.DataFrame, pd.Series]: Features e target
        """
        # Seleciona features
        feature_columns = [
            "total_vendas_90dias",
            "num_vendas_90dias",
            "total_vendas_30dias",
            "num_vendas_30dias",
            "dias_sem_venda",
            "total_vendas_historico",
            "num_vendas_historico",
            "media_vendas_mes",
            "recencia_score",
            "frequencia_score",
            "valor_score",
            "rfv_score",
            "tendencia_vendas",
        ]
        
        # Remove colunas que não existem
        feature_columns = [
            col for col in feature_columns if col in df.columns
        ]
        
        # Features e target
        X = df[feature_columns].fillna(0)
        y = df["churn"]
        
        # Codifica variáveis categóricas
        categorical_columns = ["cidade", "estado"]
        for col in categorical_columns:
            if col in df.columns:
                if col not in self.label_encoders:
                    self.label_encoders[col] = LabelEncoder()
                    X[col] = self.label_encoders[col].fit_transform(
                        df[col].fillna("unknown")
                    )
                else:
                    X[col] = self.label_encoders[col].transform(
                        df[col].fillna("unknown")
                    )
                feature_columns.append(col)
        
        self.feature_columns = feature_columns
        
        return X, y
    
    def train(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        test_size: float = 0.2,
        cv_folds: int = 5
    ) -> Dict:
        """
        Treina o modelo.
        
        Args:
            X: Features
            y: Target
            test_size: Proporção de dados de teste
            cv_folds: Número de folds para cross-validation
            
        Returns:
            dict: Métricas de avaliação
        """
        try:
            # Split dos dados
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=self.random_seed
            )
            
            # Normaliza features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Treina modelo
            logger.info("Treinando modelo...")
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
                scoring="roc_auc"
            )
            
            metrics = {
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "roc_auc": roc_auc,
                "cv_mean": cv_scores.mean(),
                "cv_std": cv_scores.std(),
                "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
            }
            
            logger.info(f"Métricas: {metrics}")
            
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
            np.ndarray: Predições (probabilidades)
        """
        if not self.is_trained:
            raise ValueError("Modelo não foi treinado ainda")
        
        # Seleciona features
        X_features = X[self.feature_columns].fillna(0)
        
        # Codifica variáveis categóricas
        for col, encoder in self.label_encoders.items():
            if col in X_features.columns:
                X_features[col] = encoder.transform(
                    X_features[col].fillna("unknown")
                )
        
        # Normaliza
        X_scaled = self.scaler.transform(X_features)
        
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
            return "baixo"
        elif proba < 0.7:
            return "medio"
        else:
            return "alto"
    
    def save(self, filepath: Optional[str] = None):
        """
        Salva o modelo.
        
        Args:
            filepath: Caminho para salvar o modelo
        """
        if filepath is None:
            filepath = config.ml.models_dir / "churn_model.joblib"
        
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        joblib.dump(
            {
                "model": self.model,
                "scaler": self.scaler,
                "label_encoders": self.label_encoders,
                "feature_columns": self.feature_columns,
                "model_type": self.model_type,
            },
            filepath
        )
        
        logger.info(f"Modelo salvo em {filepath}")
    
    def load(self, filepath: Optional[str] = None):
        """
        Carrega o modelo.
        
        Args:
            filepath: Caminho para carregar o modelo
        """
        if filepath is None:
            filepath = config.ml.models_dir / "churn_model.joblib"
        
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"Modelo não encontrado: {filepath}")
        
        data = joblib.load(filepath)
        
        self.model = data["model"]
        self.scaler = data["scaler"]
        self.label_encoders = data["label_encoders"]
        self.feature_columns = data["feature_columns"]
        self.model_type = data["model_type"]
        self.is_trained = True
        
        logger.info(f"Modelo carregado de {filepath}")
    
    def train_from_datawarehouse(
        self,
        test_size: float = 0.2,
        cv_folds: int = 5
    ) -> Dict:
        """
        Treina o modelo usando dados do data warehouse.
        
        Args:
            test_size: Proporção de dados de teste
            cv_folds: Número de folds para cross-validation
            
        Returns:
            dict: Métricas de avaliação
        """
        # Cria features
        df = create_churn_features()
        
        # Prepara features
        X, y = self.prepare_features(df)
        
        # Treina modelo
        metrics = self.train(X, y, test_size=test_size, cv_folds=cv_folds)
        
        return metrics



