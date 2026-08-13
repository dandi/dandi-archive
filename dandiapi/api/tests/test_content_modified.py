"""Tests for the content_modified field reflecting version content changes."""

from __future__ import annotations

import datetime

from django.utils import timezone
import pytest

from dandiapi.api.models import Dandiset, Version
from dandiapi.api.tests.factories import (
    DraftVersionFactory,
)


@pytest.mark.django_db
def test_list_content_modified_reflects_version_modified(api_client):
    """The listing endpoint's content_modified field should reflect the version's modified."""
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

    draft_version.refresh_from_db()
    assert result['content_modified'] == draft_version.modified.isoformat().replace(
        '+00:00', 'Z'
    )


@pytest.mark.django_db
def test_retrieve_content_modified_reflects_version_modified(api_client):
    """The retrieve endpoint's content_modified field should reflect the version's modified."""
    draft_version = DraftVersionFactory.create()
    dandiset = draft_version.dandiset

    old_time = timezone.now() - datetime.timedelta(days=365)
    Dandiset.objects.filter(id=dandiset.id).update(modified=old_time)

    response = api_client.get(f'/api/dandisets/{dandiset.identifier}/')
    assert response.status_code == 200

    draft_version.refresh_from_db()
    assert response.data['content_modified'] == draft_version.modified.isoformat().replace(
        '+00:00', 'Z'
    )


@pytest.mark.django_db
def test_ordering_by_content_modified(api_client):
    """Ordering by content_modified should sort by version modified timestamps."""
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
        '/api/dandisets/',
        {'ordering': 'content_modified', 'draft': 'true', 'empty': 'true'},
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
        '/api/dandisets/',
        {'ordering': '-content_modified', 'draft': 'true', 'empty': 'true'},
    )
    assert response.status_code == 200
    ids = [r['identifier'] for r in response.data['results']]
    assert ids == [
        v2.dandiset.identifier,
        v3.dandiset.identifier,
        v1.dandiset.identifier,
    ]
