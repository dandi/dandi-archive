from __future__ import annotations

from uuid import uuid4

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django_extensions.db.models import TimeStampedModel

from dandiapi.api.storage import DynamicStorageFileField, get_embargo_storage, get_storage

from .asset import AssetBlob
from .dandiset import Dandiset


class Upload(TimeStampedModel):
    ETAG_REGEX = r'[0-9a-f]{32}(-[1-9][0-9]*)?'

    class Meta:
        indexes = [models.Index(fields=['etag'])]

    dandiset = models.ForeignKey(Dandiset, related_name='uploads', on_delete=models.CASCADE)

    # This is the key used to generate the object key, and the primary identifier for the upload.
    upload_id = models.UUIDField(unique=True, default=uuid4, db_index=True)
    blob = DynamicStorageFileField(blank=True)
    embargoed = models.BooleanField(default=False)
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
    def object_key(upload_id, dandiset: Dandiset | None = None, embargoed=False):
        upload_id = str(upload_id)
        if embargoed:
            if dandiset is None:
                raise Exception('Must provide dandiset for embargoed uplods')

            return (
                f'{settings.DANDI_DANDISETS_EMBARGO_BUCKET_PREFIX}'
                f'{dandiset.identifier}/'
                f'blobs/{upload_id[0:3]}/{upload_id[3:6]}/{upload_id}'
            )
        return (
            f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}'
            f'blobs/{upload_id[0:3]}/{upload_id[3:6]}/{upload_id}'
        )

    @classmethod
    def initialize_multipart_upload(cls, etag, size, dandiset: Dandiset, embargoed=False):
        upload_id = uuid4()
        object_key = cls.object_key(upload_id=upload_id, dandiset=dandiset, embargoed=embargoed)

        # Get storage and init upload
        storage = get_embargo_storage() if embargoed else get_storage()
        multipart_initialization = storage.multipart_manager.initialize_upload(object_key, size)

        # Create instance
        upload = cls(
            upload_id=upload_id,
            blob=object_key,
            etag=etag,
            size=size,
            dandiset=dandiset,
            multipart_upload_id=multipart_initialization.upload_id,
        )

        # Return instance alongside id and parts
        return upload, {'upload_id': upload.upload_id, 'parts': multipart_initialization.parts}

    def object_key_exists(self):
        return self.blob.field.storage.exists(self.blob.name)

    def actual_size(self):
        return self.blob.field.storage.size(self.blob.name)

    def actual_etag(self):
        return self.blob.storage.etag_from_blob_name(self.blob.name)

    def to_asset_blob(self) -> AssetBlob:
        """Convert this upload into an AssetBlob."""
        return AssetBlob(
            blob_id=self.upload_id,
            blob=self.blob,
            etag=self.etag,
            size=self.size,
            embargoed=self.embargoed,
        )
