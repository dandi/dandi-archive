from __future__ import annotations

from django.db import models


class GarbageCollectionEvent(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    type = models.CharField(
        max_length=255, help_text='The model name of the records that were garbage collected.'
    )
    records = models.JSONField(
        help_text='JSON serialization of the queryset of records that were garbage collected.'
    )

    garbage_collection_event_id = models.UUIDField(
        editable=False,
        help_text='Unique identifier for the garbage collection event. '
        'Used to associate multiple records that are part of the same GC event.',
    )

    def __str__(self) -> str:
        return f'{self.type} ({self.created})'
