# Generated by Django 4.1.1 on 2022-10-31 18:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('zarr', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='embargoedzarrarchive',
            name='checksum',
            field=models.CharField(blank=True, default=None, max_length=512, null=True),
        ),
        migrations.AlterField(
            model_name='zarrarchive',
            name='checksum',
            field=models.CharField(blank=True, default=None, max_length=512, null=True),
        ),
    ]
