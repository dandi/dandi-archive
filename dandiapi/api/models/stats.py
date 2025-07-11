from __future__ import annotations

from django.db import models


class ApplicationStats(models.Model):  # noqa: DJ008
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True, unique=True)

    # Actual stats
    dandiset_count = models.PositiveIntegerField()
    published_dandiset_count = models.PositiveIntegerField()
    user_count = models.PositiveIntegerField()
    size = models.PositiveBigIntegerField()

    class Meta:
        verbose_name_plural = 'Application Stats'
        ordering = ['timestamp']
