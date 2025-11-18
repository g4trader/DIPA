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
    
    Se DB_TYPE != "sqlite", não faz nada.
    Se DB_TYPE == "sqlite" e o arquivo não existir, tenta baixar do GCS.
    
    Raises:
        RuntimeError: Se DB_TYPE == "sqlite" mas o arquivo não existe e DIPAM_DW_GCS_URI não está configurado
        Exception: Se houver erro ao baixar do GCS
    """
    db_type = os.getenv("DB_TYPE", "sqlite")
    
    if db_type != "sqlite":
        logger.debug(f"[DW-BOOTSTRAP] DB_TYPE={db_type}, não é SQLite. Pulando bootstrap.")
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
            f"Arquivo SQLite não encontrado em {sqlite_path} e DIPAM_DW_GCS_URI não está configurado. "
            f"Configure a variável de ambiente DIPAM_DW_GCS_URI (ex.: gs://dipam-dw-prod/dipam_dw.db)"
        )
        logger.error(f"[DW-BOOTSTRAP] ❌ {error_msg}")
        raise RuntimeError(error_msg)
    
    logger.info(f"[DW-BOOTSTRAP] Arquivo SQLite não encontrado em {sqlite_path}")
    logger.info(f"[DW-BOOTSTRAP] 📥 Baixando DW SQLite de {gcs_uri} para {sqlite_path}")
    
    # Cria diretório pai se não existir
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Faz download do GCS
    try:
        _download_from_gcs(gcs_uri, sqlite_path)
        logger.info(f"[DW-BOOTSTRAP] ✅ Arquivo SQLite baixado com sucesso: {sqlite_path}")
        logger.info(f"[DW-BOOTSTRAP] Tamanho do arquivo: {sqlite_path.stat().st_size / (1024*1024):.2f} MB")
    except Exception as e:
        logger.error(f"[DW-BOOTSTRAP] ❌ Erro ao baixar arquivo do GCS: {e}")
        raise


def _download_from_gcs(gcs_uri: str, destination_path: Path) -> None:
    """
    Faz download de um arquivo do Google Cloud Storage.
    
    Args:
        gcs_uri: URI do GCS (ex.: gs://bucket-name/path/to/file.db)
        destination_path: Caminho local onde salvar o arquivo
        
    Raises:
        ValueError: Se a URI do GCS for inválida
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
        raise ValueError(f"URI do GCS inválida: {gcs_uri}. Formato esperado: gs://bucket-name/path/to/file")
    
    logger.info(f"[DW-BOOTSTRAP] Fazendo download de gs://{bucket_name}/{blob_name}")
    
    # Cria cliente do GCS
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    
    # Verifica se o blob existe
    if not blob.exists():
        raise FileNotFoundError(f"Arquivo não encontrado no GCS: gs://{bucket_name}/{blob_name}")
    
    # Faz download
    blob.download_to_filename(str(destination_path))
    
    logger.info(f"[DW-BOOTSTRAP] Download concluído: {destination_path}")

