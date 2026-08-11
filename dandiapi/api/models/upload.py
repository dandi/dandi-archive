from __future__ import annotations

from uuid import uuid4

from dandischema.digests.dandietag import DandiETag
from django.core.validators import RegexValidator
from django.db import models
from django_extensions.db.models import CreationDateTimeField
from rest_framework.exceptions import ValidationError

from dandiapi.api.multipart import DandiS3MultipartManager

from .asset import AssetBlob
from .dandiset import Dandiset


class BaseUpload(models.Model):
    """
    The fields and behavior common to all multipart uploads.

    Subclasses define what the upload belongs to (a dandiset, a zarr, etc.), and therefore
    how its object key and embargo status are determined.
    """

    ETAG_REGEX = DandiETag.REGEX

    created = CreationDateTimeField()

    blob = models.FileField(blank=True)

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
        abstract = True
        ordering = ['created']
        indexes = [models.Index(fields=['etag'])]

    @property
    def embargoed(self) -> bool:
        raise NotImplementedError

    @classmethod
    def _initialize_multipart_upload(cls, *, size: int, object_key: str, embargoed: bool):
        """Initialize a multipart upload in the object store."""
        return DandiS3MultipartManager(cls._meta.get_field('blob').storage).initialize_upload(
            object_key,
            size,
            # The upload HTTP API does not pass the file name or content type, and it would be a
            # breaking change to start requiring this.
            'application/octet-stream',
            tags={'embargoed': 'true'} if embargoed else None,
        )

    def object_key_exists(self):
        return self.blob.storage.exists(self.blob.name)

    def actual_size(self):
        return self.blob.storage.size(self.blob.name)

    def actual_etag(self) -> str | None:
        return self.blob.storage.e_tag(self.blob.name)

    def validate_successful(self):
        if not self.object_key_exists():
            raise ValidationError('Object does not exist.')

        actual_size = self.actual_size()
        if self.size != actual_size:
            raise ValidationError(f'Size {self.size} does not match actual size {actual_size}.')

        actual_etag = self.actual_etag()
        if self.etag != actual_etag:
            raise ValidationError(f'ETag {self.etag} does not match actual ETag {actual_etag}.')


class Upload(BaseUpload):  # noqa: DJ008
    """An upload of a file which will become an asset blob."""

    dandiset = models.ForeignKey(Dandiset, related_name='uploads', on_delete=models.CASCADE)

    class Meta(BaseUpload.Meta):
        abstract = False

    @property
    def embargoed(self) -> bool:
        return self.dandiset.embargoed

    @staticmethod
    def object_key(upload_id):
        upload_id = str(upload_id)
        return f'blobs/{upload_id[0:3]}/{upload_id[3:6]}/{upload_id}'

    @classmethod
    def initialize_multipart_upload(cls, etag, size, dandiset: Dandiset):
        upload_id = uuid4()
        object_key = cls.object_key(upload_id)
        embargoed = dandiset.embargo_status == Dandiset.EmbargoStatus.EMBARGOED
        multipart_initialization = cls._initialize_multipart_upload(
            size=size, object_key=object_key, embargoed=embargoed
        )

        upload = cls(
            upload_id=upload_id,
            blob=object_key,
            etag=etag,
            size=size,
            dandiset=dandiset,
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
