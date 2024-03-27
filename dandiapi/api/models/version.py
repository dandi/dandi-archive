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
    doi = models.CharField(max_length=64, null=True, default=None, blank=True)  # noqa: DJ001
    """Track the validation status of this version, without considering assets"""
    status = models.CharField(
        max_length=10,
        default=Status.PENDING,
        choices=Status.choices,
    )
    validation_errors = models.JSONField(default=list, blank=True, null=True)

    class Meta:
        ordering = ['version']
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
    def publishable(self) -> bool:
        if self.status != Version.Status.VALID:
            return False

        # Import here to avoid dependency cycle
        from .asset import Asset

        # Return False if any asset is not VALID
        return not self.assets.exclude(status=Asset.Status.VALID).exists()

    @property
    def asset_validation_errors(self) -> list[dict[str, str]]:
        # Import here to avoid dependency cycle
        from .asset import Asset

        # Get assets that are not VALID (could be pending, validating, or invalid)
        invalid_assets: models.QuerySet[Asset] = self.assets.exclude(
            status=Asset.Status.VALID
        ).values('status', 'path', 'validation_errors')

        asset_validating_error = {
            'field': '',
            'message': 'asset is currently being validated, please wait.',
        }

        def inject_path(asset: dict, err: dict):
            return {**err, 'path': asset['path']}

        # Aggregate errors, ensuring the path of the asset is included
        errors = []
        for asset in invalid_assets:
            # Must be pending or validating
            if asset['status'] != Asset.Status.INVALID:
                errors.append(inject_path(asset, asset_validating_error))
                continue

            # Must be invalid, only add entry in map if it has any errors
            if asset['validation_errors']:
                errors.extend([inject_path(asset, err) for err in asset['validation_errors']])

        return errors

    @staticmethod
    def datetime_to_version(time: datetime.datetime) -> str:
        return time.strftime('0.%y%m%d.%H%M')

    @classmethod
    def next_published_version(cls, dandiset: Dandiset) -> str:
        time = datetime.datetime.now(datetime.UTC)
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
        year = datetime.datetime.now(datetime.UTC).year
        name = metadata['name'].rstrip('.')
        url = f'https://doi.org/{metadata["doi"]}' if 'doi' in metadata else metadata['url']
        version = metadata['version']
        # If we can't find any contributors, use this citation format
        citation = f'{name} ({year}). (Version {version}) [Data set]. DANDI archive. {url}'
        if 'contributor' in metadata and isinstance(metadata['contributor'], list):
            cl = '; '.join(
                [val['name'] for val in metadata['contributor'] if val.get('includeInCitation')]
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
            'url': (
                f'{settings.DANDI_WEB_APP_URL}/dandiset/'
                f'{self.dandiset.identifier}/{self.version}'
            ),
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
