from django.db import transaction

from dandiapi.api.asset_paths import (
    add_asset_paths,
    delete_asset_paths,
    get_conflicting_paths,
    update_asset_paths,
)
from dandiapi.api.models.asset import Asset, AssetBlob, EmbargoedAssetBlob
from dandiapi.api.models.version import Version
from dandiapi.api.services.asset.exceptions import (
    AssetAlreadyExists,
    AssetPathConflict,
    DandisetOwnerRequired,
    DraftDandisetNotModifiable,
    ZarrArchiveBelongsToDifferentDandiset,
)
from dandiapi.api.services.asset.metadata import _maybe_validate_asset_metadata
from dandiapi.zarr.models import ZarrArchive


def _create_asset(
    *,
    path: str,
    asset_blob: AssetBlob | None = None,
    embargoed_asset_blob: EmbargoedAssetBlob | None = None,
    zarr_archive: ZarrArchive | None = None,
    metadata: dict,
):
    metadata = Asset.strip_metadata(metadata)

    asset = Asset(
        path=path,
        blob=asset_blob,
        embargoed_blob=embargoed_asset_blob,
        zarr=zarr_archive,
        metadata=metadata,
        status=Asset.Status.PENDING,
    )
    asset.full_clean(validate_constraints=False)
    asset.save()

    return asset


def change_asset(
    *,
    user,
    asset: Asset,
    version: Version,
    new_asset_blob: AssetBlob | EmbargoedAssetBlob | None = None,
    new_zarr_archive: ZarrArchive | None = None,
    new_metadata: dict,
) -> tuple[Asset, bool]:
    """
    Change the blob/zarr/metadata of an asset if necessary.

    Returns a tuple of the asset, and whether or not it was changed. When changing an asset, a new
    asset is created automatically.
    """
    assert (
        new_asset_blob or new_zarr_archive
    ), 'One of new_zarr_archive or new_asset_blob must be given to change_asset_metadata'
    assert 'path' in new_metadata, 'Path must be present in new_metadata'

    if not user.has_perm('owner', version.dandiset):
        raise DandisetOwnerRequired()
    elif version.version != 'draft':
        raise DraftDandisetNotModifiable()

    path = new_metadata['path']
    new_metadata_stripped = Asset.strip_metadata(new_metadata)

    if not asset.is_different_from(
        asset_blob=new_asset_blob, zarr_archive=new_zarr_archive, metadata=new_metadata_stripped
    ):
        return asset, False

    # Check if there are any assets that conflict with this path
    conflicts = get_conflicting_paths(path, version)
    if conflicts:
        raise AssetPathConflict(new_path=path, existing_paths=conflicts)

    # Verify we aren't changing path to the same value as an existing asset
    if version.assets.filter(path=path).exclude(asset_id=asset.asset_id).exists():
        raise AssetAlreadyExists()

    # Ensure zarr archive doesn't already belong to a dandiset
    if new_zarr_archive and new_zarr_archive.dandiset != version.dandiset:
        raise ZarrArchiveBelongsToDifferentDandiset()

    with transaction.atomic():
        # remove_asset_from_version(user=user, asset=asset, version=version)

        # new_asset = add_asset_to_version(
        #     user=user,
        #     version=version,
        #     asset_blob=new_asset_blob,
        #     zarr_archive=new_zarr_archive,
        #     metadata=new_metadata,
        # )
        # Set previous asset and save
        # new_asset.previous = asset
        # new_asset.save()

        # Delete asset path
        delete_asset_paths(asset=asset, version=version)

        # Assign new values, clean and save
        asset.zarr = new_zarr_archive
        asset.blob = new_asset_blob
        asset.metadata = new_metadata_stripped
        asset.full_clean(validate_constraints=False)
        asset.save()

        # Add asset path back
        add_asset_paths(asset=asset, version=version)

        # Trigger a version metadata validation, as saving the version might change the metadata
        version.status = Version.Status.PENDING
        # Save the version so that the modified field is updated
        version.save()

    return asset, True


def add_asset_to_version(
    *,
    user,
    version: Version,
    asset_blob: AssetBlob | EmbargoedAssetBlob | None = None,
    zarr_archive: ZarrArchive | None = None,
    metadata: dict,
) -> Asset:
    """Create an asset, adding it to a version."""
    assert (
        asset_blob or zarr_archive
    ), 'One of zarr_archive or asset_blob must be given to add_asset_to_version'
    assert 'path' in metadata, 'Path must be present in metadata'

    if not user.has_perm('owner', version.dandiset):
        raise DandisetOwnerRequired()
    elif version.version != 'draft':
        raise DraftDandisetNotModifiable()

    # Check if there are already any assets with the same path
    path = metadata['path']
    if version.assets.filter(path=path).exists():
        raise AssetAlreadyExists()

    # Check if there are any assets that conflict with this path
    conflicts = get_conflicting_paths(path, version)
    if conflicts:
        raise AssetPathConflict(new_path=path, existing_paths=conflicts)

    # Ensure zarr archive doesn't already belong to a dandiset
    if zarr_archive and zarr_archive.dandiset != version.dandiset:
        raise ZarrArchiveBelongsToDifferentDandiset()

    if isinstance(asset_blob, EmbargoedAssetBlob):
        embargoed_asset_blob = asset_blob
        asset_blob = None
    else:
        embargoed_asset_blob = None
        asset_blob = asset_blob

    with transaction.atomic():
        asset = _create_asset(
            path=path,
            asset_blob=asset_blob,
            embargoed_asset_blob=embargoed_asset_blob,
            zarr_archive=zarr_archive,
            metadata=metadata,
        )
        version.assets.add(asset)
        add_asset_paths(asset, version)

        # Trigger a version metadata validation, as saving the version might change the metadata
        version.status = Version.Status.PENDING
        # Save the version so that the modified field is updated
        version.save()

    # The sha256 may have been newly calculated in the time since the asset was created. If so, we
    # need to fetch the latest record from the DB so that _maybe_validate_asset_metadata sees the
    # new sha256 value and includes it in the asset metadata properly.
    asset.refresh_from_db()

    _maybe_validate_asset_metadata(asset)

    return asset


def remove_asset_from_version(*, user, asset: Asset, version: Version) -> Version:
    if not user.has_perm('owner', version.dandiset):
        raise DandisetOwnerRequired()
    elif version.version != 'draft':
        raise DraftDandisetNotModifiable()

    with transaction.atomic():
        # Remove asset paths and asset itself from version
        delete_asset_paths(asset, version)
        version.assets.remove(asset)

        # Trigger a version metadata validation, as saving the version might change the metadata
        version.status = Version.Status.PENDING
        # Save the version so that the modified field is updated
        version.save()

    return version
