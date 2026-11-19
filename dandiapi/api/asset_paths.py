"""
Maintain and query the paths of the assets of a version.

Only the paths of assets are stored (see `AssetPath`). This means that changing the assets of a
version never writes to a row that's shared with any of its other assets. Folders are derived when
they're read, by grouping together the asset paths that are within them.

Because folders aren't stored, nothing in the database prevents a path from being used as both an
asset and a folder. Anything that adds an asset path must first check `get_conflicting_paths`,
while holding the lock on the version (see `lock_version_for_asset_changes`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.db import IntegrityError, transaction
from django.db.models import CharField, Count, Func, Max, Q, QuerySet, Sum, Value
from django.db.models.functions import Coalesce, Concat, StrIndex, Substr

# Import only the asset paths models
from dandiapi.api.models.asset_paths import AssetPath

# Import models for type checking only (prevent cyclic imports)
if TYPE_CHECKING:
    from collections.abc import Iterable

    from dandiapi.api.models import Asset, Version
    from dandiapi.zarr.models import ZarrArchive


####################################################################
# Dandiset and version deletion will cascade to asset path deletion.
# Thus, no explicit action is needed for these.
####################################################################


@dataclass(frozen=True)
class PathEntry:
    """A file or folder within a version."""

    path: str
    version_id: int

    # The number and total size of the assets at or within this path
    aggregate_files: int
    aggregate_size: int

    # The asset at this path, which is only present if this is a file
    asset: Asset | None


def extract_paths(path: str) -> list[str]:
    nodepaths: list[str] = path.split('/')
    for i in range(len(nodepaths))[1:]:
        nodepaths[i] = f'{nodepaths[i - 1]}/{nodepaths[i]}'

    return nodepaths


def get_child_paths(version: Version, folder: str = '') -> QuerySet[AssetPath, dict]:
    """
    Return the files and folders directly within a folder, ordered by path.

    The folder must not have a trailing slash, with the empty string being the root folder. Each
    row that's returned has the keys `child_path`, `aggregate_files`, `aggregate_size` and
    `asset_id`. Use `get_path_entries` to convert them into `PathEntry` objects.
    """
    prefix = f'{folder}/' if folder else ''
    asset_paths = AssetPath.objects.filter(version=version)
    if prefix:
        asset_paths = asset_paths.filter(path__startswith=prefix)

    # What remains of each asset path after the folder. Everything up to the first slash of that
    # is the name of the child that the asset path belongs to, and if there's no slash at all,
    # then that child is the asset itself.
    remainder = Substr('path', len(prefix) + 1)
    child_name = Func(
        remainder, Value('/'), Value(1), function='SPLIT_PART', output_field=CharField()
    )

    return (
        asset_paths.annotate(
            child_path=Concat(Value(prefix), child_name),
            remaining_slash=StrIndex(remainder, Value('/')),
        )
        .values('child_path')
        .annotate(
            aggregate_files=Count('id'),
            aggregate_size=Sum('size'),
            asset_id=Max('asset_id', filter=Q(remaining_slash=0)),
        )
        .order_by('child_path')
    )


def get_path_entries(rows: Iterable[dict], version: Version) -> list[PathEntry]:
    """Convert rows from `get_child_paths` into path entries, fetching the asset of any files."""
    # Imported here to prevent cyclic imports
    from dandiapi.api.models import Asset

    rows = list(rows)

    # Use prefetch_related here instead of select_related,
    # as otherwise the resulting join is very large
    assets = Asset.objects.prefetch_related('blob', 'zarr').in_bulk(
        [row['asset_id'] for row in rows if row['asset_id'] is not None]
    )

    return [
        PathEntry(
            path=row['child_path'],
            version_id=version.id,
            aggregate_files=row['aggregate_files'],
            aggregate_size=row['aggregate_size'],
            asset=assets.get(row['asset_id']),
        )
        for row in rows
    ]


def get_path_entry(version: Version, path: str) -> PathEntry | None:
    """Return the file or folder at a path, if there is one."""
    asset_path = (
        AssetPath.objects.select_related('asset', 'asset__blob', 'asset__zarr')
        .filter(version=version, path=path)
        .first()
    )
    if asset_path is not None:
        return PathEntry(
            path=path,
            version_id=version.id,
            aggregate_files=1,
            aggregate_size=asset_path.size,
            asset=asset_path.asset,
        )

    folder = AssetPath.objects.filter(version=version, path__startswith=f'{path}/').aggregate(
        aggregate_files=Count('id'), aggregate_size=Coalesce(Sum('size'), 0)
    )
    if folder['aggregate_files'] == 0:
        return None

    return PathEntry(path=path, version_id=version.id, asset=None, **folder)


def get_conflicting_paths(path: str, version: Version) -> list[str]:
    """Return a list of existing paths that conflict with the given path."""
    # This path can't already be a "folder", which it is if any existing paths are within it
    is_folder = Q(path__startswith=f'{path}/')

    # None of the "folders" that this path is within can already be a "file"
    is_file = Q(path__in=extract_paths(path)[:-1])

    return list(
        AssetPath.objects.filter(is_folder | is_file, version=version)
        .order_by('path')
        .values_list('path', flat=True)
    )


def search_asset_paths(query: str, version: Version) -> QuerySet[AssetPath, dict] | None:
    """Return all direct children of this path, if there are any."""
    # Ensure no trailing slash
    fixed_query = query.rstrip('/')

    children = get_child_paths(version, fixed_query)
    if not fixed_query:
        return children

    # A folder only exists if there's something within it, so if there isn't,
    # this is only a valid path if it's the path of a file, which has no children.
    if (
        not children.exists()
        and not AssetPath.objects.filter(version=version, path=fixed_query).exists()
    ):
        return None

    return children


@transaction.atomic
def add_asset_paths(asset: Asset, version: Version) -> AssetPath:
    """Add the path of an asset to a version, if it hasn't been added already."""
    try:
        asset_path, _ = AssetPath.objects.get_or_create(
            asset=asset, version=version, defaults={'path': asset.path, 'size': asset.size}
        )
    except IntegrityError as e:
        from dandiapi.api.services.asset.exceptions import AssetAlreadyExistsError

        # If there are simultaneous requests to create the same asset, this check constraint can
        # fail, and should be handled directly, rather than be allowed to bubble up
        if 'unique-version-path' in str(e):
            raise AssetAlreadyExistsError from e

        # Re-raise original exception otherwise
        raise

    return asset_path


def delete_asset_paths(asset: Asset, version: Version) -> None:
    """Remove the path of an asset from a version."""
    AssetPath.objects.filter(asset=asset, version=version).delete()


def delete_asset_paths_many(assets: list[Asset], version: Version) -> None:
    """Remove the paths of many assets from a version."""
    AssetPath.objects.filter(asset__in=assets, version=version).delete()


@transaction.atomic
def add_version_asset_paths(version: Version) -> None:
    """Add the path of every asset of a version which doesn't already have one."""
    assets = (
        version.assets.exclude(leaf_paths__version=version)
        .annotate(asset_size=Coalesce('blob__size', 'zarr__size'))
        .values_list('id', 'path', 'asset_size')
    )
    AssetPath.objects.bulk_create(
        (
            AssetPath(asset_id=asset_id, version=version, path=path, size=size)
            for asset_id, path, size in assets.iterator()
        ),
        batch_size=5_000,
    )


def update_zarr_asset_paths(zarr: ZarrArchive) -> None:
    """Update the size of all asset paths that are associated with a zarr."""
    # Only act on draft assets/versions
    AssetPath.objects.filter(
        asset__zarr=zarr, asset__published=False, version__version='draft'
    ).update(size=zarr.size)
