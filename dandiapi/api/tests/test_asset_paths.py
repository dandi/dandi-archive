from django.db.models import QuerySet
import pytest

from dandiapi.api.models import Asset, AssetPath, Version
from dandiapi.api.models.asset_paths import AssetPathRelation
from dandiapi.api.services.asset import (
    add_asset_paths,
    delete_asset_paths,
    publish_version,
    search_path,
    update_asset_paths,
)
from dandiapi.api.services.asset.utils import extract_paths


@pytest.fixture
def ingested_asset(draft_version_factory, asset_factory) -> Asset:
    asset: Asset = asset_factory()
    version: Version = draft_version_factory()
    version.assets.add(asset)

    # Add asset to paths
    add_asset_paths(asset, version)

    return asset


@pytest.mark.parametrize(
    'path,expected',
    [
        ('foo.txt', ['foo.txt']),
        ('foo/bar.txt', ['foo', 'foo/bar.txt']),
        ('foo/bar/baz.txt', ['foo', 'foo/bar', 'foo/bar/baz.txt']),
    ],
)
def test_extract_paths(path, expected):
    assert extract_paths(path) == expected


@pytest.mark.django_db
def test_asset_path_add_asset(draft_version_factory, asset_factory):
    # Create asset with version
    asset: Asset = asset_factory()
    version: Version = draft_version_factory()
    version.assets.add(asset)

    # Add asset to paths
    add_asset_paths(asset, version)

    # Get asset path
    path: AssetPath = AssetPath.objects.get(asset=asset, version=version)

    # Get parent paths
    parent_paths: QuerySet[AssetPath] = AssetPath.objects.filter(
        version=version, child_links__child=path
    )

    # Assert not empty
    assert parent_paths.exists()

    # Check parent paths and relations
    for path in parent_paths:
        assert path.aggregate_size == asset.size
        assert path.aggregate_files == 1

        # Assert self referencing link
        assert AssetPathRelation.objects.filter(parent=path, child=path).exists()

        # Get child paths
        child_paths = AssetPath.objects.filter(version=version, path__startswith=path.path).exclude(
            id=path.id
        )

        # Assert relation to all of these child paths exists
        assert (
            AssetPathRelation.objects.filter(parent=path, child__in=child_paths).count()
            == child_paths.count()
        )


@pytest.mark.django_db
def test_asset_path_add_asset_shared_paths(draft_version_factory, asset_factory):
    # Create asset with version
    version: Version = draft_version_factory()
    asset1: Asset = asset_factory(path='foo/bar.txt')
    asset2: Asset = asset_factory(path='foo/baz.txt')
    version.assets.add(asset1)
    version.assets.add(asset2)

    # Add asset to paths
    add_asset_paths(asset1, version)
    add_asset_paths(asset2, version)

    # Get path
    path = AssetPath.objects.get(path='foo', version=version)
    assert path.aggregate_size == asset1.blob.size + asset2.blob.size
    assert path.aggregate_files == 2


@pytest.mark.django_db
def test_asset_path_delete_asset(ingested_asset):
    asset = ingested_asset
    version = ingested_asset.versions.first()

    # Delete asset
    delete_asset_paths(asset, version)

    # Ensure it no longer exists
    assert not AssetPath.objects.filter(asset=asset, version=version).exists()
    assert not AssetPath.objects.filter(path=asset.path, version=version).exists()


@pytest.mark.django_db
def test_asset_path_update_asset(draft_version_factory, asset_factory):
    # Create asset with version
    version: Version = draft_version_factory()
    old_asset: Asset = asset_factory(path='a/b.txt')
    version.assets.add(old_asset)
    add_asset_paths(old_asset, version)

    # Create new asset
    new_asset: Asset = asset_factory(path='c/d.txt')
    version.assets.add(new_asset)
    add_asset_paths(new_asset, version)

    # Update asset
    update_asset_paths(old_asset=old_asset, new_asset=new_asset, version=version)

    # Assert none of old paths exist
    old_paths = extract_paths(old_asset.path)
    for path in old_paths:
        assert not AssetPath.objects.filter(path=path, version=version).exists()

    # Assert new paths exist
    new_paths = extract_paths(new_asset.path)
    for path in new_paths:
        assert AssetPath.objects.filter(path=path, version=version).exists()


@pytest.mark.django_db
def test_asset_path_delete_asset_shared_paths(
    draft_version_factory, asset_factory, asset_blob_factory
):
    # Create asset with version
    version: Version = draft_version_factory()
    asset1: Asset = asset_factory(path='foo/bar.txt', blob=asset_blob_factory(size=128))
    asset2: Asset = asset_factory(path='foo/baz.txt', blob=asset_blob_factory(size=256))
    version.assets.add(asset1)
    version.assets.add(asset2)

    # Add asset to paths
    add_asset_paths(asset1, version)
    add_asset_paths(asset2, version)

    # Delete asset
    delete_asset_paths(asset1, version)

    # Get path
    path = AssetPath.objects.get(path='foo', version=version)
    assert path.aggregate_size == asset2.blob.size
    assert path.aggregate_files == 1


@pytest.mark.django_db
def test_asset_path_search_path(draft_version_factory, asset_factory):
    version: Version = draft_version_factory()
    assets = [asset_factory(path=path) for path in ['foo/bar.txt', 'foo/baz.txt', 'bar/foo.txt']]
    for asset in assets:
        version.assets.add(asset)
        add_asset_paths(asset, version)

    # Search root path
    qs = search_path('', version)

    # Assert that there are two folders
    assert qs.count() == 2
    assert sorted([x.path for x in qs]) == ['bar', 'foo']
    assert all([x.asset is None for x in qs])

    # Search foo, assert there are two files
    qs = search_path('foo', version)
    assert qs.count() == 2
    assert all([x.asset is not None for x in qs])


@pytest.mark.django_db
def test_asset_path_publish_version(draft_version_factory, asset_factory):
    version: Version = draft_version_factory()
    asset = asset_factory(path='foo/bar.txt')
    version.assets.add(asset)
    add_asset_paths(asset, version)

    # Publish version
    published_version = version.publish_version
    published_version.save()

    # Check doesn't already exist
    paths = AssetPath.objects.filter(version=version).values_list('path', flat=True)
    assert not AssetPath.objects.filter(version=published_version).exists()

    # Publish version paths
    publish_version(version, published_version)

    # Assert all paths copied
    for path in paths:
        AssetPath.objects.get(path=path, version=published_version)
