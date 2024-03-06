from __future__ import annotations

from django.db import models


class AuditRecord(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    dandiset_id = models.IntegerField()
    username = models.CharField(max_length=39)
    user_email = models.CharField(max_length=254)
    user_fullname = models.CharField(max_length=301)
    record_type = models.CharField(max_length=32, choices=AUDIT_RECORD_CHOICES)
    details = models.JSONField(blank=True)

    def __str__(self):
        return f'{self.record_type}/{self.dandiset_id:06}'
