# Generated by Django 3.0.9 on 2020-11-16 18:46

import django.core.validators
from django.db import migrations, models
import django_extensions.db.fields

import dandiapi.api.models.validation
import dandiapi.api.storage


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_remove_version_meta'),
    ]

    operations = [
        migrations.CreateModel(
            name='Validation',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                (
                    'created',
                    django_extensions.db.fields.CreationDateTimeField(
                        auto_now_add=True, verbose_name='created'
                    ),
                ),
                (
                    'modified',
                    django_extensions.db.fields.ModificationDateTimeField(
                        auto_now=True, verbose_name='modified'
                    ),
                ),
                (
                    'blob',
                    dandiapi.api.storage.DeconstructableFileField(
                        blank=True,
                        storage=dandiapi.api.models.validation._get_validation_blob_storage,
                        upload_to=dandiapi.api.models.validation._get_validation_blob_prefix,
                    ),
                ),
                (
                    'sha256',
                    models.CharField(
                        max_length=64,
                        unique=True,
                        validators=[django.core.validators.RegexValidator('^[0-9a-f]{64}$')],
                    ),
                ),
                (
                    'state',
                    models.CharField(
                        choices=[
                            ('IN_PROGRESS', 'In Progress'),
                            ('SUCCEEDED', 'Succeeded'),
                            ('FAILED', 'Failed'),
                        ],
                        max_length=20,
                    ),
                ),
                ('error', models.TextField(null=True)),
            ],
            options={
                'ordering': ('-modified', '-created'),
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
    ]
