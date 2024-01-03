from __future__ import annotations
import djclick as click

from dandiapi.api.garbage import stale_assets


def echo_report():
    click.echo(f'Assets: {stale_assets().count()}')
    click.echo('AssetBlobs: Coming soon')
    click.echo('Uploads: Coming soon')
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

    if assetblobs:
        raise click.NoSuchOption('Deleting AssetBlobs is not yet implemented')
    if uploads:
        raise click.NoSuchOption('Deleting Uploads is not yet implemented')
    if s3blobs:
        raise click.NoSuchOption('Deleting S3 Blobs is not yet implemented')
    if assets:
        assets_to_delete = stale_assets()
        if click.confirm(f'This will delete {assets_to_delete.count()} assets. Are you sure?'):
            assets_to_delete.delete()

    # Log how many things there are, either after deletion
    # or if the user forgot to specify anything to delete
    echo_report()
