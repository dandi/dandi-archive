from __future__ import annotations

import pytest


@pytest.mark.django_db()
def test_stats_baseline(api_client):
    assert api_client.get('/api/stats/').data == {
        'dandiset_count': 0,
        'published_dandiset_count': 0,
        # django-guardian automatically creates an AnonymousUser
        'user_count': 1,
        'size': 0,
    }


@pytest.mark.django_db()
def test_stats_draft(api_client, dandiset):
    stats = api_client.get('/api/stats/').data

    assert stats['dandiset_count'] == 1
    assert stats['published_dandiset_count'] == 0


@pytest.mark.django_db()
def test_stats_published(api_client, published_version_factory):
    published_version_factory()
    stats = api_client.get('/api/stats/').data

    assert stats['dandiset_count'] == 1
    assert stats['published_dandiset_count'] == 1


@pytest.mark.django_db()
def test_stats_user(api_client, user):
    stats = api_client.get('/api/stats/').data

    # django-guardian automatically creates an AnonymousUser
    assert stats['user_count'] == 2


@pytest.mark.django_db()
def test_stats_asset(api_client, version, asset):
    version.assets.add(asset)
    stats = api_client.get('/api/stats/').data

    assert stats['size'] == asset.size


@pytest.mark.django_db()
def test_stats_embargoed_asset(api_client, version, asset_factory, embargoed_asset_blob_factory):
    embargoed_asset = asset_factory()
    embargoed_asset.blob = embargoed_asset_blob_factory()
    version.assets.add(embargoed_asset)

    stats = api_client.get('/api/stats/').data
    assert stats['size'] == embargoed_asset.size


@pytest.mark.django_db()
def test_stats_embargoed_and_regular_blobs(
    api_client, version, asset_factory, asset_blob_factory, embargoed_asset_blob_factory
):
    asset = asset_factory()
    asset.blob = asset_blob_factory()
    version.assets.add(asset)

    embargoed_asset = asset_factory()
    embargoed_asset.blob = embargoed_asset_blob_factory()
    version.assets.add(embargoed_asset)

    stats = api_client.get('/api/stats/').data
    assert stats['size'] == asset.size + embargoed_asset.size
