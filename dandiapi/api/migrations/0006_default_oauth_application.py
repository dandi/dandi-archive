from django.db import migrations
from django.db.models import Q


def create_application(apps, schema_editor):
    Application = apps.get_model('oauth2_provider', 'Application')
    name = 'DANDI GUI'
    # TODO: Aaron -- This needs to match the value that is passed for the app
    # This is specified so it matches the default value used in the frontend.
    client_id = 'Dk0zosgt1GAAKfN8LT4STJmLJXwMDPbYWYzfNtAl'
    if not Application.objects.filter(Q(name=name) | Q(client_id=client_id)).exists():
        application = Application(
            # Production instances should change this. Aaron
            client_id='Dk0zosgt1GAAKfN8LT4STJmLJXwMDPbYWYzfNtAl',
            # Production instances must change this. Aaron
            redirect_uris='https://lincbrain.org',
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
        ('api', '0005_version_doi'),
        ('oauth2_provider', '0003_auto_20201211_1314'),
    ]

    operations = [migrations.RunPython(create_application, reverse_create_application)]
