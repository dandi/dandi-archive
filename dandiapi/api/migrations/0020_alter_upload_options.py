# Generated by Django 4.2.20 on 2025-04-14 20:17
from __future__ import annotations

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0019_asset_status_pending'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='upload',
            options={'ordering': ['created']},
        ),
    ]
