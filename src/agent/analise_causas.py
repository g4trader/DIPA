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
    
    ATIVA TEMPLATE DE RESPOSTA NEGATIVA quando:
    - atingimento_medio < 100% OU
    - realizado_total < meta_total
    
    Args:
        dados_dw: Dicionário com dados retornados do DW
        
    Returns:
        True se atingimento < 100% OU realizado < meta, False caso contrário
    """
    # Tenta extrair meta_total e realizado_total de várias formas
    meta_total = 0.0
    realizado_total = 0.0
    atingimento_medio = None
    
    # Forma 1: Dados agregados diretos
    if "meta_total" in dados_dw:
        meta_total = float(dados_dw["meta_total"]) if dados_dw["meta_total"] else 0.0
    if "realizado_total" in dados_dw:
        realizado_total = float(dados_dw["realizado_total"]) if dados_dw["realizado_total"] else 0.0
    if "atingimento_medio" in dados_dw:
        atingimento_medio = float(dados_dw["atingimento_medio"]) if dados_dw["atingimento_medio"] else None
    
    # Forma 2: Lista de dados (agrega)
    if "dados" in dados_dw and isinstance(dados_dw["dados"], list):
        for item in dados_dw["dados"]:
            if isinstance(item, dict):
                meta_total += float(item.get("meta_total", 0) or 0)
                realizado_total += float(item.get("realizado_total", 0) or 0)
                if atingimento_medio is None and "atingimento_medio" in item:
                    # Se não tem atingimento_medio agregado, calcula
                    pass
            elif hasattr(item, "meta_total"):
                meta_total += float(item.meta_total or 0)
                realizado_total += float(item.realizado_total or 0)
    
    # Calcula atingimento se não fornecido
    if atingimento_medio is None and meta_total > 0:
        atingimento_medio = (realizado_total / meta_total) * 100
    
    # ATIVA TEMPLATE se:
    # 1. atingimento_medio < 100% OU
    # 2. realizado_total < meta_total
    if atingimento_medio is not None and atingimento_medio < 100.0:
        return True
    
    if meta_total > 0 and realizado_total < meta_total:
        return True
    
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
        "skus_queda_expressiva": [],
        "outras_causas": [],
        "gargalos_rupturas": [],
        "checklist_problemas": []
    }
    
    try:
        # 1. Vendedores com pior desempenho (calcula impacto % do gap total)
        try:
            vendedores = get_piores_vendedores(session, mes_ano, limite_vendedores)
            
            # Calcula gap total para calcular impacto
            gap_total_geral = sum(abs(v.gap_total) for v in vendedores if v.gap_total < 0)
            
            resultado["vendedores_pior_desempenho"] = []
            for v in vendedores:
                impacto_pct = (abs(v.gap_total) / gap_total_geral * 100) if gap_total_geral > 0 else 0
                
                resultado["vendedores_pior_desempenho"].append({
                    "id": v.vendedor_id,
                    "nome": v.vendedor_nome,
                    "rota": v.rota,
                    "meta": v.meta_total,
                    "realizado": v.realizado_total,
                    "gap": v.gap_total,
                    "atingimento": v.atingimento_pct,
                    "impacto_pct": impacto_pct
                })
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
        
        # 3. Clientes que reduziram compra (calcula variação vs média)
        try:
            clientes = get_clientes_com_queda(session, mes_ano, limite=limite_clientes)
            
            # Calcula média de faturamento para variação vs média
            if clientes:
                faturamento_medio = sum(c.faturamento_anterior for c in clientes) / len(clientes) if clientes else 0
            else:
                faturamento_medio = 0
            
            resultado["clientes_reduziram_compra"] = []
            for c in clientes:
                variacao_vs_media_pct = ((c.faturamento_atual - faturamento_medio) / faturamento_medio * 100) if faturamento_medio > 0 else 0
                
                resultado["clientes_reduziram_compra"].append({
                    "nome": c.cliente_nome,
                    "vendedor": c.vendedor_nome or "",
                    "faturamento_atual": c.faturamento_atual,
                    "faturamento_anterior": c.faturamento_anterior,
                    "variacao_vs_mes_anterior_pct": c.variacao_pct,
                    "variacao_vs_media_pct": variacao_vs_media_pct
                })
        except Exception as e:
            logger.error(f"[analise_causas] Erro ao buscar clientes com queda: {e}")
        
        # 4. SKUs com queda expressiva (calcula impacto financeiro)
        try:
            skus = get_skus_com_quebra(session, mes_ano, limite=limite_skus)
            
            resultado["skus_queda_expressiva"] = []
            for s in skus:
                impacto_financeiro = s.vendas_anterior - s.vendas_atual  # Quanto deixou de vender
                
                resultado["skus_queda_expressiva"].append({
                    "sku": s.codigo_produto,
                    "descricao": s.desc_produto,
                    "vendas_atual": s.vendas_atual,
                    "vendas_anterior": s.vendas_anterior,
                    "variacao_pct": s.variacao_pct,
                    "impacto_financeiro": impacto_financeiro,
                    "ruptura": s.ruptura
                })
        except Exception as e:
            logger.error(f"[analise_causas] Erro ao buscar SKUs com quebra: {e}")
        
        # 5. Outras causas detectadas
        try:
            outras_causas = []
            
            # Detecta ruptura de estoque
            skus_ruptura = [s for s in resultado["skus_queda_expressiva"] if s.get("ruptura", False)]
            if skus_ruptura:
                outras_causas.append(f"Ruptura de estoque: {len(skus_ruptura)} SKUs sem venda no período")
            
            # Detecta concentração excessiva (se houver cliente com > 30% do faturamento)
            if resultado["clientes_reduziram_compra"]:
                # Verifica se há concentração (simplificado)
                outras_causas.append("Concentração de vendas: verificar dependência de poucos clientes")
            
            # Detecta mix desfavorável (se muitos SKUs com queda)
            if len(resultado["skus_queda_expressiva"]) > 10:
                outras_causas.append("Mix desfavorável: múltiplos produtos com queda expressiva")
            
            # Sazonalidade (detecção simplificada - pode ser melhorada)
            # Por enquanto, apenas menciona se houver padrão
            outras_causas.append("Sazonalidade: considerar padrões históricos do período")
            
            resultado["outras_causas"] = outras_causas
        except Exception as e:
            logger.error(f"[analise_causas] Erro ao identificar outras causas: {e}")
        
        # 6. Gargalos e rupturas (mantido para compatibilidade)
        try:
            gargalos = []
            
            # Rupturas de SKU
            skus_ruptura = [s for s in resultado["skus_queda_expressiva"] if s.get("ruptura", False)]
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
        
        # 7. Checklist de problemas
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
            if resultado["skus_queda_expressiva"]:
                rupturas = [s for s in resultado["skus_queda_expressiva"] if s.get("ruptura", False)]
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

