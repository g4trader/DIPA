"""
Detector Inteligente de Causas - DIPAM COPILOT™.

Este módulo detecta as causas mais relevantes para explicar por que um mês não bateu meta,
consumindo dados do dw/causas.py e aplicando regras de negócio.

ARQUITETURA:
- Consome exclusivamente dw/causas.py
- Aplica regras de negócio para identificar causas críticas
- Retorna dict estruturado para uso no pós-processador
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
import logging

from src.dw.causas import (
    get_metas_realizado_por_mes,
    get_piores_vendedores_no_mes,
    get_rotas_com_maior_gap_no_mes,
    get_clientes_com_queda_no_mes,
    get_skus_com_queda_no_mes
)

logger = logging.getLogger(__name__)


def detectar_causas_para_mes(
    session: Session,
    ano_mes: str,
    gap_vendedor_minimo: float = 10000.0,
    percent_gap_rota_minimo: float = 20.0,
    percent_queda_cliente_minimo: float = 25.0,
    percent_queda_sku_minimo: float = 30.0,
    atingimento_vendedor_critico: float = 85.0
) -> Dict[str, Any]:
    """
    Detecta causas mais relevantes para explicar o gap do mês.
    
    Args:
        session: Sessão SQLAlchemy
        ano_mes: Mês/ano no formato "YYYY-MM" (ex.: "2025-08")
        gap_vendedor_minimo: Gap mínimo em R$ para considerar vendedor crítico
        percent_gap_rota_minimo: Percentual mínimo do gap total para considerar rota crítica
        percent_queda_cliente_minimo: Queda percentual mínima para considerar cliente crítico
        percent_queda_sku_minimo: Queda percentual mínima para considerar SKU crítico
        atingimento_vendedor_critico: Atingimento mínimo para considerar vendedor crítico
        
    Returns:
        dict com estrutura:
        {
            "gap_total": float,
            "atingimento_medio": float,
            "causas": {
                "rotas": List[Dict],
                "vendedores": List[Dict],
                "clientes": List[Dict],
                "skus": List[Dict]
            },
            "resumo_causas": List[str]
        }
        
    Exemplo:
        >>> causas = detectar_causas_para_mes(session, "2025-08")
        >>> causas["gap_total"]  # R$ X.XXX,XX
        >>> len(causas["causas"]["vendedores"])  # N vendedores críticos
    """
    # Busca meta e realizado do mês
    metas_mes = get_metas_realizado_por_mes(session, ano_mes, ano_mes)
    
    if not metas_mes:
        logger.warning(f"[causas_detector] Nenhum dado encontrado para {ano_mes}")
        return {
            "gap_total": 0.0,
            "atingimento_medio": 0.0,
            "causas": {
                "rotas": [],
                "vendedores": [],
                "clientes": [],
                "skus": []
            },
            "resumo_causas": []
        }
    
    meta_mes = metas_mes[0]
    gap_total = meta_mes.gap_total
    atingimento_medio = meta_mes.atingimento_medio
    
    # Se gap_total <= 0, não há causas negativas
    if gap_total >= 0:
        logger.info(
            f"[causas_detector] Gap total >= 0 para {ano_mes}. "
            f"Não há causas negativas a detectar."
        )
        return {
            "gap_total": gap_total,
            "atingimento_medio": atingimento_medio,
            "causas": {
                "rotas": [],
                "vendedores": [],
                "clientes": [],
                "skus": []
            },
            "resumo_causas": ["Meta foi batida ou superada. Não há causas negativas."]
        }
    
    # Busca dados de causas
    vendedores = get_piores_vendedores_no_mes(session, ano_mes, limite=20)
    rotas = get_rotas_com_maior_gap_no_mes(session, ano_mes, limite=20)
    clientes = get_clientes_com_queda_no_mes(session, ano_mes, limite=30)
    skus = get_skus_com_queda_no_mes(session, ano_mes, limite=30)
    
    # Filtra causas críticas baseado em regras de negócio
    rotas_criticas = []
    for rota in rotas:
        # Causa crítica: rota com gap >= percent_gap_rota_minimo% do gap_total
        if abs(rota.gap_rota) >= (abs(gap_total) * percent_gap_rota_minimo / 100):
            rotas_criticas.append({
                "rota_id": rota.rota_id,
                "rota_nome": rota.rota_nome,
                "supervisor_id": rota.supervisor_id,
                "supervisor_nome": rota.supervisor_nome,
                "meta_rota_mes": rota.meta_rota_mes,
                "realizado_rota_mes": rota.realizado_rota_mes,
                "gap_rota": rota.gap_rota,
                "percent_gap_do_total": rota.percent_gap_do_total
            })
    
    vendedores_criticos = []
    for vendedor in vendedores:
        # Causa crítica: vendedor com atingimento < atingimento_vendedor_critico% E gap > gap_vendedor_minimo
        if (vendedor.atingimento_vendedor < atingimento_vendedor_critico and 
            abs(vendedor.gap_vendedor) >= gap_vendedor_minimo):
            vendedores_criticos.append({
                "vendedor_id": vendedor.vendedor_id,
                "vendedor_nome": vendedor.vendedor_nome,
                "supervisor_id": vendedor.supervisor_id,
                "supervisor_nome": vendedor.supervisor_nome,
                "rota_id": vendedor.rota_id,
                "rota_nome": vendedor.rota_nome,
                "meta_vendedor_mes": vendedor.meta_vendedor_mes,
                "realizado_vendedor_mes": vendedor.realizado_vendedor_mes,
                "gap_vendedor": vendedor.gap_vendedor,
                "atingimento_vendedor": vendedor.atingimento_vendedor
            })
    
    clientes_criticos = []
    for cliente in clientes:
        # Causa crítica: cliente com queda > percent_queda_cliente_minimo%
        if abs(cliente.variacao_pct) >= percent_queda_cliente_minimo:
            clientes_criticos.append({
                "cliente_id": cliente.cliente_id,
                "cliente_nome": cliente.cliente_nome,
                "faturamento_mes_atual": cliente.faturamento_mes_atual,
                "faturamento_mes_anterior": cliente.faturamento_mes_anterior,
                "variacao_abs": cliente.variacao_abs,
                "variacao_pct": cliente.variacao_pct
            })
    
    skus_criticos = []
    for sku in skus:
        # Causa crítica: SKU com queda > percent_queda_sku_minimo%
        if abs(sku.variacao_pct) >= percent_queda_sku_minimo:
            skus_criticos.append({
                "sku_id": sku.sku_id,
                "sku_nome": sku.sku_nome,
                "faturamento_mes_atual": sku.faturamento_mes_atual,
                "faturamento_mes_anterior": sku.faturamento_mes_anterior,
                "variacao_abs": sku.variacao_abs,
                "variacao_pct": sku.variacao_pct
            })
    
    # Gera resumo de causas em linguagem natural
    resumo_causas = []
    
    if rotas_criticas:
        total_rotas = len(rotas_criticas)
        maior_rota = max(rotas_criticas, key=lambda x: abs(x["gap_rota"]))
        resumo_causas.append(
            f"{total_rotas} rota(s) responderam por mais de {percent_gap_rota_minimo}% do gap. "
            f"Maior impacto: {maior_rota['rota_nome']} com {maior_rota['percent_gap_do_total']:.1f}% do gap total."
        )
    
    if vendedores_criticos:
        total_vendedores = len(vendedores_criticos)
        vendedor_menor_atingimento = min(vendedores_criticos, key=lambda x: x["atingimento_vendedor"])
        resumo_causas.append(
            f"{total_vendedores} vendedor(es) ficaram abaixo de {atingimento_vendedor_critico}% de atingimento. "
            f"Menor desempenho: {vendedor_menor_atingimento['vendedor_nome']} com "
            f"{vendedor_menor_atingimento['atingimento_vendedor']:.1f}%."
        )
    
    if clientes_criticos:
        total_clientes = len(clientes_criticos)
        maior_queda = min(clientes_criticos, key=lambda x: x["variacao_pct"])
        resumo_causas.append(
            f"{total_clientes} cliente(s) reduziram compras mais de {percent_queda_cliente_minimo}%. "
            f"Maior queda: {maior_queda['cliente_nome']} com {maior_queda['variacao_pct']:.1f}%."
        )
    
    if skus_criticos:
        total_skus = len(skus_criticos)
        maior_queda_sku = min(skus_criticos, key=lambda x: x["variacao_pct"])
        resumo_causas.append(
            f"{total_skus} SKU(s) tiveram queda superior a {percent_queda_sku_minimo}%. "
            f"Maior queda: {maior_queda_sku['sku_nome']} com {maior_queda_sku['variacao_pct']:.1f}%."
        )
    
    if not resumo_causas:
        resumo_causas.append(
            "Nenhuma causa crítica identificada com os critérios atuais. "
            "Gap pode ser distribuído de forma mais uniforme entre vendedores/rotas."
        )
    
    resultado = {
        "gap_total": gap_total,
        "atingimento_medio": atingimento_medio,
        "causas": {
            "rotas": rotas_criticas,
            "vendedores": vendedores_criticos,
            "clientes": clientes_criticos,
            "skus": skus_criticos
        },
        "resumo_causas": resumo_causas
    }
    
    logger.info(
        f"[causas_detector] Causas detectadas para {ano_mes}: "
        f"{len(rotas_criticas)} rotas, {len(vendedores_criticos)} vendedores, "
        f"{len(clientes_criticos)} clientes, {len(skus_criticos)} SKUs"
    )
    
    return resultado

