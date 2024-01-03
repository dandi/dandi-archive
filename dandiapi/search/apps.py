from __future__ import annotations
from django.apps import AppConfig


class SearchConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dandiapi.search'
    verbose_name = 'DANDI: Search'
