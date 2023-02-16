from django.db.models import Q, QuerySet
import pytest

from dandiapi.api.asset_paths import (
    add_asset_paths,
    add_version_asset_paths,
    delete_asset_paths,
    extract_paths,
    search_asset_paths,
    update_asset_paths,
)
from dandiapi.api.models import Asset, AssetPath, Version
from dandiapi.api.models.asset_paths import AssetPathRelation
from dandiapi.api.services.asset.exceptions import AssetAlreadyExists
from dandiapi.api.tasks import publish_dandiset_task


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
def test_asset_path_add_asset_idempotent(draft_version_factory, asset_factory):
    # Create asset with version
    asset: Asset = asset_factory()
    version: Version = draft_version_factory()
    version.assets.add(asset)

    # Add asset to paths
    add_asset_paths(asset, version)
    add_asset_paths(asset, version)

    # Get asset path
    path: AssetPath = AssetPath.objects.get(asset=asset, version=version)
    assert path.aggregate_files == 1
    assert path.aggregate_size == asset.size


@pytest.mark.django_db
def test_asset_path_add_asset_conflicting_path(draft_version_factory, asset_factory):
    # Create asset with version
    asset1: Asset = asset_factory()
    asset2: Asset = asset_factory(path=asset1.path)
    version: Version = draft_version_factory()
    version.assets.add(asset1)
    version.assets.add(asset2)

    # Add asset1 paths
    add_asset_paths(asset1, version)
    assert version.asset_paths.filter(asset__isnull=False).count() == 1

    # Ensure that adding asset2 raises the correct exception
    with pytest.raises(AssetAlreadyExists):
        add_asset_paths(asset2, version)

    # Ensure that there no new asset paths created
    assert version.asset_paths.filter(asset__isnull=False).count() == 1


@pytest.mark.django_db
def test_asset_path_add_version_asset_paths(draft_version_factory, asset_factory):
    # Create asset with version
    version: Version = draft_version_factory()
    version.assets.add(asset_factory(path='foo/bar/baz.txt'))
    version.assets.add(asset_factory(path='foo/bar/baz2.txt'))
    version.assets.add(asset_factory(path='foo/baz/file.txt'))
    version.assets.add(asset_factory(path='top.txt'))

    # Add verison asset paths
    add_version_asset_paths(version)

    # Check paths have expected file count and size
    paths = [
        ('foo', 3, 300),
        ('foo/bar', 2, 200),
        ('foo/baz', 1, 100),
        ('top.txt', 1, 100),
    ]

    # Check parent paths and relations
    for path, count, size in paths:
        asset_path = AssetPath.objects.get(version=version, path=path)
        assert asset_path.aggregate_files == count
        assert asset_path.aggregate_size == size

    # Assert no paths have size or file count of zero
    assert (
        not AssetPath.objects.filter(version=version)
        .filter(Q(aggregate_size=0) | Q(aggregate_files=0))
        .exists()
    )


@pytest.mark.django_db
def test_asset_path_add_version_asset_paths_idempotent(draft_version_factory, asset_factory):
    # Create asset with version
    version: Version = draft_version_factory()
    version.assets.add(asset_factory(path='foo/bar/baz.txt'))
    version.assets.add(asset_factory(path='foo/bar/baz2.txt'))
    version.assets.add(asset_factory(path='foo/baz/file.txt'))
    version.assets.add(asset_factory(path='top.txt'))

    # Add verison asset paths
    add_version_asset_paths(version)
    add_version_asset_paths(version)

    # Ensure no duplicate counts
    leafpaths = AssetPath.objects.select_related('asset').filter(
        version=version, asset__isnull=False
    )
    for path in leafpaths:
        assert path.aggregate_files == 1
        assert path.aggregate_size == path.asset.size


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
def test_asset_path_delete_asset_idempotent(ingested_asset):
    asset = ingested_asset
    version = ingested_asset.versions.first()

    # Try deleting twice, ensuring no error raised
    delete_asset_paths(asset, version)
    delete_asset_paths(asset, version)


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

    # Update asset (call twice to ensure idempotence)
    update_asset_paths(old_asset=old_asset, new_asset=new_asset, version=version)
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
def test_asset_path_search_asset_paths(draft_version_factory, asset_factory):
    version: Version = draft_version_factory()
    assets = [asset_factory(path=path) for path in ['foo/bar.txt', 'foo/baz.txt', 'bar/foo.txt']]
    for asset in assets:
        version.assets.add(asset)
        add_asset_paths(asset, version)

    # Search root path
    qs = search_asset_paths('', version)

    # Assert that there are two folders
    assert qs.count() == 2
    assert sorted([x.path for x in qs]) == ['bar', 'foo']
    assert all([x.asset is None for x in qs])

    # Search foo, assert there are two files
    qs = search_asset_paths('foo', version)
    assert qs.count() == 2
    assert all([x.asset is not None for x in qs])


@pytest.mark.django_db
def test_asset_path_publish_version(draft_version_factory, asset_factory):
    version: Version = draft_version_factory()
    asset = asset_factory(path='foo/bar.txt', status=Asset.Status.VALID)
    version.assets.add(asset)
    add_asset_paths(asset, version)

    # Get existing paths
    paths = AssetPath.objects.filter(version=version).values_list('path', flat=True)

    # Pretend this dandiset is locked for publishing
    version.status = Version.Status.PUBLISHING
    version.save()

    # Publish
    publish_dandiset_task(version.dandiset.id)

    # Get published version
    published_version = (
        Version.objects.filter(dandiset=version.dandiset)
        .exclude(version='draft')
        .order_by('-version')
        .first()
    )
    assert published_version is not None

    # Assert all paths copied
    for path in paths:
        AssetPath.objects.get(path=path, version=published_version)
