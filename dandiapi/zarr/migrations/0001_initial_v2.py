import uuid

from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('api', '0001_initial_v2'),
    ]

    operations = [
        migrations.CreateModel(
            name='ZarrArchive',
            fields=[
                (
                    'id',
                    models.BigAutoField(
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
                ('zarr_id', models.UUIDField(db_index=True, default=uuid.uuid4, unique=True)),
                ('name', models.CharField(max_length=512)),
                ('file_count', models.BigIntegerField(default=0)),
                ('size', models.BigIntegerField(default=0)),
                ('checksum', models.CharField(default=None, max_length=512, null=True)),
                (
                    'status',
                    models.CharField(
                        choices=[
                            ('Pending', 'Pending'),
                            ('Uploaded', 'Uploaded'),
                            ('Ingesting', 'Ingesting'),
                            ('Complete', 'Complete'),
                        ],
                        default='Pending',
                        max_length=9,
                    ),
                ),
                (
                    'dandiset',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='zarr_archives',
                        to='api.dandiset',
                    ),
                ),
            ],
            options={
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='EmbargoedZarrArchive',
            fields=[
                (
                    'id',
                    models.BigAutoField(
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
                ('zarr_id', models.UUIDField(db_index=True, default=uuid.uuid4, unique=True)),
                ('name', models.CharField(max_length=512)),
                ('file_count', models.BigIntegerField(default=0)),
                ('size', models.BigIntegerField(default=0)),
                ('checksum', models.CharField(default=None, max_length=512, null=True)),
                (
                    'status',
                    models.CharField(
                        choices=[
                            ('Pending', 'Pending'),
                            ('Uploaded', 'Uploaded'),
                            ('Ingesting', 'Ingesting'),
                            ('Complete', 'Complete'),
                        ],
                        default='Pending',
                        max_length=9,
                    ),
                ),
                (
                    'dandiset',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='embargoed_zarr_archives',
                        to='api.dandiset',
                    ),
                ),
            ],
            options={
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.AddConstraint(
            model_name='zarrarchive',
            constraint=models.UniqueConstraint(
                fields=('dandiset', 'name'), name='zarr-zarrarchive-unique-name'
            ),
        ),
        migrations.AddConstraint(
            model_name='zarrarchive',
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(
                        ('checksum__isnull', True),
                        ('status__in', ['Pending', 'Uploaded', 'Ingesting']),
                    ),
                    models.Q(('checksum__isnull', False), ('status', 'Complete')),
                    _connector='OR',
                ),
                name='zarr-zarrarchive-consistent-checksum-status',
            ),
        ),
        migrations.AddConstraint(
            model_name='embargoedzarrarchive',
            constraint=models.UniqueConstraint(
                fields=('dandiset', 'name'), name='zarr-embargoedzarrarchive-unique-name'
            ),
        ),
        migrations.AddConstraint(
            model_name='embargoedzarrarchive',
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(
                        ('checksum__isnull', True),
                        ('status__in', ['Pending', 'Uploaded', 'Ingesting']),
                    ),
                    models.Q(('checksum__isnull', False), ('status', 'Complete')),
                    _connector='OR',
                ),
                name='zarr-embargoedzarrarchive-consistent-checksum-status',
            ),
        ),
    ]
