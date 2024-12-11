from __future__ import annotations

from django.db import models


class GarbageCollectionEvent(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    type = models.CharField(
        max_length=255, help_text='The model name of the records that were garbage collected.'
    )

    def __str__(self) -> str:
        return f'{self.type} ({self.created})'


class GarbageCollectionEventRecord(models.Model):
    event = models.ForeignKey(
        GarbageCollectionEvent, on_delete=models.CASCADE, related_name='records'
    )

    record = models.JSONField(
        help_text='JSON serialization of the record that was garbage collected.'
    )

    def __str__(self) -> str:
        return f'{self.event.type} record'
