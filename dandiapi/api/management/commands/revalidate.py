from django.db.models import Exists, OuterRef
import djclick as click

from dandiapi.api.models import Asset, Version
from dandiapi.api.tasks import validate_asset_metadata, validate_version_metadata


@click.command()
@click.option('--assets', is_flag=True, default=False)
@click.option('--versions', is_flag=True, default=False)
@click.option('--revalidate-all', is_flag=True, default=False)
@click.option('--dry-run', is_flag=True, default=False)
def revalidate(assets: bool, versions: bool, revalidate_all: bool, dry_run: bool):
    """
    Revalidate all Versions and Assets.

    This script will run the validation immediately in band without dispatching tasks to the queue.
    """
    if assets:
        asset_qs = Asset.objects
        if not revalidate_all:
            asset_qs = asset_qs.filter(status=Asset.Status.INVALID)
        click.echo(f'Revalidating {asset_qs.count()} assets')
        if not dry_run:
            for asset in asset_qs.values('id'):
                validate_asset_metadata(asset['id'])

    if versions:
        # Only revalidate draft versions
        version_qs = Version.objects.filter(version='draft')
        if not revalidate_all:
            version_qs = version_qs.filter(
                status=Version.Status.INVALID,
            )
        click.echo(f'Revalidating {version_qs.count()} versions')
        if not dry_run:
            for version in version_qs.values('id'):
                validate_version_metadata(version['id'])
