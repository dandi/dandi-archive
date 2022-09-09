from django.db.models import QuerySet
import pytest

from dandiapi.api.models import Asset, AssetPath, Version
from dandiapi.api.models.asset_paths import AssetPathRelation
from dandiapi.api.services.asset import add_asset, delete_asset, publish_version


@pytest.fixture
def ingested_asset(draft_version_factory, asset_factory) -> Asset:
    asset: Asset = asset_factory()
    version: Version = draft_version_factory()
    version.assets.add(asset)

    # Add asset to paths
    add_asset(asset, version)

    return asset


@pytest.mark.django_db
def test_asset_path_add_asset(draft_version_factory, asset_factory):
    # Create asset with version
    asset: Asset = asset_factory()
    version: Version = draft_version_factory()
    version.assets.add(asset)

    # Add asset to paths
    add_asset(asset, version)

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
def test_asset_path_delete_asset(ingested_asset):
    asset = ingested_asset
    version = ingested_asset.versions.first()

    # Delete asset
    delete_asset(asset, version)

    # Ensure it no longer exists
    assert not AssetPath.objects.filter(asset=asset, version=version).exists()
    assert not AssetPath.objects.filter(path=asset.path, version=version).exists()


@pytest.mark.django_db
def test_asset_path_publish_version(draft_version_factory, asset_factory):
    version: Version = draft_version_factory()
    asset = asset_factory(path='foo/bar.txt')
    version.assets.add(asset)
    add_asset(asset, version)

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
