from __future__ import annotations
from django.apps import AppConfig


class ZarrConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dandiapi.zarr'
    verbose_name = 'DANDI: Zarr'
