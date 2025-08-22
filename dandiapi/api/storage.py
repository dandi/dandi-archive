from __future__ import annotations

from typing import TYPE_CHECKING, Any

import boto3
from django.conf import settings
from django.core.files.storage import Storage, default_storage
from minio_storage.storage import MinioStorage, create_minio_client_from_settings
from storages.backends.s3 import S3Storage

if TYPE_CHECKING:
    from botocore.config import Config


class DeconstructableMinioStorage(MinioStorage):
    """
    A MinioStorage which is deconstructable by Django.

    This does not require a minio_client argument to the constructor.
    """

    def __init__(self, *args, **kwargs):
        # A minio.api.Minio instance cannot be serialized by Django. Since all constructor
        # arguments are serialized by the @deconstructible decorator, passing a Minio client as a
        # constructor argument causes makemigrations to fail.
        kwargs['minio_client'] = create_minio_client_from_settings()
        super().__init__(*args, **kwargs)


class TimeoutS3Storage(S3Storage):
    pass


class VerbatimNameS3Storage(TimeoutS3Storage):
    pass


class VerbatimNameMinioStorage(DeconstructableMinioStorage):
    pass


def get_boto_client(storage: Storage | None = None, config: Config | None = None):
    """Return an s3 client from the current storage."""
    storage = storage if storage else default_storage
    storage_params = get_storage_params(storage)
    region_name = 'us-east-1' if isinstance(storage, MinioStorage) else 'us-east-2'
    return boto3.client(
        's3',
        endpoint_url=storage_params['endpoint_url'],
        aws_access_key_id=storage_params['access_key'],
        aws_secret_access_key=storage_params['secret_key'],
        region_name=region_name,
        config=config,
    )


def get_storage_params(storage: Storage):
    if isinstance(storage, MinioStorage):
        return {
            'endpoint_url': storage.client._base_url._url.geturl(),  # noqa: SLF001
            'access_key': storage.client._provider.retrieve().access_key,  # noqa: SLF001
            'secret_key': storage.client._provider.retrieve().secret_key,  # noqa: SLF001
        }

    return {
        'endpoint_url': storage.endpoint_url,
        'access_key': storage.access_key,
        'secret_key': storage.secret_key,
    }


def get_storage_prefix(instance: Any, filename: str) -> str:
    return f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}{filename}'
