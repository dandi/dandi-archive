from __future__ import annotations

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0032_version_release_notes'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='asset',
            options={'ordering': ['created', 'id']},
        ),
    ]
