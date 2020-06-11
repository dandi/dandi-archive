from __future__ import annotations

import datetime
import logging

from django.contrib.postgres.fields import JSONField
from django.core.validators import RegexValidator
from django.db import models

from publish.girder import GirderClient
from .dandiset import Dandiset

logger = logging.getLogger(__name__)


class SelectRelatedManager(models.Manager):
    def __init__(self, *related_fields):
        self.related_fields = related_fields
        super().__init__()

    def get_queryset(self):
        return super().get_queryset().select_related(*self.related_fields)


def _get_default_version() -> str:
    # This cannot be a lambda, as migrations cannot serialize those
    return Version.make_version()


class Version(models.Model):
    VERSION_REGEX = r'0\.\d{6}\.\d{4}'

    dandiset = models.ForeignKey(Dandiset, related_name='versions', on_delete=models.CASCADE)
    version = models.CharField(
        max_length=13,
        validators=[RegexValidator(f'^{VERSION_REGEX}$')],
        default=_get_default_version,
    )  # TODO: rename this?

    metadata = JSONField(blank=True, default=dict)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

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
        draft_folder = client.get_json(f'folder/{dandiset.draft_folder_id}')

        version = Version(dandiset=dandiset, metadata=draft_folder['meta'])
        version.save()
        return version
