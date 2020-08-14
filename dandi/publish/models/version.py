from __future__ import annotations

import datetime
import logging

from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models

from dandi.publish.girder import GirderClient
from .common import SelectRelatedManager
from .dandiset import Dandiset

logger = logging.getLogger(__name__)


class BaseVersion(models.Model):
    """Mixin for fields and methods common to Version and DraftVersion."""

    dandiset = models.ForeignKey(Dandiset, related_name='versions', on_delete=models.CASCADE)

    name = models.CharField(max_length=150)
    description = models.TextField(max_length=3000)

    metadata = JSONField(blank=True, default=dict)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    @classmethod
    def from_girder_metadata(cls, dandiset, metadata) -> Version:
        if metadata is None:
            raise ValidationError(
                f'Girder draft folder for dandiset {dandiset.draft_folder_id} has no "meta" field.'
            )

        name = metadata['dandiset'].pop('name')
        description = metadata['dandiset'].pop('description')

        if len(description) > 3000:
            raise ValidationError(
                f'Description length is greater than 3000 for dandiset {dandiset.draft_folder_id}.'
            )

        return cls(dandiset=dandiset, name=name, description=description, metadata=metadata)


def _get_default_version() -> str:
    # This cannot be a lambda, as migrations cannot serialize those
    return Version.make_version()


class Version(BaseVersion):
    VERSION_REGEX = r'0\.\d{6}\.\d{4}'

    version = models.CharField(
        max_length=13,
        validators=[RegexValidator(f'^{VERSION_REGEX}$')],
        default=_get_default_version,
    )  # TODO: rename this?

    class Meta:
        unique_together = [['dandiset', 'version']]
        get_latest_by = 'created'
        ordering = ['dandiset', '-version']
        indexes = [
            models.Index(fields=['dandiset', 'version']),
        ]

    # Define custom "objects" first, so it will be the "_default_manager", which is more efficient
    # for many automatically generated queries
    objects = SelectRelatedManager('dandiset')

    def __str__(self) -> str:
        return f'{self.dandiset.identifier}: {self.version}'

    @property
    def count(self):
        return self.assets.count()

    @property
    def size(self):
        return self.assets.aggregate(total_size=models.Sum('size'))['total_size']

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

    @classmethod
    def from_girder(cls, dandiset: Dandiset, client: GirderClient) -> Version:
        draft_folder = client.get_folder(dandiset.draft_folder_id)

        metadata = draft_folder.get('meta')

        version = cls.from_girder_metadata(dandiset, metadata)
        version.save()
        return version
