from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import QuerySet
from django_extensions.db.models import TimeStampedModel
from rest_framework.exceptions import ValidationError
from zarr_checksum.checksum import ZarrChecksum

from dandiapi.api.models import Dandiset
from dandiapi.api.storage import get_embargo_storage, get_storage

logger = logging.Logger(name=__name__)


class ZarrUploadFileManager(models.Manager):
    def create_zarr_upload_file(
        self, zarr_archive: ZarrArchive | EmbargoedZarrArchive, path: str, **kwargs
    ):
        """
        Initialize a new ZarrUploadFile.

        blob is a field that must be saved in the DB, but is derived from the name of the zarr and
        the path of the upload in the zarr. This method exists to calculate blob and populate it
        without overwriting __init__, which has special Django semantics.
        This method should be used whenever creating a new ZarrUploadFile for saving.
        """
        blob = zarr_archive.s3_path(path)
        return zarr_archive.upload_file_class(
            zarr_archive=zarr_archive,
            path=path,
            blob=blob,
            **kwargs,
        )


class BaseZarrUploadFile(TimeStampedModel):
    ETAG_REGEX = r'[0-9a-f]{32}(-[1-9][0-9]*)?'

    class Meta:
        get_latest_by = 'modified'
        abstract = True

    objects = ZarrUploadFileManager()

    path = models.CharField(max_length=512)
    """The path relative to the zarr root"""

    etag = models.CharField(max_length=40, validators=[RegexValidator(f'^{ETAG_REGEX}$')])

    @property
    def upload_url(self) -> str:
        return self.blob.field.storage.generate_presigned_put_object_url(self.blob.name)

    def size(self) -> int:
        return self.blob.storage.size(self.blob.name)

    def actual_etag(self) -> str | None:
        return self.blob.storage.etag_from_blob_name(self.blob.name)

    def to_checksum(self) -> ZarrChecksum:
        return ZarrChecksum(name=Path(self.path).name, digest=self.etag, size=self.size())


class ZarrUploadFile(BaseZarrUploadFile):
    class Meta(BaseZarrUploadFile.Meta):
        db_table = 'api_zarruploadfile'

    blob = models.FileField(blank=True, storage=get_storage, max_length=1_000)
    """The fully qualified S3 object key"""

    zarr_archive = models.ForeignKey(
        'ZarrArchive',
        related_name='active_uploads',
        on_delete=models.CASCADE,
    )


class EmbargoedZarrUploadFile(BaseZarrUploadFile):
    class Meta(BaseZarrUploadFile.Meta):
        db_table = 'api_embargoedzarruploadfile'

    blob = models.FileField(blank=True, storage=get_embargo_storage, max_length=1_000)
    """The fully qualified S3 object key"""

    zarr_archive = models.ForeignKey(
        'EmbargoedZarrArchive',
        related_name='active_uploads',
        on_delete=models.CASCADE,
    )


# The status of the zarr ingestion (checksums, size, file count)
class ZarrArchiveStatus(models.TextChoices):
    PENDING = 'Pending'
    INGESTING = 'Ingesting'
    COMPLETE = 'Complete'


class BaseZarrArchive(TimeStampedModel):
    UUID_REGEX = r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}'
    INGEST_ERROR_MSG = 'Zarr archive already ingested'

    class Meta:
        get_latest_by = 'modified'
        abstract = True
        constraints = [
            models.UniqueConstraint(
                name='%(app_label)s-%(class)s-unique-name',
                fields=['dandiset', 'name'],
            ),
            models.CheckConstraint(
                name='%(app_label)s-%(class)s-consistent-checksum-status',
                check=models.Q(
                    checksum__isnull=True,
                    status__in=[ZarrArchiveStatus.PENDING, ZarrArchiveStatus.INGESTING],
                )
                | models.Q(checksum__isnull=False, status=ZarrArchiveStatus.COMPLETE),
            ),
        ]

    zarr_id = models.UUIDField(unique=True, default=uuid4, db_index=True)
    name = models.CharField(max_length=512)
    file_count = models.BigIntegerField(default=0)
    size = models.BigIntegerField(default=0)
    checksum = models.CharField(max_length=512, null=True, default=None)
    status = models.CharField(
        max_length=max(len(choice[0]) for choice in ZarrArchiveStatus.choices),
        choices=ZarrArchiveStatus.choices,
        default=ZarrArchiveStatus.PENDING,
    )

    @property
    def upload_in_progress(self) -> bool:
        return self.active_uploads.exists()

    @property
    def digest(self) -> dict[str, str]:
        return {'dandi:dandi-zarr-checksum': self.checksum}

    @property
    def s3_url(self):
        signed_url = self.storage.url(self.s3_path(''))
        # Strip off the query parameters from the presigning, as they are different every time
        parsed = urlparse(signed_url)
        s3_url = urlunparse((parsed[0], parsed[1], parsed[2], '', '', ''))
        return s3_url

    def generate_upload_urls(self, paths: list[str]):
        return [
            self.storage.generate_presigned_put_object_url(self.s3_path(path)) for path in paths
        ]

    def mark_pending(self):
        self.checksum = None
        self.status = ZarrArchiveStatus.PENDING
        self.file_count = 0
        self.size = 0

    def begin_upload(self, files):
        if self.upload_in_progress:
            raise ValidationError('Simultaneous uploads are not allowed.')

        # Create upload objects
        uploads = [
            self.upload_file_class.objects.create_zarr_upload_file(
                zarr_archive=self,
                path=file['path'],
                etag=file['etag'],
            )
            for file in files
        ]
        self.upload_file_class.objects.bulk_create(uploads)
        return uploads

    def complete_upload(self):
        if not self.upload_in_progress:
            raise ValidationError('No upload in progress.')
        active_uploads: QuerySet[
            ZarrUploadFile | EmbargoedZarrUploadFile
        ] = self.active_uploads.all()
        for upload in active_uploads:
            etag = upload.actual_etag()
            if etag is None:
                raise ValidationError(f'File {upload.path} does not exist.')

            if upload.etag != etag:
                raise ValidationError(
                    f'File {upload.path} ETag {upload.actual_etag()} does not match reported checksum {upload.etag}.'  # noqa: E501
                )

        active_uploads.delete()

        # New files added, ingest must be run again
        self.checksum = None
        self.status = ZarrArchiveStatus.PENDING
        self.save()

    def cancel_upload(self):
        active_uploads: QuerySet[
            ZarrUploadFile | EmbargoedZarrUploadFile
        ] = self.active_uploads.all()
        for upload in active_uploads:
            upload.blob.delete()
        active_uploads.delete()
        # TODO this does not revoke the presigned upload URLs.
        # A client could start an upload, cache the presigned upload URLs, cancel the upload,
        # start a new upload, complete it, then use the first presigned upload URLs to upload
        # arbitrary content without any checksumming.

    def delete_files(self, paths: list[str]):
        if self.upload_in_progress:
            raise ValidationError('Cannot delete files while an upload is in progress.')
        for path in paths:
            if not self.storage.exists(self.s3_path(path)):
                raise ValidationError(f'File {self.s3_path(path)} does not exist.')
        for path in paths:
            self.storage.delete(self.s3_path(path))

        # Files deleted, mark pending
        self.mark_pending()
        self.save()


class ZarrArchive(BaseZarrArchive):
    class Meta(BaseZarrArchive.Meta):
        db_table = 'api_zarrarchive'

    storage = get_storage()
    upload_file_class = ZarrUploadFile

    dandiset = models.ForeignKey(Dandiset, related_name='zarr_archives', on_delete=models.CASCADE)

    def s3_path(self, zarr_path: str | Path):
        """Generate a full S3 object path from a path in this zarr_archive."""
        return f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}{settings.DANDI_ZARR_PREFIX_NAME}/{self.zarr_id}/{str(zarr_path)}'  # noqa: E501


class EmbargoedZarrArchive(BaseZarrArchive):
    class Meta(BaseZarrArchive.Meta):
        db_table = 'api_embargoedzarrarchive'

    storage = get_embargo_storage()
    upload_file_class = EmbargoedZarrUploadFile

    dandiset = models.ForeignKey(
        Dandiset, related_name='embargoed_zarr_archives', on_delete=models.CASCADE
    )

    def s3_path(self, zarr_path: str | Path):
        """Generate a full S3 object path from a path in this zarr_archive."""
        return f'{settings.DANDI_DANDISETS_EMBARGO_BUCKET_PREFIX}{settings.DANDI_ZARR_PREFIX_NAME}/{self.dandiset.identifier}/{self.zarr_id}/{str(zarr_path)}'  # noqa: E501
