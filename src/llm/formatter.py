"""
Formatadores de Resposta para LLM.

Este módulo contém funções para formatar respostas de análise
de forma bonita e consultiva, usando apenas os números fornecidos
nos dados (nunca inventando valores).
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def format_analise_produtos(produtos: List[Dict[str, Any]], dias: int) -> str:
    """
    Formata análise de produtos com baixa venda de forma bonita e consultiva.
    
    IMPORTANTE: Usa APENAS os números fornecidos nos dados.
    NUNCA inventa valores ou estimativas.
    
    Args:
        produtos: Lista de dicionários com produtos:
            {
                "codigo": str,
                "produto": str,
                "unidades": int,
                "caixas": float,
                "faturamento": float
            }
        dias: Número de dias analisados
        
    Returns:
        str: Texto formatado de forma bonita e consultiva
    """
    if not produtos:
        return (
            f"Com base nos últimos {dias} dias, não foi possível identificar "
            f"produtos com baixa venda para análise."
        )
    
    total_produtos = len(produtos)
    
    # Monta cabeçalho da resposta
    resposta = (
        f"Com base nos últimos **{dias} dias**, identifiquei "
        f"**{total_produtos} produto(s)** que apresentam baixo giro de vendas "
        f"e precisam de atenção especial.\n\n"
    )
    
    # Determina quantos produtos mostrar (máximo 5)
    num_produtos_mostrar = min(5, total_produtos)
    
    if num_produtos_mostrar > 0:
        resposta += f"Estes são os **{num_produtos_mostrar} produtos com pior desempenho**:\n\n"
        
        # Lista os produtos ordenados (já vêm ordenados pelo menor volume)
        for i, produto in enumerate(produtos[:num_produtos_mostrar], 1):
            codigo = produto.get("codigo", "N/A")
            nome = produto.get("produto", "Produto sem nome")
            unidades = produto.get("unidades", 0)
            caixas = produto.get("caixas", 0.0)
            faturamento = produto.get("faturamento", 0.0)
            
            # Formata valores monetários no padrão brasileiro (R$ 1.234,56)
            # Remove separadores existentes e formata manualmente
            faturamento_int = int(faturamento)
            faturamento_decimal = int(round((faturamento - faturamento_int) * 100))
            # Formata parte inteira com separador de milhares
            parte_inteira_str = f"{faturamento_int:,}".replace(",", ".")
            faturamento_formatado = f"R$ {parte_inteira_str},{faturamento_decimal:02d}"
            
            # Formata caixas (usa vírgula como separador decimal no padrão brasileiro)
            caixas_formatado = f"{caixas:.1f}".replace(".", ",") if caixas > 0 else "0,0"
            
            resposta += (
                f"**{i}. {nome}**\n"
                f"   • Código: `{codigo}`\n"
                f"   • Faturamento total: {faturamento_formatado}\n"
            )
            
            # Adiciona informações de quantidade se disponíveis
            if unidades > 0 or caixas > 0:
                qtd_info = []
                if unidades > 0:
                    qtd_info.append(f"{unidades} unidade(s)")
                if caixas > 0:
                    qtd_info.append(f"{caixas_formatado} caixa(s)")
                if qtd_info:
                    resposta += f"   • Volume: {', '.join(qtd_info)}\n"
            
            resposta += "\n"
        
        # Se houver mais produtos além dos mostrados
        if total_produtos > num_produtos_mostrar:
            produtos_restantes = total_produtos - num_produtos_mostrar
            resposta += (
                f"\n*Além desses, há mais **{produtos_restantes} produto(s)** "
                f"com baixo volume de vendas que também requerem atenção.*\n\n"
            )
    
    # Adiciona recomendação consultiva (sem números inventados)
    resposta += (
        "💡 **Recomendações:**\n"
        "• Avaliar estratégias de promoção para estes produtos\n"
        "• Revisar o mix de produtos e possível descontinuação\n"
        "• Analisar a performance histórica para entender tendências\n"
        "• Considerar ações de marketing direcionadas para aumentar o giro\n"
    )
    
    return resposta

