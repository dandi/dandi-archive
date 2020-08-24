from __future__ import annotations

import hashlib
import logging
from tempfile import NamedTemporaryFile
from typing import List, Set
import uuid

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.core.files import File
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Sum

from dandi.publish.girder import GirderClient, GirderFile
from dandi.publish.storage import create_s3_storage

from .version import Version

logger = logging.getLogger(__name__)


def _get_asset_blob_prefix(instance: Asset, filename: str) -> str:
    return f'{instance.version.dandiset.identifier}/{instance.version.version}/{filename}'


class Asset(models.Model):  # TODO: was NwbFile
    UUID_REGEX = r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}'
    SHA256_REGEX = r'[0-9a-f]{64}'

    version = models.ForeignKey(
        Version, related_name='assets', on_delete=models.CASCADE
    )  # used to be called dandiset
    uuid = models.UUIDField(unique=True, default=uuid.uuid4)

    path = models.CharField(max_length=512)
    size = models.BigIntegerField()
    sha256 = models.CharField(max_length=64, validators=[RegexValidator(f'^{SHA256_REGEX}$')],)
    metadata = JSONField(blank=True, default=dict)

    blob = models.FileField(
        blank=True,
        storage=create_s3_storage(settings.DANDI_DANDISETS_BUCKET_NAME),
        upload_to=_get_asset_blob_prefix,
    )

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['uuid']),
            models.Index(fields=['version', 'path']),
        ]
        ordering = ['version', 'path']

    # objects = SelectRelatedManager('version__dandiset')

    def __str__(self) -> str:
        return self.path

    @classmethod
    def from_girder(cls, version: Version, girder_file: GirderFile, client: GirderClient) -> Asset:
        sha256_hasher = hashlib.sha256()
        blob_size = 0

        with NamedTemporaryFile('r+b') as local_stream:

            logger.info(f'Downloading file {girder_file.girder_id}')
            with client.iter_file_content(girder_file.girder_id) as file_content_iter:
                for chunk in file_content_iter:
                    sha256_hasher.update(chunk)
                    blob_size += len(chunk)
                    local_stream.write(chunk)
            logger.info(f'Downloaded file {girder_file.girder_id}')

            local_stream.seek(0)
            # local_path = Path(local_stream.name)
            sha256 = sha256_hasher.hexdigest()

            blob = File(file=local_stream, name=girder_file.path.lstrip('/'),)
            # content_type is not part of the base File class (it on some other subclasses),
            # but regardless S3Boto3Storage will respect and use it, if it's set
            blob.content_type = 'application/octet-stream'

            asset = Asset(
                version=version,
                path=girder_file.path,
                size=blob_size,
                sha256=sha256,
                metadata=girder_file.metadata,
                blob=blob,
            )
            # The actual upload of blob occurs when the asset is saved
            asset.save()
        return asset

    @classmethod
    def get_path(cls, path_prefix: str, qs: List[str]) -> Set:
        """
        Return the unique files/directories that directly reside under the specified path.

        The specified path must be a folder (must end with a slash).
        """
        if not path_prefix:
            path_prefix = '/'
        prefix_parts = [part for part in path_prefix.split('/') if part]
        paths = set()
        for asset in qs:
            path_parts = [part for part in asset['path'].split('/') if part]

            # Pivot index is -1 (include all path parts) if prefix is '/'
            pivot_index = path_parts.index(prefix_parts[-1]) if len(prefix_parts) else -1
            base_path, *remainder = path_parts[pivot_index + 1 :]
            paths.add(f'{base_path}/' if len(remainder) else base_path)

        return sorted(paths)

    @classmethod
    def total_size(cls):
        return cls.objects.aggregate(size=Sum('size'))['size'] or 0
