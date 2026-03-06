from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
import sys
from typing import TYPE_CHECKING

from dandischema.models import get_schema_version
from django.contrib.auth.models import User
from django.db import transaction
import djclick as click
from tqdm import tqdm

from dandiapi.api.models import Asset, Dandiset, Version
from dandiapi.api.services.asset import change_asset
from dandiapi.api.services.permissions.dandiset import get_dandiset_owners

if TYPE_CHECKING:
    from django.db.models import QuerySet

logger = logging.getLogger(__name__)

# The CLI only exists as an optional requirement, so ensure it's been specified correctly.
if importlib.util.find_spec('dandi') is None:
    click.echo('Module "dandi" not found. Please run:\n\tuv sync --extra cli')
    sys.exit(1)
else:
    from dandi.dandiapi import RemoteReadableAsset
    from dandi.metadata.nwb import nwb2asset
    from dandi.misctypes import Digest, DigestType


@click.group()
def group():
    pass


def get_asset_digest(asset: Asset) -> Digest:
    if asset.zarr is not None:
        return Digest(algorithm=DigestType.dandi_zarr_checksum, value=asset.zarr.checksum)
    if asset.sha256 is not None:
        return Digest(algorithm=DigestType.sha2_256, value=asset.sha256)

    # Default to Etag
    if asset.blob is not None:
        return Digest(algorithm=DigestType.dandi_etag, value=asset.blob.etag)

    raise Exception('Unsupported asset type')  # noqa: TRY002


def extract_asset_metadata(asset: Asset, draft_version: Version):
    readable_asset = RemoteReadableAsset(
        asset.s3_url, size=asset.size, mtime=asset.modified, name=Path(asset.path).name
    )

    if not asset.path.lower().endswith('.nwb'):
        logger.info('Asset %s: Not an NWB file, skipping...', asset.path)
        return

    new_metadata = nwb2asset(
        readable_asset, digest=get_asset_digest(asset), schema_version=get_schema_version()
    ).model_dump(mode='json', exclude_none=True)

    # Use dandiset owner, default to some admin user
    user = (
        get_dandiset_owners(draft_version.dandiset).first()
        or User.objects.filter(is_superuser=True, is_staff=True).first()
    )

    # Lock asset and version to ensure they don't change while performing this operation
    with transaction.atomic():
        locked_asset = Asset.objects.select_for_update().get(id=asset.id)
        locked_version = Version.objects.select_for_update().get(id=draft_version.id)

        # Ensure asset hasn't already been removed from the version
        if not locked_version.assets.filter(id=locked_asset.id).exists():
            raise Exception(f'Asset {locked_asset} no longer exists in version {locked_version}')  # noqa: TRY002

        # Replace old asset with new asset containing updated metadata
        change_asset(
            user=user,
            asset=locked_asset,
            version=locked_version,
            new_asset_blob=asset.blob,
            new_zarr_archive=asset.zarr,
            new_metadata=new_metadata,
        )


def extract_dandiset_assets(dandiset: Dandiset):
    # Only update NWB assets which are out of date and do not belong to a published version
    assets: QuerySet[Asset] = dandiset.draft_version.assets.filter(
        published=False,
        path__iendswith='.nwb',
        metadata__schemaVersion__lt=get_schema_version(),
    ).select_related('blob', 'zarr')
    if not assets:
        logger.info('No old draft NWB assets found in dandiset %s. Skipping...', dandiset)
        return

    for asset in tqdm(assets.iterator(), total=assets.count()):
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
    for version in draft_versions.iterator():
        extract_asset_metadata(asset=asset, draft_version=version)


@group.command(
    help='Re-extracts the metadata of all assets in the draft version of the provided dandiset'
)
@click.argument('dandiset_id')
def dandiset(dandiset_id: str):
    dandiset = Dandiset.objects.get(id=int(dandiset_id))
    extract_dandiset_assets(dandiset)


@group.command(name='all', help='Re-extracts the metadata of all assets in all draft versions')
def all_dandisets():
    for dandiset in Dandiset.objects.iterator():
        logger.info('DANDISET: %s', dandiset.identifier)
        extract_dandiset_assets(dandiset)
