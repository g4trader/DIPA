"""
Análise de Clientes.

Este módulo contém funções para analisar comportamento e histórico de clientes.
"""

import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, case

from src.dw.models import Venda, Cliente

logger = logging.getLogger(__name__)


def clientes_positivados_sem_compra_produto(
    session: Session,
    codigos_produto: Optional[List[str]] = None,
    termo_produto: Optional[str] = None,
    dias_sem_compra: int = 60,
    limite: int = 50,
) -> List[Dict[str, Any]]:
    """
    Identifica clientes que já compraram um produto específico mas não compram há mais de X dias.
    
    Útil para estratégias de reativação de clientes para produtos específicos.
    
    Args:
        session: Sessão SQLAlchemy
        codigos_produto: Lista de códigos de produto para filtrar (ex: ["12345", "67890"])
                       Prioridade: se fornecido e não vazio, usa este filtro (mais performático e indexável).
        termo_produto: Termo para buscar produto por descrição (ex.: "NISSIN", "MARILAN")
                      Usado apenas se codigos_produto não for fornecido.
                      A busca é case-insensitive e usa LIKE (%termo%) - mais lento (full scan).
        dias_sem_compra: Número de dias sem comprar (padrão: 60)
        limite: Número máximo de clientes a retornar (padrão: 50)
        
    Returns:
        List[dict]: Lista de dicionários com informações dos clientes
            {
                "codigo_cliente": str,
                "nome_cliente": str,
                "cidade": str,
                "supervisor": str,
                "rota": str,
                "pasta": str,
                "ultima_compra_produto": date,
                "dias_sem_compra": int,
                "total_historico_caixas": float,
                "total_historico_faturamento": float,
            }
            Ordenado por dias_sem_compra (maior primeiro)
    """
    # Validação: pelo menos um filtro deve ser fornecido
    if not codigos_produto and not termo_produto:
        raise ValueError(
            "É necessário fornecer 'codigos_produto' (lista) ou 'termo_produto' (string) para filtrar produtos."
        )
    
    # Remove códigos vazios da lista
    if codigos_produto:
        codigos_produto = [c.strip() for c in codigos_produto if c and c.strip()]
        if not codigos_produto:
            codigos_produto = None
    
    # Determina qual filtro usar
    usar_codigos = codigos_produto and len(codigos_produto) > 0
    usar_termo = termo_produto and termo_produto.strip()
    
    if usar_codigos:
        logger.info(
            f"Buscando clientes positivados em produtos com códigos {codigos_produto[:5]}{'...' if len(codigos_produto) > 5 else ''} "
            f"({len(codigos_produto)} código(s)) sem comprar há mais de {dias_sem_compra} dias..."
        )
    else:
        logger.info(
            f"Buscando clientes positivados em produtos contendo '{termo_produto}' "
            f"sem comprar há mais de {dias_sem_compra} dias..."
        )
    
    try:
        # 1. Encontra a data base (data máxima de venda no banco)
        data_base = session.query(func.max(Venda.data_venda)).scalar()
        
        if not data_base:
            logger.warning("Nenhuma venda encontrada no banco de dados")
            return []
        
        # 2. Calcula data de corte
        data_corte = data_base - timedelta(days=dias_sem_compra)
        
        logger.info(f"Data base: {data_base}, Data corte: {data_corte}")
        
        # 3. Para cada cliente que já comprou o produto, encontra:
        #    - última data de compra do produto
        #    - total histórico de caixas
        #    - total histórico de faturamento
        
        # Query para agrupar por cliente e produto
        # Toda agregação é feita no banco (GROUP BY, SUM, MAX) para evitar carregar milhões de linhas em memória
        query_base = (
            session.query(
                Venda.codigo_cliente,
                Venda.cliente_id,
                func.max(Venda.data_venda).label('ultima_compra_produto'),
                func.sum(Venda.qtd_caixas).label('total_caixas'),
                func.sum(Venda.valor_total_liquido).label('total_faturamento')
            )
            .filter(Venda.codigo_cliente.isnot(None))
        )
        
        # Aplica filtro de produto (prioriza códigos, mais performático)
        if usar_codigos:
            # Filtro por códigos de produto (usa índice, muito mais rápido)
            query_base = query_base.filter(Venda.codigo_produto.in_(codigos_produto))
        elif usar_termo:
            # Filtro por termo na descrição (full scan, mais lento - fallback)
            query_base = query_base.filter(
                func.lower(Venda.desc_produto).like(f"%{termo_produto.lower()}%")
            )
        
        # Agrupa por cliente e aplica filtro de data (tudo no banco)
        subquery = (
            query_base
            .group_by(Venda.codigo_cliente, Venda.cliente_id)
            .having(func.max(Venda.data_venda) <= data_corte)  # Última compra há mais de X dias
        ).subquery()
        
        # 4. Junta com a tabela de clientes para pegar informações adicionais
        # Usa outer join para pegar clientes mesmo se não estiverem na tabela Cliente
        query = (
            session.query(
                subquery.c.codigo_cliente.label('codigo_cliente'),
                Cliente.nome.label('nome_cliente'),
                Cliente.fantasia,
                Cliente.municipio.label('cidade'),
                Cliente.supervisor_responsavel.label('supervisor'),
                Cliente.nome_rca.label('rota'),
                Cliente.pasta,
                subquery.c.ultima_compra_produto,
                subquery.c.total_caixas,
                subquery.c.total_faturamento
            )
            .outerjoin(
                Cliente,
                or_(
                    Cliente.id == subquery.c.cliente_id,
                    Cliente.codigo == subquery.c.codigo_cliente
                )
            )
            .order_by(subquery.c.ultima_compra_produto)  # Ordena por data (menor primeiro = mais dias sem compra)
            .limit(limite)
        )
        
        results = query.all()
        
        if not results:
            logger.info("Nenhum cliente encontrado que atenda aos critérios")
            return []
        
        # Formata resultados
        clientes = []
        for row in results:
            # Calcula dias sem compra
            ultima_compra = row.ultima_compra_produto
            if ultima_compra:
                dias_sem_compra = (data_base - ultima_compra).days
            else:
                dias_sem_compra = 0
            
            # Usa fantasia se disponível, senão usa nome, senão usa codigo_cliente
            nome_cliente = None
            if row.fantasia:
                nome_cliente = row.fantasia
            elif row.nome_cliente:
                nome_cliente = row.nome_cliente
            else:
                nome_cliente = row.codigo_cliente  # Fallback
            
            # Busca informações do cliente se disponível, senão usa dados históricos da venda
            cidade = row.cidade if row.cidade else ""
            supervisor = row.supervisor if row.supervisor else ""
            rota = row.rota if row.rota else ""
            pasta = row.pasta if row.pasta else ""
            
            clientes.append({
                "codigo_cliente": str(row.codigo_cliente) if row.codigo_cliente else "",
                "nome_cliente": str(nome_cliente) if nome_cliente else "",
                "cidade": cidade,
                "supervisor": supervisor,
                "rota": rota,
                "pasta": pasta,
                "ultima_compra_produto": ultima_compra,
                "dias_sem_compra": dias_sem_compra,
                "total_historico_caixas": float(row.total_caixas) if row.total_caixas else 0.0,
                "total_historico_faturamento": float(row.total_faturamento) if row.total_faturamento else 0.0,
            })
        
        # Ordena por dias_sem_compra (maior primeiro = mais tempo sem comprar primeiro)
        clientes.sort(key=lambda x: x["dias_sem_compra"], reverse=True)
        
        logger.info(f"Encontrados {len(clientes)} clientes positivados sem comprar há mais de {dias_sem_compra} dias")
        
        return clientes
        
    except Exception as e:
        logger.error(f"Erro ao buscar clientes positivados sem compra: {str(e)}")
        raise


def clientes_risco_churn(
    session: Session,
    periodo_meses: int = 3,
    limite: int = 50,
    supervisor: Optional[str] = None,
    rota: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Radar de risco: identifica clientes com risco de churn baseado em:
    - Redução de frequência de compras
    - Redução de volume/faturamento nos últimos N meses vs período anterior
    - Perda de categorias de produtos
    
    Args:
        session: Sessão SQLAlchemy
        periodo_meses: Número de meses para comparar (padrão: 3)
        limite: Número máximo de clientes a retornar (padrão: 50)
        supervisor: Filtrar por supervisor (opcional)
        rota: Filtrar por rota (opcional)
    
    Returns:
        List[dict]: Lista de clientes em risco com métricas calculadas
    """
    logger.info(f"Identificando clientes em risco (comparando últimos {periodo_meses} meses)...")
    
    try:
        # 1. Data base
        data_base = session.query(func.max(Venda.data_venda)).scalar()
        if not data_base:
            logger.warning("Nenhuma venda encontrada")
            return []
        
        # 2. Calcula períodos
        from dateutil.relativedelta import relativedelta
        fim_periodo_recente = data_base
        inicio_periodo_recente = data_base - relativedelta(months=periodo_meses)
        fim_periodo_anterior = inicio_periodo_recente
        inicio_periodo_anterior = fim_periodo_anterior - relativedelta(months=periodo_meses)
        
        # 3. Query: agrega vendas por cliente nos dois períodos
        query_recente = (
            session.query(
                Venda.codigo_cliente,
                Venda.cliente_id,
                func.count(func.distinct(Venda.data_venda)).label('frequencia'),
                func.sum(Venda.qtd_caixas).label('total_caixas'),
                func.sum(Venda.valor_total_liquido).label('faturamento'),
                func.max(Venda.data_venda).label('ultima_compra')
            )
            .filter(
                and_(
                    Venda.data_venda >= inicio_periodo_recente,
                    Venda.data_venda <= fim_periodo_recente
                )
            )
        )
        
        if supervisor:
            query_recente = query_recente.filter(Venda.supervisor_nome == supervisor)
        if rota:
            query_recente = query_recente.filter(Venda.vendedor_nome == rota)
        
        query_recente = query_recente.group_by(Venda.codigo_cliente, Venda.cliente_id).subquery()
        
        query_anterior = (
            session.query(
                Venda.codigo_cliente,
                func.sum(Venda.qtd_caixas).label('total_caixas'),
                func.sum(Venda.valor_total_liquido).label('faturamento')
            )
            .filter(
                and_(
                    Venda.data_venda >= inicio_periodo_anterior,
                    Venda.data_venda < fim_periodo_anterior
                )
            )
        )
        
        if supervisor:
            query_anterior = query_anterior.filter(Venda.supervisor_nome == supervisor)
        if rota:
            query_anterior = query_anterior.filter(Venda.vendedor_nome == rota)
        
        query_anterior = query_anterior.group_by(Venda.codigo_cliente).subquery()
        
        # 4. Join para comparar períodos
        query_final = (
            session.query(
                query_recente.c.codigo_cliente,
                Cliente.nome.label('nome_cliente'),
                Cliente.fantasia,
                Cliente.municipio.label('cidade'),
                Cliente.supervisor_responsavel.label('supervisor'),
                Cliente.nome_rca.label('rota'),
                Cliente.pasta,
                query_recente.c.frequencia.label('freq_recente'),
                query_recente.c.total_caixas.label('caixas_recente'),
                query_recente.c.faturamento.label('faturamento_recente'),
                query_recente.c.ultima_compra,
                func.coalesce(query_anterior.c.total_caixas, 0).label('caixas_anterior'),
                func.coalesce(query_anterior.c.faturamento, 0).label('faturamento_anterior')
            )
            .outerjoin(Cliente, Cliente.codigo == query_recente.c.codigo_cliente)
            .outerjoin(query_anterior, query_anterior.c.codigo_cliente == query_recente.c.codigo_cliente)
        )
        
        results = query_final.all()
        
        # 5. Calcula métricas de risco
        clientes_risco = []
        for row in results:
            fat_recente = float(row.faturamento_recente or 0.0)
            fat_anterior = float(row.faturamento_anterior or 0.0)
            
            # Só inclui se teve faturamento no período anterior (cliente ativo que pode ter reduzido)
            if fat_anterior == 0:
                continue
            
            variacao = ((fat_recente - fat_anterior) / fat_anterior * 100) if fat_anterior > 0 else 0.0
            
            # Critérios de risco:
            # 1. Redução > 30% no faturamento
            # 2. Redução de frequência
            # 3. Sem compras há mais de 60 dias
            dias_sem_compra = (data_base - row.ultima_compra).days if row.ultima_compra else 999
            
            score_risco = 0.0
            if variacao < -30:
                score_risco += 50
            if variacao < -50:
                score_risco += 30
            if dias_sem_compra > 60:
                score_risco += 20
            
            # Só inclui se score >= 50 ou redução > 40%
            if score_risco < 50 and variacao > -40:
                continue
            
            nome_cliente = row.fantasia or row.nome_cliente or str(row.codigo_cliente)
            
            clientes_risco.append({
                "codigo_cliente": str(row.codigo_cliente),
                "nome_cliente": nome_cliente,
                "cidade": row.cidade or "",
                "supervisor": row.supervisor or "",
                "rota": row.rota or "",
                "pasta": row.pasta or "",
                "faturamento_ultimos_3_meses": fat_recente,
                "faturamento_3_meses_anteriores": fat_anterior,
                "variacao_percentual": round(variacao, 2),
                "dias_sem_compra": dias_sem_compra,
                "ultima_compra": row.ultima_compra,
                "categorias_perdidas": [],  # TODO: analisar categorias
                "score_risco": min(score_risco, 100.0)
            })
        
        # Ordena por score_risco (maior primeiro)
        clientes_risco.sort(key=lambda x: x["score_risco"], reverse=True)
        clientes_risco = clientes_risco[:limite]
        
        logger.info(f"Identificados {len(clientes_risco)} clientes em risco")
        return clientes_risco
        
    except Exception as e:
        logger.error(f"Erro ao identificar clientes em risco: {str(e)}")
        raise


def clientes_oportunidades_crescimento(
    session: Session,
    periodo_dias: int = 90,
    limite: int = 50,
    produto: Optional[str] = None,
    supervisor: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Mapa de oportunidades: identifica clientes com potencial de crescimento:
    - Clientes que já compraram e reduziram volume
    - Clientes da mesma rota/perfil que nunca compraram um produto específico
    
    Args:
        session: Sessão SQLAlchemy
        periodo_dias: Período de análise em dias (padrão: 90)
        limite: Número máximo de clientes a retornar
        produto: Produto específico para analisar (opcional)
        supervisor: Filtrar por supervisor (opcional)
    
    Returns:
        List[dict]: Lista de oportunidades identificadas
    """
    logger.info(f"Identificando oportunidades de crescimento (últimos {periodo_dias} dias)...")
    
    try:
        # Data base
        data_base = session.query(func.max(Venda.data_venda)).scalar()
        if not data_base:
            return []
        
        data_inicio = data_base - timedelta(days=periodo_dias)
        
        # Para cada cliente, calcula:
        # - faturamento atual (últimos N dias)
        # - faturamento histórico máximo (mesmo período em outros meses/anos)
        # - potencial de recuperação
        
        # Query: faturamento atual vs histórico
        query = (
            session.query(
                Venda.codigo_cliente,
                Cliente.nome.label('nome_cliente'),
                Cliente.fantasia,
                Cliente.municipio.label('cidade'),
                Cliente.supervisor_responsavel.label('supervisor'),
                Cliente.nome_rca.label('rota'),
                Cliente.pasta,
                func.sum(
                    case(
                        (Venda.data_venda >= data_inicio, Venda.valor_total_liquido),
                        else_=0
                    )
                ).label('faturamento_atual'),
                func.max(Venda.valor_total_liquido).label('faturamento_historico_max'),
                func.max(
                    case(
                        (Venda.data_venda < data_inicio, Venda.data_venda),
                        else_=None
                    )
                ).label('ultima_compra_anterior')
            )
            .outerjoin(Cliente, Cliente.codigo == Venda.codigo_cliente)
        )
        
        if produto:
            query = query.filter(func.lower(Venda.desc_produto).like(f"%{produto.lower()}%"))
        if supervisor:
            query = query.filter(Venda.supervisor_nome == supervisor)
        
        query = (
            query
            .filter(Venda.codigo_cliente.isnot(None))
            .group_by(
                Venda.codigo_cliente,
                Cliente.nome,
                Cliente.fantasia,
                Cliente.municipio,
                Cliente.supervisor_responsavel,
                Cliente.nome_rca,
                Cliente.pasta
            )
            .having(func.sum(case((Venda.data_venda >= data_inicio, Venda.valor_total_liquido), else_=0)) > 0)
        )
        
        results = query.all()
        
        oportunidades = []
        for row in results:
            fat_atual = float(row.faturamento_atual or 0.0)
            fat_max = float(row.faturamento_historico_max or 0.0)
            
            # Oportunidade: se fat_atual < fat_max (potencial de recuperação)
            if fat_atual >= fat_max or fat_max == 0:
                continue
            
            potencial = fat_max - fat_atual
            
            # Score baseado em potencial e histórico
            score = min((potencial / max(fat_max, 1)) * 100, 100.0)
            
            nome_cliente = row.fantasia or row.nome_cliente or str(row.codigo_cliente)
            dias_sem_compra_max = (data_base - row.ultima_compra_anterior).days if row.ultima_compra_anterior else None
            
            oportunidades.append({
                "codigo_cliente": str(row.codigo_cliente),
                "nome_cliente": nome_cliente,
                "cidade": row.cidade or "",
                "supervisor": row.supervisor or "",
                "rota": row.rota or "",
                "pasta": row.pasta or "",
                "faturamento_atual": fat_atual,
                "faturamento_historico_max": fat_max,
                "potencial_recuperacao": potencial,
                "dias_sem_compra_maxima": dias_sem_compra_max,
                "categoria_perdida": None,
                "score_oportunidade": round(score, 2)
            })
        
        # Ordena por potencial de recuperação
        oportunidades.sort(key=lambda x: x["potencial_recuperacao"], reverse=True)
        oportunidades = oportunidades[:limite]
        
        logger.info(f"Identificadas {len(oportunidades)} oportunidades de crescimento")
        return oportunidades
        
    except Exception as e:
        logger.error(f"Erro ao identificar oportunidades: {str(e)}")
        raise

