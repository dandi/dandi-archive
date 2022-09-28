from django.db.models import Count, QuerySet

from dandiapi.api.models import AssetPath, AssetPathRelation, Version


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
    return qs.filter(version=version).alias(num_parents=Count('parent_links')).filter(num_parents=1)


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
    return qs.filter(id__in=path_ids)
