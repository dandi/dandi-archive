# Generated by Django 3.0.9 on 2020-12-17 23:59
# flake8: noqa N806

from django.db import migrations
from django.db.models import Q


def create_application(apps, schema_editor):
    Application = apps.get_model('oauth2_provider', 'Application')
    name = 'Frontend Provider'
    # This is specified so it matches the default value used in the frontend.
    client_id = 'Dk0zosgt1GAAKfN8LT4STJmLJXwMDPbYWYzfNtAl'
    if not Application.objects.filter(Q(name=name) | Q(client_id=client_id)).exists():
        # Use the first admin user
        User = apps.get_model('auth', 'User')
        user = User.objects.filter(is_superuser=True).order_by('id')[0]
        application = Application(
            # Production instances should change this.
            client_id='Dk0zosgt1GAAKfN8LT4STJmLJXwMDPbYWYzfNtAl',
            user=user,
            # Production instances must change this.
            redirect_uris='http://localhost:8085/',
            # These values should not be modified.
            client_type='public',
            authorization_grant_type='authorization-code',
            client_secret='',
            name=name,
            # This can be turned off in production if appropriate.
            skip_authorization=False,
        )
        application.save()


def reverse_create_application(apps, schema_editor):
    # Deleting the application would destroy any customization applied to it.
    # Explicitly do nothing so the migration is still nominally reversible.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_update_asset_model'),
    ]

    operations = [migrations.RunPython(create_application, reverse_create_application)]
