from __future__ import annotations

import datetime
import re
from typing import TYPE_CHECKING
from urllib.parse import urlparse, urlunparse
import uuid

from django.conf import settings
from django.contrib.postgres.indexes import HashIndex
from django.core.exceptions import ValidationError
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

ASSET_CHARS_REGEX = r'[A-z0-9(),&\s#+~_=-]'
ASSET_PATH_REGEX = fr'^({ASSET_CHARS_REGEX}?\/?\.?{ASSET_CHARS_REGEX})+$'
ASSET_COMPUTED_FIELDS = [
    'id',
    'path',
    'identifier',
    'contentUrl',
    'contentSize',
    'digest',
    'datePublished',
    'publishedBy',
]


def validate_asset_path(path: str):
    if path.startswith('/'):
        raise ValidationError('Path must not begin with /')
    if not re.match(ASSET_PATH_REGEX, path):
        raise ValidationError('Path improperly formatted')

    return path


if TYPE_CHECKING:
    from dandiapi.zarr.models import EmbargoedZarrArchive, ZarrArchive


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
    download_count = models.PositiveBigIntegerField(default=0)

    class Meta:
        abstract = True
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
    path = models.CharField(max_length=512, validators=[validate_asset_path])
    blob = models.ForeignKey(
        AssetBlob, related_name='assets', on_delete=models.CASCADE, null=True, blank=True
    )
    embargoed_blob = models.ForeignKey(
        EmbargoedAssetBlob, related_name='assets', on_delete=models.CASCADE, null=True, blank=True
    )
    zarr = models.ForeignKey(
        'zarr.ZarrArchive', related_name='assets', on_delete=models.CASCADE, null=True, blank=True
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
        on_delete=models.SET_NULL,
    )
    published = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                name='exactly-one-blob',
                check=Q(blob__isnull=True, embargoed_blob__isnull=True, zarr__isnull=False)
                | Q(blob__isnull=True, embargoed_blob__isnull=False, zarr__isnull=True)
                | Q(blob__isnull=False, embargoed_blob__isnull=True, zarr__isnull=True),
            ),
            models.CheckConstraint(
                name='asset_metadata_has_schema_version',
                check=Q(metadata__schemaVersion__isnull=False),
            ),
            models.CheckConstraint(name='asset_path_regex', check=Q(path__regex=ASSET_PATH_REGEX)),
            models.CheckConstraint(
                name='asset_path_no_leading_slash', check=~Q(path__startswith='/')
            ),
            # Ensure that if the asset is published, its metadata must contain the computed fields
            # Otherwise, ensure its metadata contains none of the computed fields
            models.CheckConstraint(
                name='asset_metadata_no_computed_keys_or_published',
                check=(
                    (Q(published=False) & ~Q(metadata__has_any_keys=ASSET_COMPUTED_FIELDS))
                    | (Q(published=True) & Q(metadata__has_keys=ASSET_COMPUTED_FIELDS))
                ),
            ),
        ]

    @property
    def is_blob(self):
        return self.blob is not None

    @property
    def is_embargoed_blob(self):
        return self.embargoed_blob is not None

    @property
    def is_zarr(self):
        return self.zarr is not None

    @property
    def size(self):
        if self.is_blob:
            return self.blob.size
        elif self.is_embargoed_blob:
            return self.embargoed_blob.size
        else:
            return self.zarr.size

    @property
    def sha256(self):
        if self.is_blob:
            return self.blob.sha256
        elif self.is_embargoed_blob:
            return self.embargoed_blob.sha256

    @property
    def digest(self) -> dict[str, str]:
        if self.is_blob:
            return self.blob.digest
        elif self.is_embargoed_blob:
            return self.embargoed_blob.digest
        else:
            return self.zarr.digest

    @property
    def s3_url(self) -> str:
        if self.is_blob:
            return self.blob.s3_url
        elif self.is_embargoed_blob:
            return self.embargoed_blob.s3_url
        else:
            return self.zarr.s3_url

    def is_different_from(
        self,
        *,
        asset_blob: AssetBlob | EmbargoedAssetBlob | None = None,
        zarr_archive: ZarrArchive | EmbargoedZarrArchive | None = None,
        metadata: dict,
        path: str,
    ) -> bool:
        from dandiapi.zarr.models import EmbargoedZarrArchive, ZarrArchive

        if isinstance(asset_blob, AssetBlob) and self.blob is not None and self.blob != asset_blob:
            return True

        if (
            isinstance(asset_blob, EmbargoedAssetBlob)
            and self.embargoed_blob is not None
            and self.embargoed_blob != asset_blob
        ):
            return True

        if (
            isinstance(zarr_archive, ZarrArchive)
            and self.zarr is not None
            and self.zarr != zarr_archive
        ):
            return True

        if isinstance(zarr_archive, EmbargoedZarrArchive):
            raise NotImplementedError

        if self.path != path:
            return True

        if self.metadata != metadata:
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
        if self.is_zarr:
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
            for cls in (AssetBlob, EmbargoedAssetBlob, ZarrArchive)
            # adding of Zarrs to embargoed dandisets is not supported
            # so no point of adding EmbargoedZarr here since would also result in error
            # TODO: add EmbagoedZarr whenever supported
        )
