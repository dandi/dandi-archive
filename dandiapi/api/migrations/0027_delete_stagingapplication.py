from __future__ import annotations

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0026_alter_assetblob_etag_alter_upload_etag'),
    ]

    operations = [
        migrations.DeleteModel(
            name='StagingApplication',
        ),
    ]
