from __future__ import annotations

from typing import Any

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Group, User
from django.db import models


class DandisetRole(models.Model):
    group = models.OneToOneField(Group, on_delete=models.CASCADE, related_name='dandisetrole')

    dandiset = models.ForeignKey('api.Dandiset', related_name='roles', on_delete=models.CASCADE)
    rolename = models.CharField(max_length=150)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                name='unique-dandiset-rolename', fields=['dandiset', 'rolename']
            )
        ]

    def __str__(self):
        return f'{self.dandiset.identifier}/{self.rolename}'


class DandiGlobalPermissionBackend(ModelBackend):
    """Give permission to any object if the global permission is granted to the user."""

    def has_perm(self, user_obj: User, perm: str, obj: Any = None):
        # Check just the global permission
        global_perm = f'api.{perm}' if '.' not in perm else perm
        return super().has_perm(user_obj=user_obj, perm=global_perm)
