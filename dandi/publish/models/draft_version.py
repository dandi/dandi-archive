from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models

from .dandiset import Dandiset
from .version import BaseVersion


class DraftVersion(BaseVersion):
    dandiset = models.OneToOneField(
        Dandiset, related_name='draft_version', on_delete=models.CASCADE, primary_key=True
    )
    locked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta(BaseVersion.Meta):
        indexes = [
            models.Index(fields=['dandiset']),
        ]
        permissions = (('owner', 'Owns the draft version'),)

    @property
    def locked(self):
        return self.locked_by is not None

    def lock(self, user: User):
        # TODO permissions/ownership
        if self.locked:
            raise ValidationError('Draft is locked')
        self.locked_by = user

    def unlock(self, user: User):
        if not self.locked:
            raise ValidationError('Cannot unlock a draft that is not locked')
        if self.locked_by != user:
            raise ValidationError('Cannot unlock a draft locked by another user')
        self.locked_by = None
