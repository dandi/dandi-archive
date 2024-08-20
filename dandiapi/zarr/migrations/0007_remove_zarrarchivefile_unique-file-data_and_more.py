# Generated by Django 4.1.13 on 2024-08-20 00:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('zarr', '0006_remove_zarrarchivefile_unique-zarr-key-version_and_more'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='zarrarchivefile',
            name='unique-file-data',
        ),
        migrations.AlterField(
            model_name='zarrarchivefile',
            name='zarr_version',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='files', to='zarr.zarrarchiveversion'),
        ),
    ]
