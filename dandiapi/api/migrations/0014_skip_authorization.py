# flake8: noqa N806

from django.db import migrations
from django.db.models import Q


def update_application(apps, schema_editor):
    Application = apps.get_model('oauth2_provider', 'Application')
    for app in Application.objects.all():
        app.skip_authorization = True
        app.save(update_fields=['skip_authorization'])


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0013_add_published_status'),
    ]

    operations = [migrations.RunPython(update_application)]
