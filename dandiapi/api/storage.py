from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit, urlunsplit

import boto3
from django.conf import settings
from django.core.files.storage import Storage, default_storage, get_storage_class
from minio_storage.policy import Policy
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


def create_s3_storage(bucket_name: str) -> Storage:
    """
    Return a new Storage instance, compatible with the default Storage class.

    This abstracts over differences between S3Storage and MinioStorage,
    allowing either to be used as an additional non-default Storage.
    """
    # For production, calling django.core.files.storage.get_storage_class is fine
    # to return the storage class of S3Storage.
    default_storage_class = get_storage_class()

    if issubclass(default_storage_class, S3Storage):
        storage = VerbatimNameS3Storage(bucket_name=bucket_name)
        # Required to upload to the sponsored bucket
        storage.default_acl = 'bucket-owner-full-control'
    elif issubclass(default_storage_class, MinioStorage):
        base_url = None
        if getattr(settings, 'MINIO_STORAGE_MEDIA_URL', None):
            # If a new base_url is set for the media storage, it's safe to assume one should be
            # set for this storage too.
            base_url_parts = urlsplit(settings.MINIO_STORAGE_MEDIA_URL)
            # Reconstruct the URL with an updated path
            base_url = urlunsplit(
                (
                    base_url_parts.scheme,
                    base_url_parts.netloc,
                    f'/{bucket_name}',
                    base_url_parts.query,
                    base_url_parts.fragment,
                )
            )

        # The MinioMediaStorage used as the default storage is cannot be used
        # as an ad-hoc non-default storage, as it does not allow bucket_name to be
        # explicitly set.
        storage = VerbatimNameMinioStorage(
            bucket_name=bucket_name,
            base_url=base_url,
            # All S3Storage URLs are presigned, and the bucket typically is not public
            presign_urls=True,
            auto_create_bucket=True,
            auto_create_policy=True,
            policy_type=Policy.read,
            # Required to upload to the sponsored bucket
            object_metadata={'x-amz-acl': 'bucket-owner-full-control'},
        )
        # TODO: generalize policy_type?
        # TODO: filename transforming?
        # TODO: content_type
    else:
        raise TypeError(f'Unknown storage: {default_storage_class}')

    return storage


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
