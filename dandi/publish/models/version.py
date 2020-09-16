from __future__ import annotations

import datetime
import logging
from typing import Dict

from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django_extensions.db.models import TimeStampedModel

from dandi.publish.girder import GirderClient

from .common import SelectRelatedManager
from .dandiset import Dandiset

logger = logging.getLogger(__name__)


class BaseVersion(TimeStampedModel):
    """Base class for fields and methods common to Version and DraftVersion."""

    # Must be provided by subclasses
    dandiset = None

    name = models.CharField(max_length=150)

    metadata = JSONField(blank=True, default=dict)

    class Meta:
        abstract = True
        get_latest_by = 'created'

    @classmethod
    def from_girder_metadata(cls, dandiset: Dandiset, metadata: Dict) -> BaseVersion:
        if 'dandiset' not in metadata:
            raise ValidationError(
                f'Girder draft folder for dandiset {dandiset.draft_folder_id} '
                f'has no "meta.dandiset" field.'
            )
        dandiset_metadata = metadata['dandiset']

        # If 'name' (or other future metadata values) are missing, don't raise an error, as it
        # can be handled during model validation
        name = dandiset_metadata.get('name', '')

        return cls(dandiset=dandiset, name=name, metadata=dandiset_metadata)


def _get_default_version() -> str:
    # This cannot be a lambda, as migrations cannot serialize those
    return Version.make_version()


class Version(BaseVersion):
    VERSION_REGEX = r'0\.\d{6}\.\d{4}'

    dandiset = models.ForeignKey(Dandiset, related_name='versions', on_delete=models.CASCADE)
    version = models.CharField(
        max_length=13,
        validators=[RegexValidator(f'^{VERSION_REGEX}$')],
        default=_get_default_version,
    )  # TODO: rename this?

    class Meta(BaseVersion.Meta):
        unique_together = [['dandiset', 'version']]
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
    def assets_count(self):
        return self.assets.count()

    @property
    def size(self):
        size = self.assets.aggregate(total_size=models.Sum('size'))['total_size']
        if size is None:
            return 0
        return size

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

        metadata = draft_folder['meta']

        version = cls.from_girder_metadata(dandiset, metadata)
        version.full_clean()
        version.save()
        return version
