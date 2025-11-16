#!/usr/bin/env python3
"""
Script de treinamento de modelos ML (FASE 5).

Treina modelos scikit-learn para:
- Churn de clientes
- Risco de meta de vendedores
- Oportunidades de crescimento

Uso:
    # Treinar todos os modelos
    DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db python -m scripts.train_ml_models --tipo_modelo=all --mes_inicio=2024-11 --mes_fim=2025-10
    
    # Treinar apenas churn
    DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db python -m scripts.train_ml_models --tipo_modelo=churn --mes_inicio=2024-11 --mes_fim=2025-10
    
    # Treinar apenas meta_risk
    DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db python -m scripts.train_ml_models --tipo_modelo=meta_risk --mes_inicio=2024-11 --mes_fim=2025-10
    
    # Treinar oportunidades (usa apenas mes_referencia)
    DB_TYPE=sqlite SQLITE_PATH=data/dipam_dw.db python -m scripts.train_ml_models --tipo_modelo=oportunidades --mes_referencia=2025-08
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime
import numpy as np

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report
import joblib

from src.config import config
from src.dw.connection import init_db, get_db_session
from src.ml.training_pipeline import (
    preparar_dataset_churn,
    preparar_dataset_meta_risk,
    preparar_dataset_oportunidades
)
from src.ml.model_registry import (
    update_model_info,
    get_model_info,
    get_registry_path
)

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Diretório para salvar modelos
MODELS_DIR = Path(root_dir / "models")
MODELS_DIR.mkdir(parents=True, exist_ok=True)


def treinar_modelo_churn(
    session,
    mes_inicio: str,
    mes_fim: str,
    test_size: float = 0.2
) -> Dict[str, Any]:
    """
    Treina modelo de churn de clientes.
    
    Args:
        session: Sessão SQLAlchemy
        mes_inicio: Mês inicial
        mes_fim: Mês final
        test_size: Proporção do dataset para teste
        
    Returns:
        Dict com métricas e informações do modelo
    """
    logger.info("=" * 80)
    logger.info("🚀 Treinando modelo de CHURN")
    logger.info("=" * 80)
    
    # Prepara dataset
    X, y, feature_names, metadata = preparar_dataset_churn(session, mes_inicio, mes_fim)
    
    if len(X) == 0:
        logger.error("❌ Dataset vazio, não é possível treinar")
        return {"sucesso": False, "erro": "Dataset vazio"}
    
    # Remove NaN/Inf
    mask = np.isfinite(X).all(axis=1) & np.isfinite(y)
    X = X[mask]
    y = y[mask]
    
    if len(X) == 0:
        logger.error("❌ Dataset sem dados válidos após limpeza")
        return {"sucesso": False, "erro": "Dataset sem dados válidos"}
    
    # Split train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y
    )
    
    logger.info(f"📊 Dataset: {len(X_train)} treino, {len(X_test)} teste")
    logger.info(f"   Features: {len(feature_names)}")
    logger.info(f"   Classes: {np.bincount(y_train)}")
    
    # Treina modelo (GradientBoostingClassifier - bom para dados desbalanceados)
    modelo = GradientBoostingClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        random_state=42,
        verbose=0
    )
    
    logger.info("🔄 Treinando modelo...")
    modelo.fit(X_train, y_train)
    
    # Avalia
    y_pred = modelo.predict(X_test)
    y_pred_proba = modelo.predict_proba(X_test)[:, 1]
    
    accuracy = accuracy_score(y_test, y_pred)
    try:
        roc_auc = roc_auc_score(y_test, y_pred_proba)
    except ValueError:
        roc_auc = None  # Pode falhar se houver apenas uma classe
    
    logger.info(f"✅ Métricas:")
    logger.info(f"   Accuracy: {accuracy:.4f}")
    if roc_auc:
        logger.info(f"   ROC-AUC: {roc_auc:.4f}")
    
    # Salva modelo
    model_path = MODELS_DIR / "churn_model.joblib"
    joblib.dump(modelo, model_path)
    logger.info(f"💾 Modelo salvo em {model_path}")
    
    # Atualiza registry
    update_model_info("churn", {
        "path": str(model_path.relative_to(root_dir)),
        "trained_at": datetime.utcnow().isoformat(),
        "mes_inicio": mes_inicio,
        "mes_fim": mes_fim,
        "n_samples": len(X),
        "n_train": len(X_train),
        "n_test": len(X_test),
        "accuracy": float(accuracy),
        "roc_auc": float(roc_auc) if roc_auc else None,
        "feature_names": feature_names,
        "treinado": True
    })
    
    return {
        "sucesso": True,
        "accuracy": float(accuracy),
        "roc_auc": float(roc_auc) if roc_auc else None,
        "n_samples": len(X),
        "model_path": str(model_path)
    }


def treinar_modelo_meta_risk(
    session,
    mes_inicio: str,
    mes_fim: str,
    test_size: float = 0.2
) -> Dict[str, Any]:
    """
    Treina modelo de risco de meta de vendedores.
    
    Args:
        session: Sessão SQLAlchemy
        mes_inicio: Mês inicial
        mes_fim: Mês final
        test_size: Proporção do dataset para teste
        
    Returns:
        Dict com métricas e informações do modelo
    """
    logger.info("=" * 80)
    logger.info("🚀 Treinando modelo de META_RISK")
    logger.info("=" * 80)
    
    # Prepara dataset
    X, y, feature_names, metadata = preparar_dataset_meta_risk(session, mes_inicio, mes_fim)
    
    if len(X) == 0:
        logger.error("❌ Dataset vazio, não é possível treinar")
        return {"sucesso": False, "erro": "Dataset vazio"}
    
    # Remove NaN/Inf
    mask = np.isfinite(X).all(axis=1) & np.isfinite(y)
    X = X[mask]
    y = y[mask]
    
    if len(X) == 0:
        logger.error("❌ Dataset sem dados válidos após limpeza")
        return {"sucesso": False, "erro": "Dataset sem dados válidos"}
    
    # Split train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y
    )
    
    logger.info(f"📊 Dataset: {len(X_train)} treino, {len(X_test)} teste")
    logger.info(f"   Features: {len(feature_names)}")
    logger.info(f"   Classes: {np.bincount(y_train)}")
    
    # Treina modelo (RandomForestClassifier - bom para features não lineares)
    modelo = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1,
        verbose=0
    )
    
    logger.info("🔄 Treinando modelo...")
    modelo.fit(X_train, y_train)
    
    # Avalia
    y_pred = modelo.predict(X_test)
    y_pred_proba = modelo.predict_proba(X_test)[:, 1]
    
    accuracy = accuracy_score(y_test, y_pred)
    try:
        roc_auc = roc_auc_score(y_test, y_pred_proba)
    except ValueError:
        roc_auc = None
    
    logger.info(f"✅ Métricas:")
    logger.info(f"   Accuracy: {accuracy:.4f}")
    if roc_auc:
        logger.info(f"   ROC-AUC: {roc_auc:.4f}")
    
    # Salva modelo
    model_path = MODELS_DIR / "meta_risk_model.joblib"
    joblib.dump(modelo, model_path)
    logger.info(f"💾 Modelo salvo em {model_path}")
    
    # Atualiza registry
    update_model_info("meta_risk", {
        "path": str(model_path.relative_to(root_dir)),
        "trained_at": datetime.utcnow().isoformat(),
        "mes_inicio": mes_inicio,
        "mes_fim": mes_fim,
        "n_samples": len(X),
        "n_train": len(X_train),
        "n_test": len(X_test),
        "accuracy": float(accuracy),
        "roc_auc": float(roc_auc) if roc_auc else None,
        "feature_names": feature_names,
        "treinado": True
    })
    
    return {
        "sucesso": True,
        "accuracy": float(accuracy),
        "roc_auc": float(roc_auc) if roc_auc else None,
        "n_samples": len(X),
        "model_path": str(model_path)
    }


def treinar_modelo_oportunidades(
    session,
    mes_referencia: str,
    test_size: float = 0.2
) -> Dict[str, Any]:
    """
    Treina modelo de oportunidades de crescimento.
    
    Args:
        session: Sessão SQLAlchemy
        mes_referencia: Mês de referência
        test_size: Proporção do dataset para teste
        
    Returns:
        Dict com métricas e informações do modelo
    """
    logger.info("=" * 80)
    logger.info("🚀 Treinando modelo de OPORTUNIDADES")
    logger.info("=" * 80)
    
    # Prepara dataset
    X, y, feature_names, metadata = preparar_dataset_oportunidades(session, mes_referencia)
    
    if len(X) == 0:
        logger.error("❌ Dataset vazio, não é possível treinar")
        return {"sucesso": False, "erro": "Dataset vazio"}
    
    # Remove NaN/Inf
    mask = np.isfinite(X).all(axis=1) & np.isfinite(y)
    X = X[mask]
    y = y[mask]
    
    if len(X) == 0:
        logger.error("❌ Dataset sem dados válidos após limpeza")
        return {"sucesso": False, "erro": "Dataset sem dados válidos"}
    
    # Split train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y
    )
    
    logger.info(f"📊 Dataset: {len(X_train)} treino, {len(X_test)} teste")
    logger.info(f"   Features: {len(feature_names)}")
    logger.info(f"   Classes: {np.bincount(y_train)}")
    
    # Treina modelo (GradientBoostingClassifier)
    modelo = GradientBoostingClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        random_state=42,
        verbose=0
    )
    
    logger.info("🔄 Treinando modelo...")
    modelo.fit(X_train, y_train)
    
    # Avalia
    y_pred = modelo.predict(X_test)
    y_pred_proba = modelo.predict_proba(X_test)[:, 1]
    
    accuracy = accuracy_score(y_test, y_pred)
    try:
        roc_auc = roc_auc_score(y_test, y_pred_proba)
    except ValueError:
        roc_auc = None
    
    logger.info(f"✅ Métricas:")
    logger.info(f"   Accuracy: {accuracy:.4f}")
    if roc_auc:
        logger.info(f"   ROC-AUC: {roc_auc:.4f}")
    
    # Salva modelo
    model_path = MODELS_DIR / "oportunidades_model.joblib"
    joblib.dump(modelo, model_path)
    logger.info(f"💾 Modelo salvo em {model_path}")
    
    # Atualiza registry
    update_model_info("oportunidades", {
        "path": str(model_path.relative_to(root_dir)),
        "trained_at": datetime.utcnow().isoformat(),
        "mes_referencia": mes_referencia,
        "n_samples": len(X),
        "n_train": len(X_train),
        "n_test": len(X_test),
        "accuracy": float(accuracy),
        "roc_auc": float(roc_auc) if roc_auc else None,
        "feature_names": feature_names,
        "treinado": True
    })
    
    return {
        "sucesso": True,
        "accuracy": float(accuracy),
        "roc_auc": float(roc_auc) if roc_auc else None,
        "n_samples": len(X),
        "model_path": str(model_path)
    }


def main():
    """Função principal do script."""
    parser = argparse.ArgumentParser(
        description="Treina modelos ML para churn, meta_risk e oportunidades (FASE 5)"
    )
    parser.add_argument(
        "--tipo_modelo",
        type=str,
        choices=["churn", "meta_risk", "oportunidades", "all"],
        default="all",
        help="Tipo de modelo a treinar"
    )
    parser.add_argument(
        "--mes_inicio",
        type=str,
        help="Mês inicial no formato YYYY-MM (obrigatório para churn e meta_risk)"
    )
    parser.add_argument(
        "--mes_fim",
        type=str,
        help="Mês final no formato YYYY-MM (obrigatório para churn e meta_risk)"
    )
    parser.add_argument(
        "--mes_referencia",
        type=str,
        help="Mês de referência no formato YYYY-MM (obrigatório para oportunidades)"
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("🚀 DIPAM COPILOT - Treinamento de Modelos ML (FASE 5)")
    logger.info("=" * 80)
    
    # Valida argumentos
    if args.tipo_modelo in ["churn", "meta_risk", "all"]:
        if not args.mes_inicio or not args.mes_fim:
            logger.error("❌ --mes_inicio e --mes_fim são obrigatórios para churn e meta_risk")
            sys.exit(1)
    
    if args.tipo_modelo in ["oportunidades", "all"]:
        if not args.mes_referencia:
            # Usa mes_fim como fallback se disponível
            if args.mes_fim:
                args.mes_referencia = args.mes_fim
            else:
                logger.error("❌ --mes_referencia é obrigatório para oportunidades")
                sys.exit(1)
    
    # Inicializa banco
    init_db()
    session_gen = get_db_session()
    session = next(session_gen)
    
    resultados = {}
    
    try:
        # Treina modelos conforme solicitado
        if args.tipo_modelo in ["churn", "all"]:
            resultado = treinar_modelo_churn(session, args.mes_inicio, args.mes_fim)
            resultados["churn"] = resultado
            logger.info("")
        
        if args.tipo_modelo in ["meta_risk", "all"]:
            resultado = treinar_modelo_meta_risk(session, args.mes_inicio, args.mes_fim)
            resultados["meta_risk"] = resultado
            logger.info("")
        
        if args.tipo_modelo in ["oportunidades", "all"]:
            resultado = treinar_modelo_oportunidades(session, args.mes_referencia)
            resultados["oportunidades"] = resultado
            logger.info("")
        
        # Resumo final
        logger.info("=" * 80)
        logger.info("📊 RESUMO DO TREINAMENTO")
        logger.info("=" * 80)
        
        sucessos = sum(1 for r in resultados.values() if r.get("sucesso"))
        falhas = len(resultados) - sucessos
        
        for tipo, resultado in resultados.items():
            if resultado.get("sucesso"):
                logger.info(f"✅ {tipo}: Accuracy={resultado.get('accuracy', 0):.4f}, "
                          f"ROC-AUC={resultado.get('roc_auc', 0):.4f if resultado.get('roc_auc') else 'N/A'}, "
                          f"n_samples={resultado.get('n_samples', 0)}")
            else:
                logger.error(f"❌ {tipo}: {resultado.get('erro', 'Erro desconhecido')}")
        
        logger.info("")
        logger.info(f"Total: {sucessos} sucessos, {falhas} falhas")
        logger.info("=" * 80)
        
        if falhas > 0:
            sys.exit(1)
        else:
            sys.exit(0)
    
    finally:
        session.close()


if __name__ == "__main__":
    main()

