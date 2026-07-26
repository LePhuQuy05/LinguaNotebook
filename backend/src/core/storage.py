"""S3-compatible object storage abstraction (MinIO for self-hosted, S3/R2 for cloud)."""

import boto3
from botocore.config import Config

from src.core.config import settings

_storage_client = None


def get_storage_client():
    """Lazy-initialize the S3 client."""
    global _storage_client
    if _storage_client is None:
        _storage_client = boto3.client(
            "s3",
            endpoint_url=(
                f"http{'s' if settings.storage_use_ssl else ''}://{settings.storage_endpoint}"
            ),
            aws_access_key_id=settings.storage_access_key,
            aws_secret_access_key=settings.storage_secret_key,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )
        _ensure_bucket()
    return _storage_client


def _ensure_bucket() -> None:
    """Create the storage bucket if it doesn't exist."""
    client = _storage_client
    try:
        client.head_bucket(Bucket=settings.storage_bucket)
    except Exception:
        client.create_bucket(Bucket=settings.storage_bucket)


def upload_file(file_data: bytes, object_key: str, content_type: str = "application/octet-stream") -> str:
    """Upload a file to storage. Returns the object key."""
    client = get_storage_client()
    client.put_object(
        Bucket=settings.storage_bucket,
        Key=object_key,
        Body=file_data,
        ContentType=content_type,
    )
    return object_key


def get_file_url(object_key: str, expires: int = 3600) -> str:
    """Generate a presigned URL for file download."""
    client = get_storage_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.storage_bucket, "Key": object_key},
        ExpiresIn=expires,
    )


def delete_file(object_key: str) -> None:
    """Delete a file from storage."""
    client = get_storage_client()
    client.delete_object(Bucket=settings.storage_bucket, Key=object_key)
