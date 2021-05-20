from __future__ import annotations

import datetime

from django.contrib.postgres.indexes import HashIndex
from django.core.validators import RegexValidator
from django.db import models
from django_extensions.db.models import TimeStampedModel

from dandiapi.api.models.metadata import PublishableMetadataMixin

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
            },
        )

        # Create the published model
        published_version = Version(dandiset=self.dandiset, metadata=published_metadata)

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

    def _populate_metadata(self):
        metadata = {
            **self.metadata.metadata,
            'name': self.metadata.name,
            'identifier': f'DANDI:{self.dandiset.identifier}',
            'version': self.version,
            'id': f'DANDI:{self.dandiset.identifier}/{self.version}',
            'url': f'https://dandiarchive.org/{self.dandiset.identifier}/{self.version}',
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
