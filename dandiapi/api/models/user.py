from __future__ import annotations

from django.contrib.auth.models import User
from django.db import models
from django_extensions.db.models import TimeStampedModel


class UserMetadata(TimeStampedModel):
    class Status(models.TextChoices):
        INCOMPLETE = 'INCOMPLETE'
        PENDING = 'PENDING'
        APPROVED = 'APPROVED'
        REJECTED = 'REJECTED'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='metadata')
    status = models.CharField(choices=Status.choices, default=Status.INCOMPLETE, max_length=10)
    questionnaire_form = models.JSONField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, default='', max_length=1000)
