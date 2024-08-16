from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from dandiapi.api.asset_paths import add_asset_paths, delete_asset_paths, get_conflicting_paths
from dandiapi.api.models.asset import Asset, AssetBlob
from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.models.version import Version
from dandiapi.api.services import audit
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


def _add_asset_to_version(
    *,
    version: Version,
    asset_blob: AssetBlob | None,
    zarr_archive: ZarrArchive | None,
    metadata: dict,
) -> Asset:
    path = metadata['path']
    asset = _create_asset(
        path=path, asset_blob=asset_blob, zarr_archive=zarr_archive, metadata=metadata
    )
    version.assets.add(asset)
    add_asset_paths(asset, version)

    # Trigger a version metadata validation, as saving the version might change the metadata
    Version.objects.filter(id=version.id).update(
        status=Version.Status.PENDING, modified=timezone.now()
    )

    return asset


def _remove_asset_from_version(*, asset: Asset, version: Version):
    # Remove asset paths and asset itself from version
    delete_asset_paths(asset, version)
    version.assets.remove(asset)

    # Trigger a version metadata validation, as saving the version might change the metadata
    Version.objects.filter(id=version.id).update(
        status=Version.Status.PENDING, modified=timezone.now()
    )


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
        _remove_asset_from_version(asset=asset, version=version)
        new_asset = _add_asset_to_version(
            version=version,
            asset_blob=new_asset_blob,
            zarr_archive=new_zarr_archive,
            metadata=new_metadata,
        )

        # Set previous asset and save
        new_asset.previous = asset
        new_asset.save()

        audit.update_asset(dandiset=version.dandiset, user=user, asset=new_asset)

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

    with transaction.atomic():
        # Creating an asset in an OPEN dandiset that points to an embargoed blob results in that
        # blob being unembargoed
        if (
            asset_blob is not None
            and asset_blob.embargoed
            and version.dandiset.embargo_status == Dandiset.EmbargoStatus.OPEN
        ):
            asset_blob.embargoed = False
            asset_blob.save()
            transaction.on_commit(
                lambda: remove_asset_blob_embargoed_tag_task.delay(blob_id=asset_blob.blob_id)
            )

        asset = _add_asset_to_version(
            version=version,
            asset_blob=asset_blob,
            zarr_archive=zarr_archive,
            metadata=metadata,
        )
        audit.add_asset(dandiset=version.dandiset, user=user, asset=asset)

    return asset


def remove_asset_from_version(*, user, asset: Asset, version: Version) -> Version:
    if not user.has_perm('owner', version.dandiset):
        raise DandisetOwnerRequiredError
    if version.version != 'draft':
        raise DraftDandisetNotModifiableError

    with transaction.atomic():
        _remove_asset_from_version(asset=asset, version=version)
        audit.remove_asset(dandiset=version.dandiset, user=user, asset=asset)

    return version
