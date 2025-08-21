from __future__ import annotations

from uuid import uuid4

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django_extensions.db.models import CreationDateTimeField

from dandiapi.api.multipart import DandiS3MultipartManager
from dandiapi.api.storage import get_storage_prefix

from .asset import AssetBlob
from .dandiset import Dandiset


class Upload(models.Model):  # noqa: DJ008
    ETAG_REGEX = r'[0-9a-f]{32}(-[1-9][0-9]*)?'

    created = CreationDateTimeField()

    dandiset = models.ForeignKey(Dandiset, related_name='uploads', on_delete=models.CASCADE)

    blob = models.FileField(blank=True, upload_to=get_storage_prefix)
    embargoed = models.BooleanField(default=False)

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
        ordering = ['created']
        indexes = [models.Index(fields=['etag'])]

    @staticmethod
    def object_key(upload_id):
        upload_id = str(upload_id)
        return (
            f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}'
            f'blobs/{upload_id[0:3]}/{upload_id[3:6]}/{upload_id}'
        )

    @classmethod
    def initialize_multipart_upload(cls, etag, size, dandiset: Dandiset):
        upload_id = uuid4()
        object_key = cls.object_key(upload_id)
        embargoed = dandiset.embargo_status == Dandiset.EmbargoStatus.EMBARGOED
        multipart_initialization = DandiS3MultipartManager(
            cls._meta.get_field('blob').storage
        ).initialize_upload(
            object_key,
            size,
            # The upload HTTP API does not pass the file name or content type, and it would be a
            # breaking change to start requiring this.
            'application/octet-stream',
            tags={'embargoed': 'true'} if embargoed else None,
        )

        upload = cls(
            upload_id=upload_id,
            blob=object_key,
            etag=etag,
            size=size,
            dandiset=dandiset,
            embargoed=embargoed,
            multipart_upload_id=multipart_initialization.upload_id,
        )

        return upload, {
            'upload_id': upload.upload_id,
            'parts': multipart_initialization.parts,
        }

    def to_asset_blob(self) -> AssetBlob:
        """Convert this upload into an AssetBlob."""
        return AssetBlob(
            embargoed=self.embargoed,
            blob_id=self.upload_id,
            blob=self.blob,
            etag=self.etag,
            size=self.size,
        )

    def object_key_exists(self):
        return self.blob.field.storage.exists(self.blob.name)

    def actual_size(self):
        return self.blob.field.storage.size(self.blob.name)

    def actual_etag(self) -> str | None:
        return self.blob.storage.e_tag(self.blob.name)
