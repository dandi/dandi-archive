from __future__ import annotations

from typing import List, Set
import uuid

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.storage import Storage
from django.core.validators import RegexValidator
from django.db import models
from django_extensions.db.models import TimeStampedModel

from dandiapi.api.storage import DeconstructableFileField, create_s3_storage

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
    uuid = models.UUIDField(unique=True, default=uuid.uuid4)
    path = models.CharField(max_length=512)
    sha256 = models.CharField(max_length=64, validators=[RegexValidator(f'^{SHA256_REGEX}$')])

    @property
    def size(self):
        return self.blob.size

    @property
    def references(self) -> int:
        return self.assets.count()

    def __str__(self) -> str:
        return self.blob.name


class AssetMetadata(TimeStampedModel):
    metadata = JSONField(blank=True, default=dict)

    @property
    def references(self) -> int:
        return self.assets.count()

    def __str__(self) -> str:
        return str(self.metadata)

    @classmethod
    def create_or_find(cls, metadata):
        try:
            return cls.objects.get(metadata=metadata)
        except ObjectDoesNotExist:
            return cls(metadata=metadata)


class Asset(TimeStampedModel):
    UUID_REGEX = r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}'
    SHA256_REGEX = r'[0-9a-f]{64}'

    blob = models.ForeignKey(AssetBlob, related_name='assets', on_delete=models.CASCADE)
    metadata = models.ForeignKey(AssetMetadata, related_name='assets', on_delete=models.CASCADE)
    version = models.ForeignKey(Version, related_name='assets', on_delete=models.CASCADE)

    @property
    def uuid(self):
        return self.blob.uuid

    @property
    def size(self):
        return self.blob.size

    @property
    def path(self):
        return self.blob.path

    @property
    def sha256(self):
        return self.blob.sha256

    def __str__(self) -> str:
        return self.path

    @classmethod
    def copy(cls, asset, version):
        return Asset(blob=asset.blob, metadata=asset.metadata, version=version)

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
        return sum([asset.size for asset in cls.objects.all()])
        return cls.objects.values('size')
        return cls.objects.aggregate(size=models.Sum('blob__blob__size'))['size'] or 0
