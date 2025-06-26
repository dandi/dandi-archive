from __future__ import annotations

from django.db.models import Sum
import djclick as click

from dandiapi.api.services import garbage_collection


def echo_report():
    garbage_collectable_assets = garbage_collection.asset.get_queryset()
    assets_count = garbage_collectable_assets.count()

    # Django doesn't support combining .distinct() and .aggregate() in a single query,
    # so we need to manually sum the sizes of the distinct blobs.
    assets_size_in_bytes = sum(
        size
        for size in garbage_collectable_assets.order_by('blob')
        .distinct('blob')
        .values_list('blob__size', flat=True)
        .iterator()
    )

    garbage_collectable_asset_blobs = garbage_collection.asset_blob.get_queryset()
    asset_blobs_count = garbage_collectable_asset_blobs.count()
    asset_blobs_size_in_bytes = garbage_collectable_asset_blobs.aggregate(Sum('size'))['size__sum']

    garbage_collectable_uploads = garbage_collection.upload.get_queryset()
    uploads_count = garbage_collectable_uploads.count()

    # Verification of upload size only happens if the upload is explicitly validated by the
    # client. It's reasonable to assume that many garbage-collectable uploads will not have
    # their size verified, so we cannot rely on the database here and must call out
    # to the storage backend to get the size of each upload.
    uploads_size_in_bytes = 0
    for upload in garbage_collectable_uploads.iterator():
        uploads_size_in_bytes += upload.blob.size

    click.echo(f'Assets: {assets_count} ({assets_size_in_bytes / (1024 ** 3):.2f} GB)')
    click.echo(
        f'AssetBlobs: {asset_blobs_count} ({asset_blobs_size_in_bytes / (1024 ** 3):.2f} GB)'
    )
    click.echo(f'Uploads: {uploads_count} ({uploads_size_in_bytes / (1024 ** 3):.2f} GB)')
    click.echo('S3 Blobs: Coming soon')


@click.command()
@click.option('--assets', is_flag=True, default=False, help='Delete Assets')
@click.option('--assetblobs', is_flag=True, default=False, help='Delete AssetBlobs')
@click.option('--uploads', is_flag=True, default=False, help='Delete Uploads')
@click.option('--s3blobs', is_flag=True, default=False, help='Delete S3 Blobs')
def collect_garbage(*, assets: bool, assetblobs: bool, uploads: bool, s3blobs: bool):
    """Manually run garbage collection on the database."""
    # Log how many things there are before deleting them
    doing_deletes = assets or assetblobs or uploads or s3blobs
    if doing_deletes:
        echo_report()

    if assetblobs and click.confirm('This will delete all AssetBlobs. Are you sure?'):
        garbage_collection.asset_blob.garbage_collect()
    if uploads and click.confirm('This will delete all Uploads. Are you sure?'):
        garbage_collection.upload.garbage_collect()
    if s3blobs and click.confirm('This will delete all S3 Blobs. Are you sure?'):
        raise click.NoSuchOption('Deleting S3 Blobs is not yet implemented')
    if assets and click.confirm('This will delete all Assets. Are you sure?'):
        garbage_collection.asset.garbage_collect()

    # Log how many things there are, either after deletion
    # or if the user forgot to specify anything to delete
    echo_report()
