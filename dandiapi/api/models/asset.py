from __future__ import annotations

import datetime
from typing import Dict, List, Set
from urllib.parse import urlparse, urlunparse
import uuid

from django.conf import settings
from django.contrib.postgres.indexes import HashIndex
from django.core.files.storage import Storage
from django.core.validators import RegexValidator
from django.db import models
from django.urls import reverse
from django_extensions.db.models import TimeStampedModel

from dandiapi.api.models.metadata import PublishableMetadataMixin
from dandiapi.api.storage import create_s3_storage

from .version import Version


def get_asset_blob_storage() -> Storage:
    return create_s3_storage(settings.DANDI_DANDISETS_BUCKET_NAME)


def get_asset_blob_prefix(instance: AssetBlob, filename: str) -> str:
    return f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}{filename}'


class AssetBlob(TimeStampedModel):
    SHA256_REGEX = r'[0-9a-f]{64}'
    ETAG_REGEX = r'[0-9a-f]{32}(-[1-9][0-9]*)?'

    blob_id = models.UUIDField(unique=True)
    blob = models.FileField(
        blank=True, storage=get_asset_blob_storage, upload_to=get_asset_blob_prefix
    )
    sha256 = models.CharField(
        null=True,
        blank=True,
        max_length=64,
        validators=[RegexValidator(f'^{SHA256_REGEX}$')],
    )
    etag = models.CharField(max_length=40, validators=[RegexValidator(f'^{ETAG_REGEX}$')])
    size = models.PositiveBigIntegerField()

    class Meta:
        indexes = [HashIndex(fields=['etag'])]
        constraints = [
            models.UniqueConstraint(
                name='unique-etag-size',
                fields=['etag', 'size'],
            )
        ]

    @property
    def references(self) -> int:
        return self.assets.count()

    @property
    def digest(self) -> Dict[str, str]:
        digest = {'dandi:dandi-etag': self.etag}
        if self.sha256:
            digest['dandi:sha2-256'] = self.sha256
        return digest

    @property
    def s3_url(self) -> str:
        signed_url = self.blob.url
        parsed = urlparse(signed_url)
        s3_url = urlunparse((parsed[0], parsed[1], parsed[2], '', '', ''))
        return s3_url

    def __str__(self) -> str:
        return self.blob.name


class AssetMetadata(PublishableMetadataMixin, TimeStampedModel):
    metadata = models.JSONField(blank=True, unique=True, default=dict)

    @property
    def references(self) -> int:
        return self.assets.count()

    def __str__(self) -> str:
        return str(self.metadata)


class Asset(TimeStampedModel):
    UUID_REGEX = r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}'

    class Status(models.TextChoices):
        PENDING = 'Pending'
        VALIDATING = 'Validating'
        VALID = 'Valid'
        INVALID = 'Invalid'

    asset_id = models.UUIDField(unique=True, default=uuid.uuid4)
    path = models.CharField(max_length=512)
    blob = models.ForeignKey(AssetBlob, related_name='assets', on_delete=models.CASCADE)
    metadata = models.ForeignKey(AssetMetadata, related_name='assets', on_delete=models.CASCADE)
    versions = models.ManyToManyField(Version, related_name='assets')
    status = models.CharField(
        max_length=10,
        default=Status.PENDING,
        choices=Status.choices,
    )
    validation_error = models.TextField(default='')
    previous = models.ForeignKey(
        'Asset',
        blank=True,
        null=True,
        default=None,
        on_delete=models.PROTECT,
    )
    published = models.BooleanField(default=False)

    @property
    def size(self):
        return self.blob.size

    @property
    def sha256(self):
        return self.blob.sha256

    def _populate_metadata(self):
        # TODO use http://localhost:8000 for local deployments
        download_url = 'https://api.dandiarchive.org' + reverse(
            'asset-direct-download',
            kwargs={'asset_id': str(self.asset_id)},
        )
        blob_url = self.blob.s3_url

        metadata = {
            **self.metadata.metadata,
            'id': str(self.asset_id),
            'path': self.path,
            'identifier': str(self.asset_id),
            'contentUrl': [download_url, blob_url],
            'contentSize': self.blob.size,
            'digest': self.blob.digest,
        }
        return metadata

    @classmethod
    def published_asset(cls, asset: Asset):
        """
        Generate a published asset + metadata without saving it.

        This is useful to validate asset metadata without saving it.
        """
        now = datetime.datetime.utcnow()
        # Inject the publishedBy and datePublished fields
        published_metadata, _ = AssetMetadata.objects.get_or_create(
            metadata={
                **asset.metadata.metadata,
                'publishedBy': asset.metadata.published_by(now),
                'datePublished': now.isoformat(),
            },
        )

        # Create the published model
        published_asset = Asset(
            path=asset.path,
            blob=asset.blob,
            metadata=published_metadata,
            # If we're publishing, just assume that the asset was valid
            status=Asset.Status.VALID,
            previous=asset,
            published=True,
        )

        # Recompute the metadata
        published_metadata, _ = AssetMetadata.objects.get_or_create(
            metadata=published_asset._populate_metadata(),
        )
        published_asset.metadata = published_metadata

        return published_asset

    def save(self, *args, **kwargs):
        metadata = self._populate_metadata()
        new, created = AssetMetadata.objects.get_or_create(metadata=metadata)
        if created:
            new.save()
        self.metadata = new
        super().save(*args, **kwargs)

    @classmethod
    def strip_metadata(cls, metadata):
        """Strip away computed fields from a metadata dict."""
        computed_fields = [
            'id',
            'path',
            'identifier',
            'contentUrl',
            'contentSize',
            'digest',
            'datePublished',
            'publishedBy',
        ]
        return {key: metadata[key] for key in metadata if key not in computed_fields}

    def __str__(self) -> str:
        return self.path

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
