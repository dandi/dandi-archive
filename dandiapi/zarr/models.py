from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import models
from django_extensions.db.models import TimeStampedModel
from rest_framework.exceptions import ValidationError

from dandiapi.api.models import Dandiset

if TYPE_CHECKING:
    from dandiapi.storage import DandiS3Storage

logger = logging.getLogger(name=__name__)


# TODO: Move this somewhere better?
def zarr_s3_path(zarr_id: str, zarr_path: str = ''):
    return f'{settings.DANDI_ZARR_PREFIX_NAME}/{zarr_id}/{zarr_path}'


# The status of the zarr ingestion (checksums, size, file count)
class ZarrArchiveStatus(models.TextChoices):
    PENDING = 'Pending'
    UPLOADED = 'Uploaded'
    INGESTING = 'Ingesting'
    COMPLETE = 'Complete'


class ZarrArchive(TimeStampedModel):
    UUID_REGEX = r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}'
    INGEST_ERROR_MSG = 'Zarr archive is currently ingesting or has already ingested'
    storage: DandiS3Storage = default_storage

    class Meta:
        ordering = ['created']
        get_latest_by = 'modified'
        constraints = [
            models.UniqueConstraint(
                name='%(app_label)s-%(class)s-unique-name',
                fields=['dandiset', 'name'],
            ),
            models.CheckConstraint(
                name='%(app_label)s-%(class)s-consistent-checksum-status',
                condition=models.Q(
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

    dandiset = models.ForeignKey(Dandiset, related_name='zarr_archives', on_delete=models.CASCADE)
    zarr_id = models.UUIDField(unique=True, default=uuid4, db_index=True)
    name = models.CharField(max_length=512)
    file_count = models.BigIntegerField(default=0)
    size = models.BigIntegerField(default=0)
    checksum = models.CharField(max_length=512, null=True, default=None, blank=True)  # noqa: DJ001
    status = models.CharField(
        max_length=max(len(choice[0]) for choice in ZarrArchiveStatus.choices),
        choices=ZarrArchiveStatus,
        default=ZarrArchiveStatus.PENDING,
    )

    @property
    def embargoed(self):
        return self.dandiset.embargoed or self.dandiset.unembargo_in_progress

    @property
    def digest(self) -> dict[str, str]:
        return {'dandi:dandi-zarr-checksum': self.checksum}

    @property
    def s3_url(self):
        signed_url = self.storage.url(self.s3_path(''))
        # Strip off the query parameters from the presigning, as they are different every time
        parsed = urlparse(signed_url)
        return urlunparse((parsed[0], parsed[1], parsed[2], '', '', ''))

    def s3_path(self, zarr_path: str) -> str:
        """Generate a full S3 object path from a path in this zarr_archive."""
        return zarr_s3_path(str(self.zarr_id), zarr_path)

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
