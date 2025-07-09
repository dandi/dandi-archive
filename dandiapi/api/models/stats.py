from __future__ import annotations

from django.db import models


class ApplicationStats(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True, unique=True)

    # Actual stats
    dandiset_count = models.PositiveIntegerField()
    published_dandiset_count = models.PositiveIntegerField()
    user_count = models.PositiveIntegerField()
    size = models.PositiveBigIntegerField()

    class Meta:
        verbose_name_plural = 'Application Stats'

    def __str__(self) -> str:
        return super().__str__()

    @classmethod
    def latest(cls):
        return cls.objects.order_by('-timestamp').first()
