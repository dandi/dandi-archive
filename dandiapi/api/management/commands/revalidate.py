from django.db.models import Exists, OuterRef
import djclick as click

from dandiapi.api.models import Asset, Version
from dandiapi.api.tasks import validate_asset_metadata, validate_version_metadata


@click.command()
@click.option('--assets', is_flag=True, default=False)
@click.option('--versions', is_flag=True, default=False)
def revalidate(assets: bool, versions: bool):
    """
    Revalidate all Versions and Assets.

    This script will run the validation immediately in band without dispatching tasks to the queue.
    """
    if assets:
        click.echo('Revalidating assets')
        for asset in Asset.objects.filter(status=Asset.Status.INVALID).values('id'):
            validate_asset_metadata(asset['id'])

    if versions:
        click.echo('Revalidating versions')
        # Only revalidate draft versions
        for version in Version.objects.filter(
            version='draft',
            status=Version.Status.INVALID,
        ).values('id'):
            validate_version_metadata(version['id'])
