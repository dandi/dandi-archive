# Generated by Django 4.1.13 on 2024-01-16 18:31
from __future__ import annotations

from django.db import migrations, models


def migrate_embargoed_asset_blobs(apps, _):
    Asset = apps.get_model('api.Asset')
    AssetBlob = apps.get_model('api.AssetBlob')
    EmbargoedAssetBlob = apps.get_model('api.EmbargoedAssetBlob')

    def migrate_embargoed_blob(embargoed_blob):
        # Check if the blob we care about already exists (possibly under a different blob_id due to
        # de-duplication).
        # This will handle the following cases:
        #   1. This asset is part of an "asset chain", where multiple assets point to the same blob
        #   2. This blob this asset points to exists across multiple embargoed dandisets under
        #       different blob_ids, due to the lack of cross-dandiset embargo de-duplication.
        #   3. This blob this asset points to already exists as a normal AssetBlob, due to the lack
        #       of de-duplication between open and embargoed dandisets. This is essentially the same
        #       as the above case, but between an embargoed and open dandiset, instead of two
        #       embargoed dandisets.
        #
        # In case #3, the asset will effectively be unembargoed.
        existing_blob = AssetBlob.objects.filter(
            etag=embargoed_blob.etag, size=embargoed_blob.size
        ).first()
        if existing_blob:
            existing_blob.download_count += embargoed_blob.download_count
            existing_blob.save()
            return existing_blob

        blob_id = str(embargoed_blob.blob_id)
        new_blob_location = f'blobs/{blob_id[0:3]}/{blob_id[3:6]}/{blob_id}'
        return AssetBlob.objects.create(
            embargoed=True,
            blob=new_blob_location,
            blob_id=embargoed_blob.blob_id,
            created=embargoed_blob.created,
            modified=embargoed_blob.modified,
            sha256=embargoed_blob.sha256,
            etag=embargoed_blob.etag,
            size=embargoed_blob.size,
            download_count=embargoed_blob.download_count,
        )

    # For each relevant asset, create a new asset blob with embargoed=True,
    # and point the asset to that
    embargoed_assets = Asset.objects.filter(embargoed_blob__isnull=False).select_related(
        'embargoed_blob'
    )
    for asset in embargoed_assets.iterator():
        asset.blob = migrate_embargoed_blob(asset.embargoed_blob)
        asset.embargoed_blob = None
        asset.save()
    assert not Asset.objects.filter(embargoed_blob__isnull=False).exists()  # noqa: S101

    # Finally, handle orphaned EmbargoedAssetBlobs. Since we've already taken care of all assets
    # that point to embargoed blobs, we can migrate the remaining embargoed blobs without issue.
    embargoed_blobs = EmbargoedAssetBlob.objects.iterator()
    for embargoed_blob in embargoed_blobs:
        migrate_embargoed_blob(embargoed_blob)


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0007_alter_asset_options_alter_version_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='assetblob',
            name='embargoed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='upload',
            name='embargoed',
            field=models.BooleanField(default=False),
        ),
        # Migrate all embargoedassetblobs to assetblobs with embargoed=True
        migrations.RunPython(migrate_embargoed_asset_blobs),
    ]
