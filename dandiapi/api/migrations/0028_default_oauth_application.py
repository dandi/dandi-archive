from __future__ import annotations

from django.db import migrations
from oauth2_provider.settings import oauth2_settings

# This is specified so it matches the default value used in the frontend.
DEFAULT_CLIENT_ID = 'Dk0zosgt1GAAKfN8LT4STJmLJXwMDPbYWYzfNtAl'


def create_application(apps, schema_editor):
    Application = apps.get_model(oauth2_settings.APPLICATION_MODEL)
    # This work used to be done within a now-deleted "api.0003_default_oauth_application"
    # migration, so historical databases may already have this object present; if so, this
    # migration will succeed and never run again.
    Application.objects.get_or_create(
        # Production instances should change this.
        client_id=DEFAULT_CLIENT_ID,
        defaults={
            # Production instances must change this.
            'redirect_uris': 'http://localhost:8085/',
            # These values should not be modified.
            'client_type': 'public',
            'authorization_grant_type': 'authorization-code',
            'client_secret': '',
            'name': 'DANDI GUI',
            # This can be turned off in production if appropriate.
            'skip_authorization': True,
        },
    )


def reverse_create_application(apps, schema_editor):
    Application = apps.get_model(oauth2_settings.APPLICATION_MODEL)
    Application.objects.filter(client_id=DEFAULT_CLIENT_ID).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0027_delete_stagingapplication'),
        # The latest oauth2_provider migration, to ensure it's fully created
        ('oauth2_provider', '0012_add_token_checksum'),
    ]

    operations = [
        migrations.RunPython(create_application, reverse_create_application, elidable=False),
    ]
