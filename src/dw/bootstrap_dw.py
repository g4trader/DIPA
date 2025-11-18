"""
Bootstrap do Data Warehouse SQLite.

Este módulo garante que o arquivo SQLite do DW esteja disponível,
baixando automaticamente do GCS se necessário.
"""

import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def ensure_sqlite_dw_available() -> None:
    """
    Garante que o arquivo SQLite do DW esteja disponível.
    
    Se DB_TYPE != "sqlite", não faz nada.
    Se DB_TYPE == "sqlite" e o arquivo não existe, baixa do GCS.
    
    Raises:
        RuntimeError: Se DIPAM_DW_GCS_URI não estiver configurado e o arquivo não existir
        Exception: Se houver erro ao baixar do GCS
    """
    db_type = os.getenv("DB_TYPE", "sqlite")
    
    if db_type != "sqlite":
        logger.debug("[DW-BOOTSTRAP] DB_TYPE != sqlite, pulando bootstrap do DW SQLite")
        return
    
    sqlite_path_str = os.getenv("SQLITE_PATH", "/app/data/dipam_dw.db")
    if not sqlite_path_str:
        raise ValueError("SQLITE_PATH não pode ser vazio")
    
    sqlite_path = Path(sqlite_path_str)
    gcs_uri = os.getenv("DIPAM_DW_GCS_URI")
    
    # Se o arquivo já existe, não precisa fazer nada
    if sqlite_path.exists():
        logger.info(f"[DW-BOOTSTRAP] Arquivo SQLite já existe: {sqlite_path}")
        return
    
    # Se não existe e não há GCS URI configurado, erro crítico
    if not gcs_uri:
        error_msg = (
            f"DIPAM_DW_GCS_URI não configurado e arquivo SQLite não encontrado em {sqlite_path}. "
            "Configure DIPAM_DW_GCS_URI ou garanta que o arquivo existe no caminho especificado."
        )
        logger.error(f"[DW-BOOTSTRAP] {error_msg}")
        raise RuntimeError(error_msg)
    
    # Cria diretório pai se não existir
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Faz download do GCS
    logger.info(f"[DW-BOOTSTRAP] Baixando DW SQLite de {gcs_uri} para {sqlite_path}")
    
    try:
        from google.cloud import storage
        
        # Parse do URI gs://bucket/object
        if not gcs_uri.startswith("gs://"):
            raise ValueError(f"DIPAM_DW_GCS_URI deve começar com 'gs://', recebido: {gcs_uri}")
        
        # Remove gs:// e separa bucket e object
        path_without_prefix = gcs_uri[5:]  # Remove "gs://"
        parts = path_without_prefix.split("/", 1)
        if len(parts) != 2:
            raise ValueError(f"DIPAM_DW_GCS_URI deve ter formato 'gs://bucket/object', recebido: {gcs_uri}")
        
        bucket_name = parts[0]
        object_name = parts[1]
        
        # Cria cliente do GCS
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(object_name)
        
        # Faz download
        logger.info(f"[DW-BOOTSTRAP] Fazendo download de gs://{bucket_name}/{object_name}...")
        blob.download_to_filename(str(sqlite_path))
        
        # Verifica se o arquivo foi baixado
        if not sqlite_path.exists():
            raise RuntimeError(f"Download concluído, mas arquivo não encontrado em {sqlite_path}")
        
        # Obtém tamanho do arquivo
        file_size_mb = sqlite_path.stat().st_size / (1024 * 1024)
        logger.info(
            f"[DW-BOOTSTRAP] ✅ DW SQLite baixado com sucesso: {sqlite_path} "
            f"({file_size_mb:.2f} MB)"
        )
        
    except ImportError:
        error_msg = (
            "google-cloud-storage não está instalado. "
            "Instale com: pip install google-cloud-storage"
        )
        logger.error(f"[DW-BOOTSTRAP] {error_msg}")
        raise RuntimeError(error_msg)
    except Exception as e:
        error_msg = f"Erro ao baixar DW SQLite do GCS: {str(e)}"
        logger.error(f"[DW-BOOTSTRAP] {error_msg}")
        raise RuntimeError(error_msg) from e
