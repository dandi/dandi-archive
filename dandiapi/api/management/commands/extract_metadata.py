from pathlib import Path

from dandi.dandiapi import RemoteReadableAsset
from dandi.metadata import nwb2asset
from django.contrib.auth.models import User
import djclick as click
from tqdm import tqdm

from dandiapi.api.models import Asset, Dandiset, Version
from dandiapi.api.services.asset import change_asset


@click.group()
def group():
    pass


def extract_asset_metadata(asset: Asset, draft_version: Version):
    readable_asset = RemoteReadableAsset(
        asset.s3_url, size=asset.size, mtime=asset.modified, name=Path(asset.path).name
    )
    new_metadata = nwb2asset(readable_asset).json_dict()

    # Use dandiset owner, default to some admin user
    user = draft_version.dandiset.owners.first()
    if user is None:
        user = User.objects.filter(is_superuser=True, is_staff=True).first()

    # Replace old asset with new asset containing updated metadata
    change_asset(
        user=user,
        asset=asset,
        version=draft_version,
        new_asset_blob=(asset.blob or asset.embargoed_blob),
        new_zarr_archive=asset.zarr,
        new_metadata=new_metadata,
    )


def extract_dandiset_assets(dandiset: Dandiset):
    # Only update assets which do not belong to a published version
    assets = dandiset.draft_version.assets.filter(published=False).select_related(
        'blob', 'embargoed_blob', 'zarr'
    )

    for asset in tqdm(assets):
        extract_asset_metadata(asset=asset, draft_version=dandiset.draft_version)


@group.command(help='Re-extracts the metadata of this asset')
@click.argument('asset_id')
def asset(asset_id: str):
    asset = Asset.objects.get(asset_id=asset_id)
    draft_versions = asset.versions.filter(version='draft')
    if not draft_versions.exists():
        raise click.ClickException(
            'Cannot re-extract metadata of asset that has no associated draft versions.'
        )

    # Re-extract for every draft version
    for version in draft_versions:
        extract_asset_metadata(asset=asset, draft_version=version)


@group.command(
    help='Re-extracts the metadata of all assets in the draft version of the provided dandiset'
)
@click.argument('dandiset_id')
def dandiset(dandiset_id: str):
    dandiset = Dandiset.objects.get(id=int(dandiset_id))
    extract_dandiset_assets(dandiset)


@group.command(help='Re-extracts the metadata of all assets in all draft versions')
def all():
    for dandiset in Dandiset.objects.all():
        print(f'DANDISET: {dandiset.identifier}')
        extract_dandiset_assets(dandiset)
