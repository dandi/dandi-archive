from __future__ import annotations

from dandischema.consts import DANDI_SCHEMA_VERSION
import pytest

from dandiapi.api.asset_paths import (
    add_asset_paths,
    add_version_asset_paths,
    delete_asset_paths,
    delete_asset_paths_many,
    extract_paths,
    get_child_paths,
    get_conflicting_paths,
    get_path_entries,
    get_path_entry,
    search_asset_paths,
)
from dandiapi.api.models import Asset, AssetPath, Version
from dandiapi.api.services.asset import add_asset_to_version
from dandiapi.api.services.asset.exceptions import AssetAlreadyExistsError
from dandiapi.api.tasks import publish_dandiset_task
from dandiapi.api.tests.factories import DraftVersionFactory, UserFactory


@pytest.fixture
def ingested_asset(asset_factory) -> Asset:
    asset: Asset = asset_factory()
    version: Version = DraftVersionFactory.create()
    version.assets.add(asset)

    # Add asset to paths
    add_asset_paths(asset, version)

    return asset


@pytest.mark.parametrize(
    ('path', 'expected'),
    [
        ('foo.txt', ['foo.txt']),
        ('foo/bar.txt', ['foo', 'foo/bar.txt']),
        ('foo/bar/baz.txt', ['foo', 'foo/bar', 'foo/bar/baz.txt']),
    ],
)
def test_extract_paths(path, expected):
    assert extract_paths(path) == expected


@pytest.mark.django_db
def test_asset_path_add_asset(asset_factory):
    # Create asset with version
    asset: Asset = asset_factory()
    version: Version = DraftVersionFactory.create()
    version.assets.add(asset)

    # Add asset to paths
    add_asset_paths(asset, version)

    # Only the path of the asset itself is stored
    path: AssetPath = AssetPath.objects.get(version=version)
    assert path.asset == asset
    assert path.path == asset.path
    assert path.size == asset.size

    # Every path leading to the asset contains only that asset
    paths = extract_paths(asset.path)
    for parent_path in paths[:-1]:
        entry = get_path_entry(version, parent_path)
        assert entry is not None
        assert entry.asset is None
        assert entry.aggregate_size == asset.size
        assert entry.aggregate_files == 1

    entry = get_path_entry(version, asset.path)
    assert entry is not None
    assert entry.asset == asset
    assert entry.aggregate_size == asset.size
    assert entry.aggregate_files == 1


@pytest.mark.django_db
def test_asset_path_add_asset_idempotent(asset_factory):
    # Create asset with version
    asset: Asset = asset_factory()
    version: Version = DraftVersionFactory.create()
    version.assets.add(asset)

    # Add asset to paths
    add_asset_paths(asset, version)
    add_asset_paths(asset, version)

    # Get asset path
    path: AssetPath = AssetPath.objects.get(asset=asset, version=version)
    assert path.size == asset.size


@pytest.mark.django_db
def test_asset_path_add_asset_conflicting_path(asset_factory):
    # Create asset with version
    asset1: Asset = asset_factory()
    asset2: Asset = asset_factory(path=asset1.path)
    version: Version = DraftVersionFactory.create()
    version.assets.add(asset1)
    version.assets.add(asset2)

    # Add asset1 paths
    add_asset_paths(asset1, version)
    assert version.asset_paths.count() == 1

    # Ensure that adding asset2 raises the correct exception
    with pytest.raises(AssetAlreadyExistsError):
        add_asset_paths(asset2, version)

    # Ensure that there no new asset paths created
    assert version.asset_paths.count() == 1


@pytest.mark.django_db
def test_asset_path_add_version_asset_paths(asset_factory):
    # Create asset with version
    version: Version = DraftVersionFactory.create()
    version.assets.add(asset_factory(path='foo/bar/baz.txt'))
    version.assets.add(asset_factory(path='foo/bar/baz2.txt'))
    version.assets.add(asset_factory(path='foo/baz/file.txt'))
    version.assets.add(asset_factory(path='top.txt'))

    # Add version asset paths
    add_version_asset_paths(version)

    # Check paths have expected file count and size
    paths = [
        ('foo', 3, 300),
        ('foo/bar', 2, 200),
        ('foo/baz', 1, 100),
        ('top.txt', 1, 100),
    ]

    for path, count, size in paths:
        entry = get_path_entry(version, path)
        assert entry is not None
        assert entry.aggregate_files == count
        assert entry.aggregate_size == size

    # Assert no asset paths have a size of zero
    assert version.asset_paths.count() == 4
    assert not AssetPath.objects.filter(version=version, size=0).exists()


@pytest.mark.django_db
def test_asset_path_add_version_asset_paths_idempotent(asset_factory):
    # Create asset with version
    version: Version = DraftVersionFactory.create()
    version.assets.add(asset_factory(path='foo/bar/baz.txt'))
    version.assets.add(asset_factory(path='foo/bar/baz2.txt'))
    version.assets.add(asset_factory(path='foo/baz/file.txt'))
    version.assets.add(asset_factory(path='top.txt'))

    # Add version asset paths
    add_version_asset_paths(version)
    add_version_asset_paths(version)

    # Ensure no duplicate paths
    asset_paths = AssetPath.objects.select_related('asset').filter(version=version)
    assert asset_paths.count() == 4
    for path in asset_paths:
        assert path.size == path.asset.size


@pytest.mark.django_db
def test_asset_path_add_asset_shared_paths(asset_factory):
    # Create asset with version
    version: Version = DraftVersionFactory.create()
    asset1: Asset = asset_factory(path='foo/bar.txt')
    asset2: Asset = asset_factory(path='foo/baz.txt')
    version.assets.add(asset1)
    version.assets.add(asset2)

    # Add asset to paths
    add_asset_paths(asset1, version)
    add_asset_paths(asset2, version)

    # Get path
    path = get_path_entry(version, 'foo')
    assert path is not None
    assert asset1.blob is not None
    assert asset2.blob is not None
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
def test_asset_path_delete_asset_removes_empty_folders(asset_factory):
    version: Version = DraftVersionFactory.create()
    assets = [asset_factory(path=path) for path in ['a/b/c.txt', 'a/d.txt']]
    for asset in assets:
        version.assets.add(asset)
        add_asset_paths(asset, version)

    delete_asset_paths(assets[0], version)

    # A folder only exists for as long as it contains something
    assert get_path_entry(version, 'a/b') is None
    assert get_path_entry(version, 'a') is not None


@pytest.mark.django_db
def test_asset_path_delete_asset_paths_many(asset_factory):
    version: Version = DraftVersionFactory.create()
    assets = [asset_factory(path=path) for path in ['a/b.txt', 'a/c.txt', 'd.txt']]
    for asset in assets:
        version.assets.add(asset)
        add_asset_paths(asset, version)

    delete_asset_paths_many(assets[:2], version)

    assert list(version.asset_paths.values_list('path', flat=True)) == ['d.txt']


@pytest.mark.django_db
def test_asset_path_delete_asset_shared_paths(asset_factory, asset_blob_factory):
    # Create asset with version
    version: Version = DraftVersionFactory.create()
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
    path = get_path_entry(version, 'foo')
    assert path is not None
    assert asset2.blob is not None
    assert path.aggregate_size == asset2.blob.size
    assert path.aggregate_files == 1


@pytest.mark.django_db
def test_asset_path_search_asset_paths(asset_factory):
    version: Version = DraftVersionFactory.create()
    assets = [asset_factory(path=path) for path in ['foo/bar.txt', 'foo/baz.txt', 'bar/foo.txt']]
    for asset in assets:
        version.assets.add(asset)
        add_asset_paths(asset, version)

    # Search root path
    qs = search_asset_paths('', version)

    # Assert that there are two folders
    assert qs is not None
    assert qs.count() == 2
    entries = get_path_entries(qs, version)
    assert [x.path for x in entries] == ['bar', 'foo']
    assert [x.aggregate_files for x in entries] == [1, 2]
    assert all(x.asset is None for x in entries)

    # Search foo, assert there are two files. A trailing slash makes no difference.
    for query in ['foo', 'foo/']:
        qs = search_asset_paths(query, version)
        assert qs is not None
        assert qs.count() == 2
        entries = get_path_entries(qs, version)
        assert [x.path for x in entries] == ['foo/bar.txt', 'foo/baz.txt']
        assert [x.asset for x in entries] == assets[:2]

    # Search a file, which has no children
    qs = search_asset_paths('foo/bar.txt', version)
    assert qs is not None
    assert qs.count() == 0

    # Search paths that don't exist, including one that an existing path merely starts with
    assert search_asset_paths('baz', version) is None
    assert search_asset_paths('fo', version) is None


@pytest.mark.django_db
def test_asset_path_publish_version(asset_factory):
    user = UserFactory.create()
    version: Version = DraftVersionFactory.create()
    asset = asset_factory(path='foo/bar.txt', status=Asset.Status.VALID)
    version.assets.add(asset)
    add_asset_paths(asset, version)

    # Get existing paths
    paths = AssetPath.objects.filter(version=version).values_list('path', flat=True)

    # Pretend this dandiset is locked for publishing
    version.status = Version.Status.PUBLISHING
    version.save()

    # Publish
    publish_dandiset_task(version.dandiset.id, user.id)

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


@pytest.mark.django_db
def test_asset_path_get_child_paths(asset_factory):
    version = DraftVersionFactory.create()
    assets = {
        path: asset_factory(path=path)
        for path in ['a', 'b/c', 'b/d/e', 'b/d/f', 'b/g', 'd', 'e/f/g']
    }
    for asset in assets.values():
        version.assets.add(asset)
    add_version_asset_paths(version)

    # The asset paths of another version aren't included
    other_version = DraftVersionFactory.create()
    other_version.assets.add(asset_factory(path='b/other'))
    add_version_asset_paths(other_version)

    def children(folder: str) -> list[tuple[str, int, int, Asset | None]]:
        entries = get_path_entries(get_child_paths(version, folder), version)
        assert all(entry.version_id == version.id for entry in entries)
        return [(e.path, e.aggregate_files, e.aggregate_size, e.asset) for e in entries]

    assert children('') == [
        ('a', 1, 100, assets['a']),
        ('b', 4, 400, None),
        ('d', 1, 100, assets['d']),
        ('e', 1, 100, None),
    ]
    assert children('b') == [
        ('b/c', 1, 100, assets['b/c']),
        ('b/d', 2, 200, None),
        ('b/g', 1, 100, assets['b/g']),
    ]
    assert children('b/d') == [
        ('b/d/e', 1, 100, assets['b/d/e']),
        ('b/d/f', 1, 100, assets['b/d/f']),
    ]

    # Neither a file nor a path that doesn't exist has any children
    assert children('a') == []
    assert children('c') == []


@pytest.mark.django_db
def test_asset_path_get_child_paths_special_characters(asset_factory):
    """Test that the characters with a special meaning in a LIKE pattern are matched literally."""
    version = DraftVersionFactory.create()
    for path in ['a_b/c', 'aXb/d', 'aXX/f', 'a\\b/g', 'a\\\\/h']:
        version.assets.add(asset_factory(path=path))
    add_version_asset_paths(version)

    def children(folder: str) -> list[str]:
        return [row['child_path'] for row in get_child_paths(version, folder)]

    assert children('a_b') == ['a_b/c']
    assert children('a\\b') == ['a\\b/g']

    entry = get_path_entry(version, 'a_b')
    assert entry is not None
    assert entry.aggregate_files == 1
    assert get_conflicting_paths('a_b', version) == ['a_b/c']


@pytest.mark.django_db
def test_asset_path_get_path_entry(asset_factory):
    version = DraftVersionFactory.create()
    asset = asset_factory(path='a/b/c.txt')
    version.assets.add(asset)
    version.assets.add(asset_factory(path='a/d.txt'))
    add_version_asset_paths(version)

    folder = get_path_entry(version, 'a')
    assert folder is not None
    assert (folder.path, folder.aggregate_files, folder.aggregate_size) == ('a', 2, 200)
    assert folder.asset is None

    file = get_path_entry(version, 'a/b/c.txt')
    assert file is not None
    assert (file.path, file.aggregate_files, file.aggregate_size) == ('a/b/c.txt', 1, 100)
    assert file.asset == asset

    # A path that existing paths merely start with isn't a folder
    assert get_path_entry(version, 'a/b/c') is None
    assert get_path_entry(version, 'a/') is None
    assert get_path_entry(version, 'z') is None


@pytest.mark.django_db
def test_asset_path_get_conflicting_paths(asset_factory):
    version = DraftVersionFactory.create()
    for path in ['a/b/c.txt', 'a/b/d.txt', 'a/e.txt']:
        version.assets.add(asset_factory(path=path))
    add_version_asset_paths(version)

    # A file can't be added where there's a folder
    assert get_conflicting_paths('a', version) == ['a/b/c.txt', 'a/b/d.txt', 'a/e.txt']
    assert get_conflicting_paths('a/b', version) == ['a/b/c.txt', 'a/b/d.txt']

    # A file can't be added within what's already a file
    assert get_conflicting_paths('a/e.txt/f.txt', version) == ['a/e.txt']
    assert get_conflicting_paths('a/b/c.txt/f/g.txt', version) == ['a/b/c.txt']

    # Anything else is fine, including a path that's already a file
    assert get_conflicting_paths('a/b/f.txt', version) == []
    assert get_conflicting_paths('a/bb', version) == []
    assert get_conflicting_paths('a/e.txt', version) == []
    assert get_conflicting_paths('g/h.txt', version) == []


@pytest.mark.django_db
def test_asset_path_ordering(asset_blob):
    # The default collation will ignore special characters, including slashes, on the first pass. If
    # there are ties, it uses these characters to break ties. This means that in the below example,
    # removing the slashes leads to a comparison of 'az' and 'aaz', which would obviously sort the
    # latter before the former ('aaz', then 'az'). However, with the slashes, it's clear that 'a/z'
    # should come before 'aa/z'. This is fixed by changing the collation of the path field, and as
    # such this test serves as a regression test.
    user = UserFactory.create()
    draft_version = DraftVersionFactory.create(dandiset__owners=[user])
    add_asset_to_version(
        user=user,
        version=draft_version,
        asset_blob=asset_blob,
        metadata={
            'path': 'a/z',
            'schemaVersion': DANDI_SCHEMA_VERSION,
        },
    )
    add_asset_to_version(
        user=user,
        version=draft_version,
        asset_blob=asset_blob,
        metadata={
            'path': 'aa/z',
            'schemaVersion': DANDI_SCHEMA_VERSION,
        },
    )

    # This listing scenario likely wouldn't occur in the wild, due to how asset paths are
    # implemented. Nonetheless, it is a good test of this functionality.
    paths = AssetPath.objects.filter(version=draft_version, path__in=['a/z', 'aa/z']).order_by(
        'path'
    )
    assert paths[0].path == 'a/z'
    assert paths[1].path == 'aa/z'

    # The same collation applies to the folders derived from those paths
    add_asset_to_version(
        user=user,
        version=draft_version,
        asset_blob=asset_blob,
        metadata={
            'path': 'B/z',
            'schemaVersion': DANDI_SCHEMA_VERSION,
        },
    )
    assert [row['child_path'] for row in get_child_paths(draft_version)] == ['B', 'a', 'aa']
