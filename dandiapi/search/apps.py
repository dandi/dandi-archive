from __future__ import annotations

from django.apps import AppConfig
from django.conf import settings
from django.db import connections
from django.db.models.signals import post_migrate


def _load_anatomy_ontology(sender, using: str, **kwargs) -> None:
    """Keep the anatomy ontology tables in step with the packaged file after each migrate."""
    if not settings.DANDI_ANATOMY_ONTOLOGY_AUTOLOAD:
        return
    from dandiapi.search.models import OntologyRelease
    from dandiapi.search.ontology import ensure_packaged_ontology_loaded

    # Skip when migrating backward past the migration that creates the tables.
    if OntologyRelease._meta.db_table not in connections[using].introspection.table_names():
        return
    ensure_packaged_ontology_loaded()


class SearchConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dandiapi.search'
    verbose_name = 'DANDI: Search'

    def ready(self) -> None:
        post_migrate.connect(_load_anatomy_ontology, sender=self)
