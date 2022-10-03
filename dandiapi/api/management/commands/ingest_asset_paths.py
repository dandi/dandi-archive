import djclick as click

from dandiapi.api.models import Version
from dandiapi.api.services.asset.paths import add_asset_paths


def ingest_version_assets(version: Version):
    print(f'\t {version.assets.count()} assets')
    for asset in version.assets.all().iterator():
        add_asset_paths(asset, version)


@click.command()
def ingest_asset_paths():
    for version in Version.objects.all().iterator():
        print(f'Version: {version}')
        ingest_version_assets(version)
