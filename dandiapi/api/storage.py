from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
import hashlib
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from dandischema.digests.dandietag import PartGenerator
from django.conf import settings
from django.core.files.storage import Storage, get_storage_class
from minio import S3Error
from minio_storage.policy import Policy
from minio_storage.storage import MinioStorage, create_minio_client_from_settings
from s3_file_field._multipart_minio import MinioMultipartManager
from s3_file_field._multipart_s3 import S3MultipartManager
from storages.backends.s3 import S3Storage


class ChecksumCalculatorFile:
    """File-like object that calculates the checksum of everything written to it."""

    def __init__(self):
        self.h = hashlib.sha256()

    def write(self, data: bytes) -> None:
        self.h.update(data)

    @property
    def checksum(self):
        return self.h.hexdigest()


class DandiMultipartMixin:
    @staticmethod
    def _iter_part_sizes(file_size: int) -> Iterator[tuple[int, int]]:
        generator = PartGenerator.for_file_size(file_size)
        for part in generator:
            yield part.number, part.size

    _url_expiration = timedelta(days=7)


class DandiS3MultipartManager(DandiMultipartMixin, S3MultipartManager):
    """A custom multipart manager for passing ACL information."""

    def _create_upload_id(self, object_key: str, content_type: str) -> str:
        resp = self._client.create_multipart_upload(
            Bucket=self._bucket_name,
            Key=object_key,
            ContentType=content_type,
            ACL='bucket-owner-full-control',
        )
        return resp['UploadId']


class DandiMinioMultipartManager(DandiMultipartMixin, MinioMultipartManager):
    """A custom multipart manager for passing ACL information."""

    def _create_upload_id(self, object_key: str, content_type: str) -> str:
        return self._client._create_multipart_upload(
            bucket_name=self._bucket_name,
            object_name=object_key,
            headers={
                'Content-Type': content_type,
                'x-amz-acl': 'bucket-owner-full-control',
            },
        )


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


class VerbatimNameStorageMixin:
    """A Storage mixin, storing files without transforming their original filename."""

    # The basic S3Storage does not implement generate_filename or get_valid_name,
    # so upon FileField save, the following call stack normally occurs:
    #   FieldFile.save
    #   FileField.generate_filename
    #   Storage.generate_filename
    #   Storage.get_valid_name
    # Storage.generate_filename attempts to normalize the filename as a path.
    # Storage.get_valid_name uses django.utils.text.get_valid_filename,
    # which cleans spaces and other characters.
    # Since these are designed around filesystem safety, not S3 key safety, it's
    # simpler to do sanitization before saving.
    def generate_filename(self, filename: str) -> str:
        return filename


class TimeoutS3Storage(S3Storage):
    """Override boto3 default timeout values."""

    def __init__(self, **settings):
        super().__init__(**settings)

        self.config = self.config.merge(
            Config(connect_timeout=5, read_timeout=5, retries={'max_attempts': 2})
        )


class VerbatimNameS3Storage(VerbatimNameStorageMixin, TimeoutS3Storage):
    @property
    def multipart_manager(self):
        return DandiS3MultipartManager(self)

    def etag_from_blob_name(self, blob_name) -> str | None:
        client = self.connection.meta.client

        try:
            response = client.head_object(
                Bucket=self.bucket_name,
                Key=blob_name,
            )
        except ClientError:
            return None
        else:
            etag = response['ETag']
            # S3 wraps the ETag in double quotes, so we need to strip them
            if etag[0] == '"' and etag[-1] == '"':
                return etag[1:-1]
            return etag

    def generate_presigned_put_object_url(self, blob_name: str, base64md5: str) -> str:
        return self.connection.meta.client.generate_presigned_url(
            ClientMethod='put_object',
            Params={
                'Bucket': self.bucket_name,
                'Key': blob_name,
                'ACL': 'bucket-owner-full-control',
                'ContentMD5': base64md5,
            },
            ExpiresIn=600,  # TODO: proper expiration
        )

    def generate_presigned_head_object_url(self, key: str) -> str:
        return self.bucket.meta.client.generate_presigned_url(
            'head_object',
            Params={'Bucket': self.bucket.name, 'Key': key},
        )

    def generate_presigned_download_url(self, key: str, path: str) -> str:
        return self.connection.meta.client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': self.bucket_name,
                'Key': key,
                'ResponseContentDisposition': f'attachment; filename="{path}"',
            },
        )

    def generate_presigned_inline_url(self, key: str, path: str, content_type: str) -> str:
        return self.connection.meta.client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': self.bucket_name,
                'Key': key,
                'ResponseContentDisposition': f'inline; filename="{path}"',
                'ResponseContentType': content_type,
            },
        )

    def sha256_checksum(self, key: str) -> str:
        calculator = ChecksumCalculatorFile()
        obj = self.bucket.Object(key)
        obj.download_fileobj(calculator)
        return calculator.checksum


class VerbatimNameMinioStorage(VerbatimNameStorageMixin, DeconstructableMinioStorage):
    @property
    def multipart_manager(self):
        return DandiMinioMultipartManager(self)

    def etag_from_blob_name(self, blob_name) -> str | None:
        try:
            response = self.client.stat_object(self.bucket_name, blob_name)
        except S3Error as e:
            if e.code == 'NoSuchKey':
                return None
            else:
                raise
        else:
            return response.etag

    def generate_presigned_put_object_url(self, blob_name: str, _: str) -> str:
        # Note: minio-py doesn't support using Content-MD5 headers

        # storage.client will generate URLs like `http://minio:9000/...` when running in
        # docker. To avoid this, use the secondary base_url_client which is configured to
        # generate URLs like `http://localhost:9000/...`.
        return self.base_url_client.presigned_put_object(
            bucket_name=self.bucket_name,
            object_name=blob_name,
            expires=timedelta(seconds=600),  # TODO: proper expiration
        )

    def generate_presigned_head_object_url(self, key: str) -> str:
        return self.base_url_client.get_presigned_url('HEAD', self.bucket_name, key)

    def generate_presigned_download_url(self, key: str, path: str) -> str:
        return self.base_url_client.presigned_get_object(
            self.bucket_name,
            key,
            response_headers={'response-content-disposition': f'attachment; filename="{path}"'},
        )

    def generate_presigned_inline_url(self, key: str, path: str, content_type: str) -> str:
        return self.base_url_client.presigned_get_object(
            self.bucket_name,
            key,
            response_headers={
                'response-content-disposition': f'inline; filename="{path}"',
                'response-content-type': content_type,
            },
        )

    def sha256_checksum(self, key: str) -> str:
        calculator = ChecksumCalculatorFile()
        obj = self.client.get_object(self.bucket_name, key)
        for chunk in obj.stream(amt=1024 * 1024 * 16):
            calculator.write(chunk)
        return calculator.checksum


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
        raise Exception(f'Unknown storage: {default_storage_class}')

    return storage


def get_boto_client(storage: Storage | None = None):
    """Return an s3 client from the current storage."""
    storage = storage if storage else get_storage()
    if isinstance(storage, MinioStorage):
        storage_params = get_storage_params(storage)
        return boto3.client(
            's3',
            endpoint_url=storage_params['endpoint_url'],
            aws_access_key_id=storage_params['access_key'],
            aws_secret_access_key=storage_params['secret_key'],
            region_name='us-east-1',
        )

    return storage.connection.meta.client


def get_storage_params(storage: Storage):
    if isinstance(storage, MinioStorage):
        return {
            'endpoint_url': storage.client._base_url._url.geturl(),
            'access_key': storage.client._provider.retrieve().access_key,
            'secret_key': storage.client._provider.retrieve().secret_key,
        }

    return {
        'endpoint_url': storage.endpoint_url,
        'access_key': storage.access_key,
        'secret_key': storage.secret_key,
    }


def get_storage() -> Storage:
    return create_s3_storage(settings.DANDI_DANDISETS_BUCKET_NAME)


def get_storage_prefix(instance: Any, filename: str) -> str:
    return f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}{filename}'


def get_embargo_storage() -> Storage:
    return create_s3_storage(settings.DANDI_DANDISETS_EMBARGO_BUCKET_NAME)


def get_embargo_storage_prefix(instance: Any, filename: str) -> str:
    return f'{settings.DANDI_DANDISETS_EMBARGO_BUCKET_PREFIX}{filename}'
