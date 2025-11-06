from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.db import migrations

if TYPE_CHECKING:
    from django.db.backends.base.schema import BaseDatabaseSchemaEditor
    from django.db.migrations.state import StateApps


def update_default_site(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor):
    Site = apps.get_model('sites', 'Site')

    # A default site object may or may not exist.
    # If this is a brand-new database, the post_migrate will not fire until the very end of the
    # "migrate" command, so the sites app will not have created a default site object yet.
    # If this is an existing database, the sites app will likely have created an default site
    # object already.
    Site.objects.update_or_create(
        pk=settings.SITE_ID,
        defaults={
            'domain': 'api.dandiarchive.org',
            'name': 'DANDI Archive',
        },
    )


def rollback_default_site(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor):
    Site = apps.get_model('sites', 'Site')

    # This is the initial value of the default site object, as populated by the sites app.
    # If it doesn't exist for some reason, there is nothing to roll back.
    Site.objects.filter(pk=settings.SITE_ID).update(domain='example.com', name='example.com')


class Migration(migrations.Migration):
    dependencies = [
        # This is the final sites app migration
        ('sites', '0002_alter_domain_unique'),
    ]

    operations = [
        migrations.RunPython(update_default_site, rollback_default_site),
    ]
