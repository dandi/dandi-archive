from __future__ import annotations

from uuid import uuid4

from dandischema.digests.dandietag import DandiETag
from django.core.validators import RegexValidator
from django.db import models
from django_extensions.db.models import CreationDateTimeField
from rest_framework.exceptions import ValidationError

from dandiapi.api.multipart import DandiS3MultipartManager
from dandiapi.zarr.models import ZarrArchive

from .asset import AssetBlob
from .dandiset import Dandiset


class Upload(models.Model):  # noqa: DJ008
    ETAG_REGEX = DandiETag.REGEX

    created = CreationDateTimeField()

    # We store exactly one of either a dandiset, or a zarr, that this upload belongs to. This is to
    # eliminate a possible source of data divergence, since zarrs also point directly to dandisets.
    dandiset = models.ForeignKey(
        Dandiset, null=True, related_name='uploads', on_delete=models.CASCADE
    )
    zarr = models.ForeignKey(
        ZarrArchive, null=True, related_name='uploads', on_delete=models.CASCADE
    )

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
        ordering = ['created']
        indexes = [models.Index(fields=['etag'])]
        constraints = [
            # Ensure that there's exactly one of dandiset or zarr
            models.CheckConstraint(
                name='dandiset-zarr-xor',
                condition=models.Q(dandiset__isnull=True, zarr__isnull=False)
                | models.Q(dandiset__isnull=False, zarr__isnull=True),
            )
        ]

    @property
    def embargoed(self):
        dandiset = self.dandiset or self.zarr.dandiset
        return dandiset.embargoed

    @classmethod
    def initialize_zarr_multipart_upload(cls, etag, size, zarr: ZarrArchive, chunk_key: str):
        object_key = zarr.s3_path(chunk_key.lstrip('/'))
        upload, attrs = cls.initialize_multipart_upload(
            etag=etag, size=size, dandiset=zarr.dandiset, object_key=object_key
        )

        # Tack on zarr and remove dandiset from instantiated (but not yet saved) Upload
        upload.dandiset = None
        upload.zarr = zarr

        return upload, attrs

    @classmethod
    def initialize_multipart_upload(
        cls, etag, size, dandiset: Dandiset, object_key: str | None = None
    ):
        upload_id = uuid4()
        if object_key is None:
            upload_id_str = str(upload_id)
            object_key = f'blobs/{upload_id_str[0:3]}/{upload_id_str[3:6]}/{upload_id_str}'

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
