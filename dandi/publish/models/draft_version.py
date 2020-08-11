from django.contrib.postgres.fields import JSONField
from django.db import models

from .dandiset import Dandiset
from .version import BaseVersion


class DraftVersion(BaseVersion):
    dandiset = models.OneToOneField(Dandiset, on_delete=models.CASCADE, primary_key=True)

    name = models.CharField(max_length=150)
    description = models.TextField(max_length=3000)

    metadata = JSONField(blank=True, default=dict)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        get_latest_by = 'created'
        indexes = [
            models.Index(fields=['dandiset']),
        ]
