from __future__ import annotations

from django.contrib.auth.models import User
import pytest

from dandiapi.api.models import UserMetadata


@pytest.mark.django_db()
def test_stats_baseline(api_client):
    assert api_client.get('/api/stats/').data == {
        'dandiset_count': 0,
        'published_dandiset_count': 0,
        'user_count': 0,
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
def test_stats_user(api_client, user_factory):
    User.objects.all().delete()

    # Create multiple users with different statuses
    approved_user_count = 0
    users_per_status = 3
    user_index = 0

    for status in UserMetadata.Status.choices:
        status_value = status[0]
        for _ in range(users_per_status):
            username = f'{status_value.lower()}_user_{user_index}'
            user = user_factory(username=username)
            UserMetadata.objects.create(user=user, status=status_value)
            if status_value == UserMetadata.Status.APPROVED:
                approved_user_count += 1
            user_index += 1

    stats = api_client.get('/api/stats/').data

    # Assert that the user count only includes users with APPROVED status
    assert stats['user_count'] == approved_user_count


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
