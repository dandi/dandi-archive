from __future__ import annotations

from typing import TYPE_CHECKING, Any

import boto3
from django.conf import settings
from django.core.files.storage import Storage, default_storage
from storages.backends.s3 import S3Storage

if TYPE_CHECKING:
    from botocore.config import Config


class TimeoutS3Storage(S3Storage):
    pass


class VerbatimNameS3Storage(TimeoutS3Storage):
    pass


def get_boto_client(storage: Storage | None = None, config: Config | None = None):
    """Return an s3 client from the current storage."""
    storage = storage if storage else default_storage
    storage_params = get_storage_params(storage)
    region_name = 'us-east-2'
    return boto3.client(
        's3',
        endpoint_url=storage_params['endpoint_url'],
        aws_access_key_id=storage_params['access_key'],
        aws_secret_access_key=storage_params['secret_key'],
        region_name=region_name,
        config=config,
    )


def get_storage_params(storage: Storage):
    return {
        'endpoint_url': storage.endpoint_url,
        'access_key': storage.access_key,
        'secret_key': storage.secret_key,
    }


def get_storage_prefix(instance: Any, filename: str) -> str:
    return f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}{filename}'
