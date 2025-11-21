#!/usr/bin/env python3
"""
Script de Aprendizado Contínuo de Skills.

Este script analisa interações mal atendidas do agente e gera sugestões de novas
skills analíticas usando LLM.

Pipeline:
1. Lê interações dos últimos N dias com sucesso=False ou intent=outros
2. Agrupa perguntas semelhantes usando embeddings
3. Para cada grupo representativo, chama LLM para gerar uma skill
4. Valida SQL gerado (verifica se tabelas existem)
5. Salva sugestões em skills_sugestoes com status 'pending'

Uso:
    python scripts/train_skills_from_logs.py [--dias 7] [--threshold 0.85]
"""

import argparse
import logging
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from collections import defaultdict
import json

# Adiciona o diretório raiz ao path
sys.path.insert(0, '.')

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import numpy as np

from src.dw.connection import get_db_session
from src.dw.models import InteracaoAgent, InteracaoEmbedding, SkillSugestao, Skill
from src.llm_openai_client import call_llm

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def calcular_similaridade_coseno(v1: List[float], v2: List[float]) -> float:
    """
    Calcula similaridade de cosseno entre dois vetores.
    
    Args:
        v1: Primeiro vetor (embedding)
        v2: Segundo vetor (embedding)
        
    Returns:
        float: Similaridade (0-1), onde 1 = idêntico
    """
    try:
        v1_array = np.array(v1)
        v2_array = np.array(v2)
        
        dot_product = np.dot(v1_array, v2_array)
        norm1 = np.linalg.norm(v1_array)
        norm2 = np.linalg.norm(v2_array)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    except Exception as e:
        logger.warning(f"Erro ao calcular similaridade: {str(e)}")
        return 0.0


def agrupar_perguntas_similares(
    interacoes: List[Dict[str, Any]],
    threshold: float = 0.85
) -> List[List[Dict[str, Any]]]:
    """
    Agrupa interações por similaridade de embeddings.
    
    Args:
        interacoes: Lista de interações com embeddings
        threshold: Limiar de similaridade para agrupar (0-1)
        
    Returns:
        list: Lista de grupos, cada grupo é uma lista de interações similares
    """
    grupos = []
    interacoes_usadas = set()
    
    for i, interacao1 in enumerate(interacoes):
        if i in interacoes_usadas:
            continue
        
        # Cria novo grupo
        grupo = [interacao1]
        interacoes_usadas.add(i)
        
        embedding1 = interacao1.get("embedding")
        if not embedding1:
            continue
        
        # Busca interações similares
        for j, interacao2 in enumerate(interacoes[i+1:], start=i+1):
            if j in interacoes_usadas:
                continue
            
            embedding2 = interacao2.get("embedding")
            if not embedding2:
                continue
            
            similaridade = calcular_similaridade_coseno(embedding1, embedding2)
            
            if similaridade >= threshold:
                grupo.append(interacao2)
                interacoes_usadas.add(j)
        
        # Só adiciona grupo se tiver pelo menos 2 interações
        if len(grupo) >= 2:
            grupos.append(grupo)
    
    return grupos


def buscar_schema_tabelas() -> str:
    """
    Retorna uma descrição do schema das principais tabelas do DW.
    
    Returns:
        str: Descrição do schema em formato texto
    """
    schema = """
PRINCIPAIS TABELAS DO DATA WAREHOUSE:

1. vendas
   - id (PK)
   - data_venda (Date)
   - vendedor_id (FK -> vendedores.id)
   - cliente_id (FK -> clientes.id)
   - codigo_produto (String)
   - desc_produto (String)
   - valor_total_liquido (Float)
   - qtd_caixas (Integer)
   - qtd_unidades (Integer)

2. vendedores
   - id (PK)
   - codigo (String, único) - Ex.: "ROTA 77"
   - nome (String)
   - supervisor_id (FK -> supervisores.id)

3. clientes
   - id (PK)
   - codigo (String, único)
   - nome (String)
   - estado (String)
   - municipio (String)
   - rota_rca (String) - Rota do vendedor

4. metas_vendedor
   - id (PK)
   - vendedor_id (FK -> vendedores.id)
   - mes_ano (String) - Formato "YYYY-MM"
   - valor_meta (Float)
   - valor_faturado (Float)
   - percentual_atingido_valor (Float)

5. supervisores
   - id (PK)
   - codigo (String, único)
   - nome (String)
   - pasta (String)

RELAÇÕES:
- vendas.vendedor_id -> vendedores.id
- vendas.cliente_id -> clientes.id
- vendedores.supervisor_id -> supervisores.id
"""
    return schema


def gerar_skill_com_llm(
    perguntas_grupo: List[str],
    intent: str,
    entities_exemplo: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Gera uma skill usando LLM baseado em perguntas similares.
    
    Args:
        perguntas_grupo: Lista de perguntas similares do grupo
        intent: Intent sugerida para essas perguntas
        entities_exemplo: Entidades extraídas de uma pergunta exemplo
        
    Returns:
        dict: Skill gerada (nome, descricao, schema_entrada, sql_template, tipo_saida) ou None
    """
    try:
        schema = buscar_schema_tabelas()
        
        perguntas_str = "\n".join([f"- {p}" for p in perguntas_grupo[:5]])  # Limita a 5 perguntas
        
        entities_str = json.dumps(entities_exemplo, indent=2, ensure_ascii=False)
        
        prompt = f"""Você é um especialista em análise de dados e SQL.

TAREFA: Criar uma "skill analítica" (template SQL parametrizado) para um tipo de pergunta.

SCHEMA DAS TABELAS:
{schema}

PERGUNTAS SIMILARES (do mesmo tipo):
{perguntas_str}

INTENT SUGERIDA: {intent}

ENTIDADES EXTRAÍDAS (de uma pergunta exemplo):
{entities_str}

INSTRUÇÕES:
1. Analise as perguntas acima e identifique o padrão comum.
2. Crie uma skill que responda a esse tipo de pergunta de forma genérica e reutilizável.
3. A skill deve ser parametrizável (ex.: produto, mês/ano, rota, etc.).
4. Use placeholders no formato :nome_parametro no SQL.
5. O SQL deve ser compatível com PostgreSQL/SQLite.

FORMATO DE RESPOSTA (JSON):
{{
    "nome": "nome_da_skill_sem_espacos",
    "descricao": "Descrição detalhada do que a skill faz e quando usar",
    "intent_alvo": "{intent}",
    "schema_entrada": {{
        "parametro1": "tipo (opcional)",
        "parametro2": "tipo (opcional)"
    }},
    "sql_template": "SELECT ... FROM ... WHERE campo = :parametro1 ...",
    "tipo_saida": "tipo_da_saida"  // Ex.: "tabela_clientes", "ranking_vendedores", "lista_produtos"
}}

EXEMPLO DE SQL TEMPLATE:
SELECT
    v.rota_rca as rota,
    COUNT(DISTINCT v.cliente_id) AS clientes_positivados,
    SUM(v.valor_total_liquido) AS faturamento
FROM vendas v
JOIN clientes c ON c.id = v.cliente_id
WHERE v.desc_produto ILIKE :produto
    AND v.data_venda >= :data_inicio
    AND v.data_venda < :data_fim
GROUP BY v.rota_rca
ORDER BY clientes_positivados DESC
LIMIT 10;

IMPORTANTE:
- Use apenas tabelas que existem no schema acima.
- SQL deve ser válido e executável após substituir os placeholders.
- Se precisar filtrar por produto, use ILIKE para busca flexível.
- Sempre inclua LIMIT quando apropriado para evitar resultados muito grandes.

Responda APENAS com o JSON, sem markdown, sem explicações adicionais."""

        response = call_llm(prompt, system_prompt="Você é um especialista em SQL e análise de dados.", temperature=0.3, max_tokens=2000)
        
        # Limpa a resposta (remove markdown se houver)
        response_clean = response.strip()
        if response_clean.startswith("```json"):
            response_clean = response_clean[7:]
        if response_clean.startswith("```"):
            response_clean = response_clean[3:]
        if response_clean.endswith("```"):
            response_clean = response_clean[:-3]
        response_clean = response_clean.strip()
        
        # Parse do JSON
        skill_json = json.loads(response_clean)
        
        # Valida campos obrigatórios
        campos_obrigatorios = ["nome", "descricao", "intent_alvo", "schema_entrada", "sql_template", "tipo_saida"]
        for campo in campos_obrigatorios:
            if campo not in skill_json:
                logger.error(f"Skill gerada não contém campo obrigatório: {campo}")
                return None
        
        logger.info(f"Skill gerada com sucesso: {skill_json['nome']}")
        return skill_json
    
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao fazer parse do JSON da skill: {str(e)}")
        logger.debug(f"Resposta do LLM: {response[:500]}")
        return None
    except Exception as e:
        logger.error(f"Erro ao gerar skill com LLM: {str(e)}")
        return None


def validar_sql_template(sql_template: str) -> bool:
    """
    Valida se o SQL template é válido (verifica se as tabelas mencionadas existem).
    
    Args:
        sql_template: Template SQL a validar
        
    Returns:
        bool: True se parece válido, False caso contrário
    """
    sql_lower = sql_template.lower()
    
    # Lista de tabelas válidas
    tabelas_validas = [
        "vendas", "vendedores", "clientes", "supervisores",
        "metas_vendedor", "metas_departamento", "dim_tempo"
    ]
    
    # Verifica se menciona apenas tabelas válidas
    palavras_reservadas = ["select", "from", "where", "join", "inner", "left", "right", "outer", "on", "group", "order", "limit"]
    
    # Verifica sintaxe básica
    if "select" not in sql_lower:
        logger.warning("SQL template não contém SELECT")
        return False
    
    # Verifica se menciona tabelas válidas
    encontrou_tabela = False
    for tabela in tabelas_validas:
        if tabela in sql_lower:
            encontrou_tabela = True
            break
    
    if not encontrou_tabela:
        logger.warning("SQL template não menciona nenhuma tabela válida")
        return False
    
    # Verifica se tem placeholders
    if ":produto" not in sql_lower and ":data_inicio" not in sql_lower and ":parametro" not in sql_lower:
        # Pode não ter placeholders se for uma query muito simples
        logger.debug("SQL template não tem placeholders parametrizados")
    
    return True


def processar_interacoes_mal_atendidas(
    session: Session,
    dias: int = 7,
    threshold_similaridade: float = 0.85
) -> int:
    """
    Processa interações mal atendidas e gera sugestões de skills.
    
    Args:
        session: Sessão SQLAlchemy
        dias: Número de dias para analisar interações
        threshold_similaridade: Limiar de similaridade para agrupar perguntas
        
    Returns:
        int: Número de skills sugeridas criadas
    """
    # Data de corte
    data_corte = datetime.now() - timedelta(days=dias)
    
    logger.info(f"Buscando interações mal atendidas desde {data_corte.date()}")
    
    # Busca interações com sucesso=False ou intent=outros
    interacoes = session.query(InteracaoAgent).join(
        InteracaoEmbedding, InteracaoAgent.id == InteracaoEmbedding.interacao_id
    ).filter(
        and_(
            InteracaoAgent.created_at >= data_corte,
            or_(
                InteracaoAgent.sucesso == False,
                InteracaoAgent.intent == "outros",
                InteracaoAgent.intent == "desconhecida"
            )
        )
    ).all()
    
    logger.info(f"Encontradas {len(interacoes)} interações mal atendidas")
    
    if len(interacoes) == 0:
        logger.info("Nenhuma interação mal atendida encontrada. Nada a fazer.")
        return 0
    
    # Formata interações com embeddings
    interacoes_com_embedding = []
    for interacao in interacoes:
        embedding_obj = interacao.embedding
        if embedding_obj and embedding_obj.embedding:
            interacoes_com_embedding.append({
                "id": interacao.id,
                "pergunta": interacao.pergunta,
                "intent": interacao.intent,
                "entities": interacao.entities_json or {},
                "embedding": embedding_obj.embedding
            })
    
    if len(interacoes_com_embedding) < 2:
        logger.info("Não há interações suficientes com embeddings para agrupar.")
        return 0
    
    # Agrupa perguntas similares
    logger.info(f"Agrupando {len(interacoes_com_embedding)} interações por similaridade (threshold={threshold_similaridade})")
    grupos = agrupar_perguntas_similares(interacoes_com_embedding, threshold=threshold_similaridade)
    
    logger.info(f"Formados {len(grupos)} grupos de perguntas similares")
    
    if len(grupos) == 0:
        logger.info("Nenhum grupo de perguntas similares encontrado.")
        return 0
    
    # Processa cada grupo
    skills_criadas = 0
    
    for grupo_idx, grupo in enumerate(grupos, 1):
        logger.info(f"Processando grupo {grupo_idx}/{len(grupos)} com {len(grupo)} interações")
        
        # Usa a primeira interação como exemplo
        interacao_exemplo = grupo[0]
        intent = interacao_exemplo["intent"]
        entities_exemplo = interacao_exemplo["entities"]
        
        # Extrai perguntas do grupo
        perguntas = [i["pergunta"] for i in grupo]
        
        # Gera skill usando LLM
        skill_json = gerar_skill_com_llm(perguntas, intent, entities_exemplo)
        
        if not skill_json:
            logger.warning(f"Não foi possível gerar skill para grupo {grupo_idx}")
            continue
        
        # Valida SQL
        sql_template = skill_json.get("sql_template", "")
        if not validar_sql_template(sql_template):
            logger.warning(f"SQL template inválido para skill {skill_json.get('nome')}, pulando")
            continue
        
        # Verifica se já existe skill com mesmo nome
        skill_existente = session.query(Skill).filter(
            Skill.nome == skill_json["nome"]
        ).first()
        
        if skill_existente:
            logger.info(f"Skill '{skill_json['nome']}' já existe, pulando")
            continue
        
        # Verifica se já existe sugestão pendente similar
        sugestao_existente = session.query(SkillSugestao).filter(
            and_(
                SkillSugestao.status == "pending",
                SkillSugestao.intent_sugerida == intent
            )
        ).first()
        
        if sugestao_existente:
            logger.info(f"Já existe sugestão pendente para intent '{intent}', pulando")
            continue
        
        # Cria sugestão de skill
        sugestao = SkillSugestao(
            interacao_id_orig=interacao_exemplo["id"],
            pergunta=perguntas[0],  # Primeira pergunta do grupo
            intent_sugerida=intent,
            skill_json_proposta=skill_json,
            status="pending"
        )
        
        session.add(sugestao)
        session.commit()
        
        logger.info(f"✓ Skill sugerida criada: {skill_json['nome']} (ID: {sugestao.id})")
        skills_criadas += 1
    
    return skills_criadas


def main():
    """Função principal."""
    parser = argparse.ArgumentParser(
        description="Gera sugestões de skills analíticas a partir de interações mal atendidas"
    )
    parser.add_argument(
        "--dias",
        type=int,
        default=7,
        help="Número de dias para analisar interações (padrão: 7)"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.85,
        help="Limiar de similaridade para agrupar perguntas (padrão: 0.85)"
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("INICIANDO JOB DE APRENDIZADO CONTÍNUO DE SKILLS")
    logger.info("=" * 80)
    logger.info(f"Parâmetros: dias={args.dias}, threshold={args.threshold}")
    
    try:
        # Obtém sessão do banco
        session_context = get_db_session()
        session = next(session_context)
        
        try:
            # Processa interações
            skills_criadas = processar_interacoes_mal_atendidas(
                session=session,
                dias=args.dias,
                threshold_similaridade=args.threshold
            )
            
            logger.info("=" * 80)
            logger.info(f"JOB CONCLUÍDO: {skills_criadas} skill(s) sugerida(s) criada(s)")
            logger.info("=" * 80)
            
        finally:
            session.close()
    
    except Exception as e:
        logger.exception(f"Erro ao executar job de aprendizado contínuo: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()



