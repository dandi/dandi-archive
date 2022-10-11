import djclick as click

from dandiapi.api.asset_paths import add_asset_paths
from dandiapi.api.models import Version


def ingest_version_assets(version: Version):
    print(f'\t {version.assets.count()} assets')
    for asset in version.assets.all().iterator():
        add_asset_paths(asset, version)


@click.command()
def ingest_asset_paths():
    for version in Version.objects.all().iterator():
        print(f'Version: {version}')
        ingest_version_assets(version)
