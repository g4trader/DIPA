"""
Endpoint REST para Q2 (Queda de Faturamento).

Este módulo expõe a funcionalidade Q2 via API REST, permitindo que o frontend
consuma tanto o texto executivo quanto os dados estruturados.
"""

import logging
from typing import Dict, Any, Optional, List
from fastapi import HTTPException
from pydantic import BaseModel, Field

from src.llm_integration_intent_q2 import (
    detectar_intent_q2,
    executar_q2_via_orquestrador
)

logger = logging.getLogger(__name__)


class Q2Request(BaseModel):
    """Modelo de requisição para endpoint Q2."""
    pergunta: str = Field(..., description="Pergunta do usuário sobre queda de faturamento")
    
    class Config:
        schema_extra = {
            "example": {
                "pergunta": "Quais clientes tiveram queda de faturamento de setembro para outubro?"
            }
        }


class Q2Resumo(BaseModel):
    """Resumo de métricas agregadas da Q2."""
    total_clientes_queda: int = Field(..., description="Total de clientes com queda")
    percentual_clientes_queda: Optional[float] = Field(None, description="Percentual de clientes com queda")
    queda_media_absoluta: float = Field(..., description="Queda média absoluta em R$")
    queda_media_percentual: float = Field(..., description="Queda média percentual")
    queda_maxima_absoluta: float = Field(..., description="Queda máxima absoluta em R$")
    queda_maxima_percentual: float = Field(..., description="Queda máxima percentual")


class Q2TopCliente(BaseModel):
    """Cliente com queda de faturamento."""
    nome: str = Field(..., description="Nome do cliente")
    cliente_id: Optional[int] = Field(None, description="ID do cliente")
    queda_absoluta: float = Field(..., description="Queda absoluta em R$")
    queda_percentual: float = Field(..., description="Queda percentual")
    faturamento_mes_anterior: Optional[float] = Field(None, description="Faturamento no mês anterior")
    faturamento_mes_atual: Optional[float] = Field(None, description="Faturamento no mês atual")
    rota: Optional[str] = Field(None, description="Rota do cliente")
    vendedor_nome: Optional[str] = Field(None, description="Nome do vendedor")
    supervisor_nome: Optional[str] = Field(None, description="Nome do supervisor")


class Q2Rota(BaseModel):
    """Agregação por rota."""
    rota: str = Field(..., description="Código da rota")
    qtd_clientes_queda: int = Field(..., description="Quantidade de clientes com queda")
    queda_total: float = Field(..., description="Queda total da rota em R$")


class Q2Periodo(BaseModel):
    """Período analisado."""
    descricao: str = Field(..., description="Descrição do período (ex: 'set/25 x out/25')")
    data_ini_mes_anterior: Optional[str] = Field(None, description="Data inicial do mês anterior")
    data_fim_mes_anterior: Optional[str] = Field(None, description="Data final do mês anterior")
    data_ini_mes_atual: Optional[str] = Field(None, description="Data inicial do mês atual")
    data_fim_mes_atual: Optional[str] = Field(None, description="Data final do mês atual")


class Q2Response(BaseModel):
    """Modelo de resposta do endpoint Q2."""
    tipo: str = Field(..., description="Tipo de resposta (Q2_QUEDA_FATURAMENTO)")
    periodo: Q2Periodo = Field(..., description="Período analisado")
    texto_executivo: str = Field(..., description="Texto executivo formatado")
    resumo: Q2Resumo = Field(..., description="Resumo de métricas agregadas")
    top_clientes: List[Q2TopCliente] = Field(default_factory=list, description="Top clientes com queda")
    rotas: List[Q2Rota] = Field(default_factory=list, description="Agregação por rota")
    dados_brutos: Optional[Dict[str, Any]] = Field(None, description="Dados brutos do DW/orquestrador")


def normalizar_resposta_q2(resultado_q2: Dict[str, Any]) -> Q2Response:
    """
    Normaliza a resposta do orquestrador Q2 para o formato esperado pelo frontend.
    
    Args:
        resultado_q2: Resultado de executar_q2_via_orquestrador()
        
    Returns:
        Q2Response normalizado
    """
    dados_dw = resultado_q2.get("dados_dw", {})
    periodo = resultado_q2.get("periodo", {})
    periodo_desc = resultado_q2.get("periodo_descricao", "período analisado")
    
    # Extrai métricas
    metrics = dados_dw.get("metrics", {})
    dados = dados_dw.get("dados", [])
    
    # Calcula percentual de clientes com queda
    total_com_faturamento = dados_dw.get("total_com_faturamento_mes_anterior")
    percentual_clientes_queda = None
    if total_com_faturamento and total_com_faturamento > 0:
        total_clientes_queda = metrics.get("total_clientes_queda") or len(dados)
        percentual_clientes_queda = (total_clientes_queda / total_com_faturamento) * 100
    
    # Monta resumo
    resumo = Q2Resumo(
        total_clientes_queda=metrics.get("total_clientes_queda") or len(dados),
        percentual_clientes_queda=percentual_clientes_queda,
        queda_media_absoluta=metrics.get("queda_media_absoluta", 0.0),
        queda_media_percentual=metrics.get("queda_media_percentual", 0.0),
        queda_maxima_absoluta=metrics.get("queda_maxima_absoluta", 0.0),
        queda_maxima_percentual=metrics.get("queda_maxima_percentual", 0.0)
    )
    
    # Monta top clientes (top 10)
    top_clientes = []
    for cliente in dados[:10]:
        top_clientes.append(Q2TopCliente(
            nome=cliente.get("cliente_nome", "Cliente sem nome"),
            cliente_id=cliente.get("cliente_id"),
            queda_absoluta=cliente.get("queda_absoluta", 0.0),
            queda_percentual=cliente.get("queda_percentual", 0.0),
            faturamento_mes_anterior=cliente.get("faturamento_mes_anterior"),
            faturamento_mes_atual=cliente.get("faturamento_mes_atual"),
            rota=cliente.get("rota"),
            vendedor_nome=cliente.get("vendedor_nome"),
            supervisor_nome=cliente.get("supervisor_nome")
        ))
    
    # Agrupa por rota
    rotas_dict = {}
    for cliente in dados:
        rota = cliente.get("rota") or cliente.get("vendedor_nome") or "N/A"
        if rota not in rotas_dict:
            rotas_dict[rota] = {
                "qtd_clientes_queda": 0,
                "queda_total": 0.0
            }
        rotas_dict[rota]["qtd_clientes_queda"] += 1
        rotas_dict[rota]["queda_total"] += cliente.get("queda_absoluta", 0.0)
    
    # Ordena rotas por queda total (top 5)
    rotas_ordenadas = sorted(
        rotas_dict.items(),
        key=lambda x: x[1]["queda_total"],
        reverse=True
    )[:5]
    
    rotas = [
        Q2Rota(
            rota=rota,
            qtd_clientes_queda=dados_rota["qtd_clientes_queda"],
            queda_total=dados_rota["queda_total"]
        )
        for rota, dados_rota in rotas_ordenadas
    ]
    
    # Monta período
    periodo_obj = Q2Periodo(
        descricao=periodo_desc,
        data_ini_mes_anterior=periodo.get("data_ini_mes_anterior"),
        data_fim_mes_anterior=periodo.get("data_fim_mes_anterior"),
        data_ini_mes_atual=periodo.get("data_ini_mes_atual"),
        data_fim_mes_atual=periodo.get("data_fim_mes_atual")
    )
    
    return Q2Response(
        tipo="Q2_QUEDA_FATURAMENTO",
        periodo=periodo_obj,
        texto_executivo=resultado_q2.get("texto_executivo", ""),
        resumo=resumo,
        top_clientes=top_clientes,
        rotas=rotas,
        dados_brutos=dados_dw
    )


async def processar_q2_endpoint(pergunta: str) -> Q2Response:
    """
    Processa pergunta Q2 e retorna resposta normalizada.
    
    Args:
        pergunta: Pergunta do usuário
        
    Returns:
        Q2Response normalizado
        
    Raises:
        HTTPException: Se a pergunta não for sobre Q2 ou houver erro
    """
    try:
        # Detecta se é Q2
        if not detectar_intent_q2(pergunta):
            raise HTTPException(
                status_code=400,
                detail="A pergunta não é sobre queda de faturamento. Por favor, reformule sua pergunta."
            )
        
        # Executa Q2
        resultado_q2 = executar_q2_via_orquestrador(
            pergunta,
            incluir_texto_executivo=True
        )
        
        # Normaliza resposta
        resposta_normalizada = normalizar_resposta_q2(resultado_q2)
        
        logger.info(
            f"[Q2_ENDPOINT] Resposta gerada: "
            f"total_clientes={resposta_normalizada.resumo.total_clientes_queda}, "
            f"top_clientes={len(resposta_normalizada.top_clientes)}, "
            f"rotas={len(resposta_normalizada.rotas)}"
        )
        
        return resposta_normalizada
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Q2_ENDPOINT] Erro ao processar Q2: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar pergunta sobre queda de faturamento: {str(e)}"
        )

