from __future__ import annotations

import datetime
from urllib.parse import urlparse, urlunparse

from django.conf import settings
from django.contrib.postgres.indexes import HashIndex
from django.core.validators import RegexValidator
from django.db import models
from django_extensions.db.models import TimeStampedModel

from dandiapi.api.models.metadata import PublishableMetadataMixin
from dandiapi.api.storage import create_s3_storage

from .dandiset import Dandiset


class VersionMetadata(PublishableMetadataMixin, TimeStampedModel):
    metadata = models.JSONField(default=dict)
    name = models.CharField(max_length=300)

    class Meta:
        indexes = [
            HashIndex(fields=['metadata']),
            HashIndex(fields=['name']),
        ]

    @property
    def references(self) -> int:
        return self.versions.count()

    def __str__(self) -> str:
        return self.name


def _get_default_version() -> str:
    # This cannot be a lambda, as migrations cannot serialize those
    return Version.make_version()


class Version(TimeStampedModel):
    VERSION_REGEX = r'(0\.\d{6}\.\d{4})|draft'

    class Status(models.TextChoices):
        PENDING = 'Pending'
        VALIDATING = 'Validating'
        VALID = 'Valid'
        INVALID = 'Invalid'

    dandiset = models.ForeignKey(Dandiset, related_name='versions', on_delete=models.CASCADE)
    metadata = models.ForeignKey(VersionMetadata, related_name='versions', on_delete=models.CASCADE)
    version = models.CharField(
        max_length=13,
        validators=[RegexValidator(f'^{VERSION_REGEX}$')],
        default=_get_default_version,
    )  # TODO: rename this?
    doi = models.CharField(max_length=64, null=True, blank=True)
    status = models.CharField(
        max_length=10,
        default=Status.PENDING,
        choices=Status.choices,
    )
    validation_error = models.TextField(default='')

    class Meta:
        unique_together = ['dandiset', 'version']

    @property
    def asset_count(self):
        return self.assets.count()

    @property
    def name(self):
        return self.metadata.name

    @property
    def size(self):
        return self.assets.aggregate(size=models.Sum('blob__size'))['size'] or 0

    @property
    def valid(self) -> bool:
        if self.status != Version.Status.VALID:
            return False

        # Import here to avoid dependency cycle
        from .asset import Asset

        # Return False if any asset is not VALID
        return not self.assets.filter(~models.Q(status=Asset.Status.VALID)).exists()

    @staticmethod
    def datetime_to_version(time: datetime.datetime) -> str:
        return time.strftime('0.%y%m%d.%H%M')

    @classmethod
    def make_version(cls, dandiset: Dandiset = None) -> str:
        versions: models.Manager = dandiset.versions if dandiset else cls.objects

        time = datetime.datetime.utcnow()
        # increment time until there are no collisions
        while True:
            version = cls.datetime_to_version(time)
            collision = versions.filter(version=version).exists()
            if not collision:
                break
            time += datetime.timedelta(minutes=1)

        return version

    @property
    def dandiset_yaml_path(self):
        return (
            f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}'
            f'dandisets/{self.dandiset.identifier}/{self.version}/dandiset.yaml'
        )

    @property
    def assets_yaml_path(self):
        return (
            f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}'
            f'dandisets/{self.dandiset.identifier}/{self.version}/assets.yaml'
        )

    @property
    def dandiset_yaml_url(self):
        storage = create_s3_storage(settings.DANDI_DANDISETS_BUCKET_NAME)
        signed_url = storage.url(self.dandiset_yaml_path)
        parsed = urlparse(signed_url)
        s3_url = urlunparse((parsed[0], parsed[1], parsed[2], '', '', ''))
        return s3_url

    @property
    def assets_yaml_url(self):
        storage = create_s3_storage(settings.DANDI_DANDISETS_BUCKET_NAME)
        signed_url = storage.url(self.assets_yaml_path)
        parsed = urlparse(signed_url)
        s3_url = urlunparse((parsed[0], parsed[1], parsed[2], '', '', ''))
        return s3_url

    @property
    def publish_version(self):
        """
        Generate a published version + metadata without saving it.

        This is useful to validate version metadata without saving it.
        """
        now = datetime.datetime.utcnow()
        # Inject the publishedBy and datePublished fields
        published_metadata, _ = VersionMetadata.objects.get_or_create(
            name=self.metadata.name,
            metadata={
                **self.metadata.metadata,
                'publishedBy': self.metadata.published_by(now),
                'datePublished': now.isoformat(),
                'manifestLocation': [self.dandiset_yaml_url, self.assets_yaml_url],
            },
        )

        # Create the published model
        published_version = Version(
            dandiset=self.dandiset,
            metadata=published_metadata,
            status=Version.Status.VALID,
        )

        # Recompute the metadata
        published_metadata, _ = VersionMetadata.objects.get_or_create(
            name=self.name,
            metadata=published_version._populate_metadata(),
        )
        published_version.metadata = published_metadata

        return published_version

    @classmethod
    def citation(cls, metadata):
        year = datetime.datetime.now().year
        name = metadata['name']
        url = metadata['url']
        # If we can't find any contributors, use this citation format
        citation = f'{name} ({year}). Online: {url}'
        if 'contributor' in metadata and metadata['contributor']:
            cl = '; '.join(
                [
                    val['name']
                    for val in metadata['contributor']
                    if 'includeInCitation' in val and val['includeInCitation']
                ]
            )
            if cl:
                citation = f'{cl} ({year}) {name}. Online: {url}'
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
            'datePublished',
            'publishedBy',
        ]
        return {key: metadata[key] for key in metadata if key not in computed_fields}

    def _populate_metadata(self):
        number_of_bytes = 0
        number_of_files = 0
        data_standards = set()
        approaches = set()
        measurement_techniques = set()
        species = set()
        # When running _populate_metadata on an unsaved Version, self.assets is not available.
        # Only compute the asset-based properties if this Version has an id, which means it's saved.
        if self.id:
            number_of_bytes = (
                self.assets.all().aggregate(size=models.Sum('blob__size'))['size'] or 0
            )
            number_of_files = self.assets.count()
            for asset in self.assets.all():
                metadata = asset.metadata.metadata
                if 'dataStandard' in metadata:
                    data_standards = data_standards.union(set(metadata['dataStandard']))
                if 'approach' in metadata:
                    approaches = approaches.union(set(metadata['approach']))
                if 'measurementTechnique' in metadata:
                    measurement_techniques = measurement_techniques.union(
                        set(metadata['measurementTechnique'])
                    )
                if 'species' in metadata:
                    species = species.union(set(metadata['species']))
        metadata = {
            **self.metadata.metadata,
            'name': self.metadata.name,
            'identifier': f'DANDI:{self.dandiset.identifier}',
            'version': self.version,
            'id': f'DANDI:{self.dandiset.identifier}/{self.version}',
            'url': f'https://dandiarchive.org/{self.dandiset.identifier}/{self.version}',
            'assetsSummary': {
                'numberOfBytes': number_of_bytes,
                'numberOfFiles': number_of_files,
                'dataStandard': sorted(data_standards),
                'approach': sorted(approaches),
                'measurementTechnique': sorted(measurement_techniques),
                'species': sorted(species),
            },
        }
        metadata['citation'] = self.citation(metadata)
        if self.doi:
            metadata['doi'] = self.doi
        if 'schemaVersion' in metadata:
            schema_version = metadata['schemaVersion']
            metadata['@context'] = (
                'https://raw.githubusercontent.com/dandi/schema/master/releases/'
                f'{schema_version}/context.json'
            )
        return metadata

    def save(self, *args, **kwargs):
        metadata = self._populate_metadata()
        new, created = VersionMetadata.objects.get_or_create(
            name=self.metadata.name,
            metadata=metadata,
        )

        if created:
            new.save()

        self.metadata = new
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f'{self.dandiset.identifier}/{self.version}'
