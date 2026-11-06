from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('zarr', '0005_remove_zarrarchive_embargoed'),
    ]

    operations = [
        migrations.AddField(
            model_name='zarrarchive',
            name='upload_type',
            field=models.CharField(
                choices=[('singlepart', 'Singlepart'), ('multipart', 'Multipart')],
                default='singlepart',
                max_length=10,
            ),
        ),
    ]
