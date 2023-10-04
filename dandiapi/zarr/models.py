from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

from django.conf import settings
from django.db import models
from django_extensions.db.models import TimeStampedModel
from rest_framework.exceptions import ValidationError

from dandiapi.api.models import Dandiset
from dandiapi.api.storage import get_embargo_storage, get_storage

logger = logging.Logger(name=__name__)


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
    def digest(self) -> dict[str, str]:
        return {'dandi:dandi-zarr-checksum': self.checksum}

    @property
    def s3_url(self):
        signed_url = self.storage.url(self.s3_path(''))
        # Strip off the query parameters from the presigning, as they are different every time
        parsed = urlparse(signed_url)
        s3_url = urlunparse((parsed[0], parsed[1], parsed[2], '', '', ''))
        return s3_url

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

    def s3_path(self, zarr_path: str | Path):
        """Generate a full S3 object path from a path in this zarr_archive."""
        return f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}{settings.DANDI_ZARR_PREFIX_NAME}/{self.zarr_id}/{str(zarr_path)}'  # noqa: E501


class EmbargoedZarrArchive(BaseZarrArchive):
    storage = get_embargo_storage()
    dandiset = models.ForeignKey(
        Dandiset, related_name='embargoed_zarr_archives', on_delete=models.CASCADE
    )

    def s3_path(self, zarr_path: str | Path):
        """Generate a full S3 object path from a path in this zarr_archive."""
        return f'{settings.DANDI_DANDISETS_EMBARGO_BUCKET_PREFIX}{settings.DANDI_ZARR_PREFIX_NAME}/{self.dandiset.identifier}/{self.zarr_id}/{str(zarr_path)}'  # noqa: E501
