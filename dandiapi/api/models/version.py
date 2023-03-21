from __future__ import annotations

import datetime
import logging

from django.conf import settings
from django.contrib.postgres.indexes import HashIndex
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.query_utils import Q
from django_extensions.db.models import TimeStampedModel

from dandiapi.api.asset_paths import get_root_paths
from dandiapi.api.models.metadata import PublishableMetadataMixin

from .dandiset import Dandiset

logger = logging.getLogger(__name__)


class Version(PublishableMetadataMixin, TimeStampedModel):
    VERSION_REGEX = r'(0\.\d{6}\.\d{4})|draft'

    class Status(models.TextChoices):
        PENDING = 'Pending'
        VALIDATING = 'Validating'
        VALID = 'Valid'
        INVALID = 'Invalid'
        PUBLISHING = 'Publishing'
        PUBLISHED = 'Published'

    dandiset = models.ForeignKey(Dandiset, related_name='versions', on_delete=models.CASCADE)
    name = models.CharField(max_length=300)
    metadata = models.JSONField(blank=True, default=dict)
    version = models.CharField(
        max_length=13,
        validators=[RegexValidator(f'^{VERSION_REGEX}$')],
    )
    doi = models.CharField(max_length=64, null=True, blank=True)
    """Track the validation status of this version, without considering assets"""
    status = models.CharField(
        max_length=10,
        default=Status.PENDING,
        choices=Status.choices,
    )
    validation_errors = models.JSONField(default=list, blank=True, null=True)

    class Meta:
        unique_together = ['dandiset', 'version']
        constraints = [
            models.CheckConstraint(
                name='version_metadata_has_schema_version',
                check=Q(metadata__schemaVersion__isnull=False),
            )
        ]
        indexes = [
            HashIndex(fields=['metadata']),
            HashIndex(fields=['name']),
        ]

    @property
    def asset_count(self):
        return get_root_paths(self).aggregate(nfiles=models.Sum('aggregate_files'))['nfiles'] or 0

    @property
    def size(self):
        return (
            get_root_paths(self).aggregate(total_size=models.Sum('aggregate_size'))['total_size']
            or 0
        )

    @property
    def valid(self) -> bool:
        if self.status != Version.Status.VALID:
            return False

        # Import here to avoid dependency cycle
        from .asset import Asset

        # Return False if any asset is not VALID
        return not self.assets.exclude(status=Asset.Status.VALID).exists()

    @property
    def publish_status(self) -> Version.Status:
        if self.status != Version.Status.VALID:
            return self.status

        # Import here to avoid dependency cycle
        from .asset import Asset

        invalid_asset = self.assets.exclude(status=Asset.Status.VALID).first()
        if invalid_asset:
            return Version.Status.INVALID

        return Version.Status.VALID

    @property
    def asset_validation_errors(self) -> list[str]:
        # Import here to avoid dependency cycle
        from .asset import Asset

        # Assets that are not VALID (could be pending, validating, or invalid)
        invalid_assets = self.assets.filter(status=Asset.Status.INVALID).values('validation_errors')

        errors = [
            error
            for invalid_asset in invalid_assets
            for error in invalid_asset['validation_errors']
        ]

        # Assets that have not yet been validated (could be pending or validating)
        unvalidated_assets = self.assets.filter(
            ~(models.Q(status=Asset.Status.VALID) | models.Q(status=Asset.Status.INVALID))
        ).values('path')

        errors += [
            {
                'field': unvalidated_asset['path'],
                'message': 'asset is currently being validated, please wait.',
            }
            for unvalidated_asset in unvalidated_assets
        ]

        return errors

    @staticmethod
    def datetime_to_version(time: datetime.datetime) -> str:
        return time.strftime('0.%y%m%d.%H%M')

    @classmethod
    def next_published_version(cls, dandiset: Dandiset) -> str:
        time = datetime.datetime.now(datetime.timezone.utc)
        # increment time until there are no collisions
        while True:
            version = cls.datetime_to_version(time)
            collision = dandiset.versions.filter(version=version).exists()
            if not collision:
                break
            time += datetime.timedelta(minutes=1)

        return version

    @classmethod
    def citation(cls, metadata):
        year = datetime.datetime.now().year
        name = metadata['name'].rstrip('.')
        if 'doi' in metadata:
            url = f'https://doi.org/{metadata["doi"]}'
        else:
            url = metadata['url']
        version = metadata['version']
        # If we can't find any contributors, use this citation format
        citation = f'{name} ({year}). (Version {version}) [Data set]. DANDI archive. {url}'
        if 'contributor' in metadata and metadata['contributor']:
            cl = '; '.join(
                [
                    val['name']
                    for val in metadata['contributor']
                    if 'includeInCitation' in val and val['includeInCitation']
                ]
            )
            if cl:
                citation = (
                    f'{cl} ({year}) {name} (Version {version}) [Data set]. DANDI archive. {url}'
                )
        return citation

    @classmethod
    def strip_metadata(cls, metadata):
        """Strip away computed fields from a metadata dict."""
        computed_fields = [
            'name',
            'identifier',
            'version',
            'id',
            'url',
            'assetsSummary',
            'citation',
            'doi',
            'dateCreated',
            'datePublished',
            'publishedBy',
            'manifestLocation',
        ]
        return {key: metadata[key] for key in metadata if key not in computed_fields}

    def _populate_metadata(self):
        from dandiapi.api.manifests import manifest_location

        metadata = {
            **self.metadata,
            '@context': (
                'https://raw.githubusercontent.com/dandi/schema/master/releases/'
                f'{self.metadata["schemaVersion"]}/context.json'
            ),
            'manifestLocation': manifest_location(self),
            'name': self.name,
            'identifier': f'DANDI:{self.dandiset.identifier}',
            'version': self.version,
            'id': f'DANDI:{self.dandiset.identifier}/{self.version}',
            'repository': settings.DANDI_WEB_APP_URL,
            'url': f'{settings.DANDI_WEB_APP_URL}/dandiset/{self.dandiset.identifier}/{self.version}',  # noqa
            'dateCreated': self.dandiset.created.isoformat(),
        }

        if 'assetsSummary' not in metadata:
            metadata['assetsSummary'] = {
                'schemaKey': 'AssetsSummary',
                'numberOfBytes': 0,
                'numberOfFiles': 0,
            }

        if self.doi:
            metadata['doi'] = self.doi
        metadata['citation'] = self.citation(metadata)

        return metadata

    def save(self, *args, **kwargs):
        self.metadata = self._populate_metadata()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f'{self.dandiset.identifier}/{self.version}'
