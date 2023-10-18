from __future__ import annotations

from django.db import models


class GarbageCollectionEvent(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    records = models.JSONField()
