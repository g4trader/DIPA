"""
Utilitários para diagnóstico do banco de dados DW.

Fornece funções para gerar "fingerprints" do banco e validar consistência
entre ambientes (local vs produção).
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from datetime import datetime

from src.dw.models import Cliente, Vendedor, Supervisor, Venda
from src.config import config

logger = logging.getLogger(__name__)


def get_db_fingerprint(session: Session) -> Dict[str, Any]:
    """
    Gera um "fingerprint" do banco de dados para comparação entre ambientes.
    
    Args:
        session: Sessão SQLAlchemy
        
    Returns:
        Dict com informações de fingerprint:
        - db_type: tipo do banco (sqlite, postgresql, etc.)
        - db_path: caminho do arquivo (se SQLite) ou connection string (se outro)
        - total_clientes: total de clientes na base
        - total_clientes_ativos: total de clientes ativos
        - total_vendedores: total de vendedores
        - total_supervisores: total de supervisores
        - total_vendas: total de vendas
        - ultima_venda_data: data da última venda registrada
        - ultima_atualizacao: timestamp da última atualização (se disponível)
    """
    try:
        db_type = config.database.db_type
        
        # Identifica caminho/connection string
        db_path = None
        if db_type == "sqlite":
            db_path = config.database.sqlite_path
        elif db_type == "postgresql":
            db_path = config.database.database_url.split("@")[-1] if config.database.database_url else None
        
        # Contagens básicas
        total_clientes = session.query(func.count(Cliente.id)).scalar() or 0
        total_clientes_ativos = session.query(func.count(Cliente.id)).filter(
            Cliente.ativo == True
        ).scalar() or 0
        
        total_vendedores = session.query(func.count(Vendedor.id)).scalar() or 0
        total_supervisores = session.query(func.count(Supervisor.id)).scalar() or 0
        total_vendas = session.query(func.count(Venda.id)).scalar() or 0
        
        # Data da última venda
        ultima_venda = session.query(func.max(Venda.data_venda)).scalar()
        ultima_venda_data = ultima_venda.isoformat() if ultima_venda else None
        
        # Tenta obter timestamp de última atualização (se houver tabela de metadados)
        ultima_atualizacao = None
        try:
            # Verifica se existe tabela de metadados ou campo updated_at em alguma tabela
            result = session.query(func.max(Cliente.updated_at)).scalar()
            if result:
                ultima_atualizacao = result.isoformat() if hasattr(result, 'isoformat') else str(result)
        except Exception:
            pass
        
        # Hash simples baseado em contagens (para comparação rápida)
        hash_fingerprint = f"{total_clientes}_{total_clientes_ativos}_{total_vendas}_{ultima_venda_data}"
        
        fingerprint = {
            "db_type": db_type,
            "db_path": str(db_path) if db_path else None,
            "total_clientes": total_clientes,
            "total_clientes_ativos": total_clientes_ativos,
            "total_vendedores": total_vendedores,
            "total_supervisores": total_supervisores,
            "total_vendas": total_vendas,
            "ultima_venda_data": ultima_venda_data,
            "ultima_atualizacao": ultima_atualizacao,
            "hash_fingerprint": hash_fingerprint,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"[get_db_fingerprint] Fingerprint gerado: {hash_fingerprint}")
        
        return fingerprint
        
    except Exception as e:
        logger.error(f"[get_db_fingerprint] Erro ao gerar fingerprint: {e}", exc_info=True)
        raise


def get_q1_contagem(session: Session, dias: int = 60) -> Dict[str, Any]:
    """
    Executa a Q1 e retorna contagens detalhadas para diagnóstico.
    
    Args:
        session: Sessão SQLAlchemy
        dias: Número de dias sem compra (padrão: 60)
        
    Returns:
        Dict com:
        - total_clientes_q1: número de clientes únicos resultantes da Q1
        - total_clientes_ativos: total de clientes ativos na base
        - faixas_q1: dicionário com contagens por faixa de dias
        - amostra_ids: alguns cliente_id para inspeção
    """
    try:
        from src.dw.queries import get_clientes_sem_compra_ha_dias
        
        # Executa Q1
        resultados_q1 = get_clientes_sem_compra_ha_dias(session, dias=dias)
        total_clientes_q1 = len(resultados_q1)
        
        # Total de clientes ativos na base
        total_clientes_ativos = session.query(func.count(Cliente.id)).filter(
            Cliente.ativo == True
        ).scalar() or 0
        
        # Classifica por faixas
        faixas_q1 = {
            "faixa_61_120": 0,
            "faixa_121_180": 0,
            "faixa_181_300": 0,
            "faixa_maior_300": 0
        }
        
        for cliente in resultados_q1:
            dias_sem_compra = cliente.get("dias_sem_compra")
            if dias_sem_compra is None:
                continue
            
            if 61 <= dias_sem_compra <= 120:
                faixas_q1["faixa_61_120"] += 1
            elif 121 <= dias_sem_compra <= 180:
                faixas_q1["faixa_121_180"] += 1
            elif 181 <= dias_sem_compra <= 300:
                faixas_q1["faixa_181_300"] += 1
            elif dias_sem_compra > 300:
                faixas_q1["faixa_maior_300"] += 1
        
        # Amostra de IDs (primeiros 10)
        amostra_ids = [r.get("cliente_id") for r in resultados_q1[:10]]
        
        resultado = {
            "total_clientes_q1": total_clientes_q1,
            "total_clientes_ativos": total_clientes_ativos,
            "faixas_q1": faixas_q1,
            "amostra_ids": amostra_ids,
            "dias_filtro": dias,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(
            f"[get_q1_contagem] Q1 executada: {total_clientes_q1} clientes únicos, "
            f"faixas: {faixas_q1}"
        )
        
        return resultado
        
    except Exception as e:
        logger.error(f"[get_q1_contagem] Erro ao executar Q1: {e}", exc_info=True)
        raise

