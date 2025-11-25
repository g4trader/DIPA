"""
Handler refatorado que usa IntentSpec + camada DW.

Este módulo implementa o novo fluxo:
1. LLM gera IntentSpec
2. Executa consulta DW baseada no IntentSpec
3. LLM gera resposta executiva com dados brutos

ARQUITETURA:
- Usa SEMPRE camada DW (analytics_metas.py, query_executor.py)
- NUNCA queries diretas no SQLite
- BigQuery NÃO implementado (apenas roadmap)
"""

import logging
import time
import hashlib
import json
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from src.agent.intent_spec import IntentSpec
from src.agent.query_executor import executar_consulta_dw
from src.agent.orquestrador_dw import executar_intent_spec
from src.agent.rules import detectar_override_explicito
from src.agent.memoria_comportamental import (
    detectar_instrucoes_comportamentais,
    salvar_instrucao_comportamental,
    aplicar_instrucoes_comportamentais,
    gerar_contexto_instrucoes_para_llm
)
from src.agent.post_processor import processar_resposta
# Behavior Memory é aplicado no orquestrador, não precisa importar aqui
from src.llm_integration_intent import (
    gerar_intent_spec_via_llm,
    gerar_resposta_executiva_com_dados_dw
)

logger = logging.getLogger(__name__)

# ✅ PERFORMANCE: Cache em memória para respostas completas Q1
_q1_response_cache: Dict[str, Dict[str, Any]] = {}
_Q1_CACHE_TTL_SECONDS = 600  # 10 minutos


def _make_q1_cache_key(pergunta: str, papel: Optional[str] = None) -> str:
    """
    Cria chave de cache para Q1 baseada na pergunta normalizada.
    
    Para Q1, perguntas canônicas como "Quais clientes estão sem compra há mais de 60 dias?"
    devem gerar a mesma chave independente da formulação.
    """
    # Normaliza pergunta (lowercase, remove pontuação extra)
    pergunta_normalizada = pergunta.lower().strip()
    
    # Detecta padrões Q1 comuns
    q1_patterns = [
        "clientes.*sem.*compra.*60.*dias",
        "clientes.*sem.*compra.*mais.*60.*dias",
        "clientes.*ativos.*sem.*compra",
        "quais.*clientes.*sem.*compra"
    ]
    
    import re
    is_q1 = any(re.search(pattern, pergunta_normalizada) for pattern in q1_patterns)
    
    if is_q1:
        # Para Q1, usa chave fixa (pergunta canônica)
        cache_data = {
            "tipo": "q1_canonica",
            "papel": papel or "diretor"
        }
    else:
        # Para outras perguntas, usa hash da pergunta
        cache_data = {
            "pergunta": pergunta_normalizada,
            "papel": papel or "diretor"
        }
    
    key_str = json.dumps(cache_data, sort_keys=True)
    return hashlib.md5(key_str.encode()).hexdigest()


def _get_q1_cached_response(cache_key: str) -> Optional[Dict[str, Any]]:
    """Retorna resposta Q1 do cache se válida."""
    if cache_key not in _q1_response_cache:
        return None
    
    cache_entry = _q1_response_cache[cache_key]
    cache_age = time.time() - cache_entry["created_at"]
    
    if cache_age < _Q1_CACHE_TTL_SECONDS:
        logger.info(
            f"[PERF_Q1] Cache HIT: idade={cache_age:.1f}s, "
            f"tempo_salvo={cache_entry.get('tempo_total_ms', 0)}ms"
        )
        return cache_entry["response"]
    else:
        # Cache expirado
        del _q1_response_cache[cache_key]
        logger.debug(f"[PERF_Q1] Cache expirado: {cache_key}")
        return None


def _set_q1_cached_response(cache_key: str, response: Dict[str, Any], tempo_total_ms: int):
    """Armazena resposta Q1 no cache."""
    _q1_response_cache[cache_key] = {
        "response": response,
        "created_at": time.time(),
        "tempo_total_ms": tempo_total_ms
    }
    logger.info(f"[PERF_Q1] Resposta cacheada: tempo={tempo_total_ms}ms")


def processar_pergunta_com_dw(
    pergunta: str,
    session: Session,
    papel: Optional[str] = None
) -> Dict[str, Any]:
    """
    Processa pergunta usando o novo fluxo: IntentSpec → DW → Resposta executiva.
    
    Fluxo:
    1. LLM gera IntentSpec a partir da pergunta
    2. Executa consulta DW baseada no IntentSpec
    3. LLM gera resposta executiva com dados brutos do DW
    
    Args:
        pergunta: Pergunta do usuário em linguagem natural
        session: Sessão SQLAlchemy
        papel: Papel do usuário (diretor, supervisor, vendedor)
        
    Returns:
        dict com estrutura:
        {
            "resumo_executivo": str,
            "periodo_analisado": {"inicio": "YYYY-MM-DD", "fim": "YYYY-MM-DD"},
            "tabela_principal": List[Dict],
            "insights": List[str],
            "intent_spec": IntentSpec,
            "dados_dw": Dict,
            "tem_dados": bool
        }
    """
    logger.info(f"[processar_pergunta_com_dw] Processando pergunta: {pergunta[:100]}...")
    
    # ✅ PERFORMANCE: Verifica cache para Q1 antes de processar
    cache_key = _make_q1_cache_key(pergunta, papel)
    cached_response = _get_q1_cached_response(cache_key)
    if cached_response:
        # Adiciona flag de cache hit
        cached_response["contexto"] = cached_response.get("contexto", {})
        cached_response["contexto"]["q1_cached"] = True
        cached_response["contexto"]["q1_cache_age_seconds"] = int(
            time.time() - _q1_response_cache[cache_key]["created_at"]
        )
        logger.info(
            f"[PERF_Q1] ✅ Retornando resposta do cache (idade: "
            f"{cached_response['contexto']['q1_cache_age_seconds']}s)"
        )
        return cached_response
    
    # ✅ PERFORMANCE: Inicia medição de tempo total
    start_time_total = time.perf_counter()
    perf_metrics = {
        "intent_spec_ms": 0,
        "dw_query_ms": 0,
        "post_processor_ms": 0,
        "llm_resposta_ms": 0,
        "total_ms": 0
    }
    
    # PASSO 1: LLM gera IntentSpec
    logger.info(f"[PERF_STEP] START_GROQ_INTENT - gerar_intent_spec_via_llm")
    try:
        start_intent = time.perf_counter()
        intent_spec = gerar_intent_spec_via_llm(pergunta, papel=papel)
        perf_metrics["intent_spec_ms"] = int((time.perf_counter() - start_intent) * 1000)
        logger.info(f"[PERF_STEP] END_GROQ_INTENT - {perf_metrics['intent_spec_ms']:.2f}ms")
        logger.info(
            f"[processar_pergunta_com_dw] IntentSpec gerado: "
            f"tipo={intent_spec.tipo}, "
            f"periodo={intent_spec.periodo_inicio} a {intent_spec.periodo_fim}, "
            f"tempo={perf_metrics['intent_spec_ms']}ms"
        )
    except Exception as e:
        logger.error(f"[processar_pergunta_com_dw] Erro ao gerar IntentSpec: {e}")
        return {
            "resumo_executivo": "Não foi possível entender sua pergunta. Por favor, reformule de forma mais específica.",
            "periodo_analisado": {"inicio": None, "fim": None},
            "tabela_principal": [],
            "insights": ["Reformule sua pergunta de forma mais específica."],
            "intent_spec": None,
            "dados_dw": {},
            "tem_dados": False,
            "erro": str(e)
        }
    
    # PASSO 1.5: Detecta instruções comportamentais na pergunta
    instrucoes_detectadas = detectar_instrucoes_comportamentais(pergunta)
    
    # PASSO 1.6: Detecta override explícito na pergunta
    override_regras = detectar_override_explicito(pergunta)
    contexto_usuario = {
        "role": papel or "diretor",
        "override_regras": override_regras
    }
    
    # PASSO 1.7: Salva instruções comportamentais detectadas na memória permanente
    if instrucoes_detectadas and not override_regras:
        for instrucao in instrucoes_detectadas:
            try:
                salvar_instrucao_comportamental(
                    session=session,
                    instrucao=instrucao,
                    intent_spec=intent_spec,
                    owner_role=papel or "diretor"
                )
                logger.info(
                    f"[processar_pergunta_com_dw] Instrução comportamental salva: "
                    f"{instrucao['tipo']} - {instrucao['entidade']}"
                )
            except Exception as e:
                logger.error(
                    f"[processar_pergunta_com_dw] Erro ao salvar instrução comportamental: {e}"
                )
    
    # PASSO 2: Executa consulta DW via orquestrador (que aplica regras automaticamente)
    # Inicializa variáveis para garantir que existam mesmo em caso de erro
    detalhes_tecnicos_orquestrador = {}
    regras_behavior_aplicadas = []
    regras_aplicadas = {}
    analise_causas = {}
    causas_detector = {}
    
    try:
        # ✅ PERFORMANCE: Mede tempo de execução DW
        start_dw = time.perf_counter()
        resultado_orquestrador = executar_intent_spec(
            session=session,
            intent_spec=intent_spec,
            contexto_usuario=contexto_usuario
        )
        perf_metrics["dw_query_ms"] = int((time.perf_counter() - start_dw) * 1000)
        
        # Extrai dados, regras aplicadas, análise de causas e causas_detector
        dados_orquestrador = resultado_orquestrador.get("dados", [])
        
        # ✅ PERFORMANCE: Log específico para Q1
        if intent_spec.tipo == "clientes_sem_compra":
            logger.info(
                f"[PERF_Q1] DW executado: {perf_metrics['dw_query_ms']}ms, "
                f"registros={len(dados_orquestrador)}"
            )
        
        # ✅ LOG CRÍTICO: Para Q1, loga quantidade de dados do orquestrador
        if intent_spec.tipo == "clientes_sem_compra":
            logger.info(
                f"[Q1_ORQ] Payload final enviado ao LLM - registros: {len(dados_orquestrador)}"
            )
            # Validação: garante que não há duplicatas
            if isinstance(dados_orquestrador, list):
                cliente_ids = [r.get("cliente_id") for r in dados_orquestrador if isinstance(r, dict)]
                clientes_unicos = len(set(cliente_ids))
                if len(cliente_ids) != clientes_unicos:
                    logger.error(
                        f"[Q1_ORQ] ❌ ERRO: Payload tem {len(cliente_ids)} registros mas "
                        f"apenas {clientes_unicos} clientes únicos!"
                    )
                else:
                    logger.info(
                        f"[Q1_ORQ] ✅ Payload: {clientes_unicos} clientes únicos"
                    )
        
        dados_dw = {
            "status": resultado_orquestrador.get("status"),
            "dados": dados_orquestrador,
            "tem_dados": resultado_orquestrador.get("status") == "ok" and len(dados_orquestrador) > 0,
            "analise_causas": resultado_orquestrador.get("analise_causas", {}),
            "causas_detector": resultado_orquestrador.get("causas_detector", {}),
            "tabela_por_rota": resultado_orquestrador.get("tabela_por_rota"),  # Tabela agregada por rota (Q1)
            "meta_total": resultado_orquestrador.get("dados", [{}])[0].get("meta_total", 0) if resultado_orquestrador.get("dados") else 0,
            "realizado_total": resultado_orquestrador.get("dados", [{}])[0].get("realizado_total", 0) if resultado_orquestrador.get("dados") else 0,
            "gap_total": resultado_orquestrador.get("dados", [{}])[0].get("gap_total", 0) if resultado_orquestrador.get("dados") else 0,
            "atingimento_medio": resultado_orquestrador.get("dados", [{}])[0].get("atingimento_medio", 0) if resultado_orquestrador.get("dados") else 0
        }
        regras_aplicadas = resultado_orquestrador.get("regras_aplicadas", {})
        analise_causas = resultado_orquestrador.get("analise_causas", {})
        causas_detector = resultado_orquestrador.get("causas_detector", {})
        # Extrai detalhes_tecnicos do orquestrador (inclui regras_behavior_aplicadas)
        detalhes_tecnicos_orquestrador = resultado_orquestrador.get("detalhes_tecnicos", {})
        regras_behavior_aplicadas = detalhes_tecnicos_orquestrador.get("regras_behavior_aplicadas", [])
        tem_dados = dados_dw.get("tem_dados", False)
        
        logger.info(
            f"[processar_pergunta_com_dw] Consulta DW executada: "
            f"tem_dados={tem_dados}, "
            f"tipo={intent_spec.tipo}"
        )
        
        # Se não houver dados, retorna resposta direta
        if not tem_dados:
            periodo_inicio = intent_spec.periodo_inicio or "N/A"
            periodo_fim = intent_spec.periodo_fim or periodo_inicio
            
            return {
                "resumo_executivo": (
                    f"Não encontrei dados no data warehouse DIPAM para o período/filtro solicitado. "
                    f"Período solicitado: {periodo_inicio} a {periodo_fim}. "
                    f"Verifique se os dados foram carregados para este período."
                ),
                "periodo_analisado": {
                    "inicio": periodo_inicio + "-01" if periodo_inicio != "N/A" else None,
                    "fim": periodo_fim + "-01" if periodo_fim != "N/A" else None
                },
                "tabela_principal": [],
                "insights": [
                    "Verifique se os dados foram carregados no data warehouse DIPAM para o período solicitado.",
                    "Tente reformular a pergunta com um período diferente ou filtros mais amplos."
                ],
                "intent_spec": intent_spec,
                "dados_dw": dados_dw,
                "tem_dados": False
            }
        
    except Exception as e:
        logger.error(f"[processar_pergunta_com_dw] Erro ao executar consulta DW: {e}")
        return {
            "resumo_executivo": "Ocorreu um erro ao consultar o data warehouse DIPAM. Por favor, tente novamente.",
            "periodo_analisado": {"inicio": None, "fim": None},
            "tabela_principal": [],
            "insights": ["Tente novamente ou reformule sua pergunta."],
            "intent_spec": intent_spec,
            "dados_dw": {},
            "tem_dados": False,
            "erro": str(e)
        }
    
    # PASSO 3: Pós-processador estrutura resposta
    try:
        # Behavior Memory já foi aplicado no orquestrador, usa regras que vieram de lá
        # Não precisa chamar aplicar_regras_ao_intent novamente aqui
        
        # ✅ PERFORMANCE: Mede tempo de pós-processamento
        start_post = time.perf_counter()
        # Processa resposta usando post_processor
        resposta_estruturada = processar_resposta(
            intent_spec=intent_spec.to_dict() if hasattr(intent_spec, 'to_dict') else intent_spec,
            dados_dw=dados_dw,
            causas_detector=causas_detector,
            behavior_rules_aplicadas=regras_behavior_aplicadas  # Usa regras do orquestrador
        )
        perf_metrics["post_processor_ms"] = int((time.perf_counter() - start_post) * 1000)
        
        # LOG: Verifica texto do post_processor
        texto_post_processor = resposta_estruturada.get("texto", "")
        logger.info(f"[processar_pergunta_com_dw] Texto do post_processor: {len(texto_post_processor)} chars")
        if texto_post_processor:
            logger.debug(f"[processar_pergunta_com_dw] Primeiras 200 chars: {texto_post_processor[:200]}")
        
        # PASSO 4: LLM gera resposta executiva com dados estruturados
        # ✅ PERFORMANCE: Mede tempo de LLM
        logger.info(f"[PERF_STEP] START_GROQ_EXECUTIVE - gerar_resposta_executiva_com_dados_dw")
        start_llm = time.perf_counter()
        try:
            resposta_executiva = gerar_resposta_executiva_com_dados_dw(
                pergunta=pergunta,
                intent_spec=intent_spec,
                dados_dw=dados_dw,
                papel=papel,
                regras_aplicadas=regras_aplicadas,
                analise_causas=analise_causas,
                resposta_estruturada=resposta_estruturada  # Passa resposta estruturada para LLM
            )
            perf_metrics["llm_resposta_ms"] = int((time.perf_counter() - start_llm) * 1000)
            logger.info(f"[PERF_STEP] END_GROQ_EXECUTIVE - {perf_metrics['llm_resposta_ms']:.2f}ms")
        except Exception as e:
            perf_metrics["llm_resposta_ms"] = int((time.perf_counter() - start_llm) * 1000)
            logger.error(f"[PERF_STEP] END_GROQ_EXECUTIVE - ERROR após {perf_metrics['llm_resposta_ms']:.2f}ms: {e}")
            raise
        
        # ✅ PERFORMANCE: Log específico para Q1
        if intent_spec.tipo == "clientes_sem_compra":
            logger.info(
                f"[PERF_Q1] LLM executado: {perf_metrics['llm_resposta_ms']}ms"
            )
        
        # CRÍTICO: Preserva o texto completo do post_processor no resposta_executiva
        # O LLM pode ter gerado um resumo_executivo diferente, mas o texto completo deve vir do post_processor
        if texto_post_processor:
            resposta_executiva["texto_completo_post_processor"] = texto_post_processor
            logger.info(f"[processar_pergunta_com_dw] Texto completo preservado: {len(texto_post_processor)} chars")
        
        # ✅ PERFORMANCE: Log antes de montar resposta final
        logger.info(f"[PERF_STEP] START_ASSEMBLY - montagem resposta final")
        assembly_start = time.perf_counter()
        
        # Para Q1 (clientes_sem_compra), monta tabela_principal com estrutura correta
        if intent_spec.tipo == "clientes_sem_compra" and dados_dw.get("dados"):
            dados_clientes = dados_dw.get("dados", [])
            if dados_clientes and isinstance(dados_clientes, list) and len(dados_clientes) > 0:
                # Monta tabela_principal com colunas: Cliente ID, Nome, Dias sem Compra, Vendedor, Supervisor
                resposta_executiva["tabela_principal"] = [{
                    "colunas": ["Cliente ID", "Nome", "Dias sem Compra", "Vendedor", "Supervisor"],
                    "linhas": [
                        [
                            cliente.get("cliente_id", ""),
                            cliente.get("nome", ""),
                            cliente.get("dias_sem_compra", 0) or 0,
                            cliente.get("vendedor_nome", cliente.get("vendedor_codigo", cliente.get("rota_id", ""))),
                            cliente.get("supervisor_nome", cliente.get("supervisor_codigo", ""))
                        ]
                        for cliente in dados_clientes
                    ]
                }]
                logger.info(f"[processar_pergunta_com_dw] Tabela principal montada para Q1: {len(dados_clientes)} clientes")
    
    except Exception as e:
        logger.error(f"[processar_pergunta_com_dw] Erro ao processar resposta: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # Fallback: retorna resposta básica sem pós-processamento
        resposta_executiva = {
            "resumo_executivo": f"Resposta gerada, mas houve erro no pós-processamento: {str(e)}",
            "periodo_analisado": {
                "inicio": intent_spec.periodo_inicio,
                "fim": intent_spec.periodo_fim
            },
            "tabela_principal": dados_dw.get("dados", []),
            "insights": ["Erro no processamento avançado da resposta."],
            "intent_spec": intent_spec,
            "dados_dw": dados_dw,
            "tem_dados": dados_dw.get("tem_dados", False),
            "erro": str(e)
        }
    
    # Adiciona metadados e detalhes técnicos
    resposta_executiva["intent_spec"] = intent_spec
    resposta_executiva["dados_dw"] = dados_dw
    resposta_executiva["tem_dados"] = True
    
    # Adiciona resposta estruturada do pós-processador
    if 'resposta_estruturada' in locals():
        resposta_executiva["resposta_estruturada"] = resposta_estruturada
    
    # Adiciona detalhes técnicos para o template
    # Reutiliza detalhes_tecnicos do orquestrador (já inclui regras_behavior_aplicadas)
    if detalhes_tecnicos_orquestrador:
        resposta_executiva["detalhes_tecnicos"] = detalhes_tecnicos_orquestrador
    else:
        # Fallback se orquestrador não retornou detalhes_tecnicos
        resposta_executiva["detalhes_tecnicos"] = {
            "intent_spec": intent_spec.to_dict() if hasattr(intent_spec, 'to_dict') else str(intent_spec),
            "filtros_aplicados": intent_spec.filtros if hasattr(intent_spec, 'filtros') else {},
            "regras_behavior_aplicadas": regras_behavior_aplicadas,
            "regras_instrucoes_aplicadas": regras_aplicadas,
            "query_executada": f"DW Query para tipo={intent_spec.tipo}, dimensao={intent_spec.dimensao_principal}"
        }
    
        # ✅ PERFORMANCE: Log após montagem da resposta
        assembly_duration = (time.perf_counter() - assembly_start) * 1000
        logger.info(f"[PERF_STEP] END_ASSEMBLY - {assembly_duration:.2f}ms")
    
    # ✅ PERFORMANCE: Calcula tempo total e adiciona métricas à resposta
    perf_metrics["total_ms"] = int((time.perf_counter() - start_time_total) * 1000)
    
    logger.info(
        f"[processar_pergunta_com_dw] Resposta executiva gerada: "
        f"resumo={len(resposta_executiva.get('resumo_executivo', ''))} chars, "
        f"tempo_total={perf_metrics['total_ms']}ms"
    )
    
    # ✅ PERFORMANCE: Log detalhado de métricas (especialmente para Q1)
    if intent_spec.tipo == "clientes_sem_compra":
        logger.info(
            f"[PERF_Q1] Métricas completas: "
            f"intent_spec={perf_metrics['intent_spec_ms']}ms, "
            f"dw={perf_metrics['dw_query_ms']}ms, "
            f"post_processor={perf_metrics['post_processor_ms']}ms, "
            f"llm={perf_metrics['llm_resposta_ms']}ms, "
            f"total={perf_metrics['total_ms']}ms"
        )
    
    # Adiciona métricas de performance ao contexto da resposta
    if "contexto" not in resposta_executiva:
        resposta_executiva["contexto"] = {}
    resposta_executiva["contexto"]["performance_metrics"] = perf_metrics
    
    # ✅ PERFORMANCE: Cacheia resposta Q1 completa
    if intent_spec.tipo == "clientes_sem_compra":
        _set_q1_cached_response(cache_key, resposta_executiva, perf_metrics["total_ms"])
        resposta_executiva["contexto"]["q1_cached"] = False  # Esta resposta foi calculada, não veio do cache
    
    # LOG CRÍTICO: Verifica se texto_completo_post_processor está presente
    texto_completo = resposta_executiva.get("texto_completo_post_processor", "")
    if texto_completo:
        logger.info(f"[processar_pergunta_com_dw] ✅ Texto completo disponível: {len(texto_completo)} chars")
        logger.debug(f"[processar_pergunta_com_dw] ### TEXTO_FINAL ###\n{texto_completo[:500]}")
    else:
        logger.warning(f"[processar_pergunta_com_dw] ⚠️  Texto completo NÃO disponível no resposta_executiva")
    
    return resposta_executiva

