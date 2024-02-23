from __future__ import annotations

from django.core.validators import RegexValidator
from django.db import models


class ProcessedS3Log(models.Model):
    name = models.CharField(
        max_length=36,
        validators=[
            # https://docs.aws.amazon.com/AmazonS3/latest/userguide/ServerLogs.html#server-log-keyname-format
            RegexValidator(r'^\d{4}-(\d{2}-){5}[A-F0-9]{16}$')
        ],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['name'], name='%(app_label)s_%(class)s_unique_name')
        ]

    def __str__(self) -> str:
        return self.name
