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
    # This is necessary to determine which bucket the logfile corresponds to
    embargoed = models.BooleanField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'embargoed'],
                name='%(app_label)s_%(class)s_unique_name_embargoed',
            )
        ]

    def __str__(self) -> str:
        return self.name
