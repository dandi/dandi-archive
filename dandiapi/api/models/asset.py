from __future__ import annotations

import datetime
from typing import Dict
from urllib.parse import urlparse, urlunparse
import uuid

from django.contrib.postgres.indexes import HashIndex
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django_extensions.db.models import TimeStampedModel

from dandiapi.api.models.metadata import PublishableMetadataMixin
from dandiapi.api.storage import (
    get_embargo_storage,
    get_embargo_storage_prefix,
    get_storage,
    get_storage_prefix,
)

from .dandiset import Dandiset
from .version import Version


class BaseAssetBlob(TimeStampedModel):
    SHA256_REGEX = r'[0-9a-f]{64}'
    ETAG_REGEX = r'[0-9a-f]{32}(-[1-9][0-9]*)?'

    blob_id = models.UUIDField(unique=True)
    sha256 = models.CharField(
        null=True,
        blank=True,
        max_length=64,
        validators=[RegexValidator(f'^{SHA256_REGEX}$')],
    )
    etag = models.CharField(max_length=40, validators=[RegexValidator(f'^{ETAG_REGEX}$')])
    size = models.PositiveBigIntegerField()

    class Meta:
        abstract = True
        indexes = [HashIndex(fields=['etag'])]

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
        # Strip off the query parameters from the presigning, as they are different every time
        parsed = urlparse(signed_url)
        s3_url = urlunparse((parsed[0], parsed[1], parsed[2], '', '', ''))
        return s3_url

    def __str__(self) -> str:
        return self.blob.name


class AssetBlob(BaseAssetBlob):
    blob = models.FileField(blank=True, storage=get_storage, upload_to=get_storage_prefix)

    class Meta(BaseAssetBlob.Meta):
        constraints = [
            models.UniqueConstraint(
                name='unique-etag-size',
                fields=['etag', 'size'],
            )
        ]


class EmbargoedAssetBlob(BaseAssetBlob):
    blob = models.FileField(
        blank=True, storage=get_embargo_storage, upload_to=get_embargo_storage_prefix
    )
    dandiset = models.ForeignKey(
        Dandiset, related_name='embargoed_asset_blobs', on_delete=models.CASCADE
    )

    class Meta(BaseAssetBlob.Meta):
        constraints = [
            models.UniqueConstraint(
                name='unique-embargo-etag-size',
                fields=['dandiset', 'etag', 'size'],
            )
        ]


class Asset(PublishableMetadataMixin, TimeStampedModel):
    UUID_REGEX = r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}'

    class Status(models.TextChoices):
        PENDING = 'Pending'
        VALIDATING = 'Validating'
        VALID = 'Valid'
        INVALID = 'Invalid'

    asset_id = models.UUIDField(unique=True, default=uuid.uuid4)
    path = models.CharField(max_length=512)
    blob = models.ForeignKey(
        AssetBlob, related_name='assets', on_delete=models.CASCADE, null=True, blank=True
    )
    embargoed_blob = models.ForeignKey(
        EmbargoedAssetBlob, related_name='assets', on_delete=models.CASCADE, null=True, blank=True
    )
    zarr = models.ForeignKey(
        'ZarrArchive', related_name='assets', on_delete=models.CASCADE, null=True, blank=True
    )
    metadata = models.JSONField(blank=True, default=dict)
    versions = models.ManyToManyField(Version, related_name='assets')
    status = models.CharField(
        max_length=10,
        default=Status.PENDING,
        choices=Status.choices,
    )
    validation_errors = models.JSONField(default=list, blank=True, null=True)
    previous = models.ForeignKey(
        'Asset',
        blank=True,
        null=True,
        default=None,
        on_delete=models.PROTECT,
    )
    published = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                name='exactly-one-blob',
                check=Q(blob__isnull=True, embargoed_blob__isnull=True, zarr__isnull=False)
                | Q(blob__isnull=True, embargoed_blob__isnull=False, zarr__isnull=True)
                | Q(blob__isnull=False, embargoed_blob__isnull=True, zarr__isnull=True),
            )
        ]

    @property
    def is_blob(self):
        return self.blob is not None and self.zarr is None

    @property
    def is_zarr(self):
        return self.zarr is not None and self.blob is None

    @property
    def size(self):
        if self.is_blob:
            return self.blob.size
        else:
            return self.zarr.size

    @property
    def sha256(self):
        return self.blob.sha256

    @property
    def digest(self) -> Dict[str, str]:
        if self.is_blob:
            return self.blob.digest
        else:
            return self.zarr.digest

    def _populate_metadata(self):
        # TODO use http://localhost:8000 for local deployments
        download_url = 'https://api.dandiarchive.org' + reverse(
            'asset-direct-download',
            kwargs={'asset_id': str(self.asset_id)},
        )
        if self.is_blob:
            s3_url = self.blob.s3_url
        else:
            s3_url = self.zarr.s3_url

        metadata = {
            **self.metadata,
            'id': f'dandiasset:{self.asset_id}',
            'path': self.path,
            'identifier': str(self.asset_id),
            'contentUrl': [download_url, s3_url],
            'contentSize': self.size,
            'digest': self.digest,
        }
        if 'schemaVersion' in metadata:
            schema_version = metadata['schemaVersion']
            metadata['@context'] = (
                'https://raw.githubusercontent.com/dandi/schema/master/releases/'
                f'{schema_version}/context.json'
            )
        if self.is_zarr:
            metadata['encodingFormat'] = 'application/x-zarr'
        return metadata

    def published_metadata(self):
        """Generate the metadata of this asset as if it were being published."""
        now = datetime.datetime.now(datetime.timezone.utc)
        # Inject the publishedBy and datePublished fields
        return {
            **self.metadata,
            'publishedBy': self.published_by(now),
            'datePublished': now.isoformat(),
        }

    def publish(self):
        """
        Modify the metadata of this asset as if it were being published.

        This is useful to validate asset metadata without saving it.
        To actually publish this Asset, simply save() after calling publish().
        """
        # These fields need to be listed in the bulk_update() in VersionViewSet#publish.
        self.metadata = self.published_metadata()
        self.published = True

    def save(self, *args, **kwargs):
        self.metadata = self._populate_metadata()
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
    def total_size(cls):
        return (
            AssetBlob.objects.filter(assets__versions__isnull=False)
            .distinct()
            .aggregate(size=models.Sum('size'))['size']
            or 0
        )
