from __future__ import annotations

import contextlib
import os

from django.db.models import Count, F, QuerySet, Sum
from django.db.models.functions import Coalesce
from django.db.transaction import atomic

from dandiapi.api.models import Asset, AssetPath, AssetPathRelation, Version
from dandiapi.zarr.models import ZarrArchive

####################################################################
# Dandiset and version deletion will cascade to asset path deletion.
# Thus, no explicit action is needed for these.
####################################################################


def extract_paths(path: str) -> list[str]:
    nodepaths: list[str] = path.split('/')
    for i in range(len(nodepaths))[1:]:
        nodepaths[i] = os.path.join(nodepaths[i - 1], nodepaths[i])

    return nodepaths


def get_root_paths(version: Version) -> QuerySet[AssetPath]:
    """Return all root paths for a version."""
    # Use prefetch_related here instead of select_related,
    # as otherwise the resulting join is very large
    qs = AssetPath.objects.prefetch_related(
        'asset',
        'asset__blob',
        'asset__embargoed_blob',
        'asset__zarr',
    )
    return (
        qs.filter(version=version)
        .alias(num_parents=Count('parent_links'))
        .filter(num_parents=1)
        .order_by('path')
    )


def get_path_children(path: AssetPath) -> QuerySet[AssetPath]:
    """Get all direct children from an existing path."""
    qs = AssetPath.objects.select_related(
        'asset',
        'asset__blob',
        'asset__embargoed_blob',
        'asset__zarr',
    )
    path_ids = (
        AssetPathRelation.objects.filter(parent=path, depth=1)
        .values_list('child', flat=True)
        .distinct()
    )
    return qs.filter(id__in=path_ids).order_by('path')


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
    # Get or create leaf path
    leaf, created = AssetPath.objects.get_or_create(path=asset.path, asset=asset, version=version)
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


# TODO: Make idempotent
def add_asset_paths(asset: Asset, version: Version, transaction=True):
    with atomic() if transaction else contextlib.nullcontext():
        # Insert leaf node and all required parent paths
        leaf = insert_asset_paths(asset, version)

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


def delete_asset_paths(asset: Asset, version: Version, transaction=True):
    with atomic() if transaction else contextlib.nullcontext():
        leaf: AssetPath = AssetPath.objects.get(asset=asset, version=version)

        # Fetch parents
        parent_ids = (
            AssetPathRelation.objects.filter(child=leaf)
            .distinct('parent')
            .values_list('parent', flat=True)
        )
        parent_paths = AssetPath.objects.filter(id__in=parent_ids)

        # Update parents
        parent_paths.update(
            aggregate_size=F('aggregate_size') - asset.size,
            aggregate_files=F('aggregate_files') - 1,
        )

        # Ensure integrity
        leaf.refresh_from_db()
        assert leaf.aggregate_size == 0
        assert leaf.aggregate_files == 0

        # Delete leaf node and any other paths with no contained files
        AssetPath.objects.filter(aggregate_files=0).delete()


@atomic()
def update_asset_paths(old_asset: Asset, new_asset: Asset, version: Version):
    delete_asset_paths(old_asset, version, transaction=False)
    add_asset_paths(new_asset, version, transaction=False)


@atomic()
def add_version_asset_paths(version: Version):
    """Add every asset from a version."""
    for asset in version.assets.all().iterator():
        insert_asset_paths(asset, version)

    # Compute aggregate file size + count for each asset path, instead of when each asset
    # is added. This is done because updating the same row many times within a transaction is slow.
    # https://stackoverflow.com/a/60221875
    nodes = AssetPath.objects.filter(version=version)
    for node in nodes:
        child_link_ids = node.child_links.distinct('child_id').values_list('child_id', flat=True)
        child_leaves = AssetPath.objects.filter(id__in=child_link_ids, asset__isnull=False)

        # Get all aggregates
        sizes = child_leaves.aggregate(
            size=Coalesce(Sum('asset__blob__size'), 0),
            esize=Coalesce(Sum('asset__embargoed_blob__size'), 0),
            zsize=Coalesce(Sum('asset__zarr__size'), 0),
        )

        node.aggregate_files += child_leaves.count()
        node.aggregate_size += sizes['size'] + sizes['esize'] + sizes['zsize']
        node.save()


@atomic()
def add_zarr_paths(zarr: ZarrArchive):
    """Add all asset paths that are associated with a zarr."""
    # Only act on draft assets/versions
    for asset in zarr.assets.filter(published=False).iterator():
        for version in asset.versions.filter(version='draft').iterator():
            add_asset_paths(asset, version, transaction=False)


@atomic()
def delete_zarr_paths(zarr: ZarrArchive):
    """Remove all asset paths that are associated with a zarr."""
    # Only act on draft assets/versions
    for asset in zarr.assets.filter(published=False).iterator():
        for version in asset.versions.filter(version='draft').iterator():
            delete_asset_paths(asset, version, transaction=False)
