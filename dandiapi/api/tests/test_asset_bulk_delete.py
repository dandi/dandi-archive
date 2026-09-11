from __future__ import annotations

from uuid import uuid4

import pytest

from dandiapi.api.asset_paths import add_asset_paths
from dandiapi.api.models import AuditRecord, Version
from dandiapi.api.models.asset_paths import AssetPath
from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.tests.factories import (
    DraftVersionFactory,
    PublishedVersionFactory,
    UserFactory,
)


def bulk_delete_url(version: Version) -> str:
    return (
        f'/api/dandisets/{version.dandiset.identifier}/'
        f'versions/{version.version}/assets/bulk-delete/'
    )


@pytest.fixture
def version_with_assets(draft_asset_factory):
    """Create a draft version owned by a new user, containing three assets under one folder."""
    user = UserFactory.create()
    version = DraftVersionFactory.create(dandiset__owners=[user])
    assets = [draft_asset_factory(path=f'foo/bar/{i}.nwb') for i in range(3)]
    for asset in assets:
        version.assets.add(asset)
        add_asset_paths(asset, version)

    return user, version, assets


@pytest.mark.django_db
def test_asset_rest_bulk_delete(api_client, version_with_assets):
    user, version, assets = version_with_assets
    api_client.force_authenticate(user=user)

    start_time = version.modified
    resp = api_client.post(
        bulk_delete_url(version),
        {'asset_ids': [str(asset.asset_id) for asset in assets]},
        format='json',
    )
    assert resp.status_code == 204

    # All assets are disassociated from the version, but not deleted
    assert version.assets.count() == 0
    for asset in assets:
        asset.refresh_from_db()

    # All paths, including the now-empty parent folders, are cleaned up
    assert not AssetPath.objects.filter(version=version).exists()

    # The version is marked for revalidation, and its modified date bumped
    version.refresh_from_db()
    assert version.status == Version.Status.PENDING
    assert version.modified > start_time

    # One audit record is written per removed asset
    records = AuditRecord.objects.filter(
        dandiset_id=version.dandiset.id, record_type='bulk_remove_assets'
    )
    assert records.count() == 3
    assert {r.details['asset_id'] for r in records} == {str(a.asset_id) for a in assets}


@pytest.mark.django_db
def test_asset_rest_bulk_delete_partial(api_client, version_with_assets):
    """Deleting a subset of assets must leave the remaining aggregates correct."""
    user, version, assets = version_with_assets
    api_client.force_authenticate(user=user)

    resp = api_client.post(
        bulk_delete_url(version),
        {'asset_ids': [str(assets[0].asset_id), str(assets[1].asset_id)]},
        format='json',
    )
    assert resp.status_code == 204

    assert list(version.assets.all()) == [assets[2]]

    # The remaining asset's ancestors should account for exactly that asset
    root = AssetPath.objects.get(version=version, path='foo')
    assert root.aggregate_files == 1
    assert root.aggregate_size == assets[2].size

    # The deleted assets' leaf paths are gone
    for asset in assets[:2]:
        assert not AssetPath.objects.filter(version=version, path=asset.path).exists()


@pytest.mark.django_db
def test_asset_rest_bulk_delete_duplicate_ids(api_client, version_with_assets):
    user, version, assets = version_with_assets
    api_client.force_authenticate(user=user)

    asset_id = str(assets[0].asset_id)
    resp = api_client.post(
        bulk_delete_url(version), {'asset_ids': [asset_id, asset_id]}, format='json'
    )
    assert resp.status_code == 204
    assert version.assets.count() == 2
    assert AuditRecord.objects.filter(record_type='bulk_remove_assets').count() == 1


@pytest.mark.django_db
def test_asset_rest_bulk_delete_nonexistent_asset(api_client, version_with_assets):
    user, version, assets = version_with_assets
    api_client.force_authenticate(user=user)

    missing_id = uuid4()
    resp = api_client.post(
        bulk_delete_url(version),
        {'asset_ids': [str(assets[0].asset_id), str(missing_id)]},
        format='json',
    )
    assert resp.status_code == 404
    assert str(missing_id) in resp.data

    # Nothing should have been removed
    assert version.assets.count() == 3


@pytest.mark.django_db
def test_asset_rest_bulk_delete_asset_of_other_version(
    api_client, version_with_assets, draft_asset_factory
):
    """An asset that exists, but belongs to another version, is rejected."""
    user, version, _ = version_with_assets
    api_client.force_authenticate(user=user)

    other_version = DraftVersionFactory.create(dandiset__owners=[user])
    other_asset = draft_asset_factory()
    other_version.assets.add(other_asset)

    resp = api_client.post(
        bulk_delete_url(version), {'asset_ids': [str(other_asset.asset_id)]}, format='json'
    )
    assert resp.status_code == 404
    assert other_asset in other_version.assets.all()


@pytest.mark.django_db
def test_asset_rest_bulk_delete_empty(api_client, version_with_assets):
    user, version, _ = version_with_assets
    api_client.force_authenticate(user=user)

    resp = api_client.post(bulk_delete_url(version), {'asset_ids': []}, format='json')
    assert resp.status_code == 400


@pytest.mark.django_db
def test_asset_rest_bulk_delete_not_an_owner(api_client, version_with_assets):
    _, version, assets = version_with_assets
    api_client.force_authenticate(user=UserFactory.create())

    resp = api_client.post(
        bulk_delete_url(version), {'asset_ids': [str(assets[0].asset_id)]}, format='json'
    )
    assert resp.status_code == 403
    assert version.assets.count() == 3


@pytest.mark.django_db
def test_asset_rest_bulk_delete_published_version(api_client, asset):
    user = UserFactory.create()
    published_version = PublishedVersionFactory.create(dandiset__owners=[user])
    published_version.assets.add(asset)
    api_client.force_authenticate(user=user)

    resp = api_client.post(
        bulk_delete_url(published_version), {'asset_ids': [str(asset.asset_id)]}, format='json'
    )
    assert resp.status_code == 405
    assert resp.data == 'Only draft versions can be modified.'


@pytest.mark.django_db
def test_asset_rest_bulk_delete_unembargo_in_progress(api_client, draft_asset_factory):
    user = UserFactory.create()
    version = DraftVersionFactory.create(
        dandiset__embargo_status=Dandiset.EmbargoStatus.UNEMBARGOING, dandiset__owners=[user]
    )
    asset = draft_asset_factory()
    version.assets.add(asset)
    api_client.force_authenticate(user=user)

    resp = api_client.post(
        bulk_delete_url(version), {'asset_ids': [str(asset.asset_id)]}, format='json'
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_asset_rest_bulk_delete_failure_rolls_back(api_client, version_with_assets, mocker):
    """A failure partway through must leave the version untouched."""
    user, version, assets = version_with_assets
    api_client.force_authenticate(user=user)

    mocker.patch(
        'dandiapi.api.services.asset.delete_asset_paths_many',
        side_effect=RuntimeError('something went wrong'),
    )

    with pytest.raises(RuntimeError, match='something went wrong'):
        api_client.post(
            bulk_delete_url(version),
            {'asset_ids': [str(asset.asset_id) for asset in assets]},
            format='json',
        )

    # No assets were removed, and their paths are intact
    assert version.assets.count() == 3
    assert AssetPath.objects.filter(version=version, asset__isnull=False).count() == 3
