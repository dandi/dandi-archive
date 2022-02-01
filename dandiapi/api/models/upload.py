from __future__ import annotations

from abc import abstractmethod
from uuid import uuid4

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django_extensions.db.models import TimeStampedModel

from dandiapi.api.multipart import DandiMultipartManager
from dandiapi.api.storage import (
    get_embargo_storage,
    get_embargo_storage_prefix,
    get_storage,
    get_storage_prefix,
)

from .asset import AssetBlob, EmbargoedAssetBlob
from .dandiset import Dandiset

try:
    from storages.backends.s3boto3 import S3Boto3Storage
except ImportError:
    # This should only be used for type interrogation, never instantiation
    S3Boto3Storage = type('FakeS3Boto3Storage', (), {})
try:
    from minio_storage.storage import MinioStorage
except ImportError:
    # This should only be used for type interrogation, never instantiation
    MinioStorage = type('FakeMinioStorage', (), {})


class BaseUpload(TimeStampedModel):
    ETAG_REGEX = r'[0-9a-f]{32}(-[1-9][0-9]*)?'

    class Meta:
        indexes = [models.Index(fields=['etag'])]
        abstract = True

    # This is the key used to generate the object key, and the primary identifier for the upload.
    upload_id = models.UUIDField(unique=True, default=uuid4, db_index=True)
    etag = models.CharField(
        null=True,
        blank=True,
        max_length=40,
        validators=[RegexValidator(f'^{ETAG_REGEX}$')],
        db_index=True,
    )
    # This is the identifier the object store assigns to the multipart upload
    multipart_upload_id = models.CharField(max_length=128, unique=True, db_index=True)
    size = models.PositiveBigIntegerField()

    @staticmethod
    @abstractmethod
    def object_key(upload_id, dandiset: Dandiset | None = None):  # noqa: N805
        pass

    @classmethod
    def initialize_multipart_upload(cls, etag, size, dandiset: Dandiset):
        upload_id = uuid4()
        object_key = cls.object_key(upload_id, dandiset)
        multipart_initialization = DandiMultipartManager.from_storage(
            cls.blob.field.storage
        ).initialize_upload(object_key, size)

        upload = cls(
            upload_id=upload_id,
            blob=object_key,
            etag=etag,
            size=size,
            dandiset=dandiset,
            multipart_upload_id=multipart_initialization.upload_id,
        )

        return upload, {'upload_id': upload.upload_id, 'parts': multipart_initialization.parts}

    def object_key_exists(self):
        return self.blob.field.storage.exists(self.blob.name)

    def actual_size(self):
        return self.blob.field.storage.size(self.blob.name)

    def actual_etag(self):
        storage = self.blob.storage
        if isinstance(storage, S3Boto3Storage):
            client = storage.connection.meta.client

            response = client.head_object(
                Bucket=storage.bucket_name,
                Key=self.blob.name,
            )
            etag = response['ETag']
            # S3 wraps the ETag in double quotes, so we need to strip them
            if etag[0] == '"' and etag[-1] == '"':
                return etag[1:-1]
            return etag

        elif isinstance(storage, MinioStorage):
            client = storage.client
            response = client.stat_object(storage.bucket_name, self.blob.name)
            return response.etag
        else:
            raise ValueError(f'Unknown storage {self.blob.field.storage}')


class Upload(BaseUpload):
    blob = models.FileField(blank=True, storage=get_storage, upload_to=get_storage_prefix)
    dandiset = models.ForeignKey(Dandiset, related_name='uploads', on_delete=models.CASCADE)

    @staticmethod
    def object_key(upload_id, dandiset: Dandiset | None = None):
        upload_id = str(upload_id)
        return (
            f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}'
            f'blobs/{upload_id[0:3]}/{upload_id[3:6]}/{upload_id}'
        )

    def to_asset_blob(self) -> AssetBlob:
        """Convert this upload into an AssetBlob."""
        return AssetBlob(
            blob_id=self.upload_id,
            blob=self.blob,
            etag=self.etag,
            size=self.size,
        )


class EmbargoedUpload(BaseUpload):
    blob = models.FileField(
        blank=True, storage=get_embargo_storage, upload_to=get_embargo_storage_prefix
    )
    dandiset = models.ForeignKey(
        Dandiset, related_name='embargoed_uploads', on_delete=models.CASCADE
    )

    @staticmethod
    def object_key(upload_id, dandiset: Dandiset):
        upload_id = str(upload_id)
        return (
            f'{settings.DANDI_DANDISETS_EMBARGO_BUCKET_PREFIX}'
            f'{dandiset.identifier}/'
            f'blobs/{upload_id[0:3]}/{upload_id[3:6]}/{upload_id}'
        )

    def to_embargoed_asset_blob(self) -> EmbargoedAssetBlob:
        """Convert this upload into an AssetBlob."""
        return EmbargoedAssetBlob(
            blob_id=self.upload_id,
            blob=self.blob,
            etag=self.etag,
            size=self.size,
            dandiset=self.dandiset,
        )
