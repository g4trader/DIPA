"""
Funções estendidas de análise do Data Warehouse - DIPAM COPILOT™.

Este módulo fornece funções avançadas de análise para suportar o TEMPLATE DE RESPOSTA NEGATIVA:
- Análise de gap por rota
- Identificação de piores vendedores
- Clientes com queda de compra
- SKUs com quebra/ruptura
- Análise de tendências

ARQUITETURA:
- Usa sempre camada DW (connection.py, models.py)
- Retorna dataclasses tipadas
- Logs legíveis para auditoria
- Compatível com SQLite e PostgreSQL
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case, desc, asc
import logging

from src.dw.models import Venda, MetaVendedor, Vendedor, Cliente, Supervisor
from src.dw.models_analytics import AnalyticsVendedorMes, AnalyticsClienteMes

logger = logging.getLogger(__name__)


# ============================================================================
# DATACLASSES DE RETORNO
# ============================================================================

@dataclass
class GapRota:
    """Representa gap agregado por rota."""
    rota: str
    vendedor_id: Optional[int]
    vendedor_nome: str
    meta_total: float
    realizado_total: float
    gap_total: float
    atingimento_pct: float
    quantidade_vendedores: int


@dataclass
class VendedorGap:
    """Representa vendedor com gap detalhado."""
    vendedor_id: int
    vendedor_nome: str
    rota: str
    supervisor_id: Optional[int]
    supervisor_nome: Optional[str]
    meta_total: float
    realizado_total: float
    gap_total: float
    atingimento_pct: float
    posicao_ranking: int


@dataclass
class ClienteQueda:
    """Representa cliente com queda de compra."""
    cliente_id: int
    cliente_nome: str
    vendedor_id: Optional[int]
    vendedor_nome: Optional[str]
    rota: Optional[str]
    faturamento_atual: float
    faturamento_anterior: float
    variacao_pct: float
    dias_sem_compra: int
    mes_ano_atual: str
    mes_ano_anterior: str


@dataclass
class SKUQuebra:
    """Representa SKU com quebra/ruptura."""
    codigo_produto: str
    desc_produto: str
    departamento: Optional[str]
    vendas_atual: float
    vendas_anterior: float
    variacao_pct: float
    dias_sem_venda: int
    ruptura: bool  # True se não teve venda no período atual
    mes_ano_atual: str
    mes_ano_anterior: str


@dataclass
class Tendencia:
    """Representa tendência de uma métrica."""
    metrica: str  # "meta", "vendas", "clientes", etc.
    periodo_inicio: str
    periodo_fim: str
    valor_inicial: float
    valor_final: float
    variacao_pct: float
    tendencia: str  # "alta", "queda", "estavel"
    media_periodo: float


# ============================================================================
# FUNÇÕES DE CONSULTA
# ============================================================================

def get_metas_por_mes(
    session: Session,
    mes_ano: str,
    excluir_totais: bool = True
) -> Dict[str, Any]:
    """
    Obtém metas agregadas por mês.
    
    Esta função é um wrapper que chama get_metas_realizado_por_mes de queries_analytics.py
    para manter compatibilidade.
    
    Args:
        session: Sessão SQLAlchemy
        mes_ano: Mês/ano no formato "YYYY-MM"
        excluir_totais: Se True, exclui linhas de "Totais"
        
    Returns:
        dict com meta_total, realizado_total, gap_total, atingimento_medio, total_vendedores
    """
    from src.agent.queries_analytics import get_metas_realizado_por_mes
    
    resultado = get_metas_realizado_por_mes(session, mes_ano, excluir_totais)
    
    logger.info(
        f"[analytics_metas_extended] get_metas_por_mes: "
        f"mes={mes_ano}, meta_total={resultado['meta_total']:,.2f}, "
        f"realizado_total={resultado['realizado_total']:,.2f}, "
        f"atingimento={resultado['atingimento_medio']:.2f}%"
    )
    
    return resultado


def get_gap_por_rota(
    session: Session,
    mes_ano: str,
    top_n: Optional[int] = None,
    excluir_totais: bool = True
) -> List[GapRota]:
    """
    Obtém gap agregado por rota (vendedor).
    
    Args:
        session: Sessão SQLAlchemy
        mes_ano: Mês/ano no formato "YYYY-MM"
        top_n: Se fornecido, retorna apenas os top N rotas com maior gap
        excluir_totais: Se True, exclui linhas de "Totais"
        
    Returns:
        Lista de GapRota ordenada por gap_total decrescente
    """
    query = session.query(
        AnalyticsVendedorMes.vendedor_id,
        AnalyticsVendedorMes.vendedor_nome,
        func.sum(AnalyticsVendedorMes.meta_total).label('meta_total'),
        func.sum(AnalyticsVendedorMes.realizado_total).label('realizado_total')
    ).filter(
        AnalyticsVendedorMes.mes_ano == mes_ano
    )
    
    if excluir_totais:
        query = query.filter(
            ~func.lower(AnalyticsVendedorMes.vendedor_nome).like('%total%'),
            AnalyticsVendedorMes.vendedor_nome != 'Totais',
            AnalyticsVendedorMes.vendedor_id.isnot(None)
        )
    
    query = query.group_by(
        AnalyticsVendedorMes.vendedor_id,
        AnalyticsVendedorMes.vendedor_nome
    )
    
    resultados = query.all()
    
    gaps = []
    for row in resultados:
        meta_total = float(row.meta_total) if row.meta_total else 0.0
        realizado_total = float(row.realizado_total) if row.realizado_total else 0.0
        gap_total = realizado_total - meta_total
        atingimento_pct = (realizado_total / meta_total * 100) if meta_total > 0 else 0.0
        
        # Extrai rota do nome do vendedor (ex.: "ROTA 77" ou usa nome completo)
        rota = row.vendedor_nome if row.vendedor_nome else f"Vendedor {row.vendedor_id}"
        
        gaps.append(GapRota(
            rota=rota,
            vendedor_id=row.vendedor_id,
            vendedor_nome=row.vendedor_nome or "",
            meta_total=meta_total,
            realizado_total=realizado_total,
            gap_total=gap_total,
            atingimento_pct=atingimento_pct,
            quantidade_vendedores=1
        ))
    
    # Ordena por gap_total decrescente (maior gap primeiro)
    gaps.sort(key=lambda x: x.gap_total)
    
    # Aplica top_n se fornecido
    if top_n:
        gaps = gaps[:top_n]
    
    logger.info(
        f"[analytics_metas_extended] get_gap_por_rota: "
        f"mes={mes_ano}, encontradas {len(gaps)} rotas"
    )
    
    return gaps


def get_piores_vendedores(
    session: Session,
    mes_ano: str,
    limite: int = 10,
    excluir_totais: bool = True
) -> List[VendedorGap]:
    """
    Obtém lista de piores vendedores por gap (maior gap negativo = pior desempenho).
    
    Args:
        session: Sessão SQLAlchemy
        mes_ano: Mês/ano no formato "YYYY-MM"
        limite: Número máximo de vendedores a retornar
        excluir_totais: Se True, exclui linhas de "Totais"
        
    Returns:
        Lista de VendedorGap ordenada por gap_total crescente (piores primeiro)
    """
    query = session.query(
        AnalyticsVendedorMes.vendedor_id,
        AnalyticsVendedorMes.vendedor_nome,
        AnalyticsVendedorMes.supervisor_id,
        func.sum(AnalyticsVendedorMes.meta_total).label('meta_total'),
        func.sum(AnalyticsVendedorMes.realizado_total).label('realizado_total')
    ).filter(
        AnalyticsVendedorMes.mes_ano == mes_ano
    )
    
    if excluir_totais:
        query = query.filter(
            ~func.lower(AnalyticsVendedorMes.vendedor_nome).like('%total%'),
            AnalyticsVendedorMes.vendedor_nome != 'Totais',
            AnalyticsVendedorMes.vendedor_id.isnot(None)
        )
    
    query = query.group_by(
        AnalyticsVendedorMes.vendedor_id,
        AnalyticsVendedorMes.vendedor_nome,
        AnalyticsVendedorMes.supervisor_id
    )
    
    resultados = query.all()
    
    vendedores = []
    for row in resultados:
        meta_total = float(row.meta_total) if row.meta_total else 0.0
        realizado_total = float(row.realizado_total) if row.realizado_total else 0.0
        gap_total = realizado_total - meta_total
        atingimento_pct = (realizado_total / meta_total * 100) if meta_total > 0 else 0.0
        
        # Extrai rota do nome
        rota = row.vendedor_nome if row.vendedor_nome else f"Vendedor {row.vendedor_id}"
        
        # Busca nome do supervisor se disponível
        supervisor_nome = None
        if row.supervisor_id:
            supervisor = session.query(Supervisor).filter(
                Supervisor.id == row.supervisor_id
            ).first()
            if supervisor:
                supervisor_nome = supervisor.nome
        
        vendedores.append(VendedorGap(
            vendedor_id=row.vendedor_id,
            vendedor_nome=row.vendedor_nome or "",
            rota=rota,
            supervisor_id=row.supervisor_id,
            supervisor_nome=supervisor_nome,
            meta_total=meta_total,
            realizado_total=realizado_total,
            gap_total=gap_total,
            atingimento_pct=atingimento_pct,
            posicao_ranking=0  # Será preenchido depois
        ))
    
    # Ordena por gap_total crescente (piores primeiro)
    vendedores.sort(key=lambda x: x.gap_total)
    
    # Aplica limite
    vendedores = vendedores[:limite]
    
    # Atualiza posição no ranking
    for idx, vendedor in enumerate(vendedores, 1):
        vendedor.posicao_ranking = idx
    
    logger.info(
        f"[analytics_metas_extended] get_piores_vendedores: "
        f"mes={mes_ano}, retornados {len(vendedores)} vendedores"
    )
    
    return vendedores


def get_clientes_com_queda(
    session: Session,
    mes_ano_atual: str,
    mes_ano_anterior: Optional[str] = None,
    limite: int = 20,
    variacao_minima_pct: float = -10.0
) -> List[ClienteQueda]:
    """
    Identifica clientes com queda de compra comparando dois períodos.
    
    Args:
        session: Sessão SQLAlchemy
        mes_ano_atual: Mês atual no formato "YYYY-MM"
        mes_ano_anterior: Mês anterior no formato "YYYY-MM" (se None, calcula automaticamente)
        limite: Número máximo de clientes a retornar
        variacao_minima_pct: Variação percentual mínima para considerar queda (ex.: -10.0 = -10%)
        
    Returns:
        Lista de ClienteQueda ordenada por maior queda (mais negativo primeiro)
    """
    # Se mes_anterior não fornecido, calcula automaticamente
    if mes_ano_anterior is None:
        try:
            dt_atual = datetime.strptime(mes_ano_atual + "-01", "%Y-%m-%d")
            dt_anterior = dt_atual - timedelta(days=32)  # Aproximadamente 1 mês
            mes_ano_anterior = dt_anterior.strftime("%Y-%m")
        except:
            logger.error(f"[analytics_metas_extended] Erro ao calcular mês anterior para {mes_ano_atual}")
            return []
    
    # Busca faturamento por cliente no período atual
    from sqlalchemy import cast, String, extract
    
    ano_atual = extract('year', Venda.data_venda)
    mes_atual = extract('month', Venda.data_venda)
    mes_ano_expr = cast(ano_atual, String) + '-' + func.lpad(cast(mes_atual, String), 2, '0')
    
    # Agrega faturamento atual
    query_atual = session.query(
        Venda.cliente_id,
        func.max(Cliente.nome).label('cliente_nome'),
        func.max(Venda.vendedor_id).label('vendedor_id'),
        func.max(Vendedor.nome).label('vendedor_nome'),
        func.max(Vendedor.codigo).label('rota'),
        func.sum(Venda.valor_total_liquido).label('faturamento_atual')
    ).join(
        Cliente, Venda.cliente_id == Cliente.id
    ).outerjoin(
        Vendedor, Venda.vendedor_id == Vendedor.id
    ).filter(
        mes_ano_expr == mes_ano_atual
    ).group_by(
        Venda.cliente_id
    ).subquery()
    
    # Agrega faturamento anterior
    query_anterior = session.query(
        Venda.cliente_id,
        func.sum(Venda.valor_total_liquido).label('faturamento_anterior')
    ).filter(
        mes_ano_expr == mes_ano_anterior
    ).group_by(
        Venda.cliente_id
    ).subquery()
    
    # Join e calcula variação
    query = session.query(
        query_atual.c.cliente_id,
        query_atual.c.cliente_nome,
        query_atual.c.vendedor_id,
        query_atual.c.vendedor_nome,
        query_atual.c.rota,
        query_atual.c.faturamento_atual,
        func.coalesce(query_anterior.c.faturamento_anterior, 0.0).label('faturamento_anterior')
    ).outerjoin(
        query_anterior, query_atual.c.cliente_id == query_anterior.c.cliente_id
    )
    
    resultados = query.all()
    
    clientes_queda = []
    for row in resultados:
        fat_atual = float(row.faturamento_atual) if row.faturamento_atual else 0.0
        fat_anterior = float(row.faturamento_anterior) if row.faturamento_anterior else 0.0
        
        if fat_anterior == 0:
            variacao_pct = -100.0 if fat_atual == 0 else 0.0
        else:
            variacao_pct = ((fat_atual - fat_anterior) / fat_anterior) * 100
        
        # Filtra apenas quedas significativas
        if variacao_pct < variacao_minima_pct:
            # Calcula dias sem compra (simplificado: assume que se não comprou no mês atual, são ~30 dias)
            dias_sem_compra = 30 if fat_atual == 0 else 0
            
            clientes_queda.append(ClienteQueda(
                cliente_id=row.cliente_id,
                cliente_nome=row.cliente_nome or "",
                vendedor_id=row.vendedor_id,
                vendedor_nome=row.vendedor_nome,
                rota=row.rota,
                faturamento_atual=fat_atual,
                faturamento_anterior=fat_anterior,
                variacao_pct=variacao_pct,
                dias_sem_compra=dias_sem_compra,
                mes_ano_atual=mes_ano_atual,
                mes_ano_anterior=mes_ano_anterior
            ))
    
    # Ordena por maior queda (mais negativo primeiro)
    clientes_queda.sort(key=lambda x: x.variacao_pct)
    
    # Aplica limite
    clientes_queda = clientes_queda[:limite]
    
    logger.info(
        f"[analytics_metas_extended] get_clientes_com_queda: "
        f"mes_atual={mes_ano_atual}, mes_anterior={mes_ano_anterior}, "
        f"encontrados {len(clientes_queda)} clientes com queda"
    )
    
    return clientes_queda


def get_skus_com_quebra(
    session: Session,
    mes_ano_atual: str,
    mes_ano_anterior: Optional[str] = None,
    limite: int = 20,
    variacao_minima_pct: float = -20.0
) -> List[SKUQuebra]:
    """
    Identifica SKUs com quebra/ruptura comparando dois períodos.
    
    Args:
        session: Sessão SQLAlchemy
        mes_ano_atual: Mês atual no formato "YYYY-MM"
        mes_ano_anterior: Mês anterior (se None, calcula automaticamente)
        limite: Número máximo de SKUs a retornar
        variacao_minima_pct: Variação percentual mínima para considerar quebra
        
    Returns:
        Lista de SKUQuebra ordenada por maior queda
    """
    # Calcula mês anterior se não fornecido
    if mes_ano_anterior is None:
        try:
            dt_atual = datetime.strptime(mes_ano_atual + "-01", "%Y-%m-%d")
            dt_anterior = dt_atual - timedelta(days=32)
            mes_ano_anterior = dt_anterior.strftime("%Y-%m")
        except:
            logger.error(f"[analytics_metas_extended] Erro ao calcular mês anterior para {mes_ano_atual}")
            return []
    
    from sqlalchemy import extract, cast, String
    
    ano = extract('year', Venda.data_venda)
    mes = extract('month', Venda.data_venda)
    mes_ano_expr = cast(ano, String) + '-' + func.lpad(cast(mes, String), 2, '0')
    
    # Agrega vendas atual
    query_atual = session.query(
        Venda.codigo_produto,
        func.max(Venda.desc_produto).label('desc_produto'),
        func.max(Venda.departamento).label('departamento'),
        func.sum(Venda.valor_total_liquido).label('vendas_atual')
    ).filter(
        mes_ano_expr == mes_ano_atual,
        Venda.codigo_produto.isnot(None)
    ).group_by(
        Venda.codigo_produto
    ).subquery()
    
    # Agrega vendas anterior
    query_anterior = session.query(
        Venda.codigo_produto,
        func.sum(Venda.valor_total_liquido).label('vendas_anterior')
    ).filter(
        mes_ano_expr == mes_ano_anterior,
        Venda.codigo_produto.isnot(None)
    ).group_by(
        Venda.codigo_produto
    ).subquery()
    
    # Join e calcula variação
    query = session.query(
        query_atual.c.codigo_produto,
        query_atual.c.desc_produto,
        query_atual.c.departamento,
        query_atual.c.vendas_atual,
        func.coalesce(query_anterior.c.vendas_anterior, 0.0).label('vendas_anterior')
    ).outerjoin(
        query_anterior, query_atual.c.codigo_produto == query_anterior.c.codigo_produto
    )
    
    resultados = query.all()
    
    skus_quebra = []
    for row in resultados:
        vendas_atual = float(row.vendas_atual) if row.vendas_atual else 0.0
        vendas_anterior = float(row.vendas_anterior) if row.vendas_anterior else 0.0
        
        # Detecta ruptura (sem venda no período atual)
        ruptura = vendas_atual == 0.0 and vendas_anterior > 0.0
        
        if vendas_anterior == 0:
            variacao_pct = -100.0 if vendas_atual == 0 else 0.0
        else:
            variacao_pct = ((vendas_atual - vendas_anterior) / vendas_anterior) * 100
        
        # Filtra apenas quedas significativas ou rupturas
        if variacao_pct < variacao_minima_pct or ruptura:
            dias_sem_venda = 30 if ruptura else 0
            
            skus_quebra.append(SKUQuebra(
                codigo_produto=row.codigo_produto or "",
                desc_produto=row.desc_produto or "",
                departamento=row.departamento,
                vendas_atual=vendas_atual,
                vendas_anterior=vendas_anterior,
                variacao_pct=variacao_pct,
                dias_sem_venda=dias_sem_venda,
                ruptura=ruptura,
                mes_ano_atual=mes_ano_atual,
                mes_ano_anterior=mes_ano_anterior
            ))
    
    # Ordena por maior queda ou ruptura primeiro
    skus_quebra.sort(key=lambda x: (x.ruptura, x.variacao_pct))
    
    # Aplica limite
    skus_quebra = skus_quebra[:limite]
    
    logger.info(
        f"[analytics_metas_extended] get_skus_com_quebra: "
        f"mes_atual={mes_ano_atual}, encontrados {len(skus_quebra)} SKUs com quebra/ruptura"
    )
    
    return skus_quebra


def get_tendencias(
    session: Session,
    metrica: str,
    periodo_inicio: str,
    periodo_fim: str
) -> Tendencia:
    """
    Calcula tendência de uma métrica ao longo de um período.
    
    Args:
        session: Sessão SQLAlchemy
        metrica: "meta", "vendas", "clientes", "atingimento"
        periodo_inicio: Mês inicial "YYYY-MM"
        periodo_fim: Mês final "YYYY-MM"
        
    Returns:
        Tendencia com análise da métrica
    """
    if metrica == "meta":
        # Usa analytics_vendedor_mes
        query = session.query(
            AnalyticsVendedorMes.mes_ano,
            func.sum(AnalyticsVendedorMes.meta_total).label('valor')
        ).filter(
            and_(
                AnalyticsVendedorMes.mes_ano >= periodo_inicio,
                AnalyticsVendedorMes.mes_ano <= periodo_fim
            )
        ).group_by(
            AnalyticsVendedorMes.mes_ano
        ).order_by(
            AnalyticsVendedorMes.mes_ano
        )
        
        resultados = query.all()
        valores = [float(r.valor) for r in resultados]
        
    elif metrica == "vendas":
        # Usa tabela vendas
        from sqlalchemy import extract, cast, String
        
        ano = extract('year', Venda.data_venda)
        mes = extract('month', Venda.data_venda)
        mes_ano_expr = cast(ano, String) + '-' + func.lpad(cast(mes, String), 2, '0')
        
        query = session.query(
            mes_ano_expr.label('mes_ano'),
            func.sum(Venda.valor_total_liquido).label('valor')
        ).filter(
            and_(
                mes_ano_expr >= periodo_inicio,
                mes_ano_expr <= periodo_fim
            )
        ).group_by(
            mes_ano_expr
        ).order_by(
            mes_ano_expr
        )
        
        resultados = query.all()
        valores = [float(r.valor) for r in resultados]
        
    else:
        logger.warning(f"[analytics_metas_extended] Métrica '{metrica}' não suportada")
        return Tendencia(
            metrica=metrica,
            periodo_inicio=periodo_inicio,
            periodo_fim=periodo_fim,
            valor_inicial=0.0,
            valor_final=0.0,
            variacao_pct=0.0,
            tendencia="estavel",
            media_periodo=0.0
        )
    
    if not valores:
        return Tendencia(
            metrica=metrica,
            periodo_inicio=periodo_inicio,
            periodo_fim=periodo_fim,
            valor_inicial=0.0,
            valor_final=0.0,
            variacao_pct=0.0,
            tendencia="estavel",
            media_periodo=0.0
        )
    
    valor_inicial = valores[0]
    valor_final = valores[-1]
    media_periodo = sum(valores) / len(valores) if valores else 0.0
    
    if valor_inicial == 0:
        variacao_pct = 0.0
    else:
        variacao_pct = ((valor_final - valor_inicial) / valor_inicial) * 100
    
    # Determina tendência
    if variacao_pct > 5.0:
        tendencia = "alta"
    elif variacao_pct < -5.0:
        tendencia = "queda"
    else:
        tendencia = "estavel"
    
    logger.info(
        f"[analytics_metas_extended] get_tendencias: "
        f"metrica={metrica}, periodo={periodo_inicio} a {periodo_fim}, "
        f"variacao={variacao_pct:.2f}%, tendencia={tendencia}"
    )
    
    return Tendencia(
        metrica=metrica,
        periodo_inicio=periodo_inicio,
        periodo_fim=periodo_fim,
        valor_inicial=valor_inicial,
        valor_final=valor_final,
        variacao_pct=variacao_pct,
        tendencia=tendencia,
        media_periodo=media_periodo
    )

