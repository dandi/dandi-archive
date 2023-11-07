# Generated by Django 4.1.13 on 2023-11-07 01:06

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0044_remove_embargoedupload_modified_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='assetblob',
            name='sha256',
            field=models.CharField(
                blank=True,
                default='',
                max_length=64,
                validators=[django.core.validators.RegexValidator('^[0-9a-f]{64}$')],
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='embargoedassetblob',
            name='sha256',
            field=models.CharField(
                blank=True,
                default='',
                max_length=64,
                validators=[django.core.validators.RegexValidator('^[0-9a-f]{64}$')],
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='embargoedupload',
            name='etag',
            field=models.CharField(
                blank=True,
                db_index=True,
                default='',
                max_length=40,
                validators=[django.core.validators.RegexValidator('^[0-9a-f]{32}(-[1-9][0-9]*)?$')],
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='upload',
            name='etag',
            field=models.CharField(
                blank=True,
                db_index=True,
                default='',
                max_length=40,
                validators=[django.core.validators.RegexValidator('^[0-9a-f]{32}(-[1-9][0-9]*)?$')],
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='version',
            name='doi',
            field=models.CharField(blank=True, default='', max_length=64),
            preserve_default=False,
        ),
    ]
