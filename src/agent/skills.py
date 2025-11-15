"""
Módulo de Skills Analíticas.

Skills são templates SQL reutilizáveis que representam análises específicas.
Quando o agente detecta uma pergunta compatível com uma skill, ele usa o template
SQL parametrizado para executar a query e gerar a resposta.

Este módulo fornece funções para:
- Buscar skills ativas por intent
- Preencher templates SQL com parâmetros
- Executar queries usando skills
"""

import logging
import re
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.dw.models import Skill

logger = logging.getLogger(__name__)


def buscar_skill_por_intent(session: Session, intent: str) -> Optional[Skill]:
    """
    Busca uma skill ativa que atenda uma intent específica.
    
    Args:
        session: Sessão SQLAlchemy
        intent: Intent detectada (ex.: "clientes_churn_produto")
        
    Returns:
        Skill ou None se não encontrar skill ativa
    """
    try:
        skill = session.query(Skill).filter(
            and_(
                Skill.intent_alvo == intent,
                Skill.ativo == True
            )
        ).first()
        
        if skill:
            logger.info(f"Skill encontrada: {skill.nome} para intent {intent}")
        else:
            logger.debug(f"Nenhuma skill ativa encontrada para intent {intent}")
        
        return skill
    except Exception as e:
        logger.error(f"Erro ao buscar skill por intent {intent}: {str(e)}")
        return None


def preencher_sql_template(sql_template: str, params: Dict[str, Any]) -> str:
    """
    Preenche um template SQL com parâmetros.
    
    O template usa placeholders no formato :nome_parametro.
    Exemplo:
        sql_template = "SELECT * FROM vendas WHERE produto ILIKE :produto AND data_venda >= :data_inicio"
        params = {"produto": "Nissin", "data_inicio": "2025-01-01"}
        Resultado: "SELECT * FROM vendas WHERE produto ILIKE 'Nissin' AND data_venda >= '2025-01-01'"
    
    Args:
        sql_template: Template SQL com placeholders :parametro
        params: Dicionário com valores dos parâmetros
        
    Returns:
        str: SQL preenchido com os valores
    """
    sql = sql_template
    
    for param_name, param_value in params.items():
        placeholder = f":{param_name}"
        
        if placeholder in sql:
            # Formata o valor conforme o tipo
            if param_value is None:
                sql_value = "NULL"
            elif isinstance(param_value, str):
                # Escapa aspas simples e adiciona aspas
                escaped_value = param_value.replace("'", "''")
                sql_value = f"'{escaped_value}'"
            elif isinstance(param_value, (int, float)):
                sql_value = str(param_value)
            elif isinstance(param_value, datetime):
                sql_value = f"'{param_value.isoformat()}'"
            else:
                # Converte para string
                sql_value = f"'{str(param_value)}'"
            
            # Substitui todas as ocorrências do placeholder
            sql = sql.replace(placeholder, sql_value)
    
    return sql


def extrair_params_de_entities(entities: Dict[str, Any], schema_entrada: Dict[str, str]) -> Dict[str, Any]:
    """
    Extrai parâmetros das entidades baseado no schema de entrada da skill.
    
    Args:
        entities: Entidades extraídas da pergunta (ex.: {"produto": "Nissin", "mes_ano": "2025-08"})
        schema_entrada: Schema de entrada da skill (ex.: {"produto": "string", "mes_ano": "string (opcional)"})
        
    Returns:
        dict: Dicionário com parâmetros prontos para usar no template SQL
    """
    params = {}
    
    for param_name, param_type_desc in schema_entrada.items():
        # Remove sufixo "(opcional)" se houver
        param_type = param_type_desc.replace(" (opcional)", "").strip()
        
        # Busca o valor nas entidades
        if param_name in entities:
            value = entities[param_name]
            if value is not None:
                params[param_name] = value
        elif "mes_ano" in param_name and "mes_ano" in entities:
            # Compatibilidade: mes_ano pode ser usado como data_inicio/data_fim
            mes_ano = entities.get("mes_ano")
            if mes_ano:
                params[param_name] = mes_ano
        
        # Se não encontrou e é obrigatório, usa defaults
        if param_name not in params:
            if "opcional" not in param_type_desc.lower():
                # Parâmetro obrigatório não encontrado - tenta default
                if param_name == "data_inicio" or param_name == "data_fim":
                    # Default: últimos 90 dias
                    if param_name == "data_inicio":
                        params[param_name] = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
                    else:
                        params[param_name] = datetime.now().strftime("%Y-%m-%d")
    
    # Processa datas se necessário
    if "mes_ano" in entities and "data_inicio" not in params:
        mes_ano = entities.get("mes_ano")
        if mes_ano:
            try:
                # Converte mes_ano (YYYY-MM) para data_inicio (primeiro dia do mês)
                ano, mes = mes_ano.split("-")
                data_inicio = datetime(int(ano), int(mes), 1)
                # data_fim é o último dia do mês
                if int(mes) == 12:
                    data_fim = datetime(int(ano) + 1, 1, 1) - timedelta(days=1)
                else:
                    data_fim = datetime(int(ano), int(mes) + 1, 1) - timedelta(days=1)
                
                params["data_inicio"] = data_inicio.strftime("%Y-%m-%d")
                params["data_fim"] = data_fim.strftime("%Y-%m-%d")
            except Exception as e:
                logger.warning(f"Erro ao processar mes_ano {mes_ano}: {str(e)}")
    
    return params


def executar_skill(session: Session, skill: Skill, entities: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Executa uma skill com as entidades extraídas da pergunta.
    
    Args:
        session: Sessão SQLAlchemy
        skill: Skill a ser executada
        entities: Entidades extraídas da pergunta
        
    Returns:
        dict: Resultado da query com dados estruturados ou None em caso de erro
    """
    try:
        # Extrai parâmetros do schema
        schema_entrada = skill.schema_entrada
        if isinstance(schema_entrada, str):
            import json
            schema_entrada = json.loads(schema_entrada)
        
        params = extrair_params_de_entities(entities, schema_entrada)
        
        # Preenche template SQL
        sql = preencher_sql_template(skill.sql_template, params)
        
        logger.info(f"Executando skill {skill.nome} com SQL: {sql[:200]}...")
        
        # Executa query usando text() do SQLAlchemy para SQL raw
        from sqlalchemy import text
        result = session.execute(text(sql))
        
        # Formata resultado conforme tipo de saída
        rows = []
        for row in result:
            if hasattr(row, '_mapping'):
                rows.append(dict(row._mapping))
            elif hasattr(row, '_asdict'):
                rows.append(row._asdict())
            else:
                # Tenta converter para dict
                try:
                    rows.append(dict(row))
                except:
                    # Fallback: converte para lista e depois dict
                    row_dict = {}
                    for idx, value in enumerate(row):
                        row_dict[f"col_{idx}"] = value
                    rows.append(row_dict)
        
        return {
            "tipo": skill.tipo_saida,
            "total": len(rows),
            "dados": rows
        }
    
    except Exception as e:
        logger.error(f"Erro ao executar skill {skill.nome}: {str(e)}")
        return None

