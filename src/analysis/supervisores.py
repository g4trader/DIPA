"""
Análise de Supervisores e Equipes.

Este módulo contém funções para analisar desempenho de supervisores,
comparar equipes e identificar gaps de gestão.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case, distinct

from src.dw.models import (
    MetaDepartamento, MetaVendedor, Supervisor, Vendedor, Venda, Cliente
)

logger = logging.getLogger(__name__)


def desempenho_supervisores(
    session: Session,
    periodo_meses: int = 6,
    mes_base: Optional[str] = None,
    supervisor_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Analisa desempenho de supervisores comparando:
    - Atingimento de metas
    - Cobertura de clientes ativos
    - Concentração de faturamento (dependência de poucos clientes)
    - Perda de clientes ativos
    
    Args:
        session: Sessão SQLAlchemy
        periodo_meses: Número de meses para analisar (padrão: 6)
        mes_base: Mês base no formato YYYY-MM (padrão: maior mês disponível)
        supervisor_id: ID do supervisor específico para filtrar (opcional)
    
    Returns:
        Dicionário com resumo de desempenho por supervisor
    """
    logger.info(f"Analisando desempenho de supervisores (últimos {periodo_meses} meses)...")
    
    try:
        # 1. Determina mes_base
        if not mes_base:
            mes_base = session.query(func.max(MetaDepartamento.mes_ano)).scalar()
            if not mes_base:
                logger.warning("Nenhuma meta encontrada")
                return {
                    "tipo": "desempenho_supervisores",
                    "periodo_meses": periodo_meses,
                    "mes_base": None,
                    "total_supervisores": 0,
                    "supervisores": [],
                    "meta_total_empresa": 0.0,
                    "realizado_total_empresa": 0.0,
                    "percentual_atingido_empresa": 0.0
                }
        
        # 2. Gera lista de meses
        data_base = datetime.strptime(mes_base, "%Y-%m")
        meses_lista = []
        for i in range(periodo_meses - 1, -1, -1):
            mes = data_base - relativedelta(months=i)
            meses_lista.append(mes.strftime("%Y-%m"))
        
        # 3. Agrega metas por supervisor no período
        query_metas = (
            session.query(
                MetaDepartamento.supervisor_id,
                MetaDepartamento.supervisor_nome,
                Supervisor.pasta,
                func.sum(MetaDepartamento.valor_meta).label('meta_total'),
                func.sum(MetaDepartamento.valor_faturado).label('realizado_total')
            )
            .join(Supervisor, MetaDepartamento.supervisor_id == Supervisor.id)
            .filter(MetaDepartamento.mes_ano.in_(meses_lista))
        )
        
        if supervisor_id:
            query_metas = query_metas.filter(MetaDepartamento.supervisor_id == supervisor_id)
        
        query_metas = (
            query_metas
            .group_by(
                MetaDepartamento.supervisor_id,
                MetaDepartamento.supervisor_nome,
                Supervisor.pasta
            )
        )
        
        resultados_metas = query_metas.all()
        
        # 4. Para cada supervisor, calcula métricas adicionais
        supervisores_desempenho = []
        meta_total_empresa = 0.0
        realizado_total_empresa = 0.0
        
        for row in resultados_metas:
            supervisor_id_val = row.supervisor_id
            supervisor_nome = row.supervisor_nome or "N/A"
            pasta = row.pasta or ""
            meta_total = float(row.meta_total or 0.0)
            realizado_total = float(row.realizado_total or 0.0)
            
            meta_total_empresa += meta_total
            realizado_total_empresa += realizado_total
            
            perc_atingido = (realizado_total / meta_total * 100) if meta_total > 0 else 0.0
            
            # 5. Conta vendedores do supervisor
            qtd_vendedores = (
                session.query(func.count(distinct(Vendedor.id)))
                .filter(Vendedor.supervisor_id == supervisor_id_val)
                .filter(Vendedor.ativo == True)
                .scalar() or 0
            )
            
            # 6. Conta clientes ativos (compraram nos últimos 90 dias)
            data_base_vendas = session.query(func.max(Venda.data_venda)).scalar()
            if data_base_vendas:
                data_corte_clientes = data_base_vendas - timedelta(days=90)
                qtd_clientes_ativos = (
                    session.query(func.count(distinct(Venda.codigo_cliente)))
                    .join(Vendedor, Venda.vendedor_id == Vendedor.id)
                    .filter(Vendedor.supervisor_id == supervisor_id_val)
                    .filter(Venda.data_venda >= data_corte_clientes)
                    .scalar() or 0
                )
            else:
                qtd_clientes_ativos = 0
            
            # 7. Calcula concentração de faturamento (% do faturamento vindo dos top 20% clientes)
            # Query: top 20% de clientes por faturamento
            if realizado_total > 0:
                faturamento_por_cliente = (
                    session.query(
                        Venda.codigo_cliente,
                        func.sum(Venda.valor_total_liquido).label('faturamento_cliente')
                    )
                    .join(Vendedor, Venda.vendedor_id == Vendedor.id)
                    .filter(Vendedor.supervisor_id == supervisor_id_val)
                    .filter(Venda.data_venda >= data_base - relativedelta(months=periodo_meses))
                    .group_by(Venda.codigo_cliente)
                    .order_by(func.sum(Venda.valor_total_liquido).desc())
                    .limit(max(1, int(qtd_clientes_ativos * 0.2)))  # Top 20%
                    .all()
                )
                
                faturamento_top_20 = sum(float(row.faturamento_cliente or 0.0) for row in faturamento_por_cliente)
                concentracao = (faturamento_top_20 / realizado_total * 100) if realizado_total > 0 else 0.0
            else:
                concentracao = 0.0
            
            # 8. Calcula clientes perdidos (compraram no período anterior mas não no recente)
            # TODO: Implementar comparação entre períodos
            
            # 9. Score de desempenho (0-100)
            # Baseado em: atingimento (50%), cobertura (30%), concentração (20% - quanto menor melhor)
            score_atingimento = min(perc_atingido, 100.0)
            score_cobertura = min((qtd_clientes_ativos / max(qtd_vendedores * 10, 1)) * 100, 100.0)  # Normalizado
            score_concentracao = max(100.0 - concentracao, 0.0)  # Quanto menor concentração, melhor
            
            score_desempenho = (
                score_atingimento * 0.5 +
                score_cobertura * 0.3 +
                score_concentracao * 0.2
            )
            
            supervisores_desempenho.append({
                "supervisor_id": supervisor_id_val,
                "supervisor_nome": supervisor_nome,
                "pasta": pasta,
                "meta_total": meta_total,
                "realizado_total": realizado_total,
                "percentual_atingido": round(perc_atingido, 2),
                "qtd_vendedores": qtd_vendedores,
                "qtd_clientes_ativos": qtd_clientes_ativos,
                "concentracao_faturamento": round(concentracao, 2),
                "clientes_perdidos": 0,  # TODO: calcular
                "score_desempenho": round(score_desempenho, 2)
            })
        
        # Ordena por score_desempenho (menor primeiro = pior desempenho primeiro)
        supervisores_desempenho.sort(key=lambda x: x["score_desempenho"])
        
        perc_atingido_empresa = (realizado_total_empresa / meta_total_empresa * 100) if meta_total_empresa > 0 else 0.0
        
        return {
            "tipo": "desempenho_supervisores",
            "periodo_meses": periodo_meses,
            "mes_base": mes_base,
            "total_supervisores": len(supervisores_desempenho),
            "supervisores": supervisores_desempenho,
            "meta_total_empresa": round(meta_total_empresa, 2),
            "realizado_total_empresa": round(realizado_total_empresa, 2),
            "percentual_atingido_empresa": round(perc_atingido_empresa, 2)
        }
        
    except Exception as e:
        logger.error(f"Erro ao analisar desempenho de supervisores: {str(e)}")
        raise




