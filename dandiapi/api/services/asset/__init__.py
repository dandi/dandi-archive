from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction

from dandiapi.api.asset_paths import add_asset_paths, delete_asset_paths, get_conflicting_paths
from dandiapi.api.models.asset import Asset, AssetBlob
from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.models.version import Version
from dandiapi.api.services.asset.exceptions import (
    AssetAlreadyExistsError,
    AssetPathConflictError,
    DandisetOwnerRequiredError,
    DraftDandisetNotModifiableError,
    ZarrArchiveBelongsToDifferentDandisetError,
)
from dandiapi.api.tasks import remove_asset_blob_embargoed_tag_task

if TYPE_CHECKING:
    from dandiapi.zarr.models import ZarrArchive


def _create_asset(
    *,
    path: str,
    asset_blob: AssetBlob | None = None,
    zarr_archive: ZarrArchive | None = None,
    metadata: dict,
):
    metadata = Asset.strip_metadata(metadata)

    asset = Asset(
        path=path,
        blob=asset_blob,
        zarr=zarr_archive,
        metadata=metadata,
        status=Asset.Status.PENDING,
    )
    asset.full_clean(validate_constraints=False)
    asset.save()

    return asset


def change_asset(  # noqa: PLR0913
    *,
    user,
    asset: Asset,
    version: Version,
    new_asset_blob: AssetBlob | None = None,
    new_zarr_archive: ZarrArchive | None = None,
    new_metadata: dict,
) -> tuple[Asset, bool]:
    """
    Change the blob/zarr/metadata of an asset if necessary.

    Returns a tuple of the asset, and whether or not it was changed. When changing an asset, a new
    asset is created automatically.
    """
    if not new_asset_blob and not new_zarr_archive:
        raise ValueError('One of new_zarr_archive or new_asset_blob must be given')
    if 'path' not in new_metadata:
        raise ValueError('Path must be present in new_metadata')

    if not user.has_perm('owner', version.dandiset):
        raise DandisetOwnerRequiredError
    if version.version != 'draft':
        raise DraftDandisetNotModifiableError

    path = new_metadata['path']
    new_metadata_stripped = Asset.strip_metadata(new_metadata)

    if not asset.is_different_from(
        asset_blob=new_asset_blob,
        zarr_archive=new_zarr_archive,
        metadata=new_metadata_stripped,
        path=path,
    ):
        return asset, False

    # Verify we aren't changing path to the same value as an existing asset
    if version.assets.filter(path=path).exclude(asset_id=asset.asset_id).exists():
        raise AssetAlreadyExistsError

    with transaction.atomic():
        remove_asset_from_version(user=user, asset=asset, version=version)

        new_asset = add_asset_to_version(
            user=user,
            version=version,
            asset_blob=new_asset_blob,
            zarr_archive=new_zarr_archive,
            metadata=new_metadata,
        )
        # Set previous asset and save
        new_asset.previous = asset
        new_asset.save()

    return new_asset, True


def add_asset_to_version(
    *,
    user,
    version: Version,
    asset_blob: AssetBlob | None = None,
    zarr_archive: ZarrArchive | None = None,
    metadata: dict,
) -> Asset:
    """Create an asset, adding it to a version."""
    if not asset_blob and not zarr_archive:
        raise RuntimeError(
            'One of zarr_archive or asset_blob must be given to add_asset_to_version'
        )
    if 'path' not in metadata:
        raise RuntimeError('Path must be present in metadata')

    if not user.has_perm('owner', version.dandiset):
        raise DandisetOwnerRequiredError
    if version.version != 'draft':
        raise DraftDandisetNotModifiableError

    # Check if there are already any assets with the same path
    path = metadata['path']
    if version.assets.filter(path=path).exists():
        raise AssetAlreadyExistsError

    # Check if there are any assets that conflict with this path
    conflicts = get_conflicting_paths(path, version)
    if conflicts:
        raise AssetPathConflictError(new_path=path, existing_paths=conflicts)

    # Ensure zarr archive doesn't already belong to a dandiset
    if zarr_archive and zarr_archive.dandiset != version.dandiset:
        raise ZarrArchiveBelongsToDifferentDandisetError

    # Creating an asset in an OPEN dandiset that points to an embargoed blob results in that
    # blob being un-embargoed
    unembargo_asset_blob = (
        asset_blob is not None
        and asset_blob.embargoed
        and version.dandiset.embargo_status == Dandiset.EmbargoStatus.OPEN
    )
    with transaction.atomic():
        if asset_blob and unembargo_asset_blob:
            asset_blob.embargoed = False
            asset_blob.save()

        asset = _create_asset(
            path=path, asset_blob=asset_blob, zarr_archive=zarr_archive, metadata=metadata
        )
        version.assets.add(asset)
        add_asset_paths(asset, version)

        # Trigger a version metadata validation, as saving the version might change the metadata
        version.status = Version.Status.PENDING
        # Save the version so that the modified field is updated
        version.save()

    # Perform this after the above transaction has finished, to ensure we only operate on
    # un-embargoed asset blobs
    if asset_blob and unembargo_asset_blob:
        remove_asset_blob_embargoed_tag_task.delay(blob_id=asset_blob.blob_id)

    return asset


def remove_asset_from_version(*, user, asset: Asset, version: Version) -> Version:
    if not user.has_perm('owner', version.dandiset):
        raise DandisetOwnerRequiredError
    if version.version != 'draft':
        raise DraftDandisetNotModifiableError

    with transaction.atomic():
        # Remove asset paths and asset itself from version
        delete_asset_paths(asset, version)
        version.assets.remove(asset)

        # Trigger a version metadata validation, as saving the version might change the metadata
        version.status = Version.Status.PENDING
        # Save the version so that the modified field is updated
        version.save()

    return version
