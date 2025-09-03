from __future__ import annotations

from django.db import models

from dandiapi.api.models.dandiset import Dandiset


class DataciteEventType(models.TextChoices):
    CREATE_DOI = 'CREATE_DOI', 'Create DOI'
    UPDATE_DOI = 'UPDATE_DOI', 'Update DOI'
    HIDE_DOI = 'HIDE_DOI', 'Hide DOI'
    DELETE_DOI = 'DELETE_DOI', 'Delete DOI'


class DataciteEvent(models.Model):
    timestamp = models.DateTimeField()
    event_type = models.CharField(
        max_length=max(len(choice[0]) for choice in DataciteEventType.choices),
        choices=DataciteEventType.choices,
    )

    # Since the deletion of a dandiset will set the foreign key relation to null,
    # also store the dandiset ID in a separate field
    dandiset_identifier = models.PositiveIntegerField()
    dandiset = models.ForeignKey(
        Dandiset,
        related_name='datacite_events',
        on_delete=models.SET_NULL,
        null=True,
    )

    class Meta:
        ordering = ['timestamp']
        constraints = [
            models.CheckConstraint(
                check=models.Q(dandiset__isnull=True)
                | models.Q(dandiset_id=models.F('dandiset_identifier')),
                name='dandiset_fields_equal',
            )
        ]

    def __str__(self) -> str:
        return f'Datacite Event: {self.event_type} @ {self.timestamp}'
