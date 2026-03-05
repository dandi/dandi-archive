"""Tests for the modified field reflecting version content changes."""

from __future__ import annotations

import datetime

from django.utils import timezone
import pytest

from dandiapi.api.asset_paths import add_asset_paths
from dandiapi.api.models import Dandiset, Version
from dandiapi.api.tests.factories import (
    DraftAssetFactory,
    DraftVersionFactory,
    UserFactory,
)


@pytest.mark.django_db
def test_list_modified_reflects_version_modified(api_client):
    """The listing endpoint's modified field should reflect the version's modified, not the
    dandiset's."""
    draft_version = DraftVersionFactory.create()
    dandiset = draft_version.dandiset

    # Set the dandiset's own modified to something old
    old_time = timezone.now() - datetime.timedelta(days=365)
    Dandiset.objects.filter(id=dandiset.id).update(modified=old_time)

    response = api_client.get(
        '/api/dandisets/', {'draft': 'true', 'empty': 'true'}
    )
    assert response.status_code == 200
    result = response.data['results'][0]

    # The API modified should match the version's modified, not the dandiset's stale one
    dandiset.refresh_from_db()
    draft_version.refresh_from_db()
    assert result['modified'] != dandiset.modified.isoformat().replace('+00:00', 'Z')
    assert result['modified'] == draft_version.modified.isoformat().replace('+00:00', 'Z')


@pytest.mark.django_db
def test_retrieve_modified_reflects_version_modified(api_client):
    """The retrieve endpoint's modified field should reflect the version's modified."""
    draft_version = DraftVersionFactory.create()
    dandiset = draft_version.dandiset

    old_time = timezone.now() - datetime.timedelta(days=365)
    Dandiset.objects.filter(id=dandiset.id).update(modified=old_time)

    response = api_client.get(f'/api/dandisets/{dandiset.identifier}/')
    assert response.status_code == 200

    draft_version.refresh_from_db()
    assert response.data['modified'] == draft_version.modified.isoformat().replace('+00:00', 'Z')


@pytest.mark.django_db
def test_modified_updates_on_metadata_edit(api_client):
    """The version modified timestamp should update when metadata is edited via the API."""
    user = UserFactory.create()
    draft_version = DraftVersionFactory.create(dandiset__owners=[user])
    dandiset = draft_version.dandiset
    api_client.force_authenticate(user=user)

    original_modified = draft_version.modified

    api_client.put(
        f'/api/dandisets/{dandiset.identifier}/versions/{draft_version.version}/',
        {'metadata': {'foo': 'bar'}, 'name': 'Updated Name'},
        format='json',
    )

    draft_version.refresh_from_db()
    assert draft_version.modified > original_modified


@pytest.mark.django_db
def test_modified_updates_on_asset_add(api_client, asset_blob):
    """The version modified timestamp should update when an asset is added."""
    user = UserFactory.create()
    draft_version = DraftVersionFactory.create(dandiset__owners=[user])
    dandiset = draft_version.dandiset
    api_client.force_authenticate(user=user)

    original_modified = draft_version.modified

    api_client.post(
        f'/api/dandisets/{dandiset.identifier}/versions/{draft_version.version}/assets/',
        {
            'metadata': {
                'encodingFormat': 'application/x-nwb',
                'path': 'test/asset.nwb',
            },
            'blob_id': asset_blob.blob_id,
        },
        format='json',
    )

    draft_version.refresh_from_db()
    assert draft_version.modified > original_modified


@pytest.mark.django_db
def test_modified_updates_on_asset_remove(api_client):
    """The version modified timestamp should update when an asset is removed."""
    user = UserFactory.create()
    draft_version = DraftVersionFactory.create(dandiset__owners=[user])
    dandiset = draft_version.dandiset
    asset = DraftAssetFactory.create()
    draft_version.assets.add(asset)
    add_asset_paths(asset, draft_version)
    api_client.force_authenticate(user=user)

    draft_version.refresh_from_db()
    original_modified = draft_version.modified

    api_client.delete(
        f'/api/dandisets/{dandiset.identifier}'
        f'/versions/{draft_version.version}/assets/{asset.asset_id}/',
    )

    draft_version.refresh_from_db()
    assert draft_version.modified > original_modified


@pytest.mark.django_db
def test_ordering_by_modified(api_client):
    """Ordering by modified should sort by version modified timestamps."""
    now = timezone.now()

    # Create 3 dandisets with draft versions
    v1 = DraftVersionFactory.create()
    v2 = DraftVersionFactory.create()
    v3 = DraftVersionFactory.create()

    # Set different version modified times
    Version.objects.filter(id=v1.id).update(
        modified=now - datetime.timedelta(days=3)
    )
    Version.objects.filter(id=v2.id).update(
        modified=now - datetime.timedelta(days=1)
    )
    Version.objects.filter(id=v3.id).update(
        modified=now - datetime.timedelta(days=2)
    )

    # Ascending
    response = api_client.get(
        '/api/dandisets/', {'ordering': 'modified', 'draft': 'true', 'empty': 'true'}
    )
    assert response.status_code == 200
    ids = [r['identifier'] for r in response.data['results']]
    assert ids == [
        v1.dandiset.identifier,
        v3.dandiset.identifier,
        v2.dandiset.identifier,
    ]

    # Descending
    response = api_client.get(
        '/api/dandisets/', {'ordering': '-modified', 'draft': 'true', 'empty': 'true'}
    )
    assert response.status_code == 200
    ids = [r['identifier'] for r in response.data['results']]
    assert ids == [
        v2.dandiset.identifier,
        v3.dandiset.identifier,
        v1.dandiset.identifier,
    ]


@pytest.mark.django_db
def test_date_modified_populated_in_version_metadata():
    """dateModified should be populated in the version metadata JSON."""
    draft_version = DraftVersionFactory.create()

    # After save, metadata should contain dateModified
    assert 'dateModified' in draft_version.metadata
    assert draft_version.metadata['dateModified'] is not None
