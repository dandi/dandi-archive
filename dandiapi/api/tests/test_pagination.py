from __future__ import annotations

import pytest


@pytest.mark.django_db()
def test_asset_pagination(api_client, version, asset_factory):
    endpoint = f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/assets/'

    # Create assets and set their created time artificially apart
    for _ in range(10):
        version.assets.add(asset_factory())

    resp = api_client.get(endpoint, {'order': 'created', 'page_size': 5}).json()
    assert resp['count'] == 10
    assert resp['next'] is not None
    page_one = resp['results']
    assert len(page_one) == 5

    # Second page
    resp = api_client.get(endpoint, {'order': 'created', 'page_size': 5, 'page': 2}).json()
    assert resp['count'] is None
    assert resp['next'] is None
    page_two = resp['results']
    assert len(page_two) == 5

    # Full page
    resp = api_client.get(endpoint, {'order': 'created', 'page_size': 100}).json()
    assert resp['count'] is not None
    assert resp['next'] is None
    full_page = resp['results']
    assert len(full_page) == 10

    # Assert full list is ordered the same as both paginated lists
    assert full_page == page_one + page_two
