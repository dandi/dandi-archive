from __future__ import annotations

import logging
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

from django.conf import settings
from django.db import models
from django_extensions.db.models import TimeStampedModel
from rest_framework.exceptions import ValidationError

from dandiapi.api.models import Dandiset
from dandiapi.api.storage import get_storage

logger = logging.getLogger(name=__name__)


# The status of the zarr ingestion (checksums, size, file count)
class ZarrArchiveStatus(models.TextChoices):
    PENDING = 'Pending'
    UPLOADED = 'Uploaded'
    INGESTING = 'Ingesting'
    COMPLETE = 'Complete'


class BaseZarrArchive(TimeStampedModel):
    UUID_REGEX = r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}'
    INGEST_ERROR_MSG = 'Zarr archive is currently ingesting or has already ingested'

    class Meta:
        ordering = ['created']
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
                    status__in=[
                        ZarrArchiveStatus.PENDING,
                        ZarrArchiveStatus.UPLOADED,
                        ZarrArchiveStatus.INGESTING,
                    ],
                )
                | models.Q(checksum__isnull=False, status=ZarrArchiveStatus.COMPLETE),
            ),
        ]

    zarr_id = models.UUIDField(unique=True, default=uuid4, db_index=True)
    name = models.CharField(max_length=512)
    file_count = models.BigIntegerField(default=0)
    size = models.BigIntegerField(default=0)
    checksum = models.CharField(max_length=512, null=True, default=None, blank=True)  # noqa: DJ001
    status = models.CharField(
        max_length=max(len(choice[0]) for choice in ZarrArchiveStatus.choices),
        choices=ZarrArchiveStatus.choices,
        default=ZarrArchiveStatus.PENDING,
    )

    @property
    def digest(self) -> dict[str, str]:
        return {'dandi:dandi-zarr-checksum': self.checksum}

    @property
    def s3_url(self):
        signed_url = self.storage.url(self.s3_path(''))
        # Strip off the query parameters from the presigning, as they are different every time
        parsed = urlparse(signed_url)
        return urlunparse((parsed[0], parsed[1], parsed[2], '', '', ''))

    def generate_upload_urls(self, path_md5s: list[dict]):
        return [
            self.storage.generate_presigned_put_object_url(self.s3_path(o['path']), o['base64md5'])
            for o in path_md5s
        ]

    def mark_pending(self):
        self.checksum = None
        self.status = ZarrArchiveStatus.PENDING
        self.file_count = 0
        self.size = 0

    def delete_files(self, paths: list[str]):
        for path in paths:
            if not self.storage.exists(self.s3_path(path)):
                raise ValidationError(f'File {self.s3_path(path)} does not exist.')
        for path in paths:
            self.storage.delete(self.s3_path(path))

        # Files deleted, mark pending
        self.mark_pending()
        self.save()


class ZarrArchive(BaseZarrArchive):
    storage = get_storage()
    dandiset = models.ForeignKey(Dandiset, related_name='zarr_archives', on_delete=models.CASCADE)

    def s3_path(self, zarr_path: str) -> str:
        """Generate a full S3 object path from a path in this zarr_archive."""
        return (
            f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}{settings.DANDI_ZARR_PREFIX_NAME}/'
            f'{self.zarr_id}/{zarr_path}'
        )


class ZarrArchiveVersion(models.Model):
    zarr = models.ForeignKey(ZarrArchive, related_name='versions', on_delete=models.CASCADE)
    version = models.UUIDField()


class ZarrArchiveFile(models.Model):
    zarr_version = models.ForeignKey(
        ZarrArchiveVersion, related_name='files', on_delete=models.CASCADE
    )

    # File info
    key = models.CharField(max_length=256, db_index=True)
    version_id = models.CharField(max_length=32)
    etag = models.CharField(max_length=32)

    # Metadata may be contained in one of three fields
    zattrs = models.JSONField(null=True)
    zarray = models.JSONField(null=True)
    zgroup = models.JSONField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(name='unique-file-data', fields=['key', 'version_id', 'etag']),
            models.UniqueConstraint(name='unique-zarr-key', fields=['zarr_version', 'key']),
            models.CheckConstraint(
                name='consistent-metadata-field',
                check=(
                    (
                        models.Q(
                            zattrs__isnull=True,
                            zarray__isnull=True,
                            zgroup__isnull=True,
                        )
                        & ~models.Q(key__endswith='.zattrs')
                        & ~models.Q(key__endswith='.zarray')
                        & ~models.Q(key__endswith='.zgroup')
                    )
                    | models.Q(
                        key__endswith='.zattrs',
                        zattrs__isnull=False,
                        zarray__isnull=True,
                        zgroup__isnull=True,
                    )
                    | models.Q(
                        key__endswith='.zarray',
                        zattrs__isnull=True,
                        zarray__isnull=False,
                        zgroup__isnull=True,
                    )
                    | models.Q(
                        key__endswith='.zgroup',
                        zattrs__isnull=True,
                        zarray__isnull=True,
                        zgroup__isnull=False,
                    )
                ),
            ),
        ]

    @property
    def is_metadata_key(self):
        return (
            self.key.endswith('.zattrs')
            or self.key.endswith('.zarray')
            or self.key.endswith('.zgroup')
        )

    @property
    def metadata(self):
        if self.key.endswith('.zattrs'):
            return self.zattrs
        if self.key.endswith('.zarray'):
            return self.zarray
        if self.key.endswith('.zgroup'):
            return self.zgroup

        return None


class EmbargoedZarrArchive(BaseZarrArchive):
    storage = get_storage()
    dandiset = models.ForeignKey(
        Dandiset, related_name='embargoed_zarr_archives', on_delete=models.CASCADE
    )

    def s3_path(self, zarr_path: str) -> str:
        """Generate a full S3 object path from a path in this zarr_archive."""
        return (
            f'{settings.DANDI_ZARR_PREFIX_NAME}/'
            f'{self.dandiset.identifier}/{self.zarr_id}/{zarr_path}'
        )
