from __future__ import annotations

from typing import List, Set
import uuid

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.contrib.postgres.indexes import HashIndex
from django.core.files.storage import Storage
from django.core.validators import RegexValidator
from django.db import models
from django_extensions.db.models import TimeStampedModel

from dandiapi.api.copy import copy_object
from dandiapi.api.storage import DeconstructableFileField, create_s3_storage

from .validation import Validation
from .version import Version


def _get_asset_blob_storage() -> Storage:
    return create_s3_storage(settings.DANDI_DANDISETS_BUCKET_NAME)


def _get_asset_blob_prefix(instance: AssetBlob, filename: str) -> str:
    # return f'{instance.version.dandiset.identifier}/{instance.version.version}/{filename}'
    return filename


class AssetBlob(TimeStampedModel):
    SHA256_REGEX = r'[0-9a-f]{64}'

    blob = DeconstructableFileField(
        blank=True, storage=_get_asset_blob_storage, upload_to=_get_asset_blob_prefix
    )
    sha256 = models.CharField(max_length=64, validators=[RegexValidator(f'^{SHA256_REGEX}$')])
    size = models.PositiveBigIntegerField()

    class Meta:
        indexes = [HashIndex(fields=['sha256'])]

    @property
    def references(self) -> int:
        return self.assets.count()

    def __str__(self) -> str:
        return self.blob.name

    @classmethod
    def from_validation(cls, validation: Validation):
        """
        Create an AssetBlob from a Validation if necessary.

        This operation includes copying the object from the uploads zone to the blobs zone,
        and deleting the blob from the uploads zone.
        """
        try:
            # Use an existing AssetBlob if one already exists
            # This should be preemptively checked in the /uploads/validate/ endpoint, but
            # just in case a task gets run twice, we don't want to copy it twice.
            return cls.objects.get(sha256=validation.sha256), False
        except cls.DoesNotExist:
            # Copy the data from the upload zone to the blob zone
            size = validation.blob.size
            destination = (
                f'blobs/{validation.sha256[0:3]}/{validation.sha256[3:6]}/{validation.sha256[6:]}'
            )
            copy_object(validation, destination)
            return cls(blob=destination, sha256=validation.sha256, size=size), True


class AssetMetadata(TimeStampedModel):
    metadata = JSONField(blank=True, unique=True, default=dict)

    @property
    def references(self) -> int:
        return self.assets.count()

    def __str__(self) -> str:
        return str(self.metadata)


class Asset(TimeStampedModel):
    UUID_REGEX = r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}'

    uuid = models.UUIDField(unique=True, default=uuid.uuid4)
    path = models.CharField(max_length=512)
    blob = models.ForeignKey(AssetBlob, related_name='assets', on_delete=models.CASCADE)
    metadata = models.ForeignKey(AssetMetadata, related_name='assets', on_delete=models.CASCADE)
    version = models.ForeignKey(Version, related_name='assets', on_delete=models.CASCADE)

    class Meta:
        unique_together = ['path', 'version']

    @property
    def size(self):
        return self.blob.size

    @property
    def sha256(self):
        return self.blob.sha256

    def _populate_metadata(self):
        new: AssetMetadata
        new, created = AssetMetadata.objects.get_or_create(
            metadata={
                **self.metadata.metadata,
                'path': self.path,
            },
        )

        if created:
            new.save()

        self.metadata = new

    def save(self, *args, **kwargs):
        self._populate_metadata()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.path

    @classmethod
    def copy(cls, asset, version):
        return Asset(path=asset.path, blob=asset.blob, metadata=asset.metadata, version=version)

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
        return cls.objects.aggregate(size=models.Sum('blob__size'))['size'] or 0
