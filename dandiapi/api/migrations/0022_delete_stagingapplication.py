# Generated by Django 4.2.19 on 2025-04-18 19:14
from __future__ import annotations

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0021_stagingapplication_allowed_origins_and_more'),
    ]

    operations = [
        migrations.DeleteModel(
            name='StagingApplication',
        ),
    ]
