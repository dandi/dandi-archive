from __future__ import annotations

import uuid

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.core.validators import RegexValidator
from django.db import models

from dandi.publish.storage import create_s3_storage
from .draft import Draft


def _get_asset_blob_prefix(instance: DraftAsset, filename: str) -> str:
    return f'{instance.version.dandiset.identifier}/{instance.version.version}/{filename}'


# TODO this is not plugged in to anything
class DraftAsset(models.Model):
    SHA256_REGEX = r'[0-9a-f]{64}'

    draft = models.ForeignKey(
        Draft, related_name='assets', on_delete=models.CASCADE
    )  # used to be called dandiset
    uuid = models.UUIDField(unique=True, default=uuid.uuid4)

    path = models.CharField(max_length=512)
    size = models.BigIntegerField()
    sha256 = models.CharField(max_length=64, validators=[RegexValidator(f'^{SHA256_REGEX}$')],)
    metadata = JSONField(blank=True, default=dict)

    blob = models.FileField(
        blank=True,
        # TODO verify that this is where drafts should be stored
        storage=create_s3_storage(settings.DANDI_DANDISETS_BUCKET_NAME),
        upload_to=_get_asset_blob_prefix,
    )

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['uuid']),
            models.Index(fields=['path']),
        ]
        ordering = ['path']

    # objects = SelectRelatedManager('version__dandiset')

    def __str__(self) -> str:
        return self.path
