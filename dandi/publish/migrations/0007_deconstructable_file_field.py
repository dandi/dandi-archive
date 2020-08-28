from django.db import migrations

import dandi.publish.models.asset
import dandi.publish.storage


class Migration(migrations.Migration):

    dependencies = [
        ('publish', '0006_populate_drafts_from_versions'),
    ]

    operations = [
        migrations.AlterField(
            model_name='asset',
            name='blob',
            field=dandi.publish.storage.DeconstructableFileField(
                blank=True,
                storage=dandi.publish.models.asset._get_asset_blob_storage,
                upload_to=dandi.publish.models.asset._get_asset_blob_prefix,
            ),
        ),
    ]
