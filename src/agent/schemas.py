"""
Schemas Pydantic para Insights do DIPAM COPILOT™.

Define contratos de dados estruturados entre:
- Camada de análise (src/analysis/*.py)
- Camada de orquestração (src/agent/service.py)
- Camada LLM (src/llm_integration.py)

Garante tipagem forte e validação de dados em todo o pipeline.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import date, datetime


# ============================================================================
# INSIGHTS DE METAS
# ============================================================================

class MesResumoMeta(BaseModel):
    """Resumo de meta e realizado de um mês específico."""
    mes_ano: str = Field(..., description="Mês/ano no formato YYYY-MM")
    valor_meta: float = Field(..., ge=0, description="Valor da meta em R$")
    valor_faturado: float = Field(..., ge=0, description="Valor faturado em R$")
    valor_parado: float = Field(default=0.0, ge=0, description="Valor parado em R$")
    total_caixas: float = Field(default=0.0, ge=0, description="Total de caixas")
    percentual_atingido_valor: float = Field(..., ge=0, description="% de atingimento em valor")
    percentual_atingido_volume: float = Field(default=0.0, ge=0, description="% de atingimento em volume")


class DepartamentoResumoMeta(BaseModel):
    """Resumo de meta por departamento/supervisor."""
    mes_ano: str
    departamento: str
    supervisor: str
    valor_meta: float
    valor_faturado: float
    valor_parado: float
    total_caixas: float
    percentual_atingido_valor: float
    percentual_atingido_volume: float


class VendedorResumoMeta(BaseModel):
    """Resumo de meta por vendedor."""
    mes_ano: str
    vendedor_id: int
    vendedor: str
    valor_meta: float
    valor_faturado: float
    valor_parado: float
    total_caixas: float
    percentual_atingido_valor: float
    percentual_atingido_volume: float


class InsightMetasUltimosMeses(BaseModel):
    """Insight de metas e realizados dos últimos N meses."""
    tipo: str = Field(default="metas_resumo_ultimos_meses")
    data_base: str = Field(..., description="Data base (mês mais recente) no formato YYYY-MM")
    n_meses: int = Field(..., ge=1, description="Número de meses analisados")
    nivel: str = Field(..., description="Nível de agregação: empresa, departamento, vendedor")
    meses: List[MesResumoMeta] = Field(default_factory=list, description="Lista de resumos mensais")
    observacao: Optional[str] = Field(None, description="Observação sobre dados faltantes ou limitações")
    
    # Campos opcionais para níveis específicos
    departamentos: Optional[List[DepartamentoResumoMeta]] = None
    vendedores: Optional[List[VendedorResumoMeta]] = None


# ============================================================================
# INSIGHTS DE CLIENTES
# ============================================================================

class ClienteChurnProduto(BaseModel):
    """Cliente que parou de comprar um produto específico."""
    codigo_cliente: str
    nome_cliente: str
    cidade: Optional[str] = None
    supervisor: Optional[str] = None
    rota: Optional[str] = None
    pasta: Optional[str] = None
    ultima_compra_produto: date
    dias_sem_compra: int = Field(..., ge=0)
    total_historico_caixas: float = Field(default=0.0, ge=0)
    total_historico_faturamento: float = Field(default=0.0, ge=0)


class InsightClientesChurnProduto(BaseModel):
    """Insight de clientes que abandonaram um produto específico."""
    tipo: str = Field(default="clientes_churn_produto")
    produto: str = Field(..., description="Nome do produto analisado")
    codigos_produto: List[str] = Field(default_factory=list, description="Códigos de produto usados na busca")
    dias_sem_compra: int = Field(..., ge=1, description="Período mínimo sem compra (dias)")
    data_base: str = Field(..., description="Data base da análise (YYYY-MM-DD)")
    total_clientes: int = Field(..., ge=0, description="Total de clientes encontrados")
    clientes: List[ClienteChurnProduto] = Field(default_factory=list)


class ClienteOportunidade(BaseModel):
    """Cliente com potencial de crescimento identificado."""
    codigo_cliente: str
    nome_cliente: str
    cidade: Optional[str] = None
    supervisor: Optional[str] = None
    rota: Optional[str] = None
    pasta: Optional[str] = None
    faturamento_atual: float = Field(..., ge=0)
    faturamento_historico_max: float = Field(..., ge=0)
    potencial_recuperacao: float = Field(..., ge=0, description="Potencial estimado em R$")
    dias_sem_compra_maxima: Optional[int] = None
    categoria_perdida: Optional[str] = None
    score_oportunidade: float = Field(default=0.0, ge=0, le=100, description="Score de oportunidade (0-100)")


class InsightClientesOportunidades(BaseModel):
    """Insight de oportunidades de crescimento com clientes."""
    tipo: str = Field(default="clientes_oportunidades")
    criterio: str = Field(..., description="Critério de análise (ex: 'potencial_recuperacao', 'categoria_perdida')")
    periodo_dias: int = Field(default=90, ge=1)
    data_base: str = Field(..., description="Data base da análise")
    total_clientes: int = Field(..., ge=0)
    clientes: List[ClienteOportunidade] = Field(default_factory=list)
    potencial_total_recuperacao: float = Field(default=0.0, ge=0)


class ClienteRisco(BaseModel):
    """Cliente identificado com risco de churn."""
    codigo_cliente: str
    nome_cliente: str
    cidade: Optional[str] = None
    supervisor: Optional[str] = None
    rota: Optional[str] = None
    pasta: Optional[str] = None
    faturamento_ultimos_3_meses: float = Field(..., ge=0)
    faturamento_3_meses_anteriores: float = Field(..., ge=0)
    variacao_percentual: float = Field(..., description="Variação percentual de faturamento")
    dias_sem_compra: int = Field(..., ge=0)
    ultima_compra: Optional[date] = None
    categorias_perdidas: List[str] = Field(default_factory=list)
    score_risco: float = Field(default=0.0, ge=0, le=100, description="Score de risco (0-100)")


class InsightClientesRisco(BaseModel):
    """Insight de clientes em risco de churn."""
    tipo: str = Field(default="clientes_risco")
    periodo_analise_meses: int = Field(default=3, ge=1)
    data_base: str = Field(..., description="Data base da análise")
    total_clientes_risco: int = Field(..., ge=0)
    clientes: List[ClienteRisco] = Field(default_factory=list)
    faturamento_em_risco: float = Field(default=0.0, ge=0, description="Faturamento total em risco (R$)")


# ============================================================================
# INSIGHTS DE PRODUTOS
# ============================================================================

class ProdutoAnalise(BaseModel):
    """Análise de um produto específico."""
    codigo: str
    produto: str
    unidades: int = Field(default=0, ge=0)
    caixas: float = Field(default=0.0, ge=0)
    faturamento: float = Field(..., ge=0)
    giro: Optional[float] = Field(None, ge=0, description="Giro de vendas (faturamento / (unidades + caixas * 12))")
    tendencia: Optional[str] = Field(None, description="Tendência: 'queda', 'estavel', 'crescimento'")


class InsightProdutosBaixaVenda(BaseModel):
    """Insight de produtos com baixa venda/giro."""
    tipo: str = Field(default="produtos_baixa_venda")
    criterio: str = Field(default="menor_volume", description="Critério de ordenação")
    periodo_dias: int = Field(default=90, ge=1)
    data_base: str = Field(..., description="Data base da análise")
    total_produtos: int = Field(..., ge=0)
    produtos: List[ProdutoAnalise] = Field(default_factory=list)


# ============================================================================
# INSIGHTS DE SUPERVISORES/EQUIPES
# ============================================================================

class SupervisorDesempenho(BaseModel):
    """Desempenho de um supervisor/departamento."""
    supervisor_id: int
    supervisor_nome: str
    pasta: Optional[str] = None
    meta_total: float = Field(..., ge=0)
    realizado_total: float = Field(..., ge=0)
    percentual_atingido: float = Field(..., ge=0)
    qtd_vendedores: int = Field(default=0, ge=0)
    qtd_clientes_ativos: int = Field(default=0, ge=0)
    concentracao_faturamento: float = Field(default=0.0, ge=0, le=100, description="% de concentração em top clientes")
    clientes_perdidos: int = Field(default=0, ge=0)
    score_desempenho: float = Field(default=0.0, ge=0, le=100)


class InsightDesempenhoSupervisores(BaseModel):
    """Insight de desempenho de supervisores e equipes."""
    tipo: str = Field(default="desempenho_supervisores")
    periodo_meses: int = Field(default=6, ge=1)
    mes_base: str = Field(..., description="Mês base da análise (YYYY-MM)")
    total_supervisores: int = Field(..., ge=0)
    supervisores: List[SupervisorDesempenho] = Field(default_factory=list)
    meta_total_empresa: float = Field(default=0.0, ge=0)
    realizado_total_empresa: float = Field(default=0.0, ge=0)
    percentual_atingido_empresa: float = Field(default=0.0, ge=0)


# ============================================================================
# INSIGHTS DE OPORTUNIDADES (NÍVEL DIRETORIA)
# ============================================================================

class OportunidadeRecuperacao(BaseModel):
    """Oportunidade de recuperação de vendas identificada."""
    tipo: str = Field(..., description="Tipo: 'cliente_inativo', 'produto_baixo_giro', 'categoria_perdida', etc.")
    descricao: str = Field(..., description="Descrição da oportunidade")
    potencial_faturamento: float = Field(..., ge=0, description="Potencial estimado em R$")
    esforco: str = Field(..., description="Nível de esforço: 'baixo', 'medio', 'alto'")
    responsavel: Optional[str] = Field(None, description="Supervisor ou vendedor responsável")
    prioridade: int = Field(default=5, ge=1, le=10, description="Prioridade (1-10)")


class InsightOportunidadesDiretoria(BaseModel):
    """Insight executivo de oportunidades para diretor."""
    tipo: str = Field(default="oportunidades_diretoria")
    data_base: str = Field(..., description="Data base da análise")
    periodo_analise_meses: int = Field(default=6, ge=1)
    total_oportunidades: int = Field(..., ge=0)
    oportunidades: List[OportunidadeRecuperacao] = Field(default_factory=list)
    potencial_total_recuperacao: float = Field(..., ge=0, description="Potencial total de recuperação em R$")
    resumo_executivo: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# BUNDLE DE INSIGHTS (USADO PELA CAMADA DE ORQUESTRAÇÃO)
# ============================================================================

class InsightBundle(BaseModel):
    """
    Bundle unificado de insights usado pela camada de orquestração.
    
    Agrupa dados brutos, análises ML e pontos-chave para o LLM.
    """
    intent: str = Field(..., description="Intent detectada")
    usuario_id: Optional[str] = None
    papel: Optional[str] = Field(None, description="Papel do usuário: diretor, supervisor, vendedor")
    
    # Dados brutos (números, tabelas agregadas, etc.)
    dados_brutos: Dict[str, Any] = Field(default_factory=dict)
    
    # Scores e previsões ML
    scores_ml: Dict[str, Any] = Field(default_factory=dict, description="Previsões, riscos, oportunidades calculadas por ML")
    
    # Pontos-chave pré-calculados em Python
    pontos_chave: List[str] = Field(default_factory=list, description="Destaques e insights já calculados")
    
    # Flags de validação
    tem_dados_suficientes: bool = Field(default=True, description="True se há dados suficientes para responder")
    mensagem_dados_insuficientes: Optional[str] = Field(None, description="Mensagem se não houver dados suficientes")
    
    # Metadados
    data_base: Optional[str] = Field(None, description="Data base da análise")
    periodo_analisado: Optional[str] = Field(None, description="Período analisado (ex: 'últimos 6 meses')")
    
    class Config:
        json_schema_extra = {
            "example": {
                "intent": "consulta_meta",
                "papel": "diretor",
                "dados_brutos": {
                    "meses": [...],
                    "meta_total": 1000000.0,
                    "realizado_total": 850000.0
                },
                "scores_ml": {},
                "pontos_chave": [
                    "Meta total: R$ 1.000.000",
                    "Realizado: R$ 850.000 (85%)",
                    "Gap de R$ 150.000"
                ],
                "tem_dados_suficientes": True
            }
        }



