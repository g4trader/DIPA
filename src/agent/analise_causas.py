"""
Camada de Análise de Causas - DIPAM COPILOT™.

Este módulo implementa detecção automática de causas quando a meta não foi batida,
gerando análises estruturadas para o TEMPLATE DE RESPOSTA NEGATIVA.

ARQUITETURA:
- Recebe dados do DW após execução de IntentSpec
- Detecta automaticamente se atingimento < 100%
- Gera análises estruturadas: vendedores, rotas, clientes, SKUs, gargalos
- Compatível com o formato JSON esperado pelo LLM
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


def detectar_atingimento_abaixo_meta(dados_dw: Dict[str, Any]) -> bool:
    """
    Detecta se o atingimento está abaixo de 100%.
    
    Args:
        dados_dw: Dicionário com dados retornados do DW
        
    Returns:
        True se atingimento < 100%, False caso contrário
    """
    # Tenta extrair meta_total e realizado_total de várias formas
    meta_total = 0.0
    realizado_total = 0.0
    
    # Forma 1: Dados agregados diretos
    if "meta_total" in dados_dw:
        meta_total = float(dados_dw["meta_total"]) if dados_dw["meta_total"] else 0.0
    if "realizado_total" in dados_dw:
        realizado_total = float(dados_dw["realizado_total"]) if dados_dw["realizado_total"] else 0.0
    
    # Forma 2: Lista de dados (agrega)
    if "dados" in dados_dw and isinstance(dados_dw["dados"], list):
        for item in dados_dw["dados"]:
            if isinstance(item, dict):
                meta_total += float(item.get("meta_total", 0) or 0)
                realizado_total += float(item.get("realizado_total", 0) or 0)
            elif hasattr(item, "meta_total"):
                meta_total += float(item.meta_total or 0)
                realizado_total += float(item.realizado_total or 0)
    
    # Calcula atingimento
    if meta_total > 0:
        atingimento = (realizado_total / meta_total) * 100
        return atingimento < 100.0
    
    return False


def gerar_analise_causas(
    session: Session,
    dados_dw: Dict[str, Any],
    mes_ano: str,
    limite_vendedores: int = 10,
    limite_clientes: int = 20,
    limite_skus: int = 20
) -> Dict[str, Any]:
    """
    Gera análise completa de causas quando meta não foi batida.
    
    Args:
        session: Sessão SQLAlchemy
        dados_dw: Dados retornados do DW
        mes_ano: Mês/ano no formato "YYYY-MM"
        limite_vendedores: Limite de vendedores a retornar
        limite_clientes: Limite de clientes a retornar
        limite_skus: Limite de SKUs a retornar
        
    Returns:
        Dict com todas as análises estruturadas:
        - vendedores_pior_desempenho
        - rotas_maior_gap
        - clientes_reduziram_compra
        - skus_queda_relevante
        - gargalos_rupturas
        - checklist_problemas
    """
    from src.dw.analytics_metas_extended import (
        get_gap_por_rota,
        get_piores_vendedores,
        get_clientes_com_queda,
        get_skus_com_quebra
    )
    
    resultado = {
        "vendedores_pior_desempenho": [],
        "rotas_maior_gap": [],
        "clientes_reduziram_compra": [],
        "skus_queda_relevante": [],
        "gargalos_rupturas": [],
        "checklist_problemas": []
    }
    
    try:
        # 1. Vendedores com pior desempenho
        try:
            vendedores = get_piores_vendedores(session, mes_ano, limite_vendedores)
            resultado["vendedores_pior_desempenho"] = [
                {
                    "nome": v.vendedor_nome,
                    "rota": v.rota,
                    "meta": v.meta_total,
                    "realizado": v.realizado_total,
                    "gap": v.gap_total,
                    "atingimento": v.atingimento_pct
                }
                for v in vendedores
            ]
        except Exception as e:
            logger.error(f"[analise_causas] Erro ao buscar piores vendedores: {e}")
        
        # 2. Rotas com maior gap
        try:
            rotas = get_gap_por_rota(session, mes_ano, top_n=limite_vendedores)
            resultado["rotas_maior_gap"] = [
                {
                    "rota": r.rota,
                    "meta": r.meta_total,
                    "realizado": r.realizado_total,
                    "gap": r.gap_total,
                    "atingimento": r.atingimento_pct
                }
                for r in rotas
            ]
        except Exception as e:
            logger.error(f"[analise_causas] Erro ao buscar gap por rota: {e}")
        
        # 3. Clientes que reduziram compra
        try:
            clientes = get_clientes_com_queda(session, mes_ano, limite=limite_clientes)
            resultado["clientes_reduziram_compra"] = [
                {
                    "nome": c.cliente_nome,
                    "vendedor": c.vendedor_nome or "",
                    "faturamento_atual": c.faturamento_atual,
                    "faturamento_anterior": c.faturamento_anterior,
                    "variacao_pct": c.variacao_pct
                }
                for c in clientes
            ]
        except Exception as e:
            logger.error(f"[analise_causas] Erro ao buscar clientes com queda: {e}")
        
        # 4. SKUs com queda relevante
        try:
            skus = get_skus_com_quebra(session, mes_ano, limite=limite_skus)
            resultado["skus_queda_relevante"] = [
                {
                    "sku": s.codigo_produto,
                    "descricao": s.desc_produto,
                    "vendas_atual": s.vendas_atual,
                    "vendas_anterior": s.vendas_anterior,
                    "variacao_pct": s.variacao_pct,
                    "ruptura": s.ruptura
                }
                for s in skus
            ]
        except Exception as e:
            logger.error(f"[analise_causas] Erro ao buscar SKUs com quebra: {e}")
        
        # 5. Gargalos e rupturas
        try:
            gargalos = []
            
            # Rupturas de SKU
            skus_ruptura = [s for s in resultado["skus_queda_relevante"] if s.get("ruptura", False)]
            for sku in skus_ruptura[:5]:  # Top 5 rupturas
                gargalos.append({
                    "tipo": "ruptura_sku",
                    "descricao": f"SKU {sku['sku']} ({sku['descricao']}) sem venda no período",
                    "impacto": abs(sku.get("vendas_anterior", 0))
                })
            
            # Clientes sem compra
            clientes_sem_compra = [c for c in resultado["clientes_reduziram_compra"] if c.get("faturamento_atual", 0) == 0]
            if clientes_sem_compra:
                impacto_total = sum(c.get("faturamento_anterior", 0) for c in clientes_sem_compra[:10])
                gargalos.append({
                    "tipo": "cliente_sem_compra",
                    "descricao": f"{len(clientes_sem_compra)} clientes sem compra no período",
                    "impacto": impacto_total
                })
            
            resultado["gargalos_rupturas"] = gargalos
        except Exception as e:
            logger.error(f"[analise_causas] Erro ao identificar gargalos: {e}")
        
        # 6. Checklist de problemas
        try:
            problemas = []
            
            # Problema 1: Vendedores abaixo da meta
            vendedores_abaixo = [v for v in resultado["vendedores_pior_desempenho"] if v.get("atingimento", 100) < 95]
            if vendedores_abaixo:
                impacto = sum(abs(v.get("gap", 0)) for v in vendedores_abaixo)
                problemas.append({
                    "problema": f"{len(vendedores_abaixo)} vendedores com atingimento < 95%",
                    "impacto": f"R$ {impacto:,.2f}",
                    "causa_provavel": "Baixa performance individual ou problemas operacionais",
                    "urgencia": "alta" if len(vendedores_abaixo) > 5 else "media"
                })
            
            # Problema 2: Rupturas de SKU
            if resultado["skus_queda_relevante"]:
                rupturas = [s for s in resultado["skus_queda_relevante"] if s.get("ruptura", False)]
                if rupturas:
                    impacto = sum(s.get("vendas_anterior", 0) for s in rupturas)
                    problemas.append({
                        "problema": f"{len(rupturas)} SKUs em ruptura (sem venda no período)",
                        "impacto": f"R$ {impacto:,.2f}",
                        "causa_provavel": "Falta de estoque ou problemas de abastecimento",
                        "urgencia": "alta"
                    })
            
            # Problema 3: Clientes com queda significativa
            clientes_queda_forte = [c for c in resultado["clientes_reduziram_compra"] if c.get("variacao_pct", 0) < -30]
            if clientes_queda_forte:
                impacto = sum(c.get("faturamento_anterior", 0) - c.get("faturamento_atual", 0) for c in clientes_queda_forte)
                problemas.append({
                    "problema": f"{len(clientes_queda_forte)} clientes com queda > 30%",
                    "impacto": f"R$ {impacto:,.2f}",
                    "causa_provavel": "Perda de clientes ou redução de pedidos",
                    "urgencia": "alta"
                })
            
            resultado["checklist_problemas"] = problemas
        except Exception as e:
            logger.error(f"[analise_causas] Erro ao gerar checklist: {e}")
        
        logger.info(
            f"[analise_causas] Análise completa gerada para mes={mes_ano}: "
            f"{len(resultado['vendedores_pior_desempenho'])} vendedores, "
            f"{len(resultado['rotas_maior_gap'])} rotas, "
            f"{len(resultado['clientes_reduziram_compra'])} clientes, "
            f"{len(resultado['skus_queda_relevante'])} SKUs"
        )
        
    except Exception as e:
        logger.error(f"[analise_causas] Erro geral ao gerar análise de causas: {e}")
    
    return resultado

