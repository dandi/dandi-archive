from __future__ import annotations

from django.conf import settings
import pytest

from dandiapi.api.models import UserMetadata
from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.services.asset import add_asset_to_version
from dandiapi.api.services.permissions.dandiset import add_dandiset_owner


@pytest.mark.django_db
def test_stats_baseline(api_client):
    assert api_client.get('/api/stats/').data == {
        'dandiset_count': 0,
        'published_dandiset_count': 0,
        'user_count': 0,
        'size': 0,
    }


@pytest.mark.django_db
def test_stats_draft(api_client, dandiset):
    stats = api_client.get('/api/stats/').data

    assert stats['dandiset_count'] == 1
    assert stats['published_dandiset_count'] == 0


@pytest.mark.django_db
def test_stats_published(api_client, published_version_factory):
    published_version_factory()
    stats = api_client.get('/api/stats/').data

    assert stats['dandiset_count'] == 1
    assert stats['published_dandiset_count'] == 1


@pytest.mark.django_db
def test_stats_user(api_client, user_factory):
    # Create multiple users with different statuses
    users_per_status = approved_user_count = 3

    for status in UserMetadata.Status.choices:
        [user_factory(metadata__status=status[0]) for _ in range(users_per_status)]

    stats = api_client.get('/api/stats/').data

    # Assert that the user count only includes users with APPROVED status
    assert stats['user_count'] == approved_user_count


@pytest.mark.django_db
def test_stats_asset(api_client, draft_version, user, asset_blob_factory):
    add_dandiset_owner(dandiset=draft_version.dandiset, user=user)
    asset = add_asset_to_version(
        user=user,
        version=draft_version,
        asset_blob=asset_blob_factory(),
        metadata={
            'path': 'foo/bar.txt',
            'schemaVersion': settings.DANDI_SCHEMA_VERSION,
        },
    )
    stats = api_client.get('/api/stats/').data

    assert stats['size'] == asset.size


@pytest.mark.django_db
def test_stats_embargoed_asset(
    api_client, dandiset_factory, draft_version_factory, user, embargoed_asset_blob_factory
):
    embargoed_dandiset = dandiset_factory(embargo_status=Dandiset.EmbargoStatus.EMBARGOED)
    draft_version = draft_version_factory(dandiset=embargoed_dandiset)

    add_dandiset_owner(dandiset=draft_version.dandiset, user=user)
    embargoed_asset = add_asset_to_version(
        user=user,
        version=draft_version,
        asset_blob=embargoed_asset_blob_factory(),
        metadata={
            'path': 'foo/bar.txt',
            'schemaVersion': settings.DANDI_SCHEMA_VERSION,
        },
    )

    stats = api_client.get('/api/stats/').data
    assert stats['size'] == embargoed_asset.size
