from django.db import models

from .dandiset import Dandiset
from .version import BaseVersion


class DraftVersion(BaseVersion):
    dandiset = models.OneToOneField(Dandiset, on_delete=models.CASCADE, primary_key=True)

    class Meta(BaseVersion.Meta):
        indexes = [
            models.Index(fields=['dandiset']),
        ]
