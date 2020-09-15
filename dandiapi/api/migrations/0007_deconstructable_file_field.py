from django.db import migrations

import dandiapi.api.models.asset
import dandiapi.api.storage


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0006_populate_drafts_from_versions'),
    ]

    operations = [
        migrations.AlterField(
            model_name='asset',
            name='blob',
            field=dandiapi.api.storage.DeconstructableFileField(
                blank=True,
                storage=dandiapi.api.models.asset._get_asset_blob_storage,
                upload_to=dandiapi.api.models.asset._get_asset_blob_prefix,
            ),
        ),
    ]
