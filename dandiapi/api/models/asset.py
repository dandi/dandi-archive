from __future__ import annotations

import datetime
import re
from typing import TYPE_CHECKING
from urllib.parse import urlparse, urlunparse
import uuid

from dandischema.digests.dandietag import DandiETag
from dandischema.models import AccessType
from django.conf import settings
from django.contrib.postgres.indexes import HashIndex
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django_extensions.db.models import TimeStampedModel

from dandiapi.api.models.metadata import PublishableMetadataMixin

from .version import Version

ASSET_CHARS_REGEX = r'[A-z0-9(),&\s#+~_=-]'
ASSET_PATH_REGEX = rf'^({ASSET_CHARS_REGEX}?\/?\.?{ASSET_CHARS_REGEX})+$'
ASSET_COMPUTED_FIELDS = [
    'id',
    'access',
    'path',
    'identifier',
    'contentUrl',
    'contentSize',
    'digest',
    'datePublished',
    'publishedBy',
]


class AssetStatus(models.TextChoices):
    PENDING = 'Pending'
    VALIDATING = 'Validating'
    VALID = 'Valid'
    INVALID = 'Invalid'


def validate_asset_path(path: str):
    if path.startswith('/'):
        raise ValidationError('Path must not begin with /')
    if not re.match(ASSET_PATH_REGEX, path):
        raise ValidationError('Path improperly formatted')

    return path


if TYPE_CHECKING:
    from dandiapi.zarr.models import ZarrArchive


class AssetBlob(TimeStampedModel):
    SHA256_REGEX = r'[0-9a-f]{64}'
    ETAG_REGEX = DandiETag.REGEX

    embargoed = models.BooleanField(default=False)
    blob = models.FileField(blank=True)
    blob_id = models.UUIDField(unique=True)
    sha256 = models.CharField(  # noqa: DJ001
        null=True,
        default=None,
        blank=True,
        max_length=64,
        validators=[RegexValidator(f'^{SHA256_REGEX}$')],
    )
    etag = models.CharField(
        unique=True, max_length=40, validators=[RegexValidator(f'^{ETAG_REGEX}$')]
    )
    size = models.PositiveBigIntegerField()

    class Meta:
        indexes = [HashIndex(fields=['etag'])]

    @property
    def references(self) -> int:
        return self.assets.count()

    @property
    def digest(self) -> dict[str, str]:
        digest = {'dandi:dandi-etag': self.etag}
        if self.sha256:
            digest['dandi:sha2-256'] = self.sha256
        return digest

    @property
    def s3_url(self) -> str:
        signed_url = self.blob.url
        # Strip off the query parameters from the presigning, as they are different every time
        parsed = urlparse(signed_url)
        return urlunparse((parsed[0], parsed[1], parsed[2], '', '', ''))

    def __str__(self) -> str:
        return self.blob.name


class Asset(PublishableMetadataMixin, TimeStampedModel):
    UUID_REGEX = r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}'

    asset_id = models.UUIDField(unique=True, default=uuid.uuid4)
    path = models.CharField(max_length=512, validators=[validate_asset_path], db_collation='C')
    blob = models.ForeignKey(
        AssetBlob, related_name='assets', on_delete=models.CASCADE, null=True, blank=True
    )
    zarr = models.ForeignKey(
        'zarr.ZarrArchive', related_name='assets', on_delete=models.CASCADE, null=True, blank=True
    )
    metadata = models.JSONField(blank=True, default=dict)
    versions = models.ManyToManyField(Version, related_name='assets')
    status = models.CharField(
        max_length=10,
        default=AssetStatus.PENDING,
        choices=AssetStatus,
    )
    validation_errors = models.JSONField(default=list, blank=True, null=True)
    published = models.BooleanField(default=False)

    # Let other code still refer to statuses via Asset.Status
    Status = AssetStatus

    class Meta:
        ordering = ['created']
        indexes = [
            # Other statuses are likely too common to index, but pending assets are continually
            # polled and being moved through the pipeline.
            models.Index(
                fields=['status'],
                name='%(app_label)s_%(class)s_status_pending',
                condition=Q(status=AssetStatus.PENDING),
            ),
        ]
        constraints = [
            models.CheckConstraint(
                name='blob-xor-zarr',
                condition=(
                    Q(blob__isnull=True, zarr__isnull=False)
                    | Q(blob__isnull=False, zarr__isnull=True)
                ),
            ),
            models.CheckConstraint(
                name='asset_metadata_has_schema_version',
                condition=Q(metadata__schemaVersion__isnull=False),
            ),
            models.CheckConstraint(
                name='asset_path_regex', condition=Q(path__regex=ASSET_PATH_REGEX)
            ),
            models.CheckConstraint(
                name='asset_path_no_leading_slash', condition=~Q(path__startswith='/')
            ),
            # Ensure that if the asset is published, its metadata must contain the computed fields
            # Otherwise, ensure its metadata contains none of the computed fields
            models.CheckConstraint(
                name='asset_metadata_no_computed_keys_or_published',
                condition=(
                    (Q(published=False) & ~Q(metadata__has_any_keys=ASSET_COMPUTED_FIELDS))
                    | (Q(published=True) & Q(metadata__has_keys=ASSET_COMPUTED_FIELDS))
                ),
            ),
        ]

    @property
    def is_embargoed(self) -> bool:
        if self.blob is not None:
            return self.blob.embargoed
        if self.zarr is not None:
            return self.zarr.embargoed
        raise RuntimeError('Asset must have a blob or zarr archive')

    @property
    def size(self):
        if self.blob is not None:
            return self.blob.size
        if self.zarr is not None:
            return self.zarr.size
        raise RuntimeError('Asset must have a blob or zarr archive')

    @property
    def sha256(self):
        if self.blob is not None:
            return self.blob.sha256
        raise RuntimeError('Zarr does not support SHA256')

    @property
    def digest(self) -> dict[str, str]:
        if self.blob is not None:
            return self.blob.digest
        if self.zarr is not None:
            return self.zarr.digest
        raise RuntimeError('Asset must have a blob or zarr archive')

    @property
    def s3_url(self) -> str:
        if self.blob is not None:
            return self.blob.s3_url
        if self.zarr is not None:
            return self.zarr.s3_url
        raise RuntimeError('Asset must have a blob or zarr archive')

    def is_different_from(
        self,
        *,
        asset_blob: AssetBlob | None = None,
        zarr_archive: ZarrArchive | None = None,
        metadata: dict,
        path: str,
    ) -> bool:
        from dandiapi.zarr.models import ZarrArchive

        if isinstance(asset_blob, AssetBlob) and self.blob is not None and self.blob != asset_blob:
            return True

        if (
            isinstance(zarr_archive, ZarrArchive)
            and self.zarr is not None
            and self.zarr != zarr_archive
        ):
            return True

        if self.path != path:
            return True

        if self.metadata != metadata:  # noqa: SIM103
            return True

        return False

    @staticmethod
    def dandi_asset_id(asset_id: str | uuid.UUID):
        return f'dandiasset:{asset_id}'

    @property
    def full_metadata(self):
        download_url = settings.DANDI_API_URL + reverse(
            'asset-download',
            kwargs={'asset_id': str(self.asset_id)},
        )
        metadata = {
            **self.metadata,
            'id': self.dandi_asset_id(self.asset_id),
            'access': [
                {
                    'schemaKey': 'AccessRequirements',
                    'status': AccessType.EmbargoedAccess.value
                    if self.is_embargoed
                    else AccessType.OpenAccess.value,
                }
            ],
            'path': self.path,
            'identifier': str(self.asset_id),
            'contentUrl': [download_url, self.s3_url],
            'contentSize': self.size,
            'digest': self.digest,
        }
        schema_version = metadata['schemaVersion']
        metadata['@context'] = (
            'https://raw.githubusercontent.com/dandi/schema/master/releases/'
            f'{schema_version}/context.json'
        )
        if self.zarr is not None:
            metadata['encodingFormat'] = 'application/x-zarr'
        return metadata

    def published_metadata(self):
        """Generate the metadata of this asset as if it were being published."""
        now = datetime.datetime.now(datetime.UTC)
        # Inject the publishedBy and datePublished fields
        return {
            **self.full_metadata,
            'publishedBy': self.published_by(now),
            'datePublished': now.isoformat(),
        }

    @classmethod
    def strip_metadata(cls, metadata):
        """Strip away computed fields from a metadata dict."""
        return {key: metadata[key] for key in metadata if key not in ASSET_COMPUTED_FIELDS}

    def __str__(self) -> str:
        return self.path

    @classmethod
    def total_size(cls):
        from dandiapi.zarr.models import ZarrArchive

        return sum(
            cls.objects.filter(assets__versions__isnull=False)
            .distinct()
            .aggregate(size=models.Sum('size'))['size']
            or 0
            for cls in (AssetBlob, ZarrArchive)
        )
