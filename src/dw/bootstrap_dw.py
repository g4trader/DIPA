"""
Bootstrap do Data Warehouse SQLite.

Este módulo garante que o arquivo SQLite do DW esteja disponível,
baixando automaticamente do GCS se necessário.
"""

import os
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def ensure_sqlite_dw_available() -> None:
    """
    Garante que o arquivo SQLite do DW esteja disponível.
    
    Se o arquivo não existir e DIPAM_DW_GCS_URI estiver configurado,
    faz download do GCS.
    
    Raises:
        RuntimeError: Se DB_TYPE=sqlite mas o arquivo não existe e DIPAM_DW_GCS_URI não está configurado
        Exception: Se houver erro ao baixar do GCS
    """
    db_type = os.getenv("DB_TYPE", "sqlite")
    
    # Se não for SQLite, não faz nada
    if db_type != "sqlite":
        logger.debug(f"[DW-BOOTSTRAP] DB_TYPE={db_type}, pulando bootstrap SQLite")
        return
    
    sqlite_path_str = os.getenv("SQLITE_PATH", "/app/data/dipam_dw.db")
    sqlite_path = Path(sqlite_path_str)
    
    # Se o arquivo já existe, não precisa fazer nada
    if sqlite_path.exists():
        logger.info(f"[DW-BOOTSTRAP] Arquivo SQLite já existe: {sqlite_path}")
        return
    
    # Se não existe, precisa baixar do GCS
    gcs_uri = os.getenv("DIPAM_DW_GCS_URI")
    
    if not gcs_uri:
        error_msg = (
            f"DIPAM_DW_GCS_URI não configurado e SQLite não encontrado em {sqlite_path}. "
            "Configure DIPAM_DW_GCS_URI (ex.: gs://dipam-dw-prod/dipam_dw.db) ou "
            "garanta que o arquivo existe no caminho especificado."
        )
        logger.error(f"[DW-BOOTSTRAP] {error_msg}")
        raise RuntimeError(error_msg)
    
    logger.info(f"[DW-BOOTSTRAP] Arquivo SQLite não encontrado em {sqlite_path}")
    logger.info(f"[DW-BOOTSTRAP] Baixando DW SQLite de {gcs_uri} para {sqlite_path}")
    
    # Cria diretório pai se não existir
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Faz download do GCS
    try:
        _download_from_gcs(gcs_uri, sqlite_path)
        logger.info(f"[DW-BOOTSTRAP] ✅ Arquivo SQLite baixado com sucesso: {sqlite_path}")
        
        # Verifica se o arquivo foi baixado corretamente
        if not sqlite_path.exists():
            raise RuntimeError(f"Arquivo baixado mas não encontrado em {sqlite_path}")
        
        file_size = sqlite_path.stat().st_size
        logger.info(f"[DW-BOOTSTRAP] Tamanho do arquivo: {file_size / (1024*1024):.2f} MB")
        
    except Exception as e:
        logger.error(f"[DW-BOOTSTRAP] ❌ Erro ao baixar SQLite do GCS: {e}")
        raise RuntimeError(f"Falha ao baixar DW SQLite de {gcs_uri}: {e}") from e


def _download_from_gcs(gcs_uri: str, destination: Path) -> None:
    """
    Faz download de um arquivo do Google Cloud Storage.
    
    Args:
        gcs_uri: URI do GCS (ex.: gs://bucket-name/path/to/file.db)
        destination: Caminho local onde salvar o arquivo
        
    Raises:
        ValueError: Se a URI não for válida
        Exception: Se houver erro ao baixar
    """
    try:
        from google.cloud import storage
    except ImportError:
        raise ImportError(
            "google-cloud-storage não está instalado. "
            "Instale com: pip install google-cloud-storage"
        )
    
    # Parse da URI do GCS
    parsed = urlparse(gcs_uri)
    
    if parsed.scheme != "gs":
        raise ValueError(f"URI do GCS deve começar com 'gs://', recebido: {gcs_uri}")
    
    bucket_name = parsed.netloc
    blob_name = parsed.path.lstrip("/")
    
    if not bucket_name or not blob_name:
        raise ValueError(f"URI do GCS inválida: {gcs_uri}")
    
    logger.info(f"[DW-BOOTSTRAP] Fazendo download de gs://{bucket_name}/{blob_name}")
    
    # Cria cliente do GCS
    # No Cloud Run, usa Application Default Credentials automaticamente
    # Localmente, pode usar GOOGLE_APPLICATION_CREDENTIALS ou gcloud auth application-default login
    client = storage.Client()
    
    # Obtém bucket e blob
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    
    # Verifica se o blob existe
    if not blob.exists():
        raise FileNotFoundError(f"Arquivo não encontrado no GCS: gs://{bucket_name}/{blob_name}")
    
    # Faz download
    logger.info(f"[DW-BOOTSTRAP] Iniciando download... (isso pode levar alguns minutos para arquivos grandes)")
    blob.download_to_filename(str(destination))
    
    logger.info(f"[DW-BOOTSTRAP] Download concluído: {destination}")
