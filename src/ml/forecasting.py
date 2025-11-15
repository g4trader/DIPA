"""
Módulo de Forecasting para Projeção de Receitas.

Este módulo implementa previsões de faturamento mensal baseadas em:
- Histórico de vendas
- Médias móveis
- Sazonalidade (mesmo mês do ano anterior)
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func, extract

from src.dw.models import Venda

logger = logging.getLogger(__name__)


def get_monthly_revenue_series(session: Session) -> pd.DataFrame:
    """
    Lê a tabela de vendas e agrupa por mês/ano, retornando série temporal.
    
    Args:
        session: Sessão SQLAlchemy para acessar o banco de dados
        
    Returns:
        pd.DataFrame: DataFrame com colunas:
            - mes_ano (string): formato 'YYYY-MM'
            - ano (int): ano
            - mes (int): mês (1-12)
            - faturamento_total (float): soma de valor_total_liquido
    """
    logger.info("Buscando série mensal de faturamento...")
    
    try:
        # Query SQLAlchemy para agrupar vendas por mês/ano
        # Usa func.strftime para SQLite e func.to_char para PostgreSQL
        # Mas para compatibilidade, vamos usar extract e construir mes_ano depois
        query = (
            session.query(
                extract('year', Venda.data_venda).label('ano'),
                extract('month', Venda.data_venda).label('mes'),
                func.sum(Venda.valor_total_liquido).label('faturamento_total')
            )
            .group_by(
                extract('year', Venda.data_venda),
                extract('month', Venda.data_venda)
            )
            .order_by('ano', 'mes')
        )
        
        # Executa query e converte para DataFrame
        results = query.all()
        
        if not results:
            logger.warning("Nenhuma venda encontrada no banco de dados")
            return pd.DataFrame(columns=['mes_ano', 'ano', 'mes', 'faturamento_total'])
        
        # Converte para DataFrame e constrói mes_ano
        data = [
            {
                'ano': int(row.ano),
                'mes': int(row.mes),
                'mes_ano': f"{int(row.ano)}-{int(row.mes):02d}",
                'faturamento_total': float(row.faturamento_total) if row.faturamento_total else 0.0
            }
            for row in results
        ]
        
        df = pd.DataFrame(data)
        
        # Garante que mes_ano está no formato correto
        df['mes_ano'] = df['mes_ano'].astype(str)
        
        logger.info(f"Série temporal carregada: {len(df)} meses (de {df['mes_ano'].min()} a {df['mes_ano'].max()})")
        
        return df
        
    except Exception as e:
        logger.error(f"Erro ao buscar série de faturamento: {str(e)}")
        raise


def forecast_month_revenue(
    df: pd.DataFrame,
    target_year: int,
    target_month: int
) -> Dict[str, Any]:
    """
    Faz previsão de faturamento para um mês específico.
    
    Lógica:
    1. Se o mês já existe no histórico → retorna valor real
    2. Se é um mês futuro → calcula forecast usando:
       - Média dos últimos 3 meses (peso 0.5-0.6)
       - Média dos últimos 6 meses (peso 0.3-0.4)
       - Mesmo mês do ano anterior, se existir (peso 0.2)
    3. Se histórico insuficiente → retorna erro
    
    Args:
        df: DataFrame com série mensal (retorno de get_monthly_revenue_series)
        target_year: Ano alvo (ex.: 2025)
        target_month: Mês alvo (1-12)
        
    Returns:
        dict: Dicionário com:
            - tipo: "historico" | "forecast" | "insuficiente"
            - faturamento_previsto: float
            - intervalo_inferior: float (apenas para forecast)
            - intervalo_superior: float (apenas para forecast)
            - base_meses: List[str] (meses usados na base)
            - observacoes: str
    """
    logger.info(f"Gerando forecast para {target_year}-{target_month:02d}...")
    
    # Validações
    if df.empty:
        return {
            "tipo": "insuficiente",
            "mensagem": "Histórico insuficiente para projeção confiável. Nenhum dado disponível.",
        }
    
    if len(df) < 3:
        return {
            "tipo": "insuficiente",
            "mensagem": f"Histórico insuficiente para projeção confiável. Apenas {len(df)} mês(es) disponível(is).",
        }
    
    # Verifica se o mês alvo já existe no histórico
    target_mes_ano = f"{target_year}-{target_month:02d}"
    existing_row = df[df['mes_ano'] == target_mes_ano]
    
    if not existing_row.empty:
        valor_real = float(existing_row.iloc[0]['faturamento_total'])
        logger.info(f"Mês {target_mes_ano} já consolidado no histórico: R$ {valor_real:,.2f}")
        
        return {
            "tipo": "historico",
            "faturamento_previsto": valor_real,
            "intervalo_inferior": valor_real,
            "intervalo_superior": valor_real,
            "base_meses": [target_mes_ano],
            "observacoes": "Mês já consolidado; usando valor histórico real.",
        }
    
    # Ordena por data (mais antigo primeiro)
    df = df.sort_values(['ano', 'mes']).reset_index(drop=True)
    
    # Último mês disponível
    ultimo_mes = df.iloc[-1]
    ultimo_mes_ano = datetime(ultimo_mes['ano'], ultimo_mes['mes'], 1)
    target_mes_date = datetime(target_year, target_month, 1)
    
    # Se o mês alvo não é futuro, algo está errado
    if target_mes_date <= ultimo_mes_ano:
        # Pode ser que não haja dados mas o mês já passou
        logger.warning(f"Mês {target_mes_ano} não encontrado no histórico, mas data já passou.")
        return {
            "tipo": "insuficiente",
            "mensagem": f"Mês {target_mes_ano} não encontrado no histórico.",
        }
    
    # Calcula médias móveis dos últimos meses
    base_meses = []
    
    # Média dos últimos 3 meses
    if len(df) >= 3:
        media_3m = df.tail(3)['faturamento_total'].mean()
        meses_3m = df.tail(3)['mes_ano'].tolist()
        base_meses.extend(meses_3m)
    else:
        media_3m = df['faturamento_total'].mean()
        meses_3m = df['mes_ano'].tolist()
        base_meses.extend(meses_3m)
    
    # Média dos últimos 6 meses
    if len(df) >= 6:
        media_6m = df.tail(6)['faturamento_total'].mean()
        meses_6m = df.tail(6)['mes_ano'].tolist()
    else:
        media_6m = df['faturamento_total'].mean()
        meses_6m = df['mes_ano'].tolist()
    
    # Adiciona meses dos últimos 6 meses (sem duplicatas)
    for mes in meses_6m:
        if mes not in base_meses:
            base_meses.append(mes)
    
    # Busca mesmo mês do ano anterior
    mes_ano_anterior = target_mes_date - relativedelta(years=1)
    mes_ano_anterior_str = f"{mes_ano_anterior.year}-{mes_ano_anterior.month:02d}"
    
    valor_mes_ano_passado = None
    if mes_ano_anterior_str in df['mes_ano'].values:
        valor_mes_ano_passado = float(df[df['mes_ano'] == mes_ano_anterior_str].iloc[0]['faturamento_total'])
        if mes_ano_anterior_str not in base_meses:
            base_meses.append(mes_ano_anterior_str)
        logger.info(f"Encontrado mesmo mês do ano anterior ({mes_ano_anterior_str}): R$ {valor_mes_ano_passado:,.2f}")
    
    # Calcula forecast combinado
    if valor_mes_ano_passado is not None:
        # Com sazonalidade: 50% média 3m + 30% média 6m + 20% ano anterior
        forecast = 0.5 * media_3m + 0.3 * media_6m + 0.2 * valor_mes_ano_passado
        observacoes = (
            f"Previsão baseada na média dos últimos 3 meses (R$ {media_3m:,.2f}), "
            f"média dos últimos 6 meses (R$ {media_6m:,.2f}) e sazonalidade "
            f"do mesmo mês do ano anterior ({mes_ano_anterior_str}: R$ {valor_mes_ano_passado:,.2f})."
        )
    else:
        # Sem sazonalidade: 60% média 3m + 40% média 6m
        forecast = 0.6 * media_3m + 0.4 * media_6m
        observacoes = (
            f"Previsão baseada na média dos últimos 3 meses (R$ {media_3m:,.2f}) "
            f"e média dos últimos 6 meses (R$ {media_6m:,.2f}). "
            f"Sazonalidade não disponível (mês {mes_ano_anterior_str} não encontrado no histórico)."
        )
    
    # Define intervalo de confiança simples (±10%)
    intervalo_inferior = forecast * 0.9
    intervalo_superior = forecast * 1.1
    
    # Remove duplicatas de base_meses e ordena
    base_meses = sorted(list(set(base_meses)))
    
    logger.info(
        f"Forecast para {target_mes_ano}: R$ {forecast:,.2f} "
        f"(intervalo: R$ {intervalo_inferior:,.2f} - R$ {intervalo_superior:,.2f})"
    )
    
    return {
        "tipo": "forecast",
        "faturamento_previsto": round(forecast, 2),
        "intervalo_inferior": round(intervalo_inferior, 2),
        "intervalo_superior": round(intervalo_superior, 2),
        "base_meses": base_meses,
        "observacoes": observacoes,
    }

