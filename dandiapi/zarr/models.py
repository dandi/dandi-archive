from __future__ import annotations

import base64
import binascii
import logging
from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from uuid import uuid4

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import models
from django_extensions.db.models import TimeStampedModel
from rest_framework.exceptions import ValidationError
from storages.utils import clean_name

from dandiapi.api.models import Dandiset

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


def validate_base64_md5(value: str) -> str:
    """Ensure a value is a base64 encoded MD5 digest, as used in a Content-MD5 header."""
    try:
        digest = base64.b64decode(value, validate=True)
    except binascii.Error as e:
        raise ValidationError('Not a valid base64 encoded MD5 digest.') from e
    if len(digest) != 16:
        raise ValidationError('Not a valid base64 encoded MD5 digest.')
    return value


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
    # If ingestion was deferred due to upload URLs which could still modify this zarr, the time at
    # which they expire, and ingestion will be retried. Uploading the content those URLs were
    # issued for allows ingestion to proceed immediately instead.
    ingestion_deferred_until = models.DateTimeField(null=True, blank=True, default=None)

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

    def relative_s3_path(self, zarr_path: str) -> str:
        """
        Return the path of a file in this zarr archive, exactly as it will be listed from S3.

        User-supplied paths are normalized when converted to an S3 key, so this mirrors that
        normalization, as well as the conversion back to a relative path performed by
        ``zarr_checksum.generators.yield_files_s3``.
        """
        return str(PurePosixPath(clean_name(self.s3_path(zarr_path))).relative_to(self.s3_path('')))

    def mark_pending(self):
        self.checksum = None
        self.status = ZarrArchiveStatus.PENDING
        self.ingestion_deferred_until = None
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


class ZarrUploadURL(models.Model):
    """
    A presigned upload URL issued for a file in a zarr archive.

    Presigned URLs can't be revoked, so they remain usable until they expire, even after the
    zarr archive has been ingested or published. However, each URL is signed with the MD5 of the
    file's content, and can therefore only ever write that exact content to that exact path. A URL
    is harmless as long as the file at its path already has that content, as using it again would
    not change anything. Tracking issued URLs allows ingestion to verify this, ensuring that a
    zarr archive's contents can't change once it's marked as COMPLETE.
    """

    zarr_archive = models.ForeignKey(
        ZarrArchive, related_name='upload_urls', on_delete=models.CASCADE
    )
    # The path of the file, relative to the zarr root, as returned by `relative_s3_path`
    path = models.TextField()
    # The hex encoded MD5 of the content this URL permits uploading, comparable to an S3 ETag
    md5 = models.CharField(max_length=32)
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        indexes = [models.Index(fields=['zarr_archive', 'expires_at'])]

    def __str__(self) -> str:
        return f'{self.zarr_archive.zarr_id}/{self.path}'

    @staticmethod
    def base64_md5_to_hex(base64md5: str) -> str:
        return base64.b64decode(base64md5).hex()
