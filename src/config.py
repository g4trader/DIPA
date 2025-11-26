"""
Configurações centralizadas do projeto.

Este módulo centraliza todas as configurações do projeto, incluindo:
- Paths de dados
- Configurações de banco de dados
- Configurações de ML
- Configurações de logging
"""

import os
from pathlib import Path
from typing import Literal
from dataclasses import dataclass
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# ✅ Q1 EXECUTION MODE: Removido daqui - agora está na classe Config
# Mantido apenas para referência histórica


@dataclass
class DatabaseConfig:
    """
    Configurações de banco de dados.
    
    Suporta PostgreSQL (via Docker/Cloud SQL) ou SQLite para desenvolvimento/POC.
    
    Ambiente de POC (SQLite):
    - Usa SQLite com arquivo local para desenvolvimento e Cloud Run
    - Arquivo padrão local: `data/dipam_dw.db` (relativo à raiz do projeto)
    - Arquivo padrão Cloud Run: `/app/data/dipam_dw.db` (absoluto no container)
    
    Migração futura para PostgreSQL/Cloud SQL:
    - Basta definir variáveis de ambiente: DB_TYPE=postgresql, POSTGRES_HOST, etc.
    - O código automaticamente usará PostgreSQL quando DB_TYPE=postgresql
    """
    # Tipo de banco: 'postgresql' ou 'sqlite'
    # Suporta tanto DB_TYPE quanto DATABASE_TYPE para compatibilidade
    db_type: Literal["postgresql", "sqlite"] = os.getenv(
        "DB_TYPE", os.getenv("DATABASE_TYPE", "sqlite")
    )
    
    # PostgreSQL - Configurações para Cloud SQL ou PostgreSQL local
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_user: str = os.getenv("POSTGRES_USER", "dipam_user")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "dipam_password")
    postgres_db: str = os.getenv("POSTGRES_DB", "dipam_dw")
    
    # SQLite - Caminho do arquivo SQLite
    # Desenvolvimento local: "data/dipam_dw.db" (relativo à raiz do projeto)
    # Cloud Run: usar caminho relativo "data/dipam_dw.db" ou absoluto "/app/data/dipam_dw.db"
    # IMPORTANTE: Se usar caminho absoluto, o diretório deve existir ou será criado
    # Pode ser sobrescrito via variável de ambiente SQLITE_PATH
    @property
    def sqlite_path(self) -> str:
        """
        Retorna o caminho do arquivo SQLite, criando o diretório se necessário.
        
        Garante que o diretório pai existe antes de usar o caminho.
        Isso evita erros de "unable to open database file" no Cloud Run.
        
        Para caminhos relativos, usa o diretório raiz do projeto como base.
        Para caminhos absolutos, cria o diretório se não existir.
        """
        path_str = os.getenv("SQLITE_PATH", "data/dipam_dw.db")
        sqlite_path = Path(path_str)
        
        # Se o caminho é relativo, resolve em relação ao diretório raiz do projeto
        if not sqlite_path.is_absolute():
            # Raiz do projeto = 2 níveis acima de src/config.py
            project_root = Path(__file__).resolve().parent.parent
            sqlite_path = project_root / sqlite_path
        
        # Cria o diretório pai se não existir (para caminhos absolutos ou relativos)
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        
        return str(sqlite_path)
    
    # URL de conexão completa (DB_URL tem prioridade sobre connection_string)
    # Se DB_URL for definida, ela será usada diretamente, ignorando as outras configurações
    db_url: str = os.getenv("DB_URL", "")
    
    @property
    def connection_string(self) -> str:
        """
        Retorna a string de conexão com o banco de dados.
        
        Prioridade:
        1. DB_URL (se definida) - URL completa de conexão
        2. DB_TYPE + configurações específicas (postgresql ou sqlite)
        
        Returns:
            str: String de conexão formatada
        """
        # Se DB_URL foi definida explicitamente, usa ela (máxima flexibilidade)
        if self.db_url:
            return self.db_url
        
        if self.db_type == "postgresql":
            return (
                f"postgresql://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )
        else:
            # SQLite: usa 4 barras para caminho absoluto (ex: sqlite:////app/data/dipam_dw.db)
            # ou 3 barras para caminho relativo (ex: sqlite:///data/dipam_dw.db)
            # O SQLAlchemy detecta automaticamente se o caminho começa com /
            return f"sqlite:///{self.sqlite_path}"


@dataclass
class PathsConfig:
    """
    Configurações de paths do projeto.
    
    Define todos os caminhos importantes do projeto.
    """
    # Diretório raiz do projeto
    root_dir: Path = Path(__file__).parent.parent
    
    # Dados brutos (CSVs originais)
    data_raw_dir: Path = root_dir / "data_raw"
    
    # Dados processados
    data_processed_dir: Path = root_dir / "data_processed"
    
    # Data warehouse (scripts SQL, migrations)
    dw_dir: Path = root_dir / "data_warehouse"
    
    # Modelos treinados
    models_dir: Path = root_dir / "models"
    
    # Notebooks
    notebooks_dir: Path = root_dir / "notebooks"
    
    # Logs
    logs_dir: Path = root_dir / "logs"
    
    # Features
    features_dir: Path = root_dir / "features"
    
    def __post_init__(self):
        """
        Cria os diretórios se não existirem.
        """
        for path in [
            self.data_raw_dir,
            self.data_processed_dir,
            self.dw_dir,
            self.models_dir,
            self.notebooks_dir,
            self.logs_dir,
            self.features_dir,
        ]:
            path.mkdir(parents=True, exist_ok=True)


@dataclass
class MLConfig:
    """
    Configurações de Machine Learning.
    
    Define parâmetros para treinamento e avaliação de modelos.
    """
    # Random seed para reprodutibilidade
    random_seed: int = int(os.getenv("ML_RANDOM_SEED", "42"))
    
    # Test size para split de dados
    test_size: float = float(os.getenv("ML_TEST_SIZE", "0.2"))
    
    # Cross validation folds
    cv_folds: int = int(os.getenv("ML_CV_FOLDS", "5"))
    
    # Modelos
    models_dir: Path = Path(__file__).parent.parent / "models"
    
    # Features
    features_dir: Path = Path(__file__).parent.parent / "features"


@dataclass
class Config:
    """
    Configuração principal do projeto.
    
    Agrega todas as configurações em um único objeto.
    """
    # Ambiente: 'development', 'staging', 'production'
    environment: Literal["development", "staging", "production"] = os.getenv(
        "ENVIRONMENT", "development"
    )
    
    # Debug mode
    debug: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    # Log level
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # ✅ Q1 EXECUTION MODE: Configuração para modo de execução da Q1
    # "light" = sempre usa query light (LIMIT 100) - recomendado para produção
    # "full" = tenta query completa com fallback (futuro)
    q1_execution_mode: str = os.getenv("Q1_EXECUTION_MODE", "full").lower()
    
    # Configurações
    database: DatabaseConfig = None
    paths: PathsConfig = None
    ml: MLConfig = None
    
    def __post_init__(self):
        """
        Inicializa as configurações.
        """
        if self.database is None:
            self.database = DatabaseConfig()
        if self.paths is None:
            self.paths = PathsConfig()
        if self.ml is None:
            self.ml = MLConfig()


# Instância global de configuração
# Importar este objeto em outros módulos: from src.config import config
config = Config()

# ✅ Q1 EXECUTION MODE: Constante para backwards compatibility
# Permite importar como: from src.config import Q1_EXECUTION_MODE
Q1_EXECUTION_MODE = config.q1_execution_mode

# ✅ ALIAS: settings é um alias de config para padronização
# Permite importar como: from src.config import settings
settings = config


# Exemplo de uso:
# from src.config import config, settings, Q1_EXECUTION_MODE
# print(config.database.connection_string)
# print(config.paths.data_raw_dir)
# print(config.ml.random_seed)
# print(settings.q1_execution_mode)  # ou config.q1_execution_mode
# print(Q1_EXECUTION_MODE)  # constante legada



