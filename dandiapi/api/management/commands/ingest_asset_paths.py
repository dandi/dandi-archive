import djclick as click

from dandiapi.api.asset_paths import add_version_asset_paths
from dandiapi.api.models import Version


@click.command()
def ingest_asset_paths():
    for version in Version.objects.iterator():
        click.echo(f'Version: {version}')
        click.echo(f'\t {version.assets.count()} assets')
        add_version_asset_paths(version)
