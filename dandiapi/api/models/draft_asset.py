
import uuid

from django.contrib.postgres.fields import JSONField
from django.core.validators import RegexValidator
from django.db import models
from django_extensions.db.models import TimeStampedModel

from s3_file_field.fields import S3FileField
from .draft_version import DraftVersion


class Asset(TimeStampedModel):
    UUID_REGEX = r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}'
    SHA256_REGEX = r'[0-9a-f]{64}'

    draft_version = models.ForeignKey(
        DraftVersion, related_name='assets', on_delete=models.CASCADE
    )
    uuid = models.UUIDField(unique=True, default=uuid.uuid4)

    path = models.CharField(max_length=512)
    size = models.BigIntegerField()
    sha256 = models.CharField(max_length=64, validators=[RegexValidator(f'^{SHA256_REGEX}$')])
    metadata = JSONField(blank=True, default=dict)

    blob = S3FileField()

    class Meta:
        indexes = [
            models.Index(fields=['uuid']),
            models.Index(fields=['version', 'path']),
        ]
        ordering = ['version', 'path']

    # objects = SelectRelatedManager('version__dandiset')

    def __str__(self) -> str:
        return self.path
