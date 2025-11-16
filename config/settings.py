"""
Configurações da aplicação usando Pydantic Settings.

Centraliza todas as configurações do projeto, lendo variáveis de ambiente
e fornecendo valores padrão quando necessário.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Literal


class Settings(BaseSettings):
    """
    Configurações da aplicação.
    
    Lê variáveis de ambiente do arquivo .env ou do ambiente do sistema.
    Valores podem ser sobrescritos através de variáveis de ambiente.
    """
    
    # Environment
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        alias="ENVIRONMENT"
    )
    debug: bool = Field(default=True, alias="DEBUG")
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    
    # Database Configuration
    database_type: Literal["bigquery", "postgresql"] = Field(
        default="bigquery",
        alias="DATABASE_TYPE"
    )
    
    # BigQuery Configuration
    bigquery_project_id: str = Field(default="", alias="BIGQUERY_PROJECT_ID")
    bigquery_dataset: str = Field(default="", alias="BIGQUERY_DATASET")
    bigquery_credentials_path: str = Field(
        default="",
        alias="BIGQUERY_CREDENTIALS_PATH"
    )
    
    # PostgreSQL Configuration
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_user: str = Field(default="", alias="POSTGRES_USER")
    postgres_password: str = Field(default="", alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="dipam_ai", alias="POSTGRES_DB")
    
    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: Literal["json", "text"] = Field(
        default="json",
        alias="LOG_FORMAT"
    )
    
    # ML Configuration
    ml_model_path: str = Field(default="ml/models/", alias="ML_MODEL_PATH")
    ml_features_path: str = Field(
        default="ml/features/",
        alias="ML_FEATURES_PATH"
    )
    
    # Data Paths
    data_raw_path: str = Field(default="data/raw/", alias="DATA_RAW_PATH")
    data_processed_path: str = Field(
        default="data/processed/",
        alias="DATA_PROCESSED_PATH"
    )
    
    class Config:
        """
        Configuração do Pydantic.
        """
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        # Permite ler de .env na raiz ou em config/
        env_file = [".env", "config/.env"]


# Instância singleton das configurações
# Importar este objeto em outros módulos
settings = Settings()




