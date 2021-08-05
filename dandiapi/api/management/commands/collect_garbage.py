import djclick as click

from dandiapi.api.garbage import stale_assets


def echo_report():
    click.echo(f'Assets: {stale_assets().count()}')
    click.echo(f'AssetBlobs: Coming soon')
    click.echo(f'Uploads: Coming soon')
    click.echo(f'S3 Blobs: Coming soon')


@click.command()
@click.option('--assets', is_flag=True, default=False, help="Delete Assets")
@click.option('--assetblobs', is_flag=True, default=False, help="Delete AssetBlobs")
@click.option('--uploads', is_flag=True, default=False, help="Delete Uploads")
@click.option('--s3blobs', is_flag=True, default=False, help="Delete S3 Blobs")
def collect_garbage(assets: bool, assetblobs: bool, uploads: bool, s3blobs: bool):
    """Manually run garbage collection on the database."""

    # Log how many things there are before deleting them
    doing_deletes = assets or assetblobs or uploads or s3blobs
    if doing_deletes:
        echo_report()

    if assets:
        click.echo(f'Deleting {stale_assets().count()} assets...')
        stale_assets().delete()
    if assetblobs:
        click.echo(f'Deleting AssetBlobs is not yet implemented')
    if uploads:
        click.echo(f'Deleting Uploads is not yet implemented')
    if s3blobs:
        click.echo(f'Deleting S3 Blobs is not yet implemented')

    # Log how many things there are, either after deletion
    # or if the user forgot to specify anything to delete
    echo_report()
