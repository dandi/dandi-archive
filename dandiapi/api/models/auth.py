from __future__ import annotations

from django.contrib.auth.models import Group
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
