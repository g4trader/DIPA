"""
Bootstrap de Schema de Aplicação.

Este módulo garante que as estruturas de aplicação (não-DW) existam no banco,
sem alterar tabelas de fatos/dimensões do cliente.

Estruturas garantidas:
- Tabela behavior_rules
- Coluna intent_prevista em interacoes_agent
"""

from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError
import logging

logger = logging.getLogger(__name__)


def ensure_application_schema(engine):
    """
    Garante que as estruturas de aplicação existam no DW:
    - Tabela behavior_rules
    - Coluna intent_prevista em interacoes_agent
    
    Sem alterar nenhuma tabela de fatos/dimensões do cliente.
    
    Args:
        engine: Engine SQLAlchemy do banco de dados
    """
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    # 1) Criar tabela behavior_rules se não existir
    if "behavior_rules" not in existing_tables:
        logger.info("[BOOTSTRAP-SCHEMA] Criando tabela behavior_rules...")
        try:
            # Importa o modelo para ter acesso à definição da tabela
            from src.dw.models import BehaviorRule
            
            # Cria apenas a tabela behavior_rules
            BehaviorRule.__table__.create(bind=engine, checkfirst=True)
            logger.info("[BOOTSTRAP-SCHEMA] ✅ Tabela behavior_rules criada com sucesso")
        except Exception as e:
            logger.error(f"[BOOTSTRAP-SCHEMA] ❌ Erro ao criar tabela behavior_rules: {e}")
            # Não faz raise - apenas loga o erro para não quebrar a inicialização
    else:
        logger.debug("[BOOTSTRAP-SCHEMA] Tabela behavior_rules já existe")
    
    # 2) Garantir coluna intent_prevista em interacoes_agent
    if "interacoes_agent" in existing_tables:
        try:
            columns = [col["name"] for col in inspector.get_columns("interacoes_agent")]
            
            if "intent_prevista" not in columns:
                logger.info("[BOOTSTRAP-SCHEMA] Adicionando coluna intent_prevista em interacoes_agent...")
                
                # SQLite permite ADD COLUMN simples
                with engine.connect() as conn:
                    # SQLite não suporta transações DDL explícitas, mas usamos begin() para compatibilidade
                    conn.execute(
                        text("ALTER TABLE interacoes_agent ADD COLUMN intent_prevista TEXT")
                    )
                    conn.commit()
                
                logger.info("[BOOTSTRAP-SCHEMA] ✅ Coluna intent_prevista adicionada com sucesso")
            else:
                logger.debug("[BOOTSTRAP-SCHEMA] Coluna intent_prevista já existe em interacoes_agent")
        except OperationalError as e:
            # Se a coluna já existir (erro de SQLite), apenas loga
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                logger.debug("[BOOTSTRAP-SCHEMA] Coluna intent_prevista já existe (erro esperado ignorado)")
            else:
                logger.warning(f"[BOOTSTRAP-SCHEMA] ⚠️  Erro ao adicionar coluna intent_prevista: {e}")
                # Não faz raise - apenas loga o erro
        except Exception as e:
            logger.warning(f"[BOOTSTRAP-SCHEMA] ⚠️  Erro inesperado ao verificar coluna intent_prevista: {e}")
            # Não faz raise - apenas loga o erro
    else:
        logger.debug("[BOOTSTRAP-SCHEMA] Tabela interacoes_agent não existe (será criada pelo init_db se necessário)")
    
    logger.info("[BOOTSTRAP-SCHEMA] ✅ Bootstrap de schema de aplicação concluído")

