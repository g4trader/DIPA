"""
Conexão com o Data Warehouse.

Este módulo gerencia a conexão com o banco de dados (PostgreSQL ou SQLite).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from typing import Optional
import logging
import os

from src.config import config

logger = logging.getLogger(__name__)

# Base para modelos SQLAlchemy
Base = declarative_base()

# Engine e sessão globais
engine: Optional[object] = None
SessionLocal: Optional[sessionmaker] = None


def get_db_engine():
    """
    Retorna ou cria o engine SQLAlchemy.
    
    Returns:
        Engine: Engine SQLAlchemy configurado
    """
    global engine
    
    if engine is not None:
        return engine
    
    connection_string = config.database.connection_string
    
    # Configurações específicas por tipo de banco
    if config.database.db_type == "postgresql":
        engine_kwargs = {
            "pool_pre_ping": True,
            "pool_size": 5,
            "max_overflow": 10,
            "echo": config.debug,
        }
    else:  # SQLite
        engine_kwargs = {
            "poolclass": NullPool,
            "connect_args": {"check_same_thread": False},
            "echo": config.debug,
        }
    
    engine = create_engine(connection_string, **engine_kwargs)
    
    logger.info(
        f"Engine SQLAlchemy criado para {config.database.db_type}"
    )
    
    return engine


def init_db(create_tables_if_not_exists: bool = False):
    """
    Inicializa a conexão com o banco de dados.
    
    Args:
        create_tables_if_not_exists: Se True, cria as tabelas automaticamente
    """
    global engine, SessionLocal
    
    # Garante que o SQLite está disponível (baixa do GCS se necessário)
    # Isso deve acontecer ANTES de criar o engine para evitar erros de arquivo não encontrado
    if config.database.db_type == "sqlite":
        try:
            from src.dw.bootstrap_dw import ensure_sqlite_dw_available
            ensure_sqlite_dw_available()
        except ImportError as e:
            # Se o módulo não existir ou google-cloud-storage não estiver instalado
            logger.warning(f"[init_db] Bootstrap DW não disponível: {e}")
            if os.getenv("ENV") == "production":
                logger.error("[init_db] Em produção, bootstrap DW é obrigatório")
                raise
        except Exception as e:
            logger.error(f"[init_db] Erro crítico ao garantir SQLite disponível: {e}")
            # Em produção, isso deve bloquear a inicialização
            # Em desenvolvimento, pode ser apenas um aviso
            if os.getenv("ENV") == "production":
                raise RuntimeError(f"Falha ao carregar DW SQLite: {e}") from e
            else:
                logger.warning(f"[init_db] Aviso: SQLite não disponível, mas continuando (modo dev)")
    
    engine = get_db_engine()
    
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )
    
    logger.info("Banco de dados inicializado")
    
    # Se solicitado, cria as tabelas automaticamente
    if create_tables_if_not_exists:
        # Importa todos os modelos para garantir que estejam registrados
        import src.dw.models  # noqa: F401
        import src.dw.models_analytics  # noqa: F401
        import src.dw.models_agent  # noqa: F401
        
        # Cria as tabelas
        Base.metadata.create_all(bind=engine)
        logger.info("Tabelas criadas automaticamente (se não existirem)")


def get_db_session():
    """
    Retorna uma sessão de banco de dados.
    
    Yields:
        Session: Sessão SQLAlchemy
    """
    if SessionLocal is None:
        init_db()
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """
    Cria todas as tabelas definidas nos modelos.
    
    Deve ser usado apenas em desenvolvimento. Para produção,
    use migrações Alembic.
    
    Nota: Os modelos são importados aqui para evitar importação circular,
    já que os modelos também importam o Base de connection.
    """
    if engine is None:
        init_db()
    
    # Importa todos os modelos para que sejam registrados no Base.metadata
    # Isso precisa ser feito depois que o Base já foi definido
    # para evitar importação circular
    import src.dw.models  # noqa: F401
    import src.dw.models_analytics  # noqa: F401
    
    # Cria as tabelas
    Base.metadata.create_all(bind=engine)
    
    logger.info("Tabelas criadas com sucesso")


def drop_tables():
    """
    Remove todas as tabelas do banco de dados.
    
    ATENÇÃO: Use apenas em desenvolvimento!
    
    Nota: Os modelos são importados aqui para evitar importação circular,
    já que os modelos também importam o Base de connection.
    """
    if engine is None:
        init_db()
    
    # Importa todos os modelos para que sejam registrados no Base.metadata
    # Isso precisa ser feito depois que o Base já foi definido
    # para evitar importação circular
    import src.dw.models  # noqa: F401
    import src.dw.models_analytics  # noqa: F401
    
    # Remove as tabelas
    Base.metadata.drop_all(bind=engine)
    
    logger.warning("Todas as tabelas foram removidas")

