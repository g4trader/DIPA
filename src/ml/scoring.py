"""
Módulo de Scoring para ML Baseline.

Este módulo contém funções puramente em Python (sem libs pesadas)
para calcular scores de churn, risco de meta e queda de produtos.
"""

from typing import Optional
import logging

logger = logging.getLogger(__name__)


def calcular_churn_score(
    faturamento_atual: float,
    faturamento_media_3m: Optional[float],
    dias_desde_ultima_compra: Optional[int],
    variacao_pct_vs_3m: Optional[float] = None
) -> float:
    """
    Calcula score de churn para um cliente (0-100).
    
    Score alto = maior risco de churn.
    
    Args:
        faturamento_atual: Faturamento do mês atual
        faturamento_media_3m: Média de faturamento dos últimos 3 meses
        dias_desde_ultima_compra: Dias desde a última compra
        variacao_pct_vs_3m: Variação percentual vs média 3m (opcional, calcula se None)
        
    Returns:
        float: Score de churn entre 0 e 100
    """
    try:
        # Se não tem histórico, não dá para calcular
        if faturamento_media_3m is None or faturamento_media_3m == 0:
            # Se cliente não comprou no mês atual mas tinha histórico, risco alto
            if faturamento_atual == 0 and dias_desde_ultima_compra and dias_desde_ultima_compra > 30:
                return 85.0
            return 20.0  # Score baixo se não há histórico
        
        # Calcula variação se não fornecida
        if variacao_pct_vs_3m is None:
            if faturamento_media_3m > 0:
                variacao_pct_vs_3m = ((faturamento_atual - faturamento_media_3m) / faturamento_media_3m) * 100
            else:
                variacao_pct_vs_3m = 0.0
        
        score = 0.0
        
        # Critério 1: Cliente não comprou no mês atual e comprava recentemente
        if faturamento_atual == 0 and faturamento_media_3m > 0:
            # Penaliza por dias sem compra
            if dias_desde_ultima_compra:
                if dias_desde_ultima_compra > 60:
                    score += 50.0  # Muito tempo sem comprar
                elif dias_desde_ultima_compra > 30:
                    score += 30.0
                else:
                    score += 15.0
            else:
                score += 40.0  # Sem informação de última compra, assume risco médio
            
            # Se tinha faturamento alto antes, risco maior
            if faturamento_media_3m > 10000:
                score += 20.0
            elif faturamento_media_3m > 5000:
                score += 10.0
        
        # Critério 2: Queda de faturamento vs média 3m
        if variacao_pct_vs_3m < -50:  # Queda > 50%
            score += 40.0
        elif variacao_pct_vs_3m < -30:  # Queda entre 30% e 50%
            score += 25.0
        elif variacao_pct_vs_3m < -20:  # Queda entre 20% e 30%
            score += 15.0
        elif variacao_pct_vs_3m < -10:  # Queda entre 10% e 20%
            score += 8.0
        
        # Critério 3: Dias desde última compra (se disponível)
        if dias_desde_ultima_compra:
            if dias_desde_ultima_compra > 90:
                score += 30.0
            elif dias_desde_ultima_compra > 60:
                score += 20.0
            elif dias_desde_ultima_compra > 45:
                score += 10.0
        
        # Limita score entre 0 e 100
        score = max(0.0, min(100.0, score))
        
        return round(score, 2)
    
    except Exception as e:
        logger.warning(f"Erro ao calcular churn_score: {str(e)}")
        return 0.0


def classificar_churn_flag(score: float) -> bool:
    """
    Classifica se cliente está em risco de churn baseado no score.
    
    Args:
        score: Score de churn (0-100)
        
    Returns:
        bool: True se score >= 60 (risco alto)
    """
    return score >= 60.0


def calcular_meta_risk_score(
    atingimento_pct: Optional[float],
    gap_valor: Optional[float],
    tendencia: Optional[str] = None
) -> float:
    """
    Calcula score de risco de meta para um vendedor (0-100).
    
    Score alto = maior risco de não bater a meta.
    
    Args:
        atingimento_pct: Percentual de atingimento da meta
        gap_valor: Gap entre realizado e meta (negativo = abaixo da meta)
        tendencia: Tendência de atingimento ("melhorando", "piorando", "estavel")
        
    Returns:
        float: Score de risco entre 0 e 100
    """
    try:
        score = 0.0
        
        # Critério 1: Atingimento percentual
        if atingimento_pct is None:
            # Se não tem atingimento, assume risco médio
            score = 50.0
        elif atingimento_pct < 70:  # Abaixo de 70%
            score += 50.0
        elif atingimento_pct < 80:  # Entre 70% e 80%
            score += 35.0
        elif atingimento_pct < 90:  # Entre 80% e 90%
            score += 20.0
        elif atingimento_pct < 95:  # Entre 90% e 95%
            score += 10.0
        # Acima de 95% = risco baixo (não adiciona score)
        
        # Critério 2: Gap valor (quanto mais negativo, maior o risco)
        if gap_valor is not None:
            gap_abs = abs(gap_valor)
            if gap_valor < -50000:  # Gap muito negativo (> R$ 50k)
                score += 30.0
            elif gap_valor < -20000:  # Gap entre R$ 20k e R$ 50k
                score += 20.0
            elif gap_valor < -10000:  # Gap entre R$ 10k e R$ 20k
                score += 15.0
            elif gap_valor < -5000:  # Gap entre R$ 5k e R$ 10k
                score += 10.0
            elif gap_valor < -1000:  # Gap entre R$ 1k e R$ 5k
                score += 5.0
        
        # Critério 3: Tendência (se disponível)
        if tendencia == "piorando":
            score += 15.0
        elif tendencia == "melhorando":
            score -= 10.0  # Reduz risco se está melhorando
        # "estavel" não altera o score
        
        # Limita score entre 0 e 100
        score = max(0.0, min(100.0, score))
        
        return round(score, 2)
    
    except Exception as e:
        logger.warning(f"Erro ao calcular meta_risk_score: {str(e)}")
        return 0.0


def classificar_meta_risk_flag(score: float) -> bool:
    """
    Classifica se vendedor está em risco de não bater a meta.
    
    Args:
        score: Score de risco (0-100)
        
    Returns:
        bool: True se score >= 60 (risco alto)
    """
    return score >= 60.0


def calcular_queda_score(
    variacao_pct_vs_3m: Optional[float],
    qtd_vendida_atual: Optional[int] = None,
    qtd_media_3m: Optional[int] = None
) -> float:
    """
    Calcula score de queda para um produto (0-100).
    
    Score alto = produto em queda forte.
    
    Args:
        variacao_pct_vs_3m: Variação percentual de faturamento vs média 3m
        qtd_vendida_atual: Quantidade vendida no mês atual (opcional)
        qtd_media_3m: Média de quantidade dos últimos 3 meses (opcional)
        
    Returns:
        float: Score de queda entre 0 e 100
    """
    try:
        score = 0.0
        
        # Se não tem variação, tenta calcular pela quantidade
        if variacao_pct_vs_3m is None:
            if qtd_vendida_atual is not None and qtd_media_3m is not None and qtd_media_3m > 0:
                variacao_pct_vs_3m = ((qtd_vendida_atual - qtd_media_3m) / qtd_media_3m) * 100
            else:
                return 0.0  # Sem dados, score zero
        
        # Critério: Queda percentual
        if variacao_pct_vs_3m < -50:  # Queda > 50%
            score = 90.0
        elif variacao_pct_vs_3m < -40:  # Queda entre 40% e 50%
            score = 80.0
        elif variacao_pct_vs_3m < -30:  # Queda entre 30% e 40%
            score = 65.0
        elif variacao_pct_vs_3m < -20:  # Queda entre 20% e 30%
            score = 50.0
        elif variacao_pct_vs_3m < -10:  # Queda entre 10% e 20%
            score = 30.0
        else:
            score = 10.0  # Queda pequena ou crescimento
        
        # Limita score entre 0 e 100
        score = max(0.0, min(100.0, score))
        
        return round(score, 2)
    
    except Exception as e:
        logger.warning(f"Erro ao calcular queda_score: {str(e)}")
        return 0.0


def classificar_queda_flag(score: float) -> bool:
    """
    Classifica se produto está em queda baseado no score.
    
    Args:
        score: Score de queda (0-100)
        
    Returns:
        bool: True se score >= 60 (queda significativa)
    """
    return score >= 60.0

