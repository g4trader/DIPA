"""
Orquestrador DW - DIPAM COPILOT™.

Este módulo é responsável por:
1. Receber IntentSpec gerado pela IA
2. Validar o IntentSpec
3. Mapear IntentSpec → função DW correta
4. Executar função DW e normalizar resultado
5. Envelopar resposta em JSON estruturado para a IA

ARQUITETURA:
- NUNCA acessa banco diretamente (sqlite3, psycopg2)
- SEMPRE usa camada DW (dw/connection.py, dw/analytics_*.py)
- NUNCA chama LLM para inventar dados
- BigQuery NÃO implementado (apenas roadmap)
"""

import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from calendar import monthrange
from sqlalchemy.orm import Session

from src.agent.intent_spec import IntentSpec
from src.agent.rules import aplicar_regras, detectar_override_explicito
from src.agent.analise_causas import detectar_atingimento_abaixo_meta, gerar_analise_causas
from src.agent.memoria_comportamental import aplicar_instrucoes_comportamentais
from src.agent.behavior_memory import aplicar_regras_ao_intent
from src.agent.causas_detector import detectar_causas_para_mes

# Importa diretamente do arquivo analytics_metas.py sem passar por __init__.py
# Isso evita importar etl.py que requer pandas
import importlib.util
import os

# Calcula caminho absoluto do arquivo analytics_metas.py
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
analytics_path = os.path.join(base_dir, "src", "dw", "analytics_metas.py")

# Carrega módulo diretamente do arquivo
spec = importlib.util.spec_from_file_location("analytics_metas_direct", analytics_path)
analytics_metas = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analytics_metas)

listar_metas_por_mes = analytics_metas.listar_metas_por_mes
listar_vendas_por_mes = analytics_metas.listar_vendas_por_mes
listar_metas_realizado_por_supervisor = analytics_metas.listar_metas_realizado_por_supervisor
listar_clientes_criticos = analytics_metas.listar_clientes_criticos
MetaMes = analytics_metas.MetaMes
VendaMes = analytics_metas.VendaMes
SupervisorMeta = analytics_metas.SupervisorMeta
ClienteCritico = analytics_metas.ClienteCritico

from src.agent.queries_analytics import (
    get_metas_realizado_por_mes,
    get_piores_vendedores_por_gap
)

# Importa novas funções do queries.py
try:
    from src.dw.queries import (
        get_clientes_sem_compra_ha_dias,
        get_clientes_sem_compra_por_rota,
        get_clientes_queda_faturamento_ano_contra_ano,
        get_industrias_com_mais_vendedores_fora_meta,
        get_rotas_positivacao_industria,
        get_itens_baixa_media_mensal,
        get_clientes_sem_recompra_sku,
        get_clientes_segmento_sem_sku_no_periodo,
        get_clientes_uma_unidade_industria_mes,
        get_clientes_sem_sku_no_periodo,
        get_clientes_mix_minimo_nissin_mes,
        get_rotas_desempenho_mix_minimo_nissin_mes
    )
except ImportError as e:
    logger.warning(f"[orquestrador_dw] Não foi possível importar queries.py: {e}")
    # Define funções stub para evitar erros
    get_clientes_sem_compra_ha_dias = None
    get_clientes_sem_compra_por_rota = None
    get_clientes_queda_faturamento_ano_contra_ano = None
    get_industrias_com_mais_vendedores_fora_meta = None
    get_rotas_positivacao_industria = None
    get_itens_baixa_media_mensal = None
    get_clientes_sem_recompra_sku = None
    get_clientes_segmento_sem_sku_no_periodo = None
    get_clientes_uma_unidade_industria_mes = None
    get_clientes_sem_sku_no_periodo = None
    get_clientes_mix_minimo_nissin_mes = None
    get_rotas_desempenho_mix_minimo_nissin_mes = None

# Importa novas funções estendidas
import importlib.util
import os

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
analytics_extended_path = os.path.join(base_dir, "src", "dw", "analytics_metas_extended.py")

if os.path.exists(analytics_extended_path):
    spec_extended = importlib.util.spec_from_file_location("analytics_metas_extended", analytics_extended_path)
    analytics_extended = importlib.util.module_from_spec(spec_extended)
    spec_extended.loader.exec_module(analytics_extended)
    
    get_metas_por_mes = analytics_extended.get_metas_por_mes
    get_gap_por_rota = analytics_extended.get_gap_por_rota
    get_piores_vendedores = analytics_extended.get_piores_vendedores
    get_clientes_com_queda = analytics_extended.get_clientes_com_queda
    get_skus_com_quebra = analytics_extended.get_skus_com_quebra
    get_tendencias = analytics_extended.get_tendencias
else:
    # Fallback se arquivo não existir
    get_metas_por_mes = None
    get_gap_por_rota = None
    get_piores_vendedores = None
    get_clientes_com_queda = None
    get_skus_com_quebra = None
    get_tendencias = None

logger = logging.getLogger(__name__)


def _aplicar_periodo_padrao(intent_spec: IntentSpec) -> IntentSpec:
    """
    Aplica período padrão se periodo_inicio ou periodo_fim forem null.
    
    Regra padrão: mês atual ou intervalo disponível no DW.
    """
    if intent_spec.periodo_inicio is None or intent_spec.periodo_fim is None:
        # Usa mês atual como padrão
        hoje = datetime.now()
        mes_atual = hoje.strftime("%Y-%m")
        primeiro_dia = hoje.replace(day=1)
        ultimo_dia = monthrange(hoje.year, hoje.month)[1]
        ultimo_dia_mes = hoje.replace(day=ultimo_dia)
        
        if intent_spec.periodo_inicio is None:
            intent_spec.periodo_inicio = primeiro_dia.strftime("%Y-%m-%d")
        if intent_spec.periodo_fim is None:
            intent_spec.periodo_fim = ultimo_dia_mes.strftime("%Y-%m-%d")
        
        logger.info(
            f"[orquestrador_dw] Período padrão aplicado: "
            f"{intent_spec.periodo_inicio} a {intent_spec.periodo_fim}"
        )
    
    return intent_spec


def _validar_intent_spec(intent_spec: IntentSpec) -> tuple[bool, Optional[str]]:
    """
    Valida IntentSpec e retorna (valido, mensagem_erro).
    
    Returns:
        (True, None) se válido
        (False, mensagem_erro) se inválido
    """
    # Valida tipo
    tipos_validos = [
        "meta", "vendas", "clientes_criticos", "churn",
        "ranking_vendedores", "ranking_produtos",
        "analise_meta_detalhada", "metas_por_supervisor",
        "vendas_por_mes", "outros",
        # Novos tipos do ENGINEERING_QUERIES.md
        "clientes_sem_compra", "queda_faturamento", "meta_departamento",
        "positivacao", "mix", "recompra", "clientes_sem_item",
        "vendas_baixas", "mix_nissin"
    ]
    if intent_spec.tipo not in tipos_validos:
        return False, f"Tipo '{intent_spec.tipo}' não é suportado. Tipos válidos: {tipos_validos}"
    
    # Valida dimensão principal
    dimensoes_validas = [
        "mes", "vendedor", "supervisor", "rota",
        "cliente", "marca", "categoria", "sku", "produto", "nenhuma"
    ]
    if intent_spec.dimensao_principal not in dimensoes_validas:
        return False, f"Dimensão principal '{intent_spec.dimensao_principal}' não é suportada"
    
    # Valida período se fornecido
    if intent_spec.periodo_inicio:
        try:
            datetime.strptime(intent_spec.periodo_inicio, "%Y-%m-%d")
        except ValueError:
            return False, f"periodo_inicio '{intent_spec.periodo_inicio}' não é uma data válida (formato esperado: YYYY-MM-DD)"
    
    if intent_spec.periodo_fim:
        try:
            datetime.strptime(intent_spec.periodo_fim, "%Y-%m-%d")
        except ValueError:
            return False, f"periodo_fim '{intent_spec.periodo_fim}' não é uma data válida (formato esperado: YYYY-MM-DD)"
    
    # Valida que periodo_fim >= periodo_inicio se ambos existirem
    if intent_spec.periodo_inicio and intent_spec.periodo_fim:
        try:
            inicio = datetime.strptime(intent_spec.periodo_inicio, "%Y-%m-%d")
            fim = datetime.strptime(intent_spec.periodo_fim, "%Y-%m-%d")
            if fim < inicio:
                return False, f"periodo_fim ({intent_spec.periodo_fim}) deve ser >= periodo_inicio ({intent_spec.periodo_inicio})"
        except Exception:
            pass  # Já validado acima
    
    # Valida compatibilidade tipo + dimensão
    incompatibilidades = [
        ("ranking_vendedores", "produto"),
        ("ranking_produtos", "vendedor"),
    ]
    for tipo_incomp, dimensao_incomp in incompatibilidades:
        if intent_spec.tipo == tipo_incomp and intent_spec.dimensao_principal == dimensao_incomp:
            return False, f"Tipo '{intent_spec.tipo}' não é compatível com dimensão '{intent_spec.dimensao_principal}'"
    
    return True, None


def _normalizar_periodo_para_mes_ano(periodo: str) -> str:
    """
    Converte período YYYY-MM-DD para YYYY-MM (formato usado pelas funções DW).
    """
    if not periodo:
        return None
    
    try:
        # Se já for YYYY-MM, retorna
        if len(periodo) == 7:
            return periodo
        
        # Se for YYYY-MM-DD, extrai YYYY-MM
        if len(periodo) == 10:
            return periodo[:7]
        
        return periodo
    except Exception:
        return periodo


def _converter_dataclass_para_dict(obj: Any) -> Dict[str, Any]:
    """
    Converte dataclass para dicionário serializável.
    """
    if hasattr(obj, '__dict__'):
        return {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}
    elif hasattr(obj, '__dataclass_fields__'):
        # É uma dataclass
        return {field: getattr(obj, field) for field in obj.__dataclass_fields__}
    else:
        return obj


def _normalizar_resultado_dw(resultado: Any) -> List[Dict[str, Any]]:
    """
    Normaliza resultado do DW para lista de dicionários serializáveis.
    """
    if resultado is None:
        return []
    
    if isinstance(resultado, list):
        # Se for lista de dataclasses ou objetos
        normalizado = []
        for item in resultado:
            if isinstance(item, dict):
                normalizado.append(item)
            else:
                # Tenta converter dataclass/objeto para dict
                normalizado.append(_converter_dataclass_para_dict(item))
        return normalizado
    
    if isinstance(resultado, dict):
        # Se for dicionário único, converte para lista
        return [resultado]
    
    # Tenta converter objeto único para dict
    return [_converter_dataclass_para_dict(resultado)]


# ============================================================================
# MAPEAMENTO IntentSpec → FUNÇÃO DW
# ============================================================================

def _mapear_para_funcao_dw(
    intent_spec: IntentSpec,
    session: Session
) -> tuple[Optional[Callable], Optional[str], Dict[str, Any]]:
    """
    Mapeia IntentSpec para função DW correta.
    
    Returns:
        (funcao_dw, erro_mensagem, kwargs)
        Se erro_mensagem não for None, função não foi encontrada
    """
    tipo = intent_spec.tipo
    dimensao = intent_spec.dimensao_principal
    
    # Normaliza períodos para formato YYYY-MM (usado pelas funções DW)
    periodo_inicio_mes = _normalizar_periodo_para_mes_ano(intent_spec.periodo_inicio) if intent_spec.periodo_inicio else None
    periodo_fim_mes = _normalizar_periodo_para_mes_ano(intent_spec.periodo_fim) if intent_spec.periodo_fim else None
    
    # MAPEAMENTO EXPLÍCITO: (tipo, dimensao_principal) → função DW
    mapeamento = {
        # META
        ("meta", "mes"): (
            listar_metas_por_mes,
            {
                "periodo_inicio": periodo_inicio_mes,
                "periodo_fim": periodo_fim_mes or periodo_inicio_mes,
                "excluir_totais": True
            }
        ),
        ("meta", "vendedor"): (
            get_piores_vendedores_por_gap,
            {
                "mes": periodo_inicio_mes or periodo_fim_mes,
                "limite": intent_spec.filtros.get("top_n") or intent_spec.filtros.get("limite", 10),
                "excluir_totais": True
            }
        ),
        ("meta", "supervisor"): (
            listar_metas_realizado_por_supervisor,
            {
                "mes": periodo_inicio_mes or periodo_fim_mes
            }
        ),
        ("meta", "nenhuma"): (
            get_metas_realizado_por_mes,
            {
                "mes": periodo_inicio_mes or periodo_fim_mes,
                "excluir_totais": True
            }
        ),
        
        # VENDAS
        ("vendas", "mes"): (
            listar_vendas_por_mes,
            {
                "periodo_inicio": periodo_inicio_mes,
                "periodo_fim": periodo_fim_mes or periodo_inicio_mes
            }
        ),
        
        # CLIENTES CRÍTICOS / CHURN
        ("clientes_criticos", "cliente"): (
            listar_clientes_criticos,
            {
                "periodo_inicio": periodo_inicio_mes,
                "periodo_fim": periodo_fim_mes or periodo_inicio_mes,
                "supervisor_id": intent_spec.filtros.get("supervisor_id"),
                "rota_id": intent_spec.filtros.get("rota_id") or intent_spec.filtros.get("vendedor_id"),
                "limite": intent_spec.filtros.get("limite", 50)
            }
        ),
        ("churn", "cliente"): (
            listar_clientes_criticos,
            {
                "periodo_inicio": periodo_inicio_mes,
                "periodo_fim": periodo_fim_mes or periodo_inicio_mes,
                "supervisor_id": intent_spec.filtros.get("supervisor_id"),
                "rota_id": intent_spec.filtros.get("rota_id") or intent_spec.filtros.get("vendedor_id"),
                "limite": intent_spec.filtros.get("limite", 50)
            }
        ),
        
        # RANKING VENDEDORES
        ("ranking_vendedores", "vendedor"): (
            get_piores_vendedores_por_gap,
            {
                "mes": periodo_inicio_mes or periodo_fim_mes,
                "limite": intent_spec.filtros.get("top_n") or intent_spec.filtros.get("limite", 10),
                "excluir_totais": True
            }
        ),
        
        # NOVOS TIPOS DO ENGINEERING_QUERIES.md
        ("clientes_sem_compra", "cliente"): (
            get_clientes_sem_compra_ha_dias,
            {
                "dias": intent_spec.filtros.get("dias", 60),
                "data_referencia": intent_spec.periodo_fim or intent_spec.periodo_inicio
            }
        ) if get_clientes_sem_compra_ha_dias else None,
        
        ("queda_faturamento", "cliente"): (
            get_clientes_queda_faturamento_ano_contra_ano,
            {
                "ano_base": intent_spec.filtros.get("ano_base", 2024),
                "ano_comparado": intent_spec.filtros.get("ano_comparado", 2025),
                "top_n": intent_spec.filtros.get("top_n", 50)
            }
        ) if get_clientes_queda_faturamento_ano_contra_ano else None,
        
        ("meta_departamento", "nenhuma"): (
            get_industrias_com_mais_vendedores_fora_meta,
            {
                "ano": intent_spec.filtros.get("ano") or (int(periodo_inicio_mes.split("-")[0]) if periodo_inicio_mes else None),
                "mes": intent_spec.filtros.get("mes") or (int(periodo_inicio_mes.split("-")[1]) if periodo_inicio_mes else None),
                "atingimento_limite": intent_spec.filtros.get("atingimento_limite", 100.0)
            }
        ) if get_industrias_com_mais_vendedores_fora_meta else None,
        
        ("positivacao", "rota"): (
            get_rotas_positivacao_industria,
            {
                "industria": intent_spec.filtros.get("industria", ""),
                "data_inicio": intent_spec.periodo_inicio or "",
                "data_fim": intent_spec.periodo_fim or ""
            }
        ) if get_rotas_positivacao_industria else None,
        
        ("positivacao", "cliente"): (
            get_clientes_sem_sku_no_periodo,
            {
                "sku": intent_spec.filtros.get("sku", ""),
                "data_inicio": intent_spec.periodo_inicio or "",
                "data_fim": intent_spec.periodo_fim or ""
            }
        ) if get_clientes_sem_sku_no_periodo else None,
        
        ("mix", "produto"): (
            get_itens_baixa_media_mensal,
            {
                "meses_janela": intent_spec.filtros.get("meses_janela", 12),
                "limite_media": intent_spec.filtros.get("limite_media", 10.0),
                "data_referencia": intent_spec.periodo_fim or intent_spec.periodo_inicio
            }
        ) if get_itens_baixa_media_mensal else None,
        
        ("vendas_baixas", "produto"): (
            get_itens_baixa_media_mensal,
            {
                "meses_janela": intent_spec.filtros.get("meses_janela", 12),
                "limite_media": intent_spec.filtros.get("limite_media", 10.0),
                "data_referencia": intent_spec.periodo_fim or intent_spec.periodo_inicio
            }
        ) if get_itens_baixa_media_mensal else None,
        
        ("recompra", "cliente"): (
            get_clientes_sem_recompra_sku,
            {
                "sku": intent_spec.filtros.get("sku", ""),
                "meses_janela": intent_spec.filtros.get("meses_janela", 6),
                "data_referencia": intent_spec.periodo_fim or intent_spec.periodo_inicio
            }
        ) if get_clientes_sem_recompra_sku else None,
        
        ("clientes_sem_item", "cliente"): (
            get_clientes_segmento_sem_sku_no_periodo if intent_spec.filtros.get("segmento") else get_clientes_sem_sku_no_periodo,
            {
                "segmento": intent_spec.filtros.get("segmento"),
                "sku": intent_spec.filtros.get("sku", ""),
                "data_inicio": intent_spec.periodo_inicio or "",
                "data_fim": intent_spec.periodo_fim or ""
            }
        ) if (get_clientes_segmento_sem_sku_no_periodo or get_clientes_sem_sku_no_periodo) else None,
        
        ("vendas_baixas", "cliente"): (
            get_clientes_uma_unidade_industria_mes,
            {
                "industria": intent_spec.filtros.get("industria", ""),
                "ano": intent_spec.filtros.get("ano") or (int(periodo_inicio_mes.split("-")[0]) if periodo_inicio_mes else None),
                "mes": intent_spec.filtros.get("mes") or (int(periodo_inicio_mes.split("-")[1]) if periodo_inicio_mes else None)
            }
        ) if get_clientes_uma_unidade_industria_mes else None,
        
        ("mix_nissin", "cliente"): (
            get_clientes_mix_minimo_nissin_mes,
            {
                "ano": intent_spec.filtros.get("ano") or (int(periodo_inicio_mes.split("-")[0]) if periodo_inicio_mes else None),
                "mes": intent_spec.filtros.get("mes") or (int(periodo_inicio_mes.split("-")[1]) if periodo_inicio_mes else None)
            }
        ) if get_clientes_mix_minimo_nissin_mes else None,
        
        ("mix_nissin", "rota"): (
            get_rotas_desempenho_mix_minimo_nissin_mes,
            {
                "ano": intent_spec.filtros.get("ano") or (int(periodo_inicio_mes.split("-")[0]) if periodo_inicio_mes else None),
                "mes": intent_spec.filtros.get("mes") or (int(periodo_inicio_mes.split("-")[1]) if periodo_inicio_mes else None)
            }
        ) if get_rotas_desempenho_mix_minimo_nissin_mes else None,
    }
    
    # Remove entradas None (funções não disponíveis)
    mapeamento = {k: v for k, v in mapeamento.items() if v is not None}
    
    # Busca mapeamento
    chave = (tipo, dimensao)
    if chave in mapeamento:
        funcao, kwargs = mapeamento[chave]
        return funcao, None, kwargs
    
    # Fallback: tenta mapeamento genérico por tipo
    mapeamento_generico = {
        "meta": (
            get_metas_realizado_por_mes,
            {"mes": periodo_inicio_mes or periodo_fim_mes, "excluir_totais": True}
        ),
        "vendas": (
            listar_vendas_por_mes,
            {
                "periodo_inicio": periodo_inicio_mes,
                "periodo_fim": periodo_fim_mes or periodo_inicio_mes
            }
        ),
        "clientes_criticos": (
            listar_clientes_criticos,
            {
                "periodo_inicio": periodo_inicio_mes,
                "periodo_fim": periodo_fim_mes or periodo_inicio_mes,
                "limite": intent_spec.filtros.get("limite", 50)
            }
        ),
        "churn": (
            listar_clientes_criticos,
            {
                "periodo_inicio": periodo_inicio_mes,
                "periodo_fim": periodo_fim_mes or periodo_inicio_mes,
                "limite": intent_spec.filtros.get("limite", 50)
            }
        ),
    }
    
    if tipo in mapeamento_generico:
        funcao, kwargs = mapeamento_generico[tipo]
        return funcao, None, kwargs
    
    # Não encontrou mapeamento
    return None, f"Combinação (tipo='{tipo}', dimensao_principal='{dimensao}') não é suportada", {}


def executar_intent_spec(
    session: Session,
    intent_spec: IntentSpec,
    contexto_usuario: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Orquestra a execução de um IntentSpec no DW.
    
    Fluxo:
    1. Aplica período padrão se necessário
    2. Valida IntentSpec
    3. Mapeia para função DW
    4. Executa função DW
    5. Normaliza resultado
    6. Envelopa resposta
    
    Args:
        session: Sessão SQLAlchemy
        intent_spec: IntentSpec a ser executado
        contexto_usuario: Contexto do usuário (ex.: {"role": "diretor", "user_id": "123"})
        
    Returns:
        dict com estrutura:
        {
            "status": "ok" | "sem_dados" | "erro_validacao" | "erro_interno",
            "mensagem": "texto curto explicando o status",
            "intent": { ... IntentSpec ... },
            "periodo_analisado": {"inicio": "...", "fim": "..."},
            "dados": [ ... linhas retornadas pelo DW ... ],
            "regras_aplicadas": {...}  # Resumo das regras aplicadas
        }
    """
    logger.info(
        f"[orquestrador_dw] Executando IntentSpec: "
        f"tipo={intent_spec.tipo}, "
        f"dimensao={intent_spec.dimensao_principal}, "
        f"periodo={intent_spec.periodo_inicio} a {intent_spec.periodo_fim}"
    )
    
    # Inicializa contexto_usuario se não fornecido
    if contexto_usuario is None:
        contexto_usuario = {"role": "diretor"}
    
    # PASSO 1: Aplica período padrão se necessário
    intent_spec = _aplicar_periodo_padrao(intent_spec)
    
    # PASSO 1.5: Aplica behavior memory (regras persistentes do banco)
    intent_spec, regras_behavior_aplicadas = aplicar_regras_ao_intent(intent_spec, session)
    # regras_behavior_aplicadas será incluído em detalhes_tecnicos
    if not regras_behavior_aplicadas:
        regras_behavior_aplicadas = []  # Garante que é sempre uma lista
    
    # PASSO 1.6: Aplica instruções comportamentais e regras de feedback (antes de validar)
    filtros_sql = intent_spec.filtros.copy()
    
    # Aplica instruções comportamentais (que incluem regras de feedback)
    resultado_instrucoes = aplicar_instrucoes_comportamentais(
        session=session,
        intent_spec=intent_spec,
        filtros_sql=filtros_sql,
        contexto_usuario=contexto_usuario
    )
    
    # Atualiza filtros do IntentSpec com instruções aplicadas
    intent_spec.filtros.update(resultado_instrucoes["filtros_ajustados"])
    regras_aplicadas = resultado_instrucoes.get("instrucoes_aplicadas", resultado_instrucoes.get("regras_aplicadas", {}))
    
    logger.info(
        f"[orquestrador_dw] Instruções comportamentais aplicadas, "
        f"filtros ajustados: {intent_spec.filtros}"
    )
    
    # PASSO 2: Valida IntentSpec
    valido, mensagem_erro = _validar_intent_spec(intent_spec)
    if not valido:
        logger.warning(f"[orquestrador_dw] IntentSpec inválido: {mensagem_erro}")
        return {
            "status": "erro_validacao",
            "mensagem": mensagem_erro,
            "intent": intent_spec.to_dict(),
            "periodo_analisado": {
                "inicio": intent_spec.periodo_inicio,
                "fim": intent_spec.periodo_fim
            },
            "dados": []
        }
    
    # PASSO 3: Mapeia para função DW
    funcao_dw, erro_mapeamento, kwargs = _mapear_para_funcao_dw(intent_spec, session)
    if erro_mapeamento:
        logger.warning(f"[orquestrador_dw] Erro no mapeamento: {erro_mapeamento}")
        return {
            "status": "erro_validacao",
            "mensagem": erro_mapeamento,
            "intent": intent_spec.to_dict(),
            "periodo_analisado": {
                "inicio": intent_spec.periodo_inicio,
                "fim": intent_spec.periodo_fim
            },
            "dados": []
        }
    
    # PASSO 4: Executa função DW
    try:
        # Prepara argumentos baseado na assinatura da função
        # As funções DW têm assinaturas diferentes, então precisamos adaptar
        
        # Extrai kwargs específicos
        periodo_inicio_kwarg = kwargs.pop("periodo_inicio", None)
        periodo_fim_kwarg = kwargs.pop("periodo_fim", None)
        mes_kwarg = kwargs.pop("mes", None)
        limite_kwarg = kwargs.pop("limite", None)
        excluir_totais_kwarg = kwargs.pop("excluir_totais", True)
        supervisor_id_kwarg = kwargs.pop("supervisor_id", None)
        rota_id_kwarg = kwargs.pop("rota_id", None)
        
        # Chama função baseado na assinatura esperada
        # listar_metas_por_mes(session, periodo_inicio, periodo_fim, excluir_totais=True)
        if funcao_dw == listar_metas_por_mes:
            resultado = funcao_dw(
                session,
                periodo_inicio_kwarg,
                periodo_fim_kwarg or periodo_inicio_kwarg,
                excluir_totais=excluir_totais_kwarg
            )
        # listar_vendas_por_mes(session, periodo_inicio, periodo_fim)
        elif funcao_dw == listar_vendas_por_mes:
            resultado = funcao_dw(
                session,
                periodo_inicio_kwarg,
                periodo_fim_kwarg or periodo_inicio_kwarg
            )
        # listar_metas_realizado_por_supervisor(session, mes_ano)
        elif funcao_dw == listar_metas_realizado_por_supervisor:
            resultado = funcao_dw(session, mes_kwarg or periodo_inicio_kwarg)
        # listar_clientes_criticos(session, periodo_inicio, periodo_fim, supervisor_id=None, rota_id=None, limite=50)
        elif funcao_dw == listar_clientes_criticos:
            resultado = funcao_dw(
                session,
                periodo_inicio_kwarg,
                periodo_fim_kwarg or periodo_inicio_kwarg,
                supervisor_id=supervisor_id_kwarg,
                rota_id=rota_id_kwarg,
                limite=limite_kwarg or 50
            )
        # get_metas_realizado_por_mes(session, mes_ano, excluir_totais=True)
        elif funcao_dw == get_metas_realizado_por_mes:
            periodo = mes_kwarg or periodo_inicio_kwarg or periodo_fim_kwarg
            resultado = funcao_dw(
                session,
                periodo,
                excluir_totais=excluir_totais_kwarg
            )
        # get_piores_vendedores_por_gap(session, mes_ano, limite=10, excluir_totais=True)
        elif funcao_dw == get_piores_vendedores_por_gap:
            periodo = mes_kwarg or periodo_inicio_kwarg or periodo_fim_kwarg
            resultado = funcao_dw(
                session,
                periodo,
                limite=limite_kwarg or 10,
                excluir_totais=excluir_totais_kwarg
            )
        else:
            # Fallback: tenta chamar com session + kwargs
            # Para novas funções de queries.py, adiciona filtros_behavior
            if 'filtros_behavior' not in kwargs:
                # Prepara filtros_behavior a partir das regras aplicadas
                filtros_behavior = {}
                if regras_aplicadas:
                    # Converte regras aplicadas para formato esperado pelas queries
                    if "excluir_pastas" in str(regras_aplicadas) or "excluir_carteiras" in intent_spec.filtros:
                        filtros_behavior["excluir_pastas"] = intent_spec.filtros.get("excluir_carteiras", [])
                    if "excluir_rotas" in intent_spec.filtros:
                        filtros_behavior["excluir_rotas"] = intent_spec.filtros.get("excluir_rotas", [])
                    if "excluir_segmentos" in intent_spec.filtros:
                        filtros_behavior["excluir_segmentos"] = intent_spec.filtros.get("excluir_segmentos", [])
                kwargs["filtros_behavior"] = filtros_behavior if filtros_behavior else None
            
            # ✅ CORREÇÃO CRÍTICA Q1: Para Q1, bypassa cache para garantir resultado correto
            if intent_spec.tipo == "clientes_sem_compra":
                kwargs["bypass_cache"] = True
                logger.info(
                    f"[Q1_ORQ] Bypassando cache para garantir resultado correto. "
                    f"Função: {funcao_dw.__name__ if funcao_dw else 'None'}, "
                    f"kwargs: {kwargs}"
                )
            
            resultado = funcao_dw(session, **kwargs)
            
            # ✅ LOG CRÍTICO: Para Q1, loga tipo e tamanho do resultado
            if intent_spec.tipo == "clientes_sem_compra":
                logger.info(
                    f"[Q1_ORQ] Função DW retornou: tipo={type(resultado)}, "
                    f"tamanho={len(resultado) if isinstance(resultado, (list, dict)) else 'N/A'}"
                )
                if isinstance(resultado, dict):
                    logger.warning(
                        f"[Q1_ORQ] ⚠️  Resultado é dict, não lista! Chaves: {list(resultado.keys())[:10]}"
                    )
            
            # ✅ LOG CRÍTICO: Para Q1, loga quantidade de registros retornados pela função DW
            if intent_spec.tipo == "clientes_sem_compra":
                if isinstance(resultado, list):
                    logger.info(
                        f"[Q1_ORQ] Resultado DW bruto - registros: {len(resultado)}"
                    )
                    # Verifica duplicatas
                    cliente_ids = [r.get("cliente_id") for r in resultado if isinstance(r, dict)]
                    clientes_unicos = len(set(cliente_ids))
                    if len(cliente_ids) != clientes_unicos:
                        logger.error(
                            f"[Q1_ORQ] ❌ ERRO: Função DW retornou {len(cliente_ids)} registros mas "
                            f"apenas {clientes_unicos} clientes únicos (duplicatas na query!)"
                        )
                    else:
                        logger.info(
                            f"[Q1_ORQ] ✅ Função DW: {clientes_unicos} clientes únicos (sem duplicatas)"
                        )
                else:
                    logger.warning(
                        f"[Q1_ORQ] ⚠️  Função DW retornou tipo inesperado: {type(resultado)}"
                    )
        
        logger.info(f"[orquestrador_dw] Função DW executada com sucesso, resultado: {type(resultado)}")
        
    except Exception as e:
        logger.error(f"[orquestrador_dw] Erro ao executar função DW: {e}", exc_info=True)
        return {
            "status": "erro_interno",
            "mensagem": f"Erro interno ao executar consulta DW: {str(e)}",
            "intent": intent_spec.to_dict(),
            "periodo_analisado": {
                "inicio": intent_spec.periodo_inicio,
                "fim": intent_spec.periodo_fim
            },
            "dados": []
        }
    
    # PASSO 5: Normaliza resultado
    # ✅ CORREÇÃO CRÍTICA Q1: Para Q1, NÃO permite que normalização altere cardinalidade
    if intent_spec.tipo == "clientes_sem_compra":
        # Para Q1, resultado já vem como lista de dicts, não precisa normalizar
        # A query Q1 já garante 1 linha por cliente (GROUP BY cliente_id)
        if isinstance(resultado, list):
            dados_normalizados = resultado
            logger.info(
                f"[Q1_ORQ] Resultado DW bruto - registros: {len(dados_normalizados)}"
            )
            # Validação defensiva: garante que não há duplicatas
            cliente_ids = [r.get("cliente_id") for r in dados_normalizados if isinstance(r, dict)]
            clientes_unicos = len(set(cliente_ids))
            if len(cliente_ids) != clientes_unicos:
                logger.error(
                    f"[Q1_ORQ] ❌ ERRO CRÍTICO: Query retornou {len(cliente_ids)} registros mas "
                    f"apenas {clientes_unicos} clientes únicos. Isso não deveria acontecer!"
                )
                # Remove duplicatas mantendo a primeira ocorrência
                visto = set()
                dados_normalizados = []
                for r in resultado:
                    if isinstance(r, dict):
                        cliente_id = r.get("cliente_id")
                        if cliente_id not in visto:
                            visto.add(cliente_id)
                            dados_normalizados.append(r)
                logger.warning(
                    f"[Q1_ORQ] Duplicatas removidas: {len(resultado)} -> {len(dados_normalizados)}"
                )
            else:
                logger.info(
                    f"[Q1_ORQ] ✅ Q1: {clientes_unicos} clientes únicos (sem duplicatas)"
                )
        else:
            # Fallback: normaliza se não for lista
            dados_normalizados = _normalizar_resultado_dw(resultado)
            logger.warning(
                f"[Q1_ORQ] ⚠️  Q1 retornou tipo inesperado: {type(resultado)}, normalizado para {len(dados_normalizados)} registros"
            )
    else:
        # Para outros tipos, usa normalização padrão
        dados_normalizados = _normalizar_resultado_dw(resultado)
    
    # ✅ LOG CRÍTICO: Para Q1, loga quantidade após normalização
    if intent_spec.tipo == "clientes_sem_compra":
        logger.info(
            f"[Q1_ORQ] Resultado após normalização - registros: {len(dados_normalizados)}"
        )
        # Validação final: garante que cardinalidade não mudou
        cliente_ids_final = [r.get("cliente_id") for r in dados_normalizados if isinstance(r, dict)]
        clientes_unicos_final = len(set(cliente_ids_final))
        if len(cliente_ids_final) != clientes_unicos_final:
            logger.error(
                f"[Q1_ORQ] ❌ ERRO: Normalização alterou cardinalidade! "
                f"{len(cliente_ids_final)} registros vs {clientes_unicos_final} clientes únicos"
            )
    
    # Se resultado for dict com estrutura especial (ex.: kpis_mes), extrai dados
    # ✅ CORREÇÃO CRÍTICA: Para Q1, NUNCA processa essa lógica (já normalizado acima)
    # Essa lógica pode estar expandindo dados incorretamente para Q1
    if intent_spec.tipo != "clientes_sem_compra" and isinstance(resultado, dict):
        # Se tiver "linhas_detalhadas" ou "metas_por_mes", usa isso
        if "linhas_detalhadas" in resultado:
            dados_normalizados = _normalizar_resultado_dw(resultado["linhas_detalhadas"])
        elif "metas_por_mes" in resultado:
            dados_normalizados = _normalizar_resultado_dw(resultado["metas_por_mes"])
        elif "vendas_por_mes" in resultado:
            dados_normalizados = _normalizar_resultado_dw(resultado["vendas_por_mes"])
        elif "clientes_criticos" in resultado:
            dados_normalizados = _normalizar_resultado_dw(resultado["clientes_criticos"])
        elif "supervisores_meta" in resultado:
            dados_normalizados = _normalizar_resultado_dw(resultado["supervisores_meta"])
        elif "piores_vendedores" in resultado:
            dados_normalizados = _normalizar_resultado_dw(resultado["piores_vendedores"])
        # Se não tiver estrutura especial, mas tem "tem_dados", mantém dict original
        elif resultado.get("tem_dados") is False:
            dados_normalizados = []
        else:
            # Tenta normalizar o dict inteiro
            dados_normalizados = [resultado]
    
    # ✅ VALIDAÇÃO FINAL CRÍTICA Q1: Garante que cardinalidade não mudou
    if intent_spec.tipo == "clientes_sem_compra":
        # Para Q1, resultado DEVE ser uma lista
        if isinstance(resultado, list):
            # Se normalização alterou cardinalidade, usa resultado original
            if len(resultado) != len(dados_normalizados):
                logger.error(
                    f"[Q1_ORQ] ❌ ERRO CRÍTICO: Normalização alterou cardinalidade! "
                    f"Resultado original: {len(resultado)}, Após normalização: {len(dados_normalizados)}"
                )
                # CORREÇÃO: Usa resultado original se normalização alterou cardinalidade
                dados_normalizados = resultado
                logger.warning(
                    f"[Q1_ORQ] ✅ CORRIGIDO: Usando resultado original ({len(dados_normalizados)} registros)"
                )
            # Validação adicional: garante que não há duplicatas
            cliente_ids_final = [r.get("cliente_id") for r in dados_normalizados if isinstance(r, dict)]
            clientes_unicos_final = len(set(cliente_ids_final))
            if len(cliente_ids_final) != clientes_unicos_final:
                logger.error(
                    f"[Q1_ORQ] ❌ ERRO: Duplicatas detectadas após normalização! "
                    f"{len(cliente_ids_final)} registros vs {clientes_unicos_final} clientes únicos"
                )
                # Remove duplicatas mantendo a primeira ocorrência
                visto = set()
                dados_normalizados_limpos = []
                for r in dados_normalizados:
                    if isinstance(r, dict):
                        cliente_id = r.get("cliente_id")
                        if cliente_id not in visto:
                            visto.add(cliente_id)
                            dados_normalizados_limpos.append(r)
                dados_normalizados = dados_normalizados_limpos
                logger.warning(
                    f"[Q1_ORQ] ✅ Duplicatas removidas: {len(cliente_ids_final)} -> {len(dados_normalizados)}"
                )
        else:
            # Se resultado não for lista, algo está errado
            logger.error(
                f"[Q1_ORQ] ❌ ERRO CRÍTICO: Resultado não é lista! Tipo: {type(resultado)}"
            )
            # Tenta normalizar
            dados_normalizados = _normalizar_resultado_dw(resultado)
            logger.warning(
                f"[Q1_ORQ] ⚠️  Normalizado para {len(dados_normalizados)} registros"
            )
    
    # PASSO 6: Determina status
    if len(dados_normalizados) == 0:
        status = "sem_dados"
        mensagem = f"Não há dados no data warehouse DIPAM para o período/filtro solicitado. Período: {intent_spec.periodo_inicio} a {intent_spec.periodo_fim}."
    else:
        status = "ok"
        mensagem = f"Dados consultados com sucesso. {len(dados_normalizados)} registro(s) encontrado(s)."
    
    # PASSO 6.5: Detecta atingimento abaixo de meta e gera análise de causas
    analise_causas = {}
    causas_detector = {}  # Inicializa causas_detector
    if status == "ok" and dados_normalizados:
        # Prepara dados_dw para detecção
        dados_dw_para_deteccao = {
            "dados": dados_normalizados,
            "status": status
        }
        
        # Tenta extrair meta_total e realizado_total agregados
        if isinstance(dados_normalizados, list) and len(dados_normalizados) > 0:
            meta_total = sum(float(item.get("meta_total", 0) or 0) for item in dados_normalizados if isinstance(item, dict))
            realizado_total = sum(float(item.get("realizado_total", 0) or 0) for item in dados_normalizados if isinstance(item, dict))
            if meta_total > 0:
                dados_dw_para_deteccao["meta_total"] = meta_total
                dados_dw_para_deteccao["realizado_total"] = realizado_total
        
        # Detecta se atingimento < 100%
        if detectar_atingimento_abaixo_meta(dados_dw_para_deteccao):
            # Extrai mes_ano do período
            mes_ano = _normalizar_periodo_para_mes_ano(intent_spec.periodo_inicio) if intent_spec.periodo_inicio else None
            if not mes_ano and intent_spec.periodo_fim:
                mes_ano = _normalizar_periodo_para_mes_ano(intent_spec.periodo_fim)
            
            if mes_ano:
                logger.info(f"[orquestrador_dw] Meta não batida detectada para {mes_ano}. Gerando análise de causas...")
                try:
                    analise_causas = gerar_analise_causas(
                        session=session,
                        dados_dw=dados_dw_para_deteccao,
                        mes_ano=mes_ano,
                        limite_vendedores=10,
                        limite_clientes=20,
                        limite_skus=20
                    )
                    logger.info(f"[orquestrador_dw] Análise de causas gerada: {len(analise_causas.get('vendedores_pior_desempenho', []))} vendedores, {len(analise_causas.get('clientes_reduziram_compra', []))} clientes")
                except Exception as e:
                    logger.error(f"[orquestrador_dw] Erro ao gerar análise de causas: {e}")
    
    # PASSO 6.7: Para clientes_sem_compra, adiciona tabela agregada por rota
    tabela_por_rota = None
    if intent_spec.tipo == "clientes_sem_compra" and status == "ok" and dados_normalizados:
        try:
            if get_clientes_sem_compra_por_rota:
                # Extrai parâmetros da query original
                dias = intent_spec.filtros.get("dias", 60)
                data_referencia = intent_spec.periodo_fim or intent_spec.periodo_inicio
                filtros_behavior = {}
                if regras_aplicadas:
                    if "excluir_pastas" in str(regras_aplicadas) or "excluir_carteiras" in intent_spec.filtros:
                        filtros_behavior["excluir_pastas"] = intent_spec.filtros.get("excluir_carteiras", [])
                    if "excluir_rotas" in intent_spec.filtros:
                        filtros_behavior["excluir_rotas"] = intent_spec.filtros.get("excluir_rotas", [])
                    if "excluir_segmentos" in intent_spec.filtros:
                        filtros_behavior["excluir_segmentos"] = intent_spec.filtros.get("excluir_segmentos", [])
                
                tabela_por_rota = get_clientes_sem_compra_por_rota(
                    session=session,
                    dias=dias,
                    data_referencia=data_referencia,
                    filtros_behavior=filtros_behavior if filtros_behavior else None
                )
                logger.info(f"[orquestrador_dw] Tabela por rota gerada: {len(tabela_por_rota)} vendedores")
        except Exception as e:
            logger.warning(f"[orquestrador_dw] Erro ao gerar tabela por rota: {e}")
            tabela_por_rota = None
    
    # PASSO 7: Envelopa resposta
    # Prepara detalhes_tecnicos com regras aplicadas
    detalhes_tecnicos = {
        "intent_spec": intent_spec.to_dict(),
        "filtros_aplicados": intent_spec.filtros.copy(),
        "regras_behavior_aplicadas": regras_behavior_aplicadas,  # Regras persistentes do BehaviorRule
        "regras_instrucoes_aplicadas": regras_aplicadas  # Regras de instruções comportamentais (legado)
    }
    
    resposta = {
        "status": status,
        "mensagem": mensagem,
        "intent": intent_spec.to_dict(),
        "periodo_analisado": {
            "inicio": intent_spec.periodo_inicio,
            "fim": intent_spec.periodo_fim
        },
        "dados": dados_normalizados,
        "tabela_por_rota": tabela_por_rota,  # Tabela agregada por rota (apenas para clientes_sem_compra)
        "regras_aplicadas": regras_aplicadas,  # Mantido para compatibilidade
        "analise_causas": analise_causas,  # Análise de causas quando meta não batida (legado)
        "causas_detector": causas_detector,  # Causas detectadas pelo novo módulo
        "detalhes_tecnicos": detalhes_tecnicos  # Detalhes técnicos incluindo regras behavior
    }
    
    logger.info(
        f"[orquestrador_dw] Resposta gerada: "
        f"status={status}, "
        f"dados={len(dados_normalizados)} registros, "
        f"analise_causas={'sim' if analise_causas else 'nao'}"
    )
    
    return resposta

