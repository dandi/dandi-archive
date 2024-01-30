from __future__ import annotations

from abc import abstractmethod
from uuid import uuid4

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django_extensions.db.models import CreationDateTimeField

from dandiapi.api.storage import (
    get_embargo_storage,
    get_embargo_storage_prefix,
    get_storage,
    get_storage_prefix,
)

from .asset import AssetBlob, EmbargoedAssetBlob
from .dandiset import Dandiset


class BaseUpload(models.Model):
    ETAG_REGEX = r'[0-9a-f]{32}(-[1-9][0-9]*)?'

    created = CreationDateTimeField()

    # This is the key used to generate the object key, and the primary identifier for the upload.
    upload_id = models.UUIDField(unique=True, default=uuid4, db_index=True)
    etag = models.CharField(  # noqa: DJ001
        null=True,
        default=None,
        blank=True,
        max_length=40,
        validators=[RegexValidator(f'^{ETAG_REGEX}$')],
        db_index=True,
    )
    # This is the identifier the object store assigns to the multipart upload
    multipart_upload_id = models.CharField(max_length=128, unique=True, db_index=True)
    size = models.PositiveBigIntegerField()

    class Meta:
        indexes = [models.Index(fields=['etag'])]
        abstract = True

    @staticmethod
    @abstractmethod
    def object_key(upload_id, *, dandiset: Dandiset):
        pass

    @classmethod
    def initialize_multipart_upload(cls, etag, size, dandiset: Dandiset):
        upload_id = uuid4()
        object_key = cls.object_key(upload_id, dandiset=dandiset)
        multipart_initialization = cls.blob.field.storage.multipart_manager.initialize_upload(
            object_key,
            size,
            # The upload HTTP API does not pass the file name or content type, and it would be a
            # breaking change to start requiring this.
            'application/octet-stream',
        )

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
        return self.blob.storage.etag_from_blob_name(self.blob.name)


class Upload(BaseUpload):
    blob = models.FileField(blank=True, storage=get_storage, upload_to=get_storage_prefix)
    dandiset = models.ForeignKey(Dandiset, related_name='uploads', on_delete=models.CASCADE)

    def __str__(self) -> str:
        return self.upload_id

    @staticmethod
    def object_key(upload_id, *, dandiset: Dandiset | None = None):  # noqa: ARG004
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

    def __str__(self) -> str:
        return self.upload_id

    @staticmethod
    def object_key(upload_id, *, dandiset: Dandiset):
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
