from functools import lru_cache

from app.core.config import settings
from app.storage.base import StorageProvider
from app.storage.local import LocalStorage


@lru_cache(maxsize=8)
def _build_storage_provider(
    backend: str,
    upload_dir: str,
    endpoint_url: str,
    region: str,
    bucket: str,
    access_key_id: str,
    secret_access_key: str,
    prefix: str,
) -> StorageProvider:
    if backend == "local":
        return LocalStorage(upload_dir)

    from app.storage.s3 import S3Storage

    return S3Storage(
        endpoint_url=endpoint_url,
        region=region,
        bucket=bucket,
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
        prefix=prefix,
    )


def get_storage_provider() -> StorageProvider:
    return _build_storage_provider(
        settings.storage_backend,
        str(settings.upload_dir),
        settings.s3_endpoint_url or "",
        settings.s3_region,
        settings.s3_bucket or "",
        settings.s3_access_key_id or "",
        settings.s3_secret_access_key or "",
        settings.s3_prefix,
    )


def clear_storage_provider_cache() -> None:
    _build_storage_provider.cache_clear()
