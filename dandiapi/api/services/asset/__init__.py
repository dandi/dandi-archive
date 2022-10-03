from __future__ import annotations

from django.db import transaction
from django.db.models import F, QuerySet

from dandiapi.api.models import Asset, AssetPath, AssetPathRelation, Version
from dandiapi.api.services.asset.utils import extract_paths

from .query import get_path_children, get_root_paths


def search_path(query: str, version: Version) -> QuerySet[AssetPath] | None:
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


# TODO: Make idempotent
@transaction.atomic()
def add_asset_paths(asset: Asset, version: Version):
    # Get or create leaf path
    leaf, created = AssetPath.objects.get_or_create(path=asset.path, asset=asset, version=version)
    if not created:
        return

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

    # Get all relations (including leaf node)
    parent_ids = (
        AssetPathRelation.objects.filter(child=leaf)
        .distinct('parent')
        .values_list('parent', flat=True)
    )

    # Update size + file count
    AssetPath.objects.filter(id__in=parent_ids).update(
        aggregate_size=F('aggregate_size') + asset.size, aggregate_files=F('aggregate_files') + 1
    )


@transaction.atomic()
def delete_asset_paths(asset: Asset, version: Version):
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
        aggregate_size=F('aggregate_size') - asset.size, aggregate_files=F('aggregate_files') - 1
    )

    # Ensure integrity
    leaf.refresh_from_db()
    assert leaf.aggregate_size == 0
    assert leaf.aggregate_files == 0

    # Delete leaf node and any other paths with no contained files
    AssetPath.objects.filter(aggregate_files=0).delete()


@transaction.atomic()
def update_asset_paths(old_asset: Asset, new_asset: Version, version: Version):
    delete_asset_paths(old_asset, version)
    add_asset_paths(new_asset, version)


@transaction.atomic()
def publish_version(draft_version: Version, published_version: Version):
    # Add every asset from the draft version to the published version
    for asset in draft_version.assets.all().iterator():
        add_asset_paths(asset, published_version)
