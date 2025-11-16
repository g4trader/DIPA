"""
Schemas para Respostas Estruturadas do DIPAM COPILOT™.

Define o formato JSON estruturado que o backend envia para o frontend,
permitindo renderização de cards "wow" com dados organizados.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from decimal import Decimal


class VendedorSecao(BaseModel):
    """Dados de um vendedor para seção de lista_vendedores."""
    vendedor_id: int
    vendedor_nome: str
    supervisor_id: Optional[int] = None
    supervisor_nome: Optional[str] = None
    mes_ano: str
    meta_total: float
    realizado_total: float
    atingimento_pct: Optional[float] = None
    gap_valor: Optional[float] = None
    rank_atingimento: Optional[int] = None
    meta_risk_score: Optional[float] = None
    meta_risk_flag: bool = False
    qtd_clientes_positivados: int = 0
    qtd_clientes_churn: int = 0
    qtd_skus: int = 0


class ClienteSecao(BaseModel):
    """Dados de um cliente para seção de lista_clientes."""
    cliente_id: int
    cliente_nome: str
    vendedor_id: Optional[int] = None
    vendedor_nome: Optional[str] = None
    mes_ano: str
    faturamento_total: float
    faturamento_media_3m: Optional[float] = None
    variacao_pct_vs_3m: Optional[float] = None
    qtd_compras: int = 0
    dias_desde_ultima_compra: Optional[int] = None
    churn_score: Optional[float] = None
    churn_flag: bool = False


class ProdutoSecao(BaseModel):
    """Dados de um produto para seção de lista_produtos."""
    codigo_produto: str
    desc_produto: Optional[str] = None
    mes_ano: str
    faturamento_total: float
    qtd_vendida: int = 0
    qtd_clientes_ativos: int = 0
    variacao_pct_vs_3m: Optional[float] = None
    queda_score: Optional[float] = None
    queda_flag: bool = False
    participacao_no_faturamento: Optional[float] = None


class RecomendacaoSecao(BaseModel):
    """Uma recomendação de ação para o Diretor."""
    descricao: str
    prioridade: str = Field(default="media", description="alta, media, baixa")
    tipo: Optional[str] = Field(None, description="tipo da recomendação: vendedor, cliente, produto, geral")
    referencia_id: Optional[int] = None
    referencia_nome: Optional[str] = None


class SecaoResposta(BaseModel):
    """Uma seção da resposta estruturada."""
    titulo: str
    tipo: str = Field(..., description="lista_vendedores, lista_clientes, lista_produtos, lista_recomendacoes, texto")
    dados: List[Dict[str, Any]] = Field(default_factory=list)
    # Para tipo "texto", dados pode conter apenas {"texto": "..."}


class DetalheTabela(BaseModel):
    """Estrutura de tabela para o botão 'Ver detalhamento'."""
    colunas: List[str] = Field(default_factory=list)
    linhas: List[List[Any]] = Field(default_factory=list)
    titulo: Optional[str] = None


class ContextoDebug(BaseModel):
    """Contexto técnico para debug (colapsado no frontend)."""
    intent: str
    entidades: Dict[str, Any] = Field(default_factory=dict)
    fonte_dados: str = Field(default="analytics_*", description="Fonte dos dados usados")
    mes_ano_resolvido: Optional[str] = None
    total_registros: Optional[int] = None
    tempo_processamento_ms: Optional[float] = None


class CopilotStructuredResponse(BaseModel):
    """
    Resposta estruturada completa do DIPAM COPILOT™.
    
    Este formato permite que o frontend renderize cards organizados
    com base nas seções, tabelas detalhadas e recomendações.
    """
    resumo_executivo: str = Field(..., description="Resumo executivo de 3-5 frases em linguagem de Diretor")
    secoes: List[SecaoResposta] = Field(default_factory=list, description="Lista de seções com dados organizados")
    detalhe_tabela: Optional[DetalheTabela] = None
    contexto_debug: Optional[ContextoDebug] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "resumo_executivo": "No mês de agosto de 2025, a DIPAM não atingiu a meta principalmente por causa de 2 rotas com grande gap de faturamento: ROTA 94 e ROTA 72 VD. Juntas, elas deixaram de faturar R$ 120 mil em relação à meta planejada, o que representa 45% do total do gap do mês.",
                "secoes": [
                    {
                        "titulo": "Principais responsáveis pelo não atingimento da meta em agosto/2025",
                        "tipo": "lista_vendedores",
                        "dados": [
                            {
                                "vendedor_nome": "ROTA 94",
                                "mes_ano": "2025-08",
                                "meta_total": 287443.84,
                                "realizado_total": 166658.7,
                                "atingimento_pct": 57.98,
                                "gap_valor": -120785.14,
                                "meta_risk_score": 85.5,
                                "meta_risk_flag": True
                            }
                        ]
                    }
                ],
                "detalhe_tabela": {
                    "colunas": ["vendedor_nome", "mes_ano", "meta_total", "realizado_total", "atingimento_pct", "gap_valor"],
                    "linhas": [
                        ["ROTA 94", "2025-08", 287443.84, 166658.7, 57.98, -120785.14]
                    ]
                },
                "contexto_debug": {
                    "intent": "consulta_meta",
                    "entidades": {"mes_ano": "2025-08"},
                    "fonte_dados": "analytics_vendedor_mes",
                    "mes_ano_resolvido": "2025-08"
                }
            }
        }

