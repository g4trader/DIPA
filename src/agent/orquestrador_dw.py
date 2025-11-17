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

# Importa diretamente do módulo analytics_metas sem passar por __init__.py
# Isso evita importar etl.py que requer pandas
import importlib
analytics_metas = importlib.import_module("src.dw.analytics_metas")

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
        "vendas_por_mes", "outros"
    ]
    if intent_spec.tipo not in tipos_validos:
        return False, f"Tipo '{intent_spec.tipo}' não é suportado. Tipos válidos: {tipos_validos}"
    
    # Valida dimensão principal
    dimensoes_validas = [
        "mes", "vendedor", "supervisor", "rota",
        "cliente", "marca", "categoria", "sku", "nenhuma"
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
    }
    
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
    intent_spec: IntentSpec
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
        
    Returns:
        dict com estrutura:
        {
            "status": "ok" | "sem_dados" | "erro_validacao" | "erro_interno",
            "mensagem": "texto curto explicando o status",
            "intent": { ... IntentSpec ... },
            "periodo_analisado": {"inicio": "...", "fim": "..."},
            "dados": [ ... linhas retornadas pelo DW ... ]
        }
    """
    logger.info(
        f"[orquestrador_dw] Executando IntentSpec: "
        f"tipo={intent_spec.tipo}, "
        f"dimensao={intent_spec.dimensao_principal}, "
        f"periodo={intent_spec.periodo_inicio} a {intent_spec.periodo_fim}"
    )
    
    # PASSO 1: Aplica período padrão se necessário
    intent_spec = _aplicar_periodo_padrao(intent_spec)
    
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
            resultado = funcao_dw(session, **kwargs)
        
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
    dados_normalizados = _normalizar_resultado_dw(resultado)
    
    # Se resultado for dict com estrutura especial (ex.: kpis_mes), extrai dados
    if isinstance(resultado, dict):
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
    
    # PASSO 6: Determina status
    if len(dados_normalizados) == 0:
        status = "sem_dados"
        mensagem = f"Não há dados no data warehouse DIPAM para o período/filtro solicitado. Período: {intent_spec.periodo_inicio} a {intent_spec.periodo_fim}."
    else:
        status = "ok"
        mensagem = f"Dados consultados com sucesso. {len(dados_normalizados)} registro(s) encontrado(s)."
    
    # PASSO 7: Envelopa resposta
    resposta = {
        "status": status,
        "mensagem": mensagem,
        "intent": intent_spec.to_dict(),
        "periodo_analisado": {
            "inicio": intent_spec.periodo_inicio,
            "fim": intent_spec.periodo_fim
        },
        "dados": dados_normalizados
    }
    
    logger.info(
        f"[orquestrador_dw] Resposta gerada: "
        f"status={status}, "
        f"dados={len(dados_normalizados)} registros"
    )
    
    return resposta

