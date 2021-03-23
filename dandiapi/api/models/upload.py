from __future__ import annotations

from uuid import uuid4

from django.core.validators import RegexValidator
from django.db import models
from django_extensions.db.models import TimeStampedModel
from s3_file_field._multipart import MultipartManager

from .asset import AssetBlob, get_asset_blob_prefix, get_asset_blob_storage

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


class Upload(TimeStampedModel):
    ETAG_REGEX = r'[0-9a-f]{32}(-[1-9][0-9]*)?'

    class Meta:
        indexes = [models.Index(fields=['etag'])]

    # This is the key used to generate the object key, and the primary identifier for the upload.
    upload_id = models.UUIDField(unique=True, default=uuid4, db_index=True)
    blob = models.FileField(
        blank=True, storage=get_asset_blob_storage, upload_to=get_asset_blob_prefix
    )
    etag = models.CharField(
        null=True,
        blank=True,
        max_length=40,
        validators=[RegexValidator(f'^{ETAG_REGEX}$')],
        db_index=True,
    )
    # This is the identifier the object store assigns to the multipart upload
    multipart_upload_id = models.UUIDField(unique=True, db_index=True)
    size = models.PositiveBigIntegerField()

    @classmethod
    def object_key(cls, upload_id):
        upload_id = str(upload_id)
        return f'blobs/{upload_id[0:3]}/{upload_id[3:6]}/{upload_id}'

    @classmethod
    def initialize_multipart_upload(cls, etag, size):
        upload_id = uuid4()
        object_key = cls.object_key(upload_id)
        multipart_initialization = MultipartManager.from_storage(
            AssetBlob.blob.field.storage
        ).initialize_upload(object_key, size)

        upload = cls(
            upload_id=upload_id,
            blob=object_key,
            etag=etag,
            size=size,
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
            return response['ETag']
        elif isinstance(storage, MinioStorage):
            client = storage.client
            response = client.stat_object(storage.bucket_name, self.blob.name)
            return response.etag
        else:
            raise ValueError(f'Unknown storage {self.blob.field.storage}')

    def to_asset_blob(self) -> AssetBlob:
        """Convert this upload into an AssetBlob."""
        return AssetBlob(
            uuid=self.upload_id,
            blob=self.blob,
            etag=self.etag,
            size=self.size,
        )
