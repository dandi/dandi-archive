# Generated by Django 4.1.13 on 2024-03-06 17:04
from __future__ import annotations

from django.db import migrations, models

import dandiapi.api.models.asset


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0005_null_charfield'),
    ]

    operations = [
        migrations.AlterField(
            model_name='asset',
            name='path',
            field=models.CharField(
                db_collation='C',
                max_length=512,
                validators=[dandiapi.api.models.asset.validate_asset_path],
            ),
        ),
    ]