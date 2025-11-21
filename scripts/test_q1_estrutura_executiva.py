#!/usr/bin/env python3
"""
Script para validar a estrutura executiva da Q1.

Valida:
- Presença de todos os blocos obrigatórios
- Ausência de palavras proibidas
- Coerência entre faixas de dias e prioridades
- Cliente >300 dias não aparece como oportunidade
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Adiciona o diretório raiz ao path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

import logging
from src.dw.connection import init_db, get_db_session
from src.dw.queries import get_clientes_sem_compra_ha_dias
from src.agent.intent_spec import IntentSpec
from src.llm_integration_intent import gerar_resposta_executiva_com_dados_dw, _classificar_clientes_por_faixa

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Palavras proibidas
PALAVRAS_PROIBIDAS = ["criticozinho", "movimento", "blitz", "talvez", "pode ser que", "pode ser", "talvez seja"]

# Blocos obrigatórios para Q1
BLOCOS_OBRIGATORIOS = [
    "resumo_executivo",
    "diagnostico_comercial",
    "recomendacoes_estrategicas",
    "impacto_esperado"
]


def validar_estrutura_q1(resposta: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Valida a estrutura executiva da Q1.
    
    Returns:
        (bool, List[str]): (passou, lista_de_erros)
    """
    erros = []
    
    # 1. Valida presença de blocos obrigatórios
    for bloco in BLOCOS_OBRIGATORIOS:
        if bloco not in resposta:
            erros.append(f"Bloco obrigatório ausente: {bloco}")
    
    # 2. Valida ausência de palavras proibidas
    texto_completo = json.dumps(resposta, ensure_ascii=False).lower()
    palavras_encontradas = [p for p in PALAVRAS_PROIBIDAS if p in texto_completo]
    if palavras_encontradas:
        erros.append(f"Palavras proibidas encontradas: {palavras_encontradas}")
    
    # 3. Valida estrutura de recomendacoes_estrategicas
    if "recomendacoes_estrategicas" in resposta:
        recs = resposta["recomendacoes_estrategicas"]
        if not isinstance(recs, dict):
            erros.append("recomendacoes_estrategicas deve ser um dicionário")
        else:
            if "prioridade_1" not in recs:
                erros.append("recomendacoes_estrategicas deve ter 'prioridade_1'")
            if "nao_priorizar" not in recs:
                erros.append("recomendacoes_estrategicas deve ter 'nao_priorizar'")
            
            # Valida que não menciona >300 dias como oportunidade
            texto_recs = json.dumps(recs, ensure_ascii=False).lower()
            if ">300" in texto_recs or "mais de 300" in texto_recs:
                # Verifica se está mencionado como oportunidade (não apenas como "não priorizar")
                if "oportunidade" in texto_recs or "prioridade" in texto_recs:
                    # Verifica se não está na seção "nao_priorizar"
                    nao_priorizar = recs.get("nao_priorizar", "").lower()
                    if ">300" not in nao_priorizar and "mais de 300" not in nao_priorizar:
                        erros.append("Clientes >300 dias não devem aparecer como oportunidade")
    
    # 4. Valida que prioridade_1 menciona 61-120 dias
    if "recomendacoes_estrategicas" in resposta:
        recs = resposta["recomendacoes_estrategicas"]
        prioridade_1 = recs.get("prioridade_1", "").lower()
        if "61" not in prioridade_1 and "120" not in prioridade_1:
            erros.append("prioridade_1 deve mencionar faixa 61-120 dias")
    
    # 5. Valida resumo_executivo (deve existir e não estar vazio)
    if "resumo_executivo" in resposta:
        resumo = resposta["resumo_executivo"]
        if not resumo or len(resumo.strip()) < 50:
            erros.append("resumo_executivo deve ter pelo menos 50 caracteres")
        # Valida que não é muito longo (máximo 1000 caracteres)
        if len(resumo) > 1000:
            erros.append("resumo_executivo deve ser curto (máximo 1000 caracteres)")
    
    return len(erros) == 0, erros


def test_q1_estrutura_executiva():
    """Testa a estrutura executiva da Q1 com dados reais."""
    logger.info("=" * 80)
    logger.info("VALIDAÇÃO: ESTRUTURA EXECUTIVA Q1")
    logger.info("=" * 80)
    
    try:
        init_db()
        session = next(get_db_session())
        
        # Busca dados reais
        logger.info("Buscando clientes sem compra há mais de 60 dias...")
        clientes = get_clientes_sem_compra_ha_dias(session, dias=60)
        logger.info(f"✅ Encontrados {len(clientes)} clientes")
        
        if len(clientes) == 0:
            logger.warning("⚠️  Nenhum cliente encontrado. Criando dados simulados para teste...")
            # Cria dados simulados para teste
            clientes = [
                {"cliente_id": 1, "nome": "Cliente Teste 1", "dias_sem_compra": 75, "vendedor_nome": "ROTA 01", "supervisor_nome": "SUPERVISOR 1"},
                {"cliente_id": 2, "nome": "Cliente Teste 2", "dias_sem_compra": 150, "vendedor_nome": "ROTA 02", "supervisor_nome": "SUPERVISOR 2"},
                {"cliente_id": 3, "nome": "Cliente Teste 3", "dias_sem_compra": 250, "vendedor_nome": "ROTA 03", "supervisor_nome": "SUPERVISOR 3"},
                {"cliente_id": 4, "nome": "Cliente Teste 4", "dias_sem_compra": 350, "vendedor_nome": "ROTA 04", "supervisor_nome": "SUPERVISOR 4"},
                {"cliente_id": 5, "nome": "Cliente Teste 5", "dias_sem_compra": 90, "vendedor_nome": "ROTA 05", "supervisor_nome": "SUPERVISOR 5"},
            ]
        
        # Classifica por faixas
        classificacao = _classificar_clientes_por_faixa(clientes)
        logger.info(f"✅ Classificação por faixas:")
        logger.info(f"   61-120: {classificacao['faixa_61_120']}")
        logger.info(f"   121-180: {classificacao['faixa_121_180']}")
        logger.info(f"   181-300: {classificacao['faixa_181_300']}")
        logger.info(f"   >300: {classificacao['faixa_mais_300']}")
        
        # Cria IntentSpec para Q1
        intent_spec = IntentSpec(
            tipo="clientes_sem_compra",
            periodo_inicio=None,
            periodo_fim=None,
            dimensao_principal="cliente",
            filtros={"dias": 60}
        )
        
        # Prepara dados_dw
        dados_dw = {
            "status": "ok",
            "dados": clientes[:20],  # Top 20 para teste
            "tem_dados": True,
            "classificacao_faixas": classificacao
        }
        
        # Gera resposta executiva
        logger.info("Gerando resposta executiva...")
        resposta = gerar_resposta_executiva_com_dados_dw(
            pergunta="Quais clientes estão com cadastro ativo, mas sem nenhuma compra por mais de 60 dias?",
            intent_spec=intent_spec,
            dados_dw=dados_dw,
            papel="diretor"
        )
        
        logger.info("✅ Resposta gerada")
        logger.info(f"   Resumo: {len(resposta.get('resumo_executivo', ''))} chars")
        logger.info(f"   Insights: {len(resposta.get('insights', []))}")
        
        # Valida estrutura
        logger.info("\n" + "=" * 80)
        logger.info("VALIDANDO ESTRUTURA EXECUTIVA")
        logger.info("=" * 80)
        
        passou, erros = validar_estrutura_q1(resposta)
        
        if passou:
            logger.info("✅ VALIDAÇÃO PASSOU: Estrutura executiva correta")
            logger.info("\n📊 Estrutura encontrada:")
            logger.info(f"   - resumo_executivo: ✅")
            logger.info(f"   - diagnostico_comercial: {'✅' if 'diagnostico_comercial' in resposta else '❌'}")
            logger.info(f"   - recomendacoes_estrategicas: {'✅' if 'recomendacoes_estrategicas' in resposta else '❌'}")
            logger.info(f"   - impacto_esperado: {'✅' if 'impacto_esperado' in resposta else '❌'}")
            logger.info(f"   - Palavras proibidas: ✅ Nenhuma encontrada")
            logger.info(f"   - Prioridade 1 (61-120): ✅ Mencionada")
            logger.info(f"   - Clientes >300 dias: ✅ Não aparecem como oportunidade")
            sys.exit(0)
        else:
            logger.error("❌ VALIDAÇÃO FALHOU:")
            for erro in erros:
                logger.error(f"   - {erro}")
            sys.exit(1)
    
    except Exception as e:
        logger.error(f"❌ Erro na validação: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        if 'session' in locals():
            session.close()


if __name__ == "__main__":
    test_q1_estrutura_executiva()

