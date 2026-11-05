from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import uuid4

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import models
from django_extensions.db.models import TimeStampedModel
from rest_framework import status
from rest_framework.exceptions import ValidationError

from dandiapi.api.models import Dandiset, Version
from dandiapi.api.services.exceptions import DandiError

if TYPE_CHECKING:
    from dandiapi.storage import DandiS3Storage

logger = logging.getLogger(name=__name__)


# TODO: Move this somewhere better?
def zarr_s3_path(zarr_id: str, zarr_path: str = ''):
    return f'{settings.DANDI_ZARR_PREFIX_NAME}/{zarr_id}/{zarr_path}'


def validate_zarr_path(path: str) -> str:
    """
    Reject zarr paths that could traverse outside the zarr archive's S3 prefix.

    User-supplied paths are interpolated into an S3 key of the form
    ``{DANDI_ZARR_PREFIX_NAME}/{zarr_id}/{path}``. django-storages' ``clean_name``
    runs ``posixpath.normpath`` -- which collapses ``..`` -- *before* its
    ``safe_join`` guard, and the storage ``location`` is empty, so ``safe_join``
    only blocks escaping the (non-representable) bucket root. A ``..`` segment
    therefore resolves to an arbitrary key elsewhere in the bucket, permitting
    reads, overwrites, and deletes of unrelated objects. Reject any such segment.

    Backslashes are normalized to forward slashes before the check because
    ``clean_name`` performs the same replacement *after* normpath, which would
    otherwise let a segment containing backslashes survive normpath and then
    re-form a traversal sequence in the final key.
    """
    if any(segment == '..' for segment in path.replace('\\', '/').split('/')):
        raise ValidationError('Zarr path cannot contain ".." components.')
    return path


class ZarrArchivePublishedError(DandiError):
    http_status_code = status.HTTP_400_BAD_REQUEST
    message = (
        'This zarr archive has been published and can no longer be modified. '
        'To make changes, re-upload the data as a new zarr archive.'
    )


class ZarrArchiveDandisetPublishingError(DandiError):
    http_status_code = status.HTTP_423_LOCKED
    message = (
        'The dandiset containing this zarr archive is currently being published. '
        'Please try again once publishing has completed.'
    )


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
            # With this constraint in place, each version is guaranteed to contain uniquely named
            # zarrs, but the same name can exist across multiple versions. This makes sense in the
            # case where a zarr needs to be modified after publish, and thus must be re-uploaded to
            # the same dandiset again, since published zarrs are immutable.
            models.UniqueConstraint(
                name='%(app_label)s-%(class)s-unique-unpublished-name',
                fields=['dandiset', 'name'],
                condition=models.Q(published=False),
            ),
            models.CheckConstraint(
                name='%(app_label)s-%(class)s-published-is-complete',
                condition=models.Q(published=False) | models.Q(status=ZarrArchiveStatus.COMPLETE),
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
    # Once set (during dandiset publish), the contents of this zarr archive may never change.
    published = models.BooleanField(default=False)

    @property
    def embargoed(self):
        return self.dandiset.embargoed or self.dandiset.unembargo_in_progress

    @property
    def digest(self) -> dict[str, str]:
        return {'dandi:dandi-zarr-checksum': self.checksum}

    @property
    def s3_url(self):
        return self.storage.url(self.s3_path(''), signed=False)

    def s3_path(self, zarr_path: str) -> str:
        """Generate a full S3 object path from a path in this zarr_archive."""
        return zarr_s3_path(str(self.zarr_id), zarr_path)

    def ensure_modifiable(self) -> None:
        """
        Raise an error if this zarr archive may not be modified.

        The caller should hold a row lock on this zarr archive (``select_for_update``), so that
        the check can't race with the dandiset publish process, which locks zarr archives
        before checking or changing the draft version status.
        """
        if self.published:
            raise ZarrArchivePublishedError
        if Version.objects.filter(
            dandiset_id=self.dandiset_id,
            version='draft',
            status=Version.Status.PUBLISHING,
        ).exists():
            raise ZarrArchiveDandisetPublishingError

    def mark_pending(self):
        if self.published:
            raise ZarrArchivePublishedError
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
