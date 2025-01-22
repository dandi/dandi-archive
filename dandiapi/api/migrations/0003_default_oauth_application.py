from __future__ import annotations

from django.db import migrations
from django.db.models import Q
from oauth2_provider.settings import oauth2_settings


def create_application(apps, schema_editor):
    # This could be either "oauth2_provider.Application" or "api.StagingApplication".
    Application = apps.get_model(oauth2_settings.APPLICATION_MODEL)

    name = 'DANDI GUI'
    # This is specified so it matches the default value used in the frontend.
    client_id = 'Dk0zosgt1GAAKfN8LT4STJmLJXwMDPbYWYzfNtAl'
    if not Application.objects.filter(Q(name=name) | Q(client_id=client_id)).exists():
        application = Application(
            # Production instances should change this.
            client_id=client_id,
            # Production instances must change this.
            redirect_uris='http://localhost:8085/',
            # These values should not be modified.
            client_type='public',
            authorization_grant_type='authorization-code',
            client_secret='',
            name=name,
            # This can be turned off in production if appropriate.
            skip_authorization=True,
        )
        application.save()


def reverse_create_application(apps, schema_editor):
    # Deleting the application would destroy any customization applied to it.
    # Explicitly do nothing so the migration is still nominally reversible.
    pass


class Migration(migrations.Migration):
    dependencies = [
        # Both Application and StagingApplication should exist, though only one will be used.
        # Trying to make this actually swappable doesn't work, since "oauth2_provider.Application"
        # always gets declared when "AbstractApplication" is imported.
        ('oauth2_provider', '0003_auto_20201211_1314'),
        ('api', '0001_stagingapplication'),
    ]

    operations = [migrations.RunPython(create_application, reverse_create_application)]
