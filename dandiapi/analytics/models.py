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

    # Represents if this s3 log file was embargoed prior to the embargo re-design.
    # If this field is True, the log file lives in the S3 bucket pointed to by the
    # DANDI_DANDISETS_EMBARGO_LOG_BUCKET_NAME setting.
    historically_embargoed = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'historically_embargoed'],
                name='%(app_label)s_%(class)s_unique_name_embargoed',
            )
        ]

    def __str__(self) -> str:
        return self.name
