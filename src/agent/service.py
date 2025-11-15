"""
Serviço do Agente de IA Comercial.

Este módulo contém a lógica principal do agente, orquestrando
detecção de intenções, queries de dados, modelos de ML e LLM.
"""

import logging
import re
import time
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.agent.intent import detect_intent, IntentType
from src.agent.utils.date_extraction import extrair_mes_ano_explicito
from src.agent.queries import (
    query_vendedor_meta,
    query_clientes_churn,
    query_vendas_analise,
    query_supervisor_meta,
    query_metas_departamento_agregadas,
    query_vendedores_que_bateram_meta,
    query_meses_disponiveis_metas,
    query_metas_vendedor_multiplos_meses,
    query_meta_realizado_por_mes,
    query_meta_realizado_por_vendedor,
    query_vendedores_pior_performance,
    query_piores_vendedores_por_meta,
    query_vendedores_menor_venda,
    analisar_meta_mensal
)
from src.models_ml import MetaModel, ChurnModel
from src.dw.connection import get_db_session
from src.dw.models import MetaVendedor, Venda
from src.llm_integration import call_llm, gerar_resposta_llm, gerar_resposta_consulta_meta
from src.llm.formatter import format_analise_produtos
from src.ml.forecasting import get_monthly_revenue_series, forecast_month_revenue
from src.analysis.produtos import get_produtos_menos_vendidos, get_top_produtos_para_recuperar
from src.analysis.clientes import clientes_positivados_sem_compra_produto
from src.agent.memory import buscar_interacoes_parecidas
from src.agent.skills import buscar_skill_por_intent, executar_skill
from src.agent.interaction_logger import registrar_interacao
from src.config.produtos_foco import obter_codigos_por_nome, obter_termos_por_nome
from datetime import datetime

logger = logging.getLogger(__name__)

# ============================================================================
# FLAG DE DEBUG: Memória baseada em embeddings
# ============================================================================
# Toggle temporário para desabilitar a memória de embeddings durante debug.
# Quando False, pula a busca de interações similares, retornando lista vazia.
# Isso ajuda a identificar se a funcionalidade de memória está causando
# travamentos ou lentidão no processamento de perguntas.
USE_MEMORY = False
# ============================================================================


def periodo_tem_dados(session: Session, mes_ano: str) -> bool:
    """
    Verifica se existe dados de metas e/ou vendas para um determinado período.
    
    Args:
        session: Sessão SQLAlchemy
        mes_ano: Mês/ano no formato YYYY-MM (ex.: "2025-08")
        
    Returns:
        bool: True se houver dados de metas OU vendas para o período, False caso contrário
    """
    if not mes_ano:
        return False
    
    # Verifica se há dados em metas_vendedor
    try:
        tem_metas = (
            session.query(func.count(MetaVendedor.id))
            .filter(MetaVendedor.mes_ano == mes_ano)
            .scalar()
            > 0
        )
    except Exception as e:
        logger.warning(f"Erro ao verificar metas_vendedor para {mes_ano}: {str(e)}")
        tem_metas = False
    
    # Verifica se há dados em vendas
    # Extrai ano e mês para filtrar vendas
    ano, mes = mes_ano.split("-")
    tem_vendas = False
    
    # Detecta tipo de banco para usar a função correta
    from src.config import config
    db_type = config.database.db_type
    
    try:
        if db_type == "sqlite":
            # SQLite usa strftime
            tem_vendas = (
                session.query(func.count(Venda.id))
                .filter(
                    func.strftime("%Y", Venda.data_venda) == ano,
                    func.strftime("%m", Venda.data_venda) == mes.zfill(2),  # Garante formato 08
                )
                .scalar()
                > 0
            )
        else:
            # PostgreSQL/MySQL usa extract
            from sqlalchemy import extract as sql_extract
            tem_vendas = (
                session.query(func.count(Venda.id))
                .filter(
                    sql_extract('year', Venda.data_venda) == int(ano),
                    sql_extract('month', Venda.data_venda) == int(mes)
                )
                .scalar()
                > 0
            )
    except Exception as e:
        # Fallback: tenta ambos os métodos
        logger.warning(f"Erro ao verificar vendas para {mes_ano} (método principal): {str(e)}")
        try:
            # Tenta SQLite strftime como fallback
            tem_vendas = (
                session.query(func.count(Venda.id))
                .filter(
                    func.strftime("%Y", Venda.data_venda) == ano,
                    func.strftime("%m", Venda.data_venda) == mes.zfill(2),
                )
                .scalar()
                > 0
            )
        except Exception as e2:
            logger.warning(f"Erro ao verificar vendas para {mes_ano} (fallback): {str(e2)}")
            tem_vendas = False
    
    resultado = tem_metas or tem_vendas
    logger.debug(f"periodo_tem_dados({mes_ano}): metas={tem_metas}, vendas={tem_vendas}, resultado={resultado}")
    return resultado


class AgentService:
    """
    Serviço do agente de IA comercial.
    
    Orquestra todo o pipeline de processamento de perguntas:
    detecção de intenção -> queries -> ML -> LLM -> resposta
    """
    
    def __init__(self):
        """Inicializa o serviço do agente."""
        self.meta_model = None
        self.churn_model = None
        self._load_models()
    
    def _load_models(self):
        """Carrega modelos de ML treinados."""
        try:
            from pathlib import Path
            from src.config import config
            
            artifacts_dir = Path(config.ml.models_dir) / "artefacts"
            
            # Tenta carregar modelo de meta
            try:
                meta_model_path = artifacts_dir / "meta_model_latest.joblib"
                if meta_model_path.exists():
                    self.meta_model = MetaModel(model_type='gradient_boosting')
                    self.meta_model.load(str(meta_model_path))
                    logger.info("Modelo de meta carregado com sucesso")
                else:
                    logger.warning(f"Modelo de meta não encontrado em: {meta_model_path}")
            except Exception as e:
                logger.warning(f"Erro ao carregar modelo de meta: {str(e)}")
            
            # Tenta carregar modelo de churn
            try:
                churn_model_path = artifacts_dir / "churn_model_latest.joblib"
                if churn_model_path.exists():
                    self.churn_model = ChurnModel(model_type='gradient_boosting')
                    self.churn_model.load(str(churn_model_path))
                    logger.info("Modelo de churn carregado com sucesso")
                else:
                    logger.warning(f"Modelo de churn não encontrado em: {churn_model_path}")
            except Exception as e:
                logger.warning(f"Erro ao carregar modelo de churn: {str(e)}")
        
        except Exception as e:
            logger.error(f"Erro ao carregar modelos: {str(e)}")
    
    def process_question(
        self,
        pergunta: str,
        usuario_id: Optional[str] = None,
        papel: Optional[str] = None,
        session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Processa uma pergunta do usuário e retorna resposta do agente.
        
        Pipeline:
        1. Detecta intenção
        2. Executa queries relevantes
        3. Usa modelos de ML quando apropriado
        4. Gera resposta com LLM
        
        Args:
            pergunta: Pergunta do usuário em linguagem natural
            usuario_id: ID do usuário (opcional)
            papel: Papel do usuário ('diretor', 'supervisor', 'vendedor') (opcional)
            session: Sessão SQLAlchemy (None = cria nova)
            
        Returns:
            dict: Resposta do agente
            {
                "resposta": str,
                "intent": str,
                "contexto": dict,
                "confianca": float,
            }
        """
        t_start = time.perf_counter()
        logger.info(f"[process_question: início] Pergunta: {pergunta[:100]}...")
        
        # Usa sessão existente ou cria nova
        if session is None:
            session_context = get_db_session()
            session = next(session_context)
            close_session = True
        else:
            close_session = False
        
        try:
            # 0. Busca interações parecidas na memória (antes de processar)
            # DEBUG: Pode ser desabilitada via flag USE_MEMORY para debug
            t_memoria_start = time.perf_counter()
            logger.info(f"[process_question: antes de buscar memória] USE_MEMORY={USE_MEMORY}, Pergunta: {pergunta[:100]}...")
            
            if USE_MEMORY:
                interacoes_parecidas = buscar_interacoes_parecidas(session, pergunta, limite=5, threshold=0.7)
                t_memoria_end = time.perf_counter()
                logger.info(
                    f"[process_question: depois de buscar memória] "
                    f"Tempo: {t_memoria_end - t_memoria_start:.3f}s, "
                    f"Interações encontradas: {len(interacoes_parecidas)}, "
                    f"Pergunta: {pergunta[:100]}..."
                )
            else:
                # Memória desativada para debug - retorna lista vazia
                interacoes_parecidas = []
                t_memoria_end = time.perf_counter()
                logger.info(
                    f"[process_question: memória DESATIVADA (debug)] "
                    f"Tempo: {t_memoria_end - t_memoria_start:.3f}s, "
                    f"USE_MEMORY=False, "
                    f"Pergunta: {pergunta[:100]}..."
                )
            
            # Se houver interação muito similar (> 0.95), reutiliza resposta
            UMBRAL_REAPROVEITAR = 0.95
            if interacoes_parecidas and interacoes_parecidas[0]["similaridade"] > UMBRAL_REAPROVEITAR:
                resposta_anterior = interacoes_parecidas[0]
                logger.info(
                    f"[process_question: resposta reaproveitada] "
                    f"ID: {resposta_anterior['interacao_id']}, "
                    f"similaridade: {resposta_anterior['similaridade']:.3f}"
                )
                return {
                    "resposta": resposta_anterior["resposta"],
                    "intent": resposta_anterior["intent"],
                    "contexto": {
                        "resposta_reaproveitada": True,
                        "interacao_original_id": resposta_anterior["interacao_id"],
                        "similaridade": resposta_anterior["similaridade"],
                        "intent_original": resposta_anterior["intent"],
                        "confianca_original": resposta_anterior["confianca"]
                    },
                    "confianca": resposta_anterior["confianca"],
                }
            
            # 1. Detecta intenção
            t_intent_start = time.perf_counter()
            logger.info(f"[process_question: antes de detectar intent] Pergunta: {pergunta[:100]}...")
            intent_result = detect_intent(pergunta)
            intent = intent_result["intent"]
            entities = intent_result["entities"]
            t_intent_end = time.perf_counter()
            logger.info(
                f"[process_question: depois de detectar intent] "
                f"Tempo: {t_intent_end - t_intent_start:.3f}s, "
                f"Intent: {intent.value}, "
                f"Entities: {list(entities.keys())}, "
                f"Pergunta: {pergunta[:100]}..."
            )
            
            # Adiciona pergunta original às entities para uso nos handlers
            entities["pergunta_original"] = pergunta
            
            # 1.5. Verifica se existe skill ativa para essa intent
            skill = buscar_skill_por_intent(session, intent.value)
            sql_executado = None
            
            # Prepara contexto de memória (interações aprovadas com alta similaridade)
            UMBRAL_MEMORIA = 0.85
            interacoes_aprovadas = [
                i for i in interacoes_parecidas
                if i.get("sucesso") is True and i["similaridade"] >= UMBRAL_MEMORIA
            ]
            
            contexto_memoria = None
            if interacoes_aprovadas:
                contexto_memoria = {
                    "interacoes_aprovadas": [
                        {
                            "pergunta": i["pergunta"],
                            "resposta": i["resposta"],
                            "similaridade": i["similaridade"],
                            "intent": i["intent"]
                        }
                        for i in interacoes_aprovadas[:3]  # Top 3 aprovadas
                    ]
                }
                logger.info(
                    f"[process_question: contexto memória preparado] "
                    f"Interações aprovadas: {len(interacoes_aprovadas)} "
                    f"(similaridade >= {UMBRAL_MEMORIA})"
                )
            
            # 2. Executa queries e monta contexto
            # Se existir skill ativa, usa ela primeiro
            if skill:
                logger.info(f"[process_question: usando skill] {skill.nome} para intent {intent.value}")
                t_skill_start = time.perf_counter()
                
                try:
                    # Executa skill
                    resultado_skill = executar_skill(session, skill, entities)
                    
                    if resultado_skill:
                        # Monta contexto baseado no resultado da skill
                        contexto = {
                            "intent": intent.value,
                            "entities": entities,
                            "skill_usada": skill.nome,
                            "tipo": resultado_skill.get("tipo"),
                            "dados": resultado_skill.get("dados", []),
                            "total": resultado_skill.get("total", 0),
                            "tem_dados_suficientes": resultado_skill.get("total", 0) > 0
                        }
                        
                        # SQL executado é o template preenchido (salvo na skill)
                        sql_executado = skill.sql_template
                        
                        # Gera resposta usando LLM
                        t_llm_start = time.perf_counter()
                        resposta = self._generate_response(intent, contexto, pergunta, contexto_memoria)
                        t_llm_end = time.perf_counter()
                        logger.info(
                            f"[process_question: depois de chamar LLM para skill] "
                            f"Tempo: {t_llm_end - t_llm_start:.3f}s"
                        )
                        
                        # Calcula confiança
                        confianca = 0.9 if contexto.get("tem_dados_suficientes") else 0.6
                        
                        t_skill_end = time.perf_counter()
                        logger.info(
                            f"[process_question: skill executada] "
                            f"Tempo: {t_skill_end - t_skill_start:.3f}s, "
                            f"Total dados: {resultado_skill.get('total', 0)}"
                        )
                    else:
                        # Erro ao executar skill - cai no fluxo normal
                        logger.warning(f"Erro ao executar skill {skill.nome}, usando fluxo normal")
                        skill = None  # Força usar fluxo normal
                except Exception as e:
                    logger.error(f"Erro ao executar skill {skill.nome}: {str(e)}, usando fluxo normal")
                    skill = None  # Força usar fluxo normal
            
            # Se não usou skill (ou skill falhou), usa fluxo normal
            if not skill or "resposta" not in locals():
                # Se for consulta de meta, usa handler específico
                t_handler_start = time.perf_counter()
                logger.info(
                    f"[process_question: antes de executar handler da intent] "
                    f"Intent: {intent.value}, "
                    f"Pergunta: {pergunta[:100]}..."
                )
                
                if intent == IntentType.CONSULTA_META:
                    contexto = self._handle_meta_query(intent, entities, session, contexto_memoria)
                    
                    # Adiciona contexto de memória se houver interações aprovadas
                    if contexto_memoria:
                        contexto["memoria_interacoes_aprovadas"] = contexto_memoria
                    
                    # A resposta já está formatada no contexto
                    resposta = contexto.get("resposta", "Desculpe, ocorreu um erro ao processar sua pergunta.")
                    confianca = contexto.get("confianca", 0.5)
                elif intent == IntentType.CONSULTA_VENDEDORES_PERFORMANCE:
                    contexto = self._handle_vendedores_performance(intent, entities, session, contexto_memoria)
                    
                    # Adiciona contexto de memória se houver interações aprovadas
                    if contexto_memoria:
                        contexto["memoria_interacoes_aprovadas"] = contexto_memoria
                    
                    # A resposta já está formatada no contexto
                    resposta = contexto.get("resposta", "Desculpe, ocorreu um erro ao processar sua pergunta.")
                    confianca = contexto.get("confianca", 0.5)
                else:
                    contexto = self._build_context(intent, entities, session)
                    
                    # 3. Usa modelos de ML quando apropriado
                    contexto = self._enrich_with_ml(intent, contexto, entities, session)
                    
                    # Adiciona contexto de memória se houver interações aprovadas
                    if contexto_memoria:
                        contexto["memoria_interacoes_aprovadas"] = contexto_memoria
                    
                    # 4. Gera resposta
                    t_llm_start = time.perf_counter()
                    logger.info(
                        f"[process_question: antes de chamar LLM] "
                        f"Intent: {intent.value}, "
                        f"Pergunta: {pergunta[:100]}..."
                    )
                    resposta = self._generate_response(intent, contexto, pergunta, contexto_memoria)
                    t_llm_end = time.perf_counter()
                    logger.info(
                        f"[process_question: depois de chamar LLM] "
                        f"Tempo: {t_llm_end - t_llm_start:.3f}s, "
                        f"Tamanho resposta: {len(resposta)} caracteres, "
                        f"Pergunta: {pergunta[:100]}..."
                    )
                    
                    # 5. Calcula confiança
                    confianca = self._calculate_confidence(intent, entities, contexto)
            
            t_handler_end = time.perf_counter()
            logger.info(
                f"[process_question: depois de executar handler da intent] "
                f"Tempo total handler: {t_handler_end - t_handler_start:.3f}s, "
                f"Intent: {intent.value}, "
                f"Pergunta: {pergunta[:100]}..."
            )
            
            t_end = time.perf_counter()
            logger.info(
                f"[process_question: fim] "
                f"Tempo total: {t_end - t_start:.3f}s, "
                f"Intent: {intent.value}, "
                f"Confiança: {confianca:.2f}, "
                f"Pergunta: {pergunta[:100]}..."
            )
            
            # Registra interação para aprendizado contínuo
            try:
                interacao_id = registrar_interacao(
                    session=session,
                    pergunta=pergunta,
                    resposta=resposta,
                    intent=intent.value,
                    entities=entities,
                    contexto=contexto,
                    confianca=confianca,
                    usuario_id=usuario_id,
                    papel=papel,
                    sql_executado=sql_executado
                )
                if interacao_id:
                    contexto["interacao_id"] = interacao_id
            except Exception as e:
                logger.warning(f"Erro ao registrar interação (não crítico): {str(e)}")
            
            return {
                "resposta": resposta,
                "intent": intent.value,
                "contexto": contexto,
                "confianca": confianca,
            }
        
        except Exception as e:
            t_exception = time.perf_counter()
            logger.exception(
                f"[process_question: EXCEÇÃO] "
                f"Tempo até exceção: {t_exception - t_start:.3f}s, "
                f"Erro: {str(e)}, "
                f"Pergunta: {pergunta[:100]}..."
            )
            # Propaga a exceção para que o endpoint possa tratar adequadamente
            raise
        finally:
            if close_session:
                session.close()
    
    def _build_context(
        self,
        intent: IntentType,
        entities: Dict[str, Any],
        session: Session
    ) -> Dict[str, Any]:
        """
        Constrói contexto de dados baseado na intenção e entidades.
        
        Args:
            intent: Intenção detectada
            entities: Entidades extraídas da pergunta
            session: Sessão SQLAlchemy
            
        Returns:
            dict: Contexto estruturado com dados relevantes
        """
        contexto = {
            "intent": intent.value,
            "entities": entities
        }
        
        try:
            if intent in [IntentType.META_VENDEDOR, IntentType.MOTIVO_NAO_BATEU_META, IntentType.PREVISAO_BATER_META]:
                vendedor = entities.get("vendedor") or entities.get("rota")
                mes_ano = entities.get("mes_ano")
                
                if vendedor and mes_ano:
                    # Busca dados básicos de meta
                    dados = query_vendedor_meta(session, vendedor, mes_ano)
                    contexto.update(dados)
                    
                    # Busca features completas do vendedor para análise
                    if intent == IntentType.MOTIVO_NAO_BATEU_META:
                        features = self._get_vendedor_features(session, vendedor, mes_ano)
                        contexto["features"] = features
            
            elif intent == IntentType.META_DEPARTAMENTO or intent == IntentType.RESUMO_SUPERVISOR:
                supervisor = entities.get("supervisor")
                mes_ano = entities.get("mes_ano")
                
                if supervisor and mes_ano:
                    dados = query_supervisor_meta(session, supervisor, mes_ano)
                    contexto.update(dados)
            
            elif intent in [IntentType.CHURN_CLIENTES, IntentType.CLIENTES_RISCO_CHURN]:
                vendedor = entities.get("vendedor") or entities.get("rota")
                supervisor = entities.get("supervisor")
                
                # Usa modelo de churn para ranquear clientes
                clientes = self._get_clientes_risco_churn(session, vendedor, supervisor, limite=10)
                contexto["clientes"] = clientes
                contexto["qtd_clientes_risco"] = len(clientes)
            
            elif intent == IntentType.VENDAS_ANALISE:
                mes_ano = entities.get("mes_ano")
                vendedor = entities.get("vendedor") or entities.get("rota")
                dados = query_vendas_analise(session, mes_ano, vendedor)
                contexto.update(dados)
            
            elif intent == IntentType.VENDAS_PREVISAO:
                # Usa módulo de forecasting para previsões
                mes_ano = entities.get("mes_ano")
                if mes_ano:
                    # Extrai ano e mês
                    try:
                        ano, mes = mes_ano.split('-')
                        ano = int(ano)
                        mes = int(mes)
                        
                        # Busca série histórica
                        df_series = get_monthly_revenue_series(session)
                        
                        # Faz forecast
                        forecast_result = forecast_month_revenue(df_series, ano, mes)
                        contexto.update(forecast_result)
                        contexto["mes_ano"] = mes_ano
                    except Exception as e:
                        logger.error(f"Erro ao gerar forecast: {str(e)}")
                        contexto["erro"] = str(e)
            
            elif intent == IntentType.PRODUTOS_BAIXA_VENDA:
                # Busca produtos com baixa venda
                try:
                    produtos = get_produtos_menos_vendidos(session, dias=90, limite=20)
                    
                    contexto["tipo"] = "analise_produtos"
                    contexto["periodo_dias"] = 90
                    contexto["produtos"] = produtos
                    contexto["criterio"] = "menor volume"
                    contexto["total_produtos"] = len(produtos)
                except Exception as e:
                    logger.error(f"Erro ao buscar produtos de baixa venda: {str(e)}")
                    contexto["erro"] = str(e)
                    contexto["produtos"] = []
            
            elif intent == IntentType.CLIENTES_CHURN_PRODUTO:
                produto = entities.get("produto")
                dias_sem_compra = entities.get("dias_sem_compra", 60)
                
                if produto:
                    try:
                        # Tenta obter códigos de produto do mapeamento (otimizado)
                        codigos_produto = obter_codigos_por_nome(produto)
                        
                        # Se não encontrou códigos, tenta obter termos do mapeamento
                        # Se não encontrar termos também, usa o produto original como termo
                        termo_produto_final = None
                        if not codigos_produto:
                            termos_mapeados = obter_termos_por_nome(produto)
                            if termos_mapeados and len(termos_mapeados) > 0:
                                # Usa o primeiro termo como principal (ou pode combinar com OR)
                                termo_produto_final = termos_mapeados[0]
                            else:
                                # Fallback: usa o produto original como termo de busca
                                termo_produto_final = produto
                        
                        # Busca clientes positivados sem compra do produto
                        # Prioriza códigos (mais rápido) se disponíveis, senão usa termo
                        clientes = clientes_positivados_sem_compra_produto(
                            session,
                            codigos_produto=codigos_produto if codigos_produto else None,
                            termo_produto=termo_produto_final if not codigos_produto else None,
                            dias_sem_compra=dias_sem_compra,
                            limite=50
                        )
                        contexto["tipo"] = "clientes_churn_produto"
                        contexto["produto"] = produto
                        contexto["dias_sem_compra"] = dias_sem_compra
                        contexto["total_clientes"] = len(clientes)
                        contexto["clientes"] = clientes
                        
                        # Adiciona data base para referência
                        from sqlalchemy import func
                        from src.dw.models import Venda
                        data_base = session.query(func.max(Venda.data_venda)).scalar()
                        if data_base:
                            contexto["data_base"] = data_base.isoformat()
                    except Exception as e:
                        logger.error(f"Erro ao buscar clientes churn produto: {str(e)}")
                        contexto["erro"] = str(e)
                        contexto["clientes"] = []
                else:
                    contexto["erro"] = "Produto não especificado na pergunta"
                    contexto["clientes"] = []
            
            # Outras intenções podem adicionar contexto aqui
            
        except Exception as e:
            logger.error(f"Erro ao construir contexto: {str(e)}")
            contexto["erro"] = str(e)
        
        return contexto
    
    def _get_vendedor_features(
        self,
        session: Session,
        vendedor_nome: str,
        mes_ano: str
    ) -> Dict[str, Any]:
        """
        Busca features completas do vendedor para análise.
        
        Args:
            session: Sessão SQLAlchemy
            vendedor_nome: Nome do vendedor
            mes_ano: Mês/ano (YYYY-MM)
            
        Returns:
            dict: Features do vendedor
        """
        try:
            # Tenta carregar do CSV primeiro
            import pandas as pd
            from src.config import config
            
            features_path = config.paths.data_processed_dir / "features_vendedor.csv"
            if features_path.exists():
                df_features = pd.read_csv(features_path)
                
                # Filtra por vendedor e mes_ano
                vendedor_filtrado = df_features[
                    (df_features['vendedor'] == vendedor_nome) |
                    (df_features['vendedor_nome'].str.contains(vendedor_nome, case=False, na=False))
                ]
                
                if mes_ano:
                    vendedor_filtrado = vendedor_filtrado[vendedor_filtrado['mes_ano'] == mes_ano]
                
                if len(vendedor_filtrado) > 0:
                    # Retorna primeira linha como dict
                    features = vendedor_filtrado.iloc[0].to_dict()
                    # Remove NaN e converte para tipos nativos
                    features = {k: (v if pd.notna(v) else None) for k, v in features.items()}
                    return features
            
            # Se não encontrou no CSV, retorna vazio
            # (gerar features on the fly pode ser lento, então preferimos usar CSV)
            return {}
        
        except Exception as e:
            logger.error(f"Erro ao buscar features do vendedor: {str(e)}")
            return {}
    
    def _get_clientes_risco_churn(
        self,
        session: Session,
        vendedor_nome: Optional[str] = None,
        supervisor_nome: Optional[str] = None,
        limite: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Busca clientes em risco de churn usando modelo de ML.
        
        Args:
            session: Sessão SQLAlchemy
            vendedor_nome: Filtrar por vendedor (opcional)
            supervisor_nome: Filtrar por supervisor (opcional)
            limite: Número máximo de clientes
            
        Returns:
            List[dict]: Lista de clientes com risco de churn ranqueados
        """
        try:
            import pandas as pd
            from src.config import config
            from src.dw.models import Vendedor, Supervisor, Cliente, Venda
            
            # Carrega features de cliente
            features_path = config.paths.data_processed_dir / "features_cliente.csv"
            if not features_path.exists():
                logger.warning("Arquivo de features de cliente não encontrado")
                return []
            
            df_features = pd.read_csv(features_path)
            
            # Filtra por vendedor se especificado
            if vendedor_nome:
                vendedor = session.query(Vendedor).filter(
                    (Vendedor.codigo == vendedor_nome) |
                    (Vendedor.nome.ilike(f"%{vendedor_nome}%"))
                ).first()
                
                if vendedor:
                    # Busca clientes deste vendedor
                    cliente_ids = session.query(Venda.cliente_id).filter(
                        Venda.vendedor_id == vendedor.id
                    ).distinct().all()
                    cliente_ids = [c[0] for c in cliente_ids]
                    df_features = df_features[df_features['id_cliente'].isin(cliente_ids)]
            
            # Filtra por supervisor se especificado
            if supervisor_nome:
                supervisor = session.query(Supervisor).filter(
                    Supervisor.nome.ilike(f"%{supervisor_nome}%")
                ).first()
                
                if supervisor:
                    # Busca vendedores do supervisor
                    vendedores = session.query(Vendedor).filter(
                        Vendedor.supervisor_id == supervisor.id
                    ).all()
                    vendedor_ids = [v.id for v in vendedores]
                    
                    # Busca clientes desses vendedores
                    cliente_ids = session.query(Venda.cliente_id).filter(
                        Venda.vendedor_id.in_(vendedor_ids)
                    ).distinct().all()
                    cliente_ids = [c[0] for c in cliente_ids]
                    df_features = df_features[df_features['id_cliente'].isin(cliente_ids)]
            
            if len(df_features) == 0:
                return []
            
            # Usa modelo de churn para calcular probabilidades
            if self.churn_model and self.churn_model.is_trained:
                try:
                    # Prepara features para predição (modelo espera DataFrame com colunas corretas)
                    probas = self.churn_model.predict(df_features)
                    df_features['probabilidade_churn'] = probas
                except Exception as e:
                    logger.warning(f"Erro ao usar modelo de churn para predição: {str(e)}")
                    # Fallback: usa churn_provavel do CSV
                    df_features['probabilidade_churn'] = df_features.get('churn_provavel', 0)
            else:
                # Fallback: usa churn_provavel do CSV
                df_features['probabilidade_churn'] = df_features.get('churn_provavel', 0)
            
            # Ordena por probabilidade de churn (maior primeiro)
            df_features = df_features.sort_values('probabilidade_churn', ascending=False)
            
            # Pega top N
            top_clientes = df_features.head(limite)
            
            # Formata resultado
            clientes_risco = []
            for _, row in top_clientes.iterrows():
                cliente_id = int(row['id_cliente'])
                cliente = session.query(Cliente).filter(Cliente.id == cliente_id).first()
                
                if cliente:
                    proba = float(row['probabilidade_churn'])
                    score = self.churn_model.predict_risk_score(proba) if self.churn_model else "medio"
                    
                    clientes_risco.append({
                        "id": cliente.id,
                        "codigo": cliente.codigo,
                        "nome": cliente.nome,
                        "estado": cliente.estado,
                        "municipio": cliente.municipio,
                        "probabilidade_churn": proba,
                        "score_risco": score,
                        "valor_total_mes": float(row.get('valor_total_mes', 0)),
                        "dias_desde_ultima_compra": int(row.get('dias_desde_ultima_compra', 999)),
                    })
            
            return clientes_risco
        
        except Exception as e:
            logger.error(f"Erro ao buscar clientes em risco de churn: {str(e)}")
            return []
    
    def _enrich_with_ml(
        self,
        intent: IntentType,
        contexto: Dict[str, Any],
        entities: Dict[str, Any],
        session: Session
    ) -> Dict[str, Any]:
        """
        Enriquece contexto com predições de modelos de ML.
        
        Args:
            intent: Intenção detectada
            contexto: Contexto atual
            entities: Entidades extraídas
            session: Sessão SQLAlchemy
            
        Returns:
            dict: Contexto enriquecido com predições ML
        """
        try:
            # Se pergunta sobre meta, adiciona probabilidade de bater meta
            if intent == IntentType.PREVISAO_BATER_META:
                if self.meta_model and self.meta_model.is_trained and "features" in contexto:
                    try:
                        import pandas as pd
                        df_features = pd.DataFrame([contexto["features"]])
                        proba = self.meta_model.predict(df_features)[0]
                        contexto["probabilidade_bater_meta"] = float(proba)
                    except Exception as e:
                        logger.warning(f"Erro ao prever probabilidade de bater meta: {str(e)}")
            
            # Se pergunta sobre churn, já foi processado em _get_clientes_risco_churn
        
        except Exception as e:
            logger.error(f"Erro ao enriquecer com ML: {str(e)}")
        
        return contexto
    
    def _generate_response(
        self,
        intent: IntentType,
        contexto: Dict[str, Any],
        pergunta: str,
        contexto_memoria: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Gera resposta textual baseada na intenção e contexto.
        
        Por enquanto, usa templates sem LLM. Mais tarde será substituído
        por chamada real ao LLM.
        
        Args:
            intent: Intenção detectada
            contexto: Contexto de dados
            pergunta: Pergunta original
            contexto_memoria: Contexto de memória com interações aprovadas (opcional)
            
        Returns:
            str: Resposta formatada
        """
        # Trata previsão de vendas separadamente
        if intent == IntentType.VENDAS_PREVISAO:
            return self._gerar_resposta_previsao_vendas(contexto, pergunta)
        
        # Trata produtos de baixa venda separadamente
        if intent == IntentType.PRODUTOS_BAIXA_VENDA:
            return self._gerar_resposta_produtos_baixa_venda(contexto, pergunta)
        
        # Trata clientes churn produto separadamente
        if intent == IntentType.CLIENTES_CHURN_PRODUTO:
            return self._gerar_resposta_clientes_churn_produto(contexto, pergunta, contexto_memoria)
        
        # Adiciona contexto de memória se disponível
        contexto_llm = contexto.copy()
        if contexto_memoria and contexto_memoria.get("interacoes_aprovadas"):
            # Formata contexto de memória para o LLM
            contexto_llm["memoria_referencias"] = {
                "titulo": "Perguntas semelhantes anteriores e respostas aprovadas:",
                "interacoes": contexto_memoria["interacoes_aprovadas"]
            }
        
        # Usa stub do LLM que já formata respostas baseadas no contexto
        return call_llm(contexto_llm, pergunta)
    
    def _gerar_resposta_previsao_vendas(
        self,
        contexto: Dict[str, Any],
        pergunta: str
    ) -> str:
        """
        Gera resposta consultiva para previsão de vendas/faturamento.
        
        Args:
            contexto: Contexto com resultado do forecast
            pergunta: Pergunta original
            
        Returns:
            str: Resposta formatada
        """
        tipo = contexto.get("tipo")
        mes_ano = contexto.get("mes_ano", "")
        
        # Formata mês/ano para exibição
        def formatar_mes_ano(mes_ano_str: str) -> str:
            if not mes_ano_str:
                return "o período"
            try:
                dt = datetime.strptime(mes_ano_str, "%Y-%m")
                meses = [
                    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
                    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
                ]
                return f"{meses[dt.month - 1]} de {dt.year}"
            except:
                return mes_ano_str
        
        mes_ano_formatado = formatar_mes_ano(mes_ano)
        
        # Caso 1: Histórico (mês já consolidado)
        if tipo == "historico":
            faturamento_previsto = contexto.get("faturamento_previsto", 0)
            resposta = f"Em {mes_ano_formatado} o faturamento já consolidado é de **R$ {faturamento_previsto:,.2f}**."
            
            # Tenta usar LLM para enriquecer a resposta
            try:
                contexto_llm = {
                    "intent": "vendas_previsao",
                    "tipo": "historico",
                    "mes_ano": mes_ano,
                    "faturamento_previsto": faturamento_previsto,
                    "observacoes": contexto.get("observacoes", ""),
                }
                resposta_llm = gerar_resposta_llm(contexto_llm, pergunta)
                if resposta_llm and len(resposta_llm) > 50:  # LLM retornou algo útil
                    resposta = resposta_llm
            except Exception as e:
                logger.warning(f"Erro ao gerar resposta LLM para previsão histórica: {str(e)}")
            
            return resposta
        
        # Caso 2: Forecast (previsão para mês futuro)
        if tipo == "forecast":
            faturamento_previsto = contexto.get("faturamento_previsto", 0)
            intervalo_inferior = contexto.get("intervalo_inferior", 0)
            intervalo_superior = contexto.get("intervalo_superior", 0)
            base_meses = contexto.get("base_meses", [])
            observacoes = contexto.get("observacoes", "")
            
            resposta = (
                f"Ainda não temos vendas registradas para {mes_ano_formatado}.\n\n"
                f"Com base no histórico de vendas"
            )
            
            if base_meses:
                resposta += f" dos últimos meses"
                if len(base_meses) <= 6:
                    resposta += f" ({', '.join(base_meses)})"
                else:
                    resposta += f" (incluindo {', '.join(base_meses[:3])} e mais {len(base_meses) - 3} mês[es])"
            
            resposta += (
                f", a **projeção de faturamento é de cerca de R$ {faturamento_previsto:,.2f}**, "
                f"variando entre **R$ {intervalo_inferior:,.2f}** e **R$ {intervalo_superior:,.2f}** "
                f"(intervalo de confiança de ±10%).\n\n"
            )
            
            if observacoes:
                resposta += f"*{observacoes}*"
            
            # Tenta usar LLM para enriquecer a resposta (mas mantém os números do forecast)
            try:
                contexto_llm = {
                    "intent": "vendas_previsao",
                    "tipo": "forecast",
                    "mes_ano": mes_ano,
                    "faturamento_previsto": faturamento_previsto,
                    "intervalo_inferior": intervalo_inferior,
                    "intervalo_superior": intervalo_superior,
                    "base_meses": base_meses[:10],  # Limita para o LLM
                    "observacoes": observacoes,
                }
                resposta_llm = gerar_resposta_llm(contexto_llm, pergunta)
                if resposta_llm and len(resposta_llm) > 100:  # LLM retornou algo útil
                    # Garante que os números não foram alterados
                    resposta_llm_clean = resposta_llm
                    # Verifica se mantém os números corretos (aproximadamente)
                    if f"{faturamento_previsto:,.0f}"[:8] in resposta_llm_clean.replace(",", "").replace(".", ""):
                        resposta = resposta_llm
            except Exception as e:
                logger.warning(f"Erro ao gerar resposta LLM para forecast: {str(e)}")
            
            return resposta
        
        # Caso 3: Histórico insuficiente
        if tipo == "insuficiente":
            mensagem = contexto.get("mensagem", "Histórico insuficiente para projeção confiável.")
            resposta = (
                f"Não há histórico suficiente para projetar {mes_ano_formatado} com segurança.\n\n"
                f"{mensagem}\n\n"
                f"Precisamos de pelo menos 3 meses de dados para estimar."
            )
            return resposta
        
        # Fallback
        return f"Desculpe, não foi possível gerar uma previsão para {mes_ano_formatado}."
    
    def _gerar_resposta_produtos_baixa_venda(
        self,
        contexto: Dict[str, Any],
        pergunta: str
    ) -> str:
        """
        Gera resposta consultiva para produtos com baixa venda.
        
        Args:
            contexto: Contexto com produtos de baixa venda
            pergunta: Pergunta original
            
        Returns:
            str: Resposta formatada
        """
        produtos = contexto.get("produtos", [])
        periodo_dias = contexto.get("periodo_dias", 90)
        
        # Usa formatador dedicado para resposta bonita e consultiva
        # IMPORTANTE: Os números vêm sempre do banco, nunca são inventados
        resposta = format_analise_produtos(produtos, periodo_dias)
        
        return resposta
    
    def _gerar_resposta_clientes_churn_produto(
        self,
        contexto: Dict[str, Any],
        pergunta: str,
        contexto_memoria: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Gera resposta consultiva para clientes que abandonaram um produto.
        
        Args:
            contexto: Contexto com lista de clientes
            pergunta: Pergunta original
            contexto_memoria: Contexto de memória (opcional)
            
        Returns:
            str: Resposta formatada
        """
        produto = contexto.get("produto", "produto")
        dias_sem_compra = contexto.get("dias_sem_compra", 60)
        clientes = contexto.get("clientes", [])
        total_clientes = len(clientes)
        
        # Se não há clientes, retorna mensagem específica
        if total_clientes == 0:
            return (
                f"Nenhum cliente encontrado que já tenha comprado **{produto}** "
                f"e esteja há mais de **{dias_sem_compra} dias** sem comprar."
            )
        
        # Monta contexto enxuto para o LLM (apenas números e top 5 clientes)
        contexto_llm = {
            "tipo": "clientes_churn_produto",
            "produto": produto,
            "dias_sem_compra": dias_sem_compra,
            "total_clientes": total_clientes,
            "top_5_clientes": clientes[:5],  # Limita para não sobrecarregar o contexto
        }
        
        # Adiciona contexto de memória se disponível
        if contexto_memoria and contexto_memoria.get("interacoes_aprovadas"):
            contexto_llm["memoria_referencias"] = {
                "titulo": "Perguntas semelhantes anteriores e respostas aprovadas:",
                "interacoes": contexto_memoria["interacoes_aprovadas"]
            }
        
        # Usa LLM para formatar resposta consultiva, mas com números fixos
        try:
            resposta = gerar_resposta_llm(contexto_llm, pergunta)
            return resposta
        except Exception as e:
            logger.error(f"Erro ao gerar resposta LLM para churn produto: {str(e)}")
            # Fallback: resposta template simples
            top_5 = clientes[:5]
            resposta = (
                f"Encontrei **{total_clientes} clientes** que já foram positivados em **{produto}** "
                f"e estão há mais de **{dias_sem_compra} dias** sem comprar.\n\n"
            )
            if top_5:
                resposta += "Os 5 principais são:\n\n"
                for i, cliente in enumerate(top_5, 1):
                    nome = cliente.get("nome_cliente", cliente.get("codigo_cliente", "N/A"))
                    dias = cliente.get("dias_sem_compra", 0)
                    faturamento = cliente.get("total_historico_faturamento", 0)
                    resposta += (
                        f"{i}. **{nome}** - {dias} dias sem comprar "
                        f"(histórico: R$ {faturamento:,.2f})\n"
                    )
            if total_clientes > 5:
                resposta += f"\n*Além desses, há mais {total_clientes - 5} clientes que também abandonaram o produto.*"
            return resposta
    
    def _calculate_confidence(
        self,
        intent: IntentType,
        entities: Dict[str, Any],
        contexto: Dict[str, Any]
    ) -> float:
        """
        Calcula confiança da resposta baseada em entidades e contexto.
        
        Args:
            intent: Intenção detectada
            entities: Entidades extraídas
            contexto: Contexto de dados
            
        Returns:
            float: Confiança (0.0-1.0)
        """
        confianca = 0.5  # Base
        
        # Aumenta confiança se conseguiu identificar vendedor/mes
        if entities.get("vendedor") or entities.get("rota"):
            confianca += 0.2
        if entities.get("mes_ano"):
            confianca += 0.1
        
        # Aumenta se conseguiu buscar dados
        if "erro" not in contexto:
            confianca += 0.2
        
        # Aumenta se tem modelo de ML disponível
        if (intent in [IntentType.MOTIVO_NAO_BATEU_META, IntentType.PREVISAO_BATER_META] and 
            self.meta_model and self.meta_model.is_trained):
            confianca += 0.1
        
        if (intent in [IntentType.CLIENTES_RISCO_CHURN, IntentType.CHURN_CLIENTES] and
            self.churn_model and self.churn_model.is_trained):
            confianca += 0.1
        
        return min(1.0, confianca)
    
    def _gerar_resposta_quem_bateu_meta(
        self,
        mes_ano: str,
        total_vendedores: int,
        top_vendedores: List[Dict[str, Any]],
        atingimento_medio: float,
        tem_mais: bool
    ) -> str:
        """
        Gera resposta resumida para pergunta "quem bateu meta".
        
        Args:
            mes_ano: Mês/ano (ex: "2025-08")
            total_vendedores: Total de vendedores que bateram meta
            top_vendedores: Lista dos top vendedores (máximo 5)
            atingimento_medio: Percentual médio de atingimento
            tem_mais: Se há mais vendedores além dos top 5
            
        Returns:
            str: Resposta resumida em texto
        """
        # Formata mês/ano para exibição
        def formatar_mes_ano(mes_ano_str: str) -> str:
            try:
                from datetime import datetime
                dt = datetime.strptime(mes_ano_str, "%Y-%m")
                meses = [
                    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
                    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
                ]
                return f"{meses[dt.month - 1]} de {dt.year}"
            except:
                return mes_ano_str
        
        mes_ano_formatado = formatar_mes_ano(mes_ano)
        
        resposta = f"**{total_vendedores} vendedor(es) bateram a meta em {mes_ano_formatado}**.\n\n"
        resposta += f"Atingimento médio: **{atingimento_medio:.1f}%**.\n\n"
        
        if top_vendedores:
            resposta += f"**Top {len(top_vendedores)} vendedores:**\n\n"
            for i, v in enumerate(top_vendedores, 1):
                vendedor_nome = v.get("vendedor", "")
                vendedor_codigo = v.get("vendedor_codigo", "")
                perc = v.get("perc_atingido", 0)
                
                resposta += f"{i}. **{vendedor_nome}**"
                if vendedor_codigo:
                    resposta += f" ({vendedor_codigo})"
                resposta += f" - {perc:.1f}%\n"
            
            if tem_mais:
                resposta += f"\n*E mais {total_vendedores - len(top_vendedores)} vendedor(es).*"
        
        return resposta
    
    def _gerar_resposta_meta(self, dados: Dict[str, Any], tipo: str = "geral") -> str:
        """
        Gera narrativa comercial consultiva sobre análise de metas.
        
        Cria respostas de 3-5 linhas com insights comerciais:
        - Meta total e faturado
        - Percentual de atingimento
        - Pontos de atenção (quem ficou abaixo)
        - Destaques positivos (quem superou)
        
        Args:
            dados: Dicionário com dados de meta (meta_valor, realizado_valor, etc.)
            tipo: Tipo de consulta ('vendedor', 'supervisor', 'geral', 'departamento')
            
        Returns:
            str: Narrativa comercial formatada
        """
        mes_ano = dados.get("mes_ano", "")
        
        # Formata mês/ano para exibição
        def formatar_mes_ano(mes_ano_str: str) -> str:
            if not mes_ano_str:
                return "o período"
            try:
                from datetime import datetime
                dt = datetime.strptime(mes_ano_str, "%Y-%m")
                meses = [
                    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
                    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
                ]
                return f"{meses[dt.month - 1]} de {dt.year}"
            except:
                return mes_ano_str
        
        mes_ano_formatado = formatar_mes_ano(mes_ano)
        
        # Caso 1: Meta de vendedor específico
        if tipo == "vendedor":
            meta_valor = dados.get("meta_valor", 0)
            realizado_valor = dados.get("realizado_valor", 0)
            perc_atingido = dados.get("perc_atingido", 0)
            vendedor_nome = dados.get("vendedor", "")
            vendedor_codigo = dados.get("vendedor_codigo", "")
            gap_valor = dados.get("gap_valor", 0)
            
            # Monta narrativa
            resposta = f"A meta do vendedor **{vendedor_nome}**"
            if vendedor_codigo:
                resposta += f" ({vendedor_codigo})"
            resposta += f" para {mes_ano_formatado} foi de **R$ {meta_valor:,.2f}**.\n\n"
            
            resposta += f"O faturado foi de **R$ {realizado_valor:,.2f}**, resultando em **{perc_atingido:.1f}% de atingimento**.\n\n"
            
            if perc_atingido >= 100:
                resposta += f"✅ **Resultado acima da meta!** O vendedor superou a meta em **{perc_atingido - 100:.1f}%**, demonstrando excelente performance.\n"
            elif perc_atingido >= 90:
                resposta += f"⚡ Resultado próximo da meta, com um gap de R$ {abs(gap_valor):,.2f}. Com um esforço adicional é possível atingir a meta completa.\n"
            elif perc_atingido >= 70:
                resposta += f"⚠️ Resultado abaixo do esperado, ficando **{100 - perc_atingido:.1f}% abaixo da meta** (gap de R$ {abs(gap_valor):,.2f}). Recomenda-se análise detalhada das causas.\n"
            else:
                resposta += f"🔴 **Atenção necessária:** Resultado significativamente abaixo da meta, com apenas **{perc_atingido:.1f}% de atingimento** (gap de R$ {abs(gap_valor):,.2f}). Investigação urgente recomendada.\n"
            
            if dados.get("supervisor"):
                resposta += f"\nSupervisor responsável: **{dados['supervisor']}**."
            
            return resposta
        
        # Caso 2: Meta de supervisor/departamento
        if tipo == "supervisor":
            meta_valor = dados.get("meta_valor", 0)
            realizado_valor = dados.get("realizado_valor", 0)
            perc_atingido = dados.get("perc_atingido", 0)
            supervisor_nome = dados.get("supervisor", "")
            vendedores = dados.get("vendedores", [])
            gap_valor = dados.get("gap_valor", 0)
            
            resposta = f"A meta do supervisor **{supervisor_nome}** para {mes_ano_formatado} foi de **R$ {meta_valor:,.2f}**.\n\n"
            resposta += f"O faturado foi de **R$ {realizado_valor:,.2f}**, resultando em **{perc_atingido:.1f}% de atingimento**.\n\n"
            
            # Busca detalhes dos vendedores se disponível
            if vendedores and isinstance(vendedores, list) and len(vendedores) > 0:
                # Se temos lista de nomes, tenta buscar dados detalhados
                # (Por enquanto, apenas menciona quantidade)
                resposta += f"A equipe possui **{len(vendedores)} vendedor(es)** sob gestão."
            
            if perc_atingido < 70:
                resposta += f"\n⚠️ **Abaixo do esperado**, com **{100 - perc_atingido:.1f}% abaixo da meta** (gap de R$ {abs(gap_valor):,.2f}). Ação corretiva recomendada."
            elif perc_atingido >= 100:
                resposta += f"\n✅ **Meta atingida com sucesso!** Resultado acima do esperado."
            else:
                resposta += f"\n📊 Resultado próximo da meta, com gap de R$ {abs(gap_valor):,.2f}."
            
            return resposta
        
        # Caso 3: Metas agregadas por departamento ou geral
        if tipo in ["departamento", "geral"]:
            meta_total = dados.get("total_meta", dados.get("meta_valor", 0))
            realizado_total = dados.get("total_realizado", dados.get("realizado_valor", 0))
            perc_atingido = dados.get("perc_atingido_geral", dados.get("perc_atingido", 0))
            gap_total = dados.get("total_gap", dados.get("gap_valor", 0))
            departamentos = dados.get("departamentos", [])
            
            # Narrativa principal
            resposta = f"A meta total para {mes_ano_formatado} foi de **R$ {meta_total:,.2f}**.\n\n"
            resposta += f"O faturado foi de **R$ {realizado_total:,.2f}**, resultando em **{perc_atingido:.1f}% de atingimento**.\n\n"
            
            # Analisa departamentos/vendedores para identificar pontos de atenção e destaques
            pontos_atencao_rotas = []
            pontos_atencao_dept = []
            destaques_dept = []
            destaques_vendedores = []
            
            # Analisa vendedores com baixo desempenho (rotas específicas)
            vendedores_baixo = dados.get("vendedores_baixo_desempenho", [])
            for v in vendedores_baixo[:3]:  # Máximo 3 rotas
                vendedor_codigo = v.get("vendedor_codigo", "")
                vendedor_nome = v.get("vendedor", "")
                v_perc = v.get("perc_atingido", 0)
                if v_perc < 70:
                    rotas_str = vendedor_codigo if vendedor_codigo else vendedor_nome
                    pontos_atencao_rotas.append(f"{rotas_str} ({v_perc:.0f}%)")
            
            # Analisa departamentos
            if departamentos and len(departamentos) > 0:
                for dept in departamentos:
                    dept_perc = dept.get("perc_atingido", 0)
                    if dept_perc < 70:
                        nome = dept.get("supervisor", "Departamento desconhecido")
                        pontos_atencao_dept.append(f"{nome} ({dept_perc:.1f}%)")
                    elif dept_perc > 100:
                        nome = dept.get("supervisor", "Departamento desconhecido")
                        destaques_dept.append(f"{nome} ({dept_perc:.1f}%)")
            
            # Analisa vendedores que bateram meta
            vendedores_que_bateram = dados.get("vendedores_que_bateram", [])
            for v in vendedores_que_bateram[:3]:  # Top 3
                vendedor_nome = v.get("vendedor", "")
                vendedor_codigo = v.get("vendedor_codigo", "")
                v_perc = v.get("perc_atingido", 0)
                if v_perc > 100:
                    rotas_str = vendedor_codigo if vendedor_codigo else vendedor_nome
                    destaques_vendedores.append(f"{vendedor_nome} ({rotas_str}) - {v_perc:.0f}%")
            
            # Adiciona pontos de atenção (prioriza rotas se disponíveis)
            if pontos_atencao_rotas:
                resposta += f"Abaixo do esperado principalmente nas rotas **{', '.join(pontos_atencao_rotas)}**, que ficaram abaixo de 70%.\n\n"
            elif pontos_atencao_dept:
                resposta += f"Abaixo do esperado principalmente em: **{', '.join(pontos_atencao_dept[:3])}**"
                if len(pontos_atencao_dept) > 3:
                    resposta += f" e mais {len(pontos_atencao_dept) - 3} departamento(s)."
                resposta += "\n\n"
            
            # Adiciona destaques (prioriza vendedores específicos se disponíveis)
            if destaques_vendedores:
                resposta += f"O destaque positivo foi o vendedor **{destaques_vendedores[0]}**"
                if len(destaques_vendedores) > 1:
                    resposta += f", além de {len(destaques_vendedores) - 1} outro(s) vendedor(es) acima de 100%."
                resposta += "\n"
            elif destaques_dept:
                resposta += f"O destaque positivo foi: **{destaques_dept[0]}**"
                if len(destaques_dept) > 1:
                    resposta += f" e {len(destaques_dept) - 1} outro(s) departamento(s) acima de 100%."
                resposta += "\n"
            
            # Análise geral se não tiver pontos específicos
            if not pontos_atencao_rotas and not pontos_atencao_dept and not destaques_vendedores and not destaques_dept:
                if perc_atingido < 70:
                    resposta += f"**Atenção:** Resultado significativamente abaixo da meta esperada (gap de R$ {abs(gap_total):,.2f}).\n"
                elif perc_atingido >= 100:
                    resposta += f"✅ **Excelente resultado!** Meta superada em {perc_atingido - 100:.1f}%.\n"
                else:
                    resposta += f"Resultado próximo da meta, com gap de R$ {abs(gap_total):,.2f}.\n"
            
            return resposta
        
        # Fallback: resposta básica
        meta_valor = dados.get("meta_valor", dados.get("total_meta", 0))
        realizado_valor = dados.get("realizado_valor", dados.get("total_realizado", 0))
        perc_atingido = dados.get("perc_atingido", dados.get("perc_atingido_geral", 0))
        
        resposta = f"A meta para {mes_ano_formatado} foi de **R$ {meta_valor:,.2f}**.\n\n"
        resposta += f"O faturado foi de **R$ {realizado_valor:,.2f}**, resultando em **{perc_atingido:.1f}% de atingimento**.\n"
        
        return resposta
    
    def _handle_meta_query(
        self,
        intent: IntentType,
        entities: Dict[str, Any],
        session: Session,
        contexto_memoria: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Manipula consultas de meta de forma unificada.
        
        Suporta perguntas como:
        - "me mostre a meta de agosto de 2025"
        - "qual a meta do vendedor X em abril?"
        - "meta do supervisor da pasta amarela em dezembro"
        - "quem bateu meta em 2025-03?"
        - "mostrar metas por departamento em 2025-07"
        
        Args:
            intent: Intenção detectada
            entities: Entidades extraídas (mes_ano, vendedor, supervisor, etc.)
            session: Sessão SQLAlchemy
            
        Returns:
            dict: Contexto com dados de meta e resposta formatada
        """
        logger.info(f"Processando consulta de meta: entities={entities}")
        
        # Verifica se é consulta de "últimos N meses"
        # Prioriza janela_meses (novo nome), depois n_meses (compatibilidade)
        janela_meses = entities.get("janela_meses") or entities.get("n_meses")
        pergunta_original = entities.get("pergunta_original", "")
        pergunta_lower = pergunta_original.lower() if pergunta_original else ""
        
        if janela_meses and (re.search(r"últimos.*meses|últimos.*mês", pergunta_lower) or 
                        re.search(r"como.*estão.*meta|evolução.*meta", pergunta_lower)):
            # É uma consulta de "últimos N meses"
            return self._handle_meta_ultimos_meses(
                session=session,
                n_meses=janela_meses,
                entities=entities,
                contexto_memoria=contexto_memoria
            )
        
        # Caso contrário, segue fluxo normal (mes_ano específico)
        # Normaliza mes_ano
        mes_ano = entities.get("mes_ano")
        if not mes_ano:
            # Tenta construir mes_ano a partir de mes e ano
            mes = entities.get("mes")
            ano = entities.get("ano")
            if mes and ano:
                mes_ano = f"{ano}-{mes.zfill(2)}"
            else:
                # Usa mês atual como fallback
                from datetime import datetime
                now = datetime.now()
                mes_ano = f"{now.year}-{now.month:02d}"
        
        # Valida formato de mes_ano
        try:
            from datetime import datetime
            datetime.strptime(mes_ano, "%Y-%m")
        except ValueError:
            return {
                "intent": intent.value,
                "entities": entities,
                "erro": f"Formato de data inválido: {mes_ano}. Use YYYY-MM",
                "resposta": f"Desculpe, não consegui entender a data. Por favor, use o formato YYYY-MM (ex.: 2025-08)."
            }
        
        contexto = {
            "intent": intent.value,
            "entities": entities,
            "mes_ano": mes_ano
        }
        
        # Verifica se pergunta "quem bateu meta"
        pergunta_original = entities.get("pergunta_original", "")
        pergunta_lower = pergunta_original.lower() if pergunta_original else ""
        if "quem" in pergunta_lower and "bateu" in pergunta_lower:
            # Query: quem bateu meta
            vendedores = query_vendedores_que_bateram_meta(session, mes_ano)
            
            if not vendedores:
                # Nenhum vendedor bateu meta
                contexto["resposta"] = f"Nenhum vendedor bateu a meta em {mes_ano}."
                contexto["confianca"] = 0.8
                contexto["resumo"] = {
                    "total_vendedores_bateram": 0,
                    "meta_total": 0.0,
                    "realizado_total": 0.0,
                    "atingimento_medio": 0.0,
                }
                contexto["top_vendedores"] = []
                contexto["demais_vendedores"] = []
                return contexto
            
            # Calcula resumo agregado
            meta_total = sum(v["meta_valor"] for v in vendedores)
            realizado_total = sum(v["realizado_valor"] for v in vendedores)
            atingimentos = [v["perc_atingido"] for v in vendedores]
            atingimento_medio = sum(atingimentos) / len(atingimentos) if atingimentos else 0.0
            
            # Separa top vendedores (top 5 por atingimento) dos demais
            vendedores_ordenados = sorted(vendedores, key=lambda x: x["perc_atingido"], reverse=True)
            top_vendedores = vendedores_ordenados[:5]
            demais_vendedores = vendedores_ordenados[5:]
            
            # Formata dados estruturados para top vendedores
            top_vendedores_estruturados = []
            for v in top_vendedores:
                top_vendedores_estruturados.append({
                    "vendedor": v.get("vendedor", ""),
                    "rota": v.get("vendedor_codigo", ""),
                    "supervisor": v.get("supervisor"),
                    "meta": v.get("meta_valor", 0.0),
                    "realizado": v.get("realizado_valor", 0.0),
                    "atingimento": v.get("perc_atingido", 0.0),
                })
            
            # Formata dados estruturados para demais vendedores (versão simplificada)
            demais_vendedores_estruturados = []
            for v in demais_vendedores:
                demais_vendedores_estruturados.append({
                    "vendedor": v.get("vendedor", ""),
                    "rota": v.get("vendedor_codigo", ""),
                    "supervisor": v.get("supervisor"),
                    "atingimento": v.get("perc_atingido", 0.0),
                    # Opcional: incluir meta e realizado se necessário
                    "meta": v.get("meta_valor", 0.0),
                    "realizado": v.get("realizado_valor", 0.0),
                })
            
            # Monta contexto estruturado primeiro (para o LLM e frontend)
            contexto["resumo"] = {
                "total_vendedores_bateram": len(vendedores),
                "meta_total": float(meta_total),
                "realizado_total": float(realizado_total),
                "atingimento_medio": float(atingimento_medio),
            }
            contexto["top_vendedores"] = top_vendedores_estruturados
            contexto["demais_vendedores"] = demais_vendedores_estruturados
            
            # Gera resposta usando LLM (com fallback para template)
            pergunta_original = entities.get("pergunta_original", "quem bateu meta")
            try:
                # Cria contexto enxuto para o LLM
                contexto_llm = {
                    "intent": "quem_bateu_meta",
                    "mes_ano": mes_ano,
                    "resumo": contexto["resumo"],
                    "top_vendedores": contexto["top_vendedores"][:3],  # Limita a top 3 para o LLM
                    "total_demais": len(demais_vendedores),
                }
                
                # Adiciona contexto de memória se disponível
                if contexto_memoria and contexto_memoria.get("interacoes_aprovadas"):
                    contexto_llm["memoria_referencias"] = {
                        "titulo": "Perguntas semelhantes anteriores e respostas aprovadas:",
                        "interacoes": contexto_memoria["interacoes_aprovadas"]
                    }
                
                # Chama LLM para gerar resposta
                resposta = gerar_resposta_llm(contexto_llm, pergunta_original)
                contexto["resposta"] = resposta
                contexto["confianca"] = 0.9
            except Exception as e:
                logger.warning(f"Erro ao gerar resposta com LLM, usando template: {str(e)}")
                # Fallback para resposta template
                resposta = self._gerar_resposta_quem_bateu_meta(
                    mes_ano=mes_ano,
                    total_vendedores=len(vendedores),
                    top_vendedores=top_vendedores,
                    atingimento_medio=atingimento_medio,
                    tem_mais=len(demais_vendedores) > 0
                )
                contexto["resposta"] = resposta
                contexto["confianca"] = 0.85
            
            return contexto
        
        # Caso 1: Tem vendedor específico
        vendedor = entities.get("vendedor") or entities.get("rota")
        if vendedor:
            dados = query_vendedor_meta(session, vendedor, mes_ano)
            
            if "erro" in dados:
                contexto["erro"] = dados.get("erro")
                contexto["resposta"] = f"Desculpe, não encontrei informações sobre a meta do vendedor '{vendedor}' em {mes_ano}."
                contexto["confianca"] = 0.3
                return contexto
            
            # Atualiza contexto com dados
            contexto.update(dados)
            
            # Gera resposta usando LLM (com fallback para template)
            pergunta_original = entities.get("pergunta_original", "qual a meta do vendedor")
            try:
                # Cria contexto enxuto para o LLM
                contexto_llm = {
                    "intent": "meta_vendedor",
                    "mes_ano": mes_ano,
                    "vendedor": dados.get("vendedor"),
                    "vendedor_codigo": dados.get("vendedor_codigo"),
                    "meta_valor": dados.get("meta_valor", 0),
                    "realizado_valor": dados.get("realizado_valor", 0),
                    "perc_atingido": dados.get("perc_atingido", 0),
                    "gap_valor": dados.get("gap_valor", 0),
                    "supervisor": dados.get("supervisor"),
                }
                
                # Adiciona contexto de memória se disponível
                if contexto_memoria and contexto_memoria.get("interacoes_aprovadas"):
                    contexto_llm["memoria_referencias"] = {
                        "titulo": "Perguntas semelhantes anteriores e respostas aprovadas:",
                        "interacoes": contexto_memoria["interacoes_aprovadas"]
                    }
                
                resposta = gerar_resposta_llm(contexto_llm, pergunta_original)
                contexto["resposta"] = resposta
                contexto["confianca"] = 0.85
            except Exception as e:
                logger.warning(f"Erro ao gerar resposta com LLM, usando template: {str(e)}")
                # Fallback para template
                resposta = self._gerar_resposta_meta(dados, tipo="vendedor")
                contexto["resposta"] = resposta
                contexto["confianca"] = 0.8
            
            return contexto
        
        # Caso 2: Tem supervisor específico
        supervisor = entities.get("supervisor")
        if supervisor:
            dados = query_supervisor_meta(session, supervisor, mes_ano)
            
            if "erro" in dados:
                contexto["erro"] = dados.get("erro")
                contexto["resposta"] = f"Desculpe, não encontrei informações sobre a meta do supervisor '{supervisor}' em {mes_ano}."
                contexto["confianca"] = 0.3
                return contexto
            
            # Busca detalhes dos vendedores para análise mais completa
            # (Pode enriquecer a narrativa com quem ficou abaixo/acima)
            vendedores_detalhados = []
            if dados.get('vendedores'):
                for vendedor_nome in dados['vendedores'][:10]:  # Limita busca
                    try:
                        vendedor_dados = query_vendedor_meta(session, vendedor_nome, mes_ano)
                        if "erro" not in vendedor_dados:
                            vendedores_detalhados.append(vendedor_dados)
                    except:
                        pass
            
            # Se temos dados detalhados, adiciona à estrutura
            if vendedores_detalhados:
                dados['vendedores_detalhados'] = vendedores_detalhados
            
            # Atualiza contexto com dados
            contexto.update(dados)
            
            # Gera resposta usando LLM (com fallback para template)
            pergunta_original = entities.get("pergunta_original", "qual a meta do supervisor")
            try:
                # Cria contexto enxuto para o LLM
                contexto_llm = {
                    "intent": "meta_supervisor",
                    "mes_ano": mes_ano,
                    "supervisor": dados.get("supervisor"),
                    "meta_valor": dados.get("meta_valor", 0),
                    "realizado_valor": dados.get("realizado_valor", 0),
                    "perc_atingido": dados.get("perc_atingido", 0),
                    "gap_valor": dados.get("gap_valor", 0),
                    "qtd_vendedores": dados.get("qtd_vendedores", 0),
                }
                
                # Adiciona contexto de memória se disponível
                if contexto_memoria and contexto_memoria.get("interacoes_aprovadas"):
                    contexto_llm["memoria_referencias"] = {
                        "titulo": "Perguntas semelhantes anteriores e respostas aprovadas:",
                        "interacoes": contexto_memoria["interacoes_aprovadas"]
                    }
                
                resposta = gerar_resposta_llm(contexto_llm, pergunta_original)
                contexto["resposta"] = resposta
                contexto["confianca"] = 0.85
            except Exception as e:
                logger.warning(f"Erro ao gerar resposta com LLM, usando template: {str(e)}")
                # Fallback para template
                resposta = self._gerar_resposta_meta(dados, tipo="supervisor")
                contexto["resposta"] = resposta
                contexto["confianca"] = 0.8
            
            return contexto
        
        # Caso 3: Só tem mês/ano (consulta geral ou por departamento)
        # Verifica se pergunta sobre "metas por departamento"
        if pergunta_lower and ("departamento" in pergunta_lower or "por departamento" in pergunta_lower):
            dados = query_metas_departamento_agregadas(session, mes_ano)
            
            if "erro" in dados:
                contexto["erro"] = dados.get("erro")
                contexto["resposta"] = f"Desculpe, não encontrei informações sobre metas por departamento em {mes_ano}."
                contexto["confianca"] = 0.3
                return contexto
            
            # Atualiza contexto com dados
            contexto.update(dados)
            
            # Gera resposta usando LLM (com fallback para template)
            pergunta_original = entities.get("pergunta_original", "mostrar metas por departamento")
            try:
                # Cria contexto enxuto para o LLM
                contexto_llm = {
                    "intent": "metas_departamento",
                    "mes_ano": mes_ano,
                    "total_meta": dados.get("total_meta", 0),
                    "total_realizado": dados.get("total_realizado", 0),
                    "perc_atingido_geral": dados.get("perc_atingido_geral", 0),
                    "total_gap": dados.get("total_gap", 0),
                    "qtd_departamentos": dados.get("qtd_departamentos", 0),
                    "departamentos": dados.get("departamentos", [])[:5],  # Top 5 para o LLM
                }
                
                # Adiciona contexto de memória se disponível
                if contexto_memoria and contexto_memoria.get("interacoes_aprovadas"):
                    contexto_llm["memoria_referencias"] = {
                        "titulo": "Perguntas semelhantes anteriores e respostas aprovadas:",
                        "interacoes": contexto_memoria["interacoes_aprovadas"]
                    }
                
                resposta = gerar_resposta_llm(contexto_llm, pergunta_original)
                contexto["resposta"] = resposta
                contexto["confianca"] = 0.85
            except Exception as e:
                logger.warning(f"Erro ao gerar resposta com LLM, usando template: {str(e)}")
                # Fallback para template
                resposta = self._gerar_resposta_meta(dados, tipo="departamento")
                contexto["resposta"] = resposta
                contexto["confianca"] = 0.8
            
            return contexto
        
        # Caso 4: Só tem mês/ano (consulta geral da meta do período)
        # NOVA ABORDAGEM: Usa analisar_meta_mensal para análise profunda quando há mês específico
        mes_ano = entities.get("mes_ano")
        janela_meses = entities.get("janela_meses") or entities.get("n_meses") or 6
        
        contexto_dados: Dict[str, Any] = {}
        
        # Se há mês específico, usa análise profunda
        if mes_ano:
            try:
                ano, mes = mes_ano.split("-")
                ano_int = int(ano)
                mes_int = int(mes)
                
                # Chama função analítica profunda
                analise = analisar_meta_mensal(session, ano_int, mes_int)
                
                if analise.get("semDados"):
                    contexto["resposta"] = (
                        f"Não encontrei dados de metas e realizados para {mes_ano}. "
                        f"O sistema possui dados de {analise.get('limitesDados', {}).get('primeiroMesAno', 'N/A')} "
                        f"até {analise.get('limitesDados', {}).get('ultimoMesAno', 'N/A')}."
                    )
                    contexto["confianca"] = 0.5
                    contexto.update(analise)
                    return contexto
                
                # Injeta análise completa no contexto
                contexto_dados.update(analise)
                contexto_dados["mes_ano"] = mes_ano
                
            except (ValueError, Exception) as e:
                logger.warning(f"Erro ao analisar meta mensal: {str(e)}")
                # Fallback para método antigo
                pass
        
        # Fallback: método antigo (série mensal + detalhe vendedores)
        if not contexto_dados.get("kpis"):
            # 1) Série histórica de metas x realizado por mês
            try:
                serie_mensal = query_meta_realizado_por_mes(session, meses_retroativos=janela_meses)
                contexto_dados["serie_mensal"] = serie_mensal
            except Exception as e:
                logger.warning(f"Erro ao buscar série mensal: {str(e)}")
                serie_mensal = []
            
            # 2) Se o usuário pediu um mês específico, tentar detalhar por vendedor
            vendedores_mes = []
            if mes_ano:
                try:
                    vendedores_mes = query_meta_realizado_por_vendedor(session, mes_ano)
                except Exception as e:
                    logger.warning(f"Erro ao buscar vendedores: {str(e)}")
            
            contexto_dados["detalhe_vendedores_mes"] = {
                "mes_ano": mes_ano,
                "vendedores": vendedores_mes,
            }
            
            # 3) Flags de disponibilidade
            contexto_dados["tem_serie_mensal"] = len(serie_mensal) > 0
            contexto_dados["tem_detalhe_vendedores"] = bool(mes_ano and vendedores_mes)
            
            # Se não há dados, retorna mensagem apropriada
            if not contexto_dados.get("tem_serie_mensal") and not contexto_dados.get("tem_detalhe_vendedores"):
                contexto["resposta"] = (
                    "Não encontrei dados de metas e realizados no banco de dados. "
                    "Verifique se os dados foram carregados corretamente."
                )
                contexto["confianca"] = 0.5
                contexto.update(contexto_dados)
                return contexto
            
            # Busca meses disponíveis para contexto adicional
            try:
                meses_disponiveis = query_meses_disponiveis_metas(session)
                contexto_dados["meses_disponiveis"] = meses_disponiveis
            except Exception as e:
                logger.warning(f"Erro ao buscar meses disponíveis: {str(e)}")
                meses_disponiveis = []
        
        # Atualiza contexto com dados estruturados
        contexto.update(contexto_dados)
        
        # Gera resposta usando LLM (com fallback para template)
        pergunta_original = entities.get("pergunta_original", "qual a meta")
        try:
            # Cria contexto rico para o LLM usando os dados estruturados
            contexto_llm = {
                "intent": "consulta_meta_geral",
                "mes_ano": mes_ano,
                "janela_meses": janela_meses,
            }
            
            # Se temos análise profunda, usa ela
            if contexto_dados.get("kpis"):
                contexto_llm.update({
                    "kpis": contexto_dados["kpis"],
                    "pioresVendedores": contexto_dados.get("pioresVendedores", []),
                    "melhoresVendedores": contexto_dados.get("melhoresVendedores", []),
                    "clientesCriticos": contexto_dados.get("clientesCriticos", []),
                    "limitesDados": contexto_dados.get("limitesDados", {}),
                })
            else:
                # Fallback: método antigo
                contexto_llm["meses_disponiveis"] = contexto_dados.get("meses_disponiveis", [])[-12:] if contexto_dados.get("meses_disponiveis") else []
                
                # Adiciona série mensal (meta x realizado por mês)
                if contexto_dados.get("tem_serie_mensal"):
                    contexto_llm["serie_mensal"] = contexto_dados["serie_mensal"]
                    # Calcula totais agregados da série
                    if contexto_dados["serie_mensal"]:
                        total_meta_serie = sum(m.get("meta", 0) for m in contexto_dados["serie_mensal"])
                        total_realizado_serie = sum(m.get("realizado", 0) for m in contexto_dados["serie_mensal"])
                        perc_atingido_serie = (total_realizado_serie / total_meta_serie * 100) if total_meta_serie > 0 else 0
                        contexto_llm["total_meta_serie"] = total_meta_serie
                        contexto_llm["total_realizado_serie"] = total_realizado_serie
                        contexto_llm["perc_atingido_serie"] = perc_atingido_serie
                
                # Adiciona detalhe por vendedor (se disponível)
                if contexto_dados.get("tem_detalhe_vendedores"):
                    detalhe = contexto_dados["detalhe_vendedores_mes"]
                    contexto_llm["detalhe_vendedores"] = {
                        "mes_ano": detalhe["mes_ano"],
                        "vendedores": detalhe["vendedores"][:15],  # Top 15 vendedores
                        "total_vendedores": len(detalhe["vendedores"]),
                    }
                    # Calcula totais do mês específico
                    if detalhe["vendedores"]:
                        total_meta_mes = sum(v.get("meta", 0) for v in detalhe["vendedores"])
                        total_realizado_mes = sum(v.get("realizado", 0) for v in detalhe["vendedores"])
                        perc_atingido_mes = (total_realizado_mes / total_meta_mes * 100) if total_meta_mes > 0 else 0
                        contexto_llm["total_meta_mes"] = total_meta_mes
                        contexto_llm["total_realizado_mes"] = total_realizado_mes
                        contexto_llm["perc_atingido_mes"] = perc_atingido_mes
            
            # Adiciona observação se houver
            if contexto_dados.get("observacao"):
                contexto_llm["observacao"] = contexto_dados["observacao"]
            
            # Adiciona flags de disponibilidade
            contexto_llm["tem_serie_mensal"] = contexto_dados.get("tem_serie_mensal", False)
            contexto_llm["tem_detalhe_vendedores"] = contexto_dados.get("tem_detalhe_vendedores", False)
            
            # Adiciona contexto de memória se disponível
            if contexto_memoria and contexto_memoria.get("interacoes_aprovadas"):
                contexto_llm["memoria_referencias"] = {
                    "titulo": "Perguntas semelhantes anteriores e respostas aprovadas:",
                    "interacoes": contexto_memoria["interacoes_aprovadas"]
                }
            
            # Usa função especializada para consultas de meta
            resposta, confianca_calculada = gerar_resposta_consulta_meta(
                pergunta=pergunta_original,
                contexto=contexto_llm
            )
            contexto["resposta"] = resposta
            contexto["confianca"] = confianca_calculada
        except Exception as e:
            logger.warning(f"Erro ao gerar resposta com LLM, usando template: {str(e)}")
            # Fallback para template usando os dados estruturados
            resposta = self._gerar_resposta_meta_template(contexto_dados)
            contexto["resposta"] = resposta
            contexto["confianca"] = 0.8
        
        return contexto
    
    def _handle_vendedores_performance(
        self,
        intent: IntentType,
        entities: Dict[str, Any],
        session: Session,
        contexto_memoria: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Manipula consultas sobre performance de vendedores (piores desempenhos).
        
        Suporta perguntas como:
        - "quais foram os vendedores que mais geraram impacto negativo no realizado do mês de agosto 2025?"
        - "quais foram os vendedores venderam menos no mês de agosto 2025?"
        
        Args:
            intent: Intenção detectada (CONSULTA_VENDEDORES_PERFORMANCE)
            entities: Entidades extraídas (mes_ano, etc.)
            session: Sessão SQLAlchemy
            contexto_memoria: Contexto de memória de interações anteriores
            
        Returns:
            dict: Contexto com dados de vendedores e resposta formatada
        """
        logger.info(f"Processando consulta de performance de vendedores: entities={entities}")
        
        # Texto original da pergunta
        pergunta_original = entities.get("pergunta_original", "")
        if not pergunta_original:
            # Tenta pegar do contexto de processamento se disponível
            pergunta_original = entities.get("pergunta", "")
        
        logger.info(f"[_handle_vendedores_performance] pergunta_original='{pergunta_original}' (tamanho={len(pergunta_original) if pergunta_original else 0})")
        
        # 1) Tentar extrair MES/ANO EXPLÍCITO da pergunta (agosto 2025, etc.)
        mes_ano_solicitado = extrair_mes_ano_explicito(pergunta_original) if pergunta_original else None
        logger.info(f"[_handle_vendedores_performance] mes_ano_solicitado extraído={mes_ano_solicitado}")
        
        # 2) Se não encontrar nada explícito, usa o que o parser geral colocou
        if not mes_ano_solicitado:
            mes_ano_solicitado = entities.get("mes_ano")
            logger.info(f"[_handle_vendedores_performance] mes_ano_solicitado do entities.get('mes_ano')={mes_ano_solicitado}")
        
        contexto_dados = {
            "mes_ano_solicitado": mes_ano_solicitado,
        }
        
        logger.info(f"[_handle_vendedores_performance] Verificando periodo_tem_dados para {mes_ano_solicitado}")
        
        # 3) Só buscamos dados se EXISTIR dado para esse período
        if mes_ano_solicitado and periodo_tem_dados(session, mes_ano_solicitado):
            logger.info(f"[_handle_vendedores_performance] periodo_tem_dados retornou True para {mes_ano_solicitado}")
            mes_ano_analise = mes_ano_solicitado
            
            try:
                piores_meta = query_piores_vendedores_por_meta(
                    session, mes_ano_analise, top_n=10
                )
                menores_venda = query_vendedores_menor_venda(
                    session, mes_ano_analise, limite=10
                )
                
                contexto_dados["mes_ano_analise"] = mes_ano_analise
                contexto_dados["tem_dados"] = True
                contexto_dados["piores_meta"] = piores_meta
                contexto_dados["menores_venda"] = menores_venda
                
            except Exception as e:
                logger.error(f"Erro ao buscar dados de performance dos vendedores: {str(e)}")
                contexto = {
                    "intent": intent.value,
                    "entities": entities,
                    "erro": str(e),
                    "resposta": f"Desculpe, ocorreu um erro ao buscar dados de performance dos vendedores: {str(e)}",
                    "confianca": 0.3
                }
                return contexto
        else:
            # Sem dados para o período pedido → NÃO FAZEMOS fallback para outro mês
            contexto_dados["mes_ano_analise"] = None
            contexto_dados["tem_dados"] = False
            contexto_dados["piores_meta"] = []
            contexto_dados["menores_venda"] = []
        
        # Gera resposta usando função especializada
        try:
            from src.llm_integration import gerar_resposta_performance_vendedores
            
            resposta_texto, confianca = gerar_resposta_performance_vendedores(
                pergunta=pergunta_original,
                contexto=contexto_dados,
            )
            
            return {
                "resposta": resposta_texto,
                "intent": intent.value,
                "contexto": contexto_dados,
                "confianca": confianca,
            }
            
        except Exception as e:
            logger.warning(f"Erro ao gerar resposta com LLM, usando template: {str(e)}")
            # Fallback para template
            resposta = self._gerar_resposta_vendedores_performance_template(
                mes_ano=contexto_dados.get("mes_ano_analise") or contexto_dados.get("mes_ano_solicitado") or "N/A",
                vendedores_piores=contexto_dados.get("piores_meta", []),
                contexto_dados=contexto_dados
            )
            return {
                "intent": intent.value,
                "entities": entities,
                "resposta": resposta,
                "contexto": contexto_dados,
                "confianca": 0.75
            }
    
    def _gerar_resposta_vendedores_performance_template(
        self,
        mes_ano: str,
        vendedores_piores: List[Dict[str, Any]],
        contexto_dados: Dict[str, Any]
    ) -> str:
        """
        Gera resposta template para consulta de performance de vendedores (fallback).
        
        Args:
            mes_ano: Mês/ano analisado
            vendedores_piores: Lista de vendedores com pior performance
            contexto_dados: Contexto com dados agregados
            
        Returns:
            str: Resposta formatada em texto
        """
        resposta = f"## Análise de Performance de Vendedores - {mes_ano}\n\n"
        
        resposta += f"Identificados {len(vendedores_piores)} vendedores com pior desempenho no período:\n\n"
        
        # Lista top 10 piores
        for vendedor in vendedores_piores[:10]:
            nome = vendedor.get("vendedor_nome", "N/A")
            meta = vendedor.get("meta", 0)
            realizado = vendedor.get("realizado", 0)
            atingimento = vendedor.get("atingimento")
            gap = vendedor.get("gap", 0)
            posicao = vendedor.get("posicao_ranking", 0)
            
            atingimento_str = f"{atingimento:.1f}%" if atingimento is not None else "N/A"
            gap_str = f"R$ {abs(gap):,.2f} abaixo" if gap < 0 else f"R$ {gap:,.2f} acima"
            
            resposta += (
                f"{posicao}. **{nome}**\n"
                f"   - Meta: R$ {meta:,.2f}\n"
                f"   - Realizado: R$ {realizado:,.2f}\n"
                f"   - Atingimento: {atingimento_str}\n"
                f"   - Gap: {gap_str}\n\n"
            )
        
        # Resumo agregado
        total_meta = contexto_dados.get("total_meta", 0)
        total_realizado = contexto_dados.get("total_realizado", 0)
        total_gap = contexto_dados.get("total_gap", 0)
        atingimento_medio = contexto_dados.get("atingimento_medio")
        
        resposta += "## Resumo Agregado\n\n"
        resposta += f"- Total de meta: R$ {total_meta:,.2f}\n"
        resposta += f"- Total realizado: R$ {total_realizado:,.2f}\n"
        if atingimento_medio:
            resposta += f"- Atingimento médio: {atingimento_medio:.1f}%\n"
        resposta += f"- Gap total: R$ {abs(total_gap):,.2f} abaixo da meta\n"
        
        return resposta
    
    def _gerar_resposta_meta_template(self, contexto_dados: Dict[str, Any]) -> str:
        """
        Gera resposta template para consulta de meta usando dados estruturados (fallback).
        
        Args:
            contexto_dados: Dicionário com serie_mensal e detalhe_vendedores_mes
            
        Returns:
            str: Resposta formatada em texto
        """
        resposta_parts = []
        
        # Série mensal
        if contexto_dados.get("tem_serie_mensal"):
            serie = contexto_dados["serie_mensal"]
            resposta_parts.append(f"Análise de metas dos últimos {len(serie)} meses:\n")
            
            for mes_data in serie:
                mes_ano = mes_data.get("mes_ano", "N/A")
                meta = mes_data.get("meta", 0)
                realizado = mes_data.get("realizado", 0)
                atingimento = mes_data.get("atingimento")
                
                atingimento_str = f"{atingimento:.1f}%" if atingimento is not None else "N/A"
                resposta_parts.append(
                    f"- {mes_ano}: Meta R$ {meta:,.2f}, Realizado R$ {realizado:,.2f} "
                    f"({atingimento_str} de atingimento)"
                )
        
        # Detalhe por vendedor
        if contexto_dados.get("tem_detalhe_vendedores"):
            detalhe = contexto_dados["detalhe_vendedores_mes"]
            mes_ano = detalhe.get("mes_ano", "N/A")
            vendedores = detalhe.get("vendedores", [])
            
            resposta_parts.append(f"\nDetalhamento por vendedor em {mes_ano}:\n")
            
            # Mostra top 10 e piores 5
            top_vendedores = [v for v in vendedores if v.get("atingimento", 0) >= 100][:10]
            piores_vendedores = [v for v in vendedores if v.get("atingimento", 0) < 100][:5]
            
            if top_vendedores:
                resposta_parts.append("Top vendedores que bateram meta:")
                for v in top_vendedores:
                    nome = v.get("vendedor_nome", "N/A")
                    atingimento = v.get("atingimento", 0)
                    resposta_parts.append(f"- {nome}: {atingimento:.1f}% de atingimento")
            
            if piores_vendedores:
                resposta_parts.append("\nVendedores abaixo da meta (atenção):")
                for v in piores_vendedores:
                    nome = v.get("vendedor_nome", "N/A")
                    atingimento = v.get("atingimento", 0)
                    resposta_parts.append(f"- {nome}: {atingimento:.1f}% de atingimento")
        
        if not resposta_parts:
            return "Não encontrei dados suficientes para gerar uma resposta."
        
        return "\n".join(resposta_parts)
    
    def _handle_meta_ultimos_meses(
        self,
        session: Session,
        n_meses: int,
        entities: Dict[str, Any],
        contexto_memoria: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Manipula consultas de meta dos últimos N meses.
        
        Args:
            session: Sessão SQLAlchemy
            n_meses: Número de meses para analisar (pode vir de entities["janela_meses"] ou entities["n_meses"])
            entities: Entidades extraídas
            contexto_memoria: Contexto de memória de interações anteriores
            
        Returns:
            dict: Contexto com dados de meta e resposta formatada
        """
        logger.info(f"Processando consulta de meta dos últimos {n_meses} meses")
        
        from src.analysis.metas import metas_resumo_ultimos_meses
        
        try:
            # Chama função de análise
            resultado = metas_resumo_ultimos_meses(
                session=session,
                n_meses=n_meses,
                nivel="empresa",  # Por enquanto, nível empresa
            )
            
            contexto = {
                "intent": IntentType.CONSULTA_META.value,
                "entities": entities,
                "tipo": "metas_resumo_ultimos_meses",
                "data_base": resultado.get("data_base"),
                "n_meses": resultado.get("n_meses"),
                "nivel": resultado.get("nivel"),
                "meses": resultado.get("meses", []),
            }
            
            meses_disponiveis = len(contexto["meses"])
            
            # Verifica se há menos meses que o solicitado
            if meses_disponiveis < n_meses:
                if meses_disponiveis == 0:
                    contexto["resposta"] = (
                        f"Não foram encontrados dados de metas e realizados no banco de dados."
                    )
                    contexto["confianca"] = 0.5
                    return contexto
                
                # Determina primeiro e último mês disponíveis
                meses = contexto["meses"]
                primeiro_mes = meses[0]["mes_ano"] if meses else "N/A"
                ultimo_mes = meses[-1]["mes_ano"] if meses else "N/A"
                
                observacao = (
                    f"Nota: Encontrei dados de metas e realizados para apenas {meses_disponiveis} meses "
                    f"(de {primeiro_mes} a {ultimo_mes}). "
                )
                contexto["observacao_meses"] = observacao
            else:
                contexto["observacao_meses"] = ""
            
            # Monta contexto numérico para LLM
            contexto_llm = {
                "tipo": "metas_resumo_ultimos_meses",
                "data_base": contexto["data_base"],
                "n_meses_solicitados": n_meses,
                "n_meses_disponiveis": meses_disponiveis,
                "meses": contexto["meses"],
            }
            
            # Adiciona observação se houver menos meses
            if contexto.get("observacao_meses"):
                contexto_llm["observacao"] = contexto["observacao_meses"]
            
            # Adiciona contexto de memória se disponível
            if contexto_memoria and contexto_memoria.get("interacoes_aprovadas"):
                contexto_llm["memoria_referencias"] = {
                    "titulo": "Perguntas semelhantes anteriores e respostas aprovadas:",
                    "interacoes": contexto_memoria["interacoes_aprovadas"]
                }
            
            # Gera resposta usando LLM
            pergunta_original = entities.get("pergunta_original", f"metas dos últimos {n_meses} meses")
            try:
                resposta = gerar_resposta_llm(contexto_llm, pergunta_original)
                
                # Adiciona observação se necessário
                if contexto.get("observacao_meses"):
                    resposta = contexto["observacao_meses"] + resposta
                
                contexto["resposta"] = resposta
                contexto["confianca"] = 0.9
            except Exception as e:
                logger.warning(f"Erro ao gerar resposta com LLM, usando template: {str(e)}")
                # Fallback para resposta template
                resposta = self._gerar_resposta_meta_ultimos_meses_template(
                    meses=contexto["meses"],
                    n_meses_solicitados=n_meses,
                    meses_disponiveis=meses_disponiveis,
                    observacao=contexto.get("observacao_meses", "")
                )
                contexto["resposta"] = resposta
                contexto["confianca"] = 0.85
            
            return contexto
            
        except Exception as e:
            logger.error(f"Erro ao processar metas dos últimos meses: {str(e)}")
            return {
                "intent": IntentType.CONSULTA_META.value,
                "entities": entities,
                "erro": str(e),
                "resposta": f"Desculpe, ocorreu um erro ao processar a consulta de metas dos últimos {n_meses} meses: {str(e)}",
                "confianca": 0.3
            }
    
    def _gerar_resposta_meta_ultimos_meses_template(
        self,
        meses: List[Dict[str, Any]],
        n_meses_solicitados: int,
        meses_disponiveis: int,
        observacao: str = ""
    ) -> str:
        """
        Gera resposta template para consulta de metas dos últimos meses (fallback).
        """
        if not meses:
            return "Não foram encontrados dados de metas e realizados no banco de dados."
        
        resposta = observacao
        
        resposta += f"Análise de metas e realizados dos últimos {meses_disponiveis} meses:\n\n"
        
        for mes_data in meses:
            mes_ano = mes_data.get("mes_ano", "N/A")
            valor_meta = mes_data.get("valor_meta", 0.0)
            valor_faturado = mes_data.get("valor_faturado", 0.0)
            perc_atingido = mes_data.get("percentual_atingido_valor", 0.0)
            
            resposta += (
                f"**{mes_ano}:**\n"
                f"  - Meta: R$ {valor_meta:,.2f}\n"
                f"  - Realizado: R$ {valor_faturado:,.2f}\n"
                f"  - Atingimento: {perc_atingido:.1f}%\n\n"
            )
        
        # Resumo geral
        total_meta = sum(m.get("valor_meta", 0.0) for m in meses)
        total_realizado = sum(m.get("valor_faturado", 0.0) for m in meses)
        perc_medio = sum(m.get("percentual_atingido_valor", 0.0) for m in meses) / len(meses) if meses else 0.0
        
        resposta += (
            f"\n**Resumo geral ({meses_disponiveis} meses):**\n"
            f"  - Meta total: R$ {total_meta:,.2f}\n"
            f"  - Realizado total: R$ {total_realizado:,.2f}\n"
            f"  - Atingimento médio: {perc_medio:.1f}%\n"
        )
        
        return resposta


# Instância singleton do serviço
_agent_service: Optional[AgentService] = None


def get_agent_service() -> AgentService:
    """
    Retorna instância do serviço do agente (singleton).
    
    Returns:
        AgentService: Instância do serviço
    """
    global _agent_service
    
    if _agent_service is None:
        _agent_service = AgentService()
    
    return _agent_service

