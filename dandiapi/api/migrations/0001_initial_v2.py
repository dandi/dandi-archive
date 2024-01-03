import uuid

from django.conf import settings
import django.contrib.postgres.indexes
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields

import dandiapi.api.models.asset
import dandiapi.api.models.metadata
import dandiapi.api.storage


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='Asset',
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
                ('asset_id', models.UUIDField(default=uuid.uuid4, unique=True)),
                (
                    'path',
                    models.CharField(
                        max_length=512, validators=[dandiapi.api.models.asset.validate_asset_path]
                    ),
                ),
                ('metadata', models.JSONField(blank=True, default=dict)),
                (
                    'status',
                    models.CharField(
                        choices=[
                            ('Pending', 'Pending'),
                            ('Validating', 'Validating'),
                            ('Valid', 'Valid'),
                            ('Invalid', 'Invalid'),
                        ],
                        default='Pending',
                        max_length=10,
                    ),
                ),
                ('validation_errors', models.JSONField(blank=True, default=list, null=True)),
                ('published', models.BooleanField(default=False)),
            ],
            bases=(dandiapi.api.models.metadata.PublishableMetadataMixin, models.Model),
        ),
        migrations.CreateModel(
            name='AssetBlob',
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
                ('blob_id', models.UUIDField(unique=True)),
                (
                    'sha256',
                    models.CharField(
                        blank=True,
                        max_length=64,
                        null=True,
                        validators=[django.core.validators.RegexValidator('^[0-9a-f]{64}$')],
                    ),
                ),
                (
                    'etag',
                    models.CharField(
                        max_length=40,
                        validators=[
                            django.core.validators.RegexValidator('^[0-9a-f]{32}(-[1-9][0-9]*)?$')
                        ],
                    ),
                ),
                ('size', models.PositiveBigIntegerField()),
                ('download_count', models.PositiveBigIntegerField(default=0)),
                (
                    'blob',
                    models.FileField(
                        blank=True,
                        storage=dandiapi.api.storage.get_storage,
                        upload_to=dandiapi.api.storage.get_storage_prefix,
                    ),
                ),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='AssetPath',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('path', models.CharField(max_length=512)),
                ('aggregate_files', models.PositiveBigIntegerField(default=0)),
                ('aggregate_size', models.PositiveBigIntegerField(default=0)),
                (
                    'asset',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='leaf_paths',
                        to='api.asset',
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name='Dandiset',
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
                (
                    'embargo_status',
                    models.CharField(
                        choices=[
                            ('EMBARGOED', 'Embargoed'),
                            ('UNEMBARGOING', 'Unembargoing'),
                            ('OPEN', 'Open'),
                        ],
                        default='OPEN',
                        max_length=12,
                    ),
                ),
            ],
            options={
                'ordering': ['id'],
                'permissions': [('owner', 'Owns the dandiset')],
            },
        ),
        migrations.CreateModel(
            name='Version',
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
                ('name', models.CharField(max_length=300)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                (
                    'version',
                    models.CharField(
                        max_length=13,
                        validators=[
                            django.core.validators.RegexValidator('^(0\\.\\d{6}\\.\\d{4})|draft$')
                        ],
                    ),
                ),
                ('doi', models.CharField(blank=True, max_length=64, null=True)),
                (
                    'status',
                    models.CharField(
                        choices=[
                            ('Pending', 'Pending'),
                            ('Validating', 'Validating'),
                            ('Valid', 'Valid'),
                            ('Invalid', 'Invalid'),
                            ('Publishing', 'Publishing'),
                            ('Published', 'Published'),
                        ],
                        default='Pending',
                        max_length=10,
                    ),
                ),
                ('validation_errors', models.JSONField(blank=True, default=list, null=True)),
                (
                    'dandiset',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='versions',
                        to='api.dandiset',
                    ),
                ),
            ],
            bases=(dandiapi.api.models.metadata.PublishableMetadataMixin, models.Model),
        ),
        migrations.CreateModel(
            name='UserMetadata',
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
                (
                    'status',
                    models.CharField(
                        choices=[
                            ('INCOMPLETE', 'Incomplete'),
                            ('PENDING', 'Pending'),
                            ('APPROVED', 'Approved'),
                            ('REJECTED', 'Rejected'),
                        ],
                        default='INCOMPLETE',
                        max_length=10,
                    ),
                ),
                ('questionnaire_form', models.JSONField(blank=True, null=True)),
                ('rejection_reason', models.TextField(blank=True, default='', max_length=1000)),
                (
                    'user',
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='metadata',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Upload',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True)),
                ('upload_id', models.UUIDField(db_index=True, default=uuid.uuid4, unique=True)),
                (
                    'etag',
                    models.CharField(
                        blank=True,
                        db_index=True,
                        max_length=40,
                        null=True,
                        validators=[
                            django.core.validators.RegexValidator('^[0-9a-f]{32}(-[1-9][0-9]*)?$')
                        ],
                    ),
                ),
                (
                    'multipart_upload_id',
                    models.CharField(db_index=True, max_length=128, unique=True),
                ),
                ('size', models.PositiveBigIntegerField()),
                (
                    'blob',
                    models.FileField(
                        blank=True,
                        storage=dandiapi.api.storage.get_storage,
                        upload_to=dandiapi.api.storage.get_storage_prefix,
                    ),
                ),
                (
                    'dandiset',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='uploads',
                        to='api.dandiset',
                    ),
                ),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='EmbargoedUpload',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True)),
                ('upload_id', models.UUIDField(db_index=True, default=uuid.uuid4, unique=True)),
                (
                    'etag',
                    models.CharField(
                        blank=True,
                        db_index=True,
                        max_length=40,
                        null=True,
                        validators=[
                            django.core.validators.RegexValidator('^[0-9a-f]{32}(-[1-9][0-9]*)?$')
                        ],
                    ),
                ),
                (
                    'multipart_upload_id',
                    models.CharField(db_index=True, max_length=128, unique=True),
                ),
                ('size', models.PositiveBigIntegerField()),
                (
                    'blob',
                    models.FileField(
                        blank=True,
                        storage=dandiapi.api.storage.get_embargo_storage,
                        upload_to=dandiapi.api.storage.get_embargo_storage_prefix,
                    ),
                ),
                (
                    'dandiset',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='embargoed_uploads',
                        to='api.dandiset',
                    ),
                ),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='EmbargoedAssetBlob',
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
                ('blob_id', models.UUIDField(unique=True)),
                (
                    'sha256',
                    models.CharField(
                        blank=True,
                        max_length=64,
                        null=True,
                        validators=[django.core.validators.RegexValidator('^[0-9a-f]{64}$')],
                    ),
                ),
                (
                    'etag',
                    models.CharField(
                        max_length=40,
                        validators=[
                            django.core.validators.RegexValidator('^[0-9a-f]{32}(-[1-9][0-9]*)?$')
                        ],
                    ),
                ),
                ('size', models.PositiveBigIntegerField()),
                ('download_count', models.PositiveBigIntegerField(default=0)),
                (
                    'blob',
                    models.FileField(
                        blank=True,
                        storage=dandiapi.api.storage.get_embargo_storage,
                        upload_to=dandiapi.api.storage.get_embargo_storage_prefix,
                    ),
                ),
                (
                    'dandiset',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='embargoed_asset_blobs',
                        to='api.dandiset',
                    ),
                ),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='DandisetUserObjectPermission',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                (
                    'content_object',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to='api.dandiset'
                    ),
                ),
                (
                    'permission',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to='auth.permission'
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='DandisetGroupObjectPermission',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                (
                    'content_object',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to='api.dandiset'
                    ),
                ),
                (
                    'group',
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='auth.group'),
                ),
                (
                    'permission',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to='auth.permission'
                    ),
                ),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='AssetPathRelation',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('depth', models.PositiveIntegerField()),
                (
                    'child',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='parent_links',
                        to='api.assetpath',
                    ),
                ),
                (
                    'parent',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='child_links',
                        to='api.assetpath',
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name='assetpath',
            name='version',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='asset_paths',
                to='api.version',
            ),
        ),
        migrations.AddIndex(
            model_name='assetblob',
            index=django.contrib.postgres.indexes.HashIndex(
                fields=['etag'], name='api_assetbl_etag_cf8377_hash'
            ),
        ),
        migrations.AddConstraint(
            model_name='assetblob',
            constraint=models.UniqueConstraint(fields=('etag', 'size'), name='unique-etag-size'),
        ),
        migrations.AddField(
            model_name='asset',
            name='blob',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='assets',
                to='api.assetblob',
            ),
        ),
        migrations.AddField(
            model_name='asset',
            name='embargoed_blob',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='assets',
                to='api.embargoedassetblob',
            ),
        ),
        migrations.AddField(
            model_name='asset',
            name='previous',
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='api.asset',
            ),
        ),
        migrations.AddField(
            model_name='asset',
            name='versions',
            field=models.ManyToManyField(related_name='assets', to='api.version'),
        ),
        migrations.AddIndex(
            model_name='version',
            index=django.contrib.postgres.indexes.HashIndex(
                fields=['metadata'], name='api_version_metadat_f0b8f8_hash'
            ),
        ),
        migrations.AddIndex(
            model_name='version',
            index=django.contrib.postgres.indexes.HashIndex(
                fields=['name'], name='api_version_name_5d8af6_hash'
            ),
        ),
        migrations.AddConstraint(
            model_name='version',
            constraint=models.CheckConstraint(
                check=models.Q(('metadata__schemaVersion__isnull', False)),
                name='version_metadata_has_schema_version',
            ),
        ),
        migrations.AlterUniqueTogether(
            name='version',
            unique_together={('dandiset', 'version')},
        ),
        migrations.AddIndex(
            model_name='upload',
            index=models.Index(fields=['etag'], name='api_upload_etag_a467fd_idx'),
        ),
        migrations.AddIndex(
            model_name='embargoedupload',
            index=models.Index(fields=['etag'], name='api_embargo_etag_064c86_idx'),
        ),
        migrations.AddIndex(
            model_name='embargoedassetblob',
            index=django.contrib.postgres.indexes.HashIndex(
                fields=['etag'], name='api_embargo_etag_06a255_hash'
            ),
        ),
        migrations.AddConstraint(
            model_name='embargoedassetblob',
            constraint=models.UniqueConstraint(
                fields=('dandiset', 'etag', 'size'), name='unique-embargo-etag-size'
            ),
        ),
        migrations.AlterUniqueTogether(
            name='dandisetuserobjectpermission',
            unique_together={('user', 'permission', 'content_object')},
        ),
        migrations.AlterUniqueTogether(
            name='dandisetgroupobjectpermission',
            unique_together={('group', 'permission', 'content_object')},
        ),
        migrations.AddConstraint(
            model_name='assetpathrelation',
            constraint=models.UniqueConstraint(
                fields=('parent', 'child'), name='unique-relationship'
            ),
        ),
        migrations.AddConstraint(
            model_name='assetpath',
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(('path__endswith', '/'), ('path__startswith', '/'), _connector='OR'),
                    _negated=True,
                ),
                name='consistent-slash',
            ),
        ),
        migrations.AddConstraint(
            model_name='assetpath',
            constraint=models.UniqueConstraint(
                fields=('asset', 'version'), name='unique-asset-version'
            ),
        ),
        migrations.AddConstraint(
            model_name='assetpath',
            constraint=models.UniqueConstraint(
                fields=('version', 'path'), name='unique-version-path'
            ),
        ),
        migrations.AddConstraint(
            model_name='assetpath',
            constraint=models.CheckConstraint(
                check=models.Q(
                    ('asset__isnull', True),
                    models.Q(('aggregate_files__lte', 1), ('asset__isnull', False)),
                    _connector='OR',
                ),
                name='consistent-leaf-paths',
            ),
        ),
        migrations.AddConstraint(
            model_name='asset',
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(('blob__isnull', True), ('embargoed_blob__isnull', True)),
                    models.Q(('blob__isnull', True), ('embargoed_blob__isnull', False)),
                    models.Q(('blob__isnull', False), ('embargoed_blob__isnull', True)),
                    _connector='OR',
                ),
                name='exactly-one-blob',
            ),
        ),
        migrations.AddConstraint(
            model_name='asset',
            constraint=models.CheckConstraint(
                check=models.Q(('metadata__schemaVersion__isnull', False)),
                name='asset_metadata_has_schema_version',
            ),
        ),
        migrations.AddConstraint(
            model_name='asset',
            constraint=models.CheckConstraint(
                check=models.Q(
                    ('path__regex', '^([A-z0-9(),&\\s#+~_=-]?\\/?\\.?[A-z0-9(),&\\s#+~_=-])+$')
                ),
                name='asset_path_regex',
            ),
        ),
        migrations.AddConstraint(
            model_name='asset',
            constraint=models.CheckConstraint(
                check=models.Q(('path__startswith', '/'), _negated=True),
                name='asset_path_no_leading_slash',
            ),
        ),
        migrations.AddConstraint(
            model_name='asset',
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(
                        ('published', False),
                        models.Q(
                            (
                                'metadata__has_any_keys',
                                [
                                    'id',
                                    'path',
                                    'identifier',
                                    'contentUrl',
                                    'contentSize',
                                    'digest',
                                    'datePublished',
                                    'publishedBy',
                                ],
                            ),
                            _negated=True,
                        ),
                    ),
                    models.Q(
                        ('published', True),
                        (
                            'metadata__has_keys',
                            [
                                'id',
                                'path',
                                'identifier',
                                'contentUrl',
                                'contentSize',
                                'digest',
                                'datePublished',
                                'publishedBy',
                            ],
                        ),
                    ),
                    _connector='OR',
                ),
                name='asset_metadata_no_computed_keys_or_published',
            ),
        ),
    ]
