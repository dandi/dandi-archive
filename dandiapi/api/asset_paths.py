from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import IntegrityError, transaction
from django.db.models import F, QuerySet, Sum
from django.db.models.functions import Coalesce
from tqdm import tqdm

# Import only the asset paths models
from dandiapi.api.models.asset_paths import AssetPath, AssetPathRelation

# Import models for type checking only (prevent cyclic imports)
if TYPE_CHECKING:
    from dandiapi.api.models import Asset, Version
    from dandiapi.zarr.models import ZarrArchive


####################################################################
# Dandiset and version deletion will cascade to asset path deletion.
# Thus, no explicit action is needed for these.
####################################################################


def extract_paths(path: str) -> list[str]:
    nodepaths: list[str] = path.split('/')
    for i in range(len(nodepaths))[1:]:
        nodepaths[i] = f'{nodepaths[i - 1]}/{nodepaths[i]}'

    return nodepaths


def get_root_paths_many(versions: QuerySet[Version], *, join_assets=False) -> QuerySet[AssetPath]:
    """Return all root paths for all provided versions."""
    qs = AssetPath.objects.get_queryset()

    # Use prefetch_related here instead of select_related,
    # as otherwise the resulting join is very large
    if join_assets:
        qs = qs.prefetch_related('asset', 'asset__blob', 'asset__zarr')

    return qs.filter(version__in=versions).exclude(path__contains='/').order_by('path')


def get_root_paths(version: Version) -> QuerySet[AssetPath]:
    """Return all root paths for a version."""
    # Use prefetch_related here instead of select_related,
    # as otherwise the resulting join is very large
    qs = AssetPath.objects.prefetch_related('asset', 'asset__blob', 'asset__zarr')
    return qs.filter(version=version).exclude(path__contains='/').order_by('path')


def get_path_children(path: AssetPath, depth: int | None = 1) -> QuerySet[AssetPath]:
    """
    Get all children from an existing path.

    By default, returns only the direct children.
    If depth is `None`, all children will be returned, regardless of depth.
    """
    relation_qs = AssetPathRelation.objects.filter(parent=path).exclude(child=path)
    if depth is not None:
        relation_qs = relation_qs.filter(depth=depth)

    path_ids = relation_qs.values_list('child', flat=True).distinct()
    return (
        AssetPath.objects.select_related('asset', 'asset__blob', 'asset__zarr')
        .filter(id__in=path_ids)
        .order_by('path')
    )


def get_conflicting_paths(path: str, version: Version) -> list[str]:
    """Return a list of existing paths that conflict with the given path."""
    # Check that this path isn't already occupied by a "folder"
    # Database constraints ensure this queryset could return at most 1 result
    folder = AssetPath.objects.filter(version=version, path=path, asset__isnull=True).first()
    if folder:
        return list(get_path_children(folder, depth=None).values_list('path', flat=True))

    # Check that this path doesn't conflict with any existing "files"
    nodepaths = extract_paths(path)[:-1]
    return list(
        AssetPath.objects.filter(
            version=version, path__in=nodepaths, asset__isnull=False
        ).values_list('path', flat=True)
    )


def search_asset_paths(query: str, version: Version) -> QuerySet[AssetPath] | None:
    """Return all direct children of this path, if there are any."""
    if not query:
        return get_root_paths(version)

    # Ensure no trailing slash
    fixed_query = query.rstrip('/')

    # Retrieve path
    path = AssetPath.objects.filter(version=version, path=fixed_query).first()
    if path is None:
        return None

    return get_path_children(path)


def insert_asset_paths(asset: Asset, version: Version):
    """Add all intermediate paths from an asset and link them together."""
    try:
        # Get or create leaf path
        leaf, created = AssetPath.objects.get_or_create(
            path=asset.path, asset=asset, version=version
        )
    except IntegrityError as e:
        from dandiapi.api.services.asset.exceptions import AssetAlreadyExistsError

        # If there are simultaneous requests to create the same asset, this check constraint can
        # fail, and should be handled directly, rather than be allowed to bubble up
        if 'unique-version-path' in str(e):
            raise AssetAlreadyExistsError from e

        # Re-raise original exception otherwise
        raise

    # If the asset was not created, return early, as the work is already done
    if not created:
        return leaf

    # Create absolute paths (exclude leaf node)
    nodepaths = extract_paths(asset.path)[:-1]

    # Create nodes
    AssetPath.objects.bulk_create(
        [AssetPath(path=path, version=version, asset=None) for path in nodepaths],
        ignore_conflicts=True,
    )

    # Retrieve all paths
    paths = [*AssetPath.objects.filter(version=version, path__in=nodepaths).order_by('path'), leaf]

    # Create relations between paths
    links = []
    for i in range(len(paths)):
        links.extend(
            [
                AssetPathRelation(parent=paths[i], child=paths[j], depth=j - i)
                for j in range(len(paths))[i:]
            ]
        )

    # Create objects
    AssetPathRelation.objects.bulk_create(links, ignore_conflicts=True)

    return leaf


def _add_asset_paths(asset: Asset, version: Version):
    leaf = insert_asset_paths(asset, version)

    # Only increment if it hasn't been performed yet
    if leaf.aggregate_files == 1:
        return

    # Increment the size and file count of all parent paths.
    # Get all relations (including leaf node)
    parent_ids = (
        AssetPathRelation.objects.filter(child=leaf)
        .distinct('parent')
        .values_list('parent', flat=True)
    )

    # Update size + file count
    AssetPath.objects.filter(id__in=parent_ids).update(
        aggregate_size=F('aggregate_size') + leaf.asset.size,
        aggregate_files=F('aggregate_files') + 1,
    )


def _delete_asset_paths(asset: Asset, version: Version):
    leaf: AssetPath | None = AssetPath.objects.filter(asset=asset, version=version).first()
    if leaf is None:
        return

    # Fetch parents
    parent_ids = (
        AssetPathRelation.objects.filter(child=leaf)
        .distinct('parent')
        .values_list('parent', flat=True)
    )
    parent_paths = AssetPath.objects.filter(id__in=parent_ids)

    # Get the previously computed size of the leaf node, not the current asset size,
    # in case the size of the AssetBlob/ZarrArchive that it points to has changed
    leaf_size = leaf.aggregate_size

    # Update parents
    parent_paths.update(
        aggregate_size=F('aggregate_size') - leaf_size,
        aggregate_files=F('aggregate_files') - 1,
    )

    # Ensure integrity
    leaf.refresh_from_db()
    if leaf.aggregate_size != 0:
        raise RuntimeError('Remaining non-zero aggregate_size')
    if leaf.aggregate_files != 0:
        raise RuntimeError('Remaining non-zero aggregate_files')

    # Delete leaf node and any other paths with no contained files
    AssetPath.objects.filter(aggregate_files=0).delete()


@transaction.atomic
def add_asset_paths(asset: Asset, version: Version):
    _add_asset_paths(asset, version)


@transaction.atomic
def delete_asset_paths(asset: Asset, version: Version):
    _delete_asset_paths(asset, version)


@transaction.atomic
def update_asset_paths(old_asset: Asset, new_asset: Asset, version: Version):
    _delete_asset_paths(old_asset, version)
    _add_asset_paths(new_asset, version)


@transaction.atomic
def add_version_asset_paths(version: Version):
    """Add every asset from a version."""
    # Leaves
    for asset in tqdm(version.assets.all()):
        insert_asset_paths(asset, version)

    # Compute aggregate file size + count for each asset path, instead of when each asset
    # is added. This is done because updating the same row many times within a transaction is slow.
    # https://stackoverflow.com/a/60221875

    # Get all nodes which haven't been computed yet
    nodes = AssetPath.objects.filter(version=version, aggregate_files=0)
    for node in tqdm(nodes):
        child_link_ids = node.child_links.distinct('child_id').values_list('child_id', flat=True)
        child_leaves = AssetPath.objects.filter(id__in=child_link_ids, asset__isnull=False)

        # Get all aggregates
        sizes = child_leaves.aggregate(
            size=Coalesce(Sum('asset__blob__size'), 0), zsize=Coalesce(Sum('asset__zarr__size'), 0)
        )

        node.aggregate_files += child_leaves.count()
        node.aggregate_size += sizes['size'] + sizes['zsize']
        node.save()


@transaction.atomic
def add_zarr_paths(zarr: ZarrArchive):
    """Add all asset paths that are associated with a zarr."""
    # Only act on draft assets/versions
    for asset in zarr.assets.filter(published=False).iterator():
        for version in asset.versions.filter(version='draft').iterator():
            _add_asset_paths(asset, version)


@transaction.atomic
def delete_zarr_paths(zarr: ZarrArchive):
    """Remove all asset paths that are associated with a zarr."""
    # Only act on draft assets/versions
    for asset in zarr.assets.filter(published=False).iterator():
        for version in asset.versions.filter(version='draft').iterator():
            _delete_asset_paths(asset, version)
