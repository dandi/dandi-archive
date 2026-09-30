from __future__ import annotations

import pytest

from dandiapi.api.models import Asset


@pytest.mark.django_db
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


@pytest.mark.ai_generated
@pytest.mark.django_db
@pytest.mark.parametrize('params', [{'order': 'created'}, {}], ids=['order=created', 'default'])
def test_asset_pagination_ties_on_created(api_client, version, asset_factory, params):
    """Assets sharing a `created` timestamp are each listed exactly once across pages."""
    endpoint = f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/assets/'
    assets = [asset_factory() for _ in range(10)]
    for asset in assets:
        version.assets.add(asset)

    # Give every asset the same `created`.  Updating in reverse order also rewrites the rows
    # in reverse, so that without a tiebreaker their physical order no longer follows `id`.
    created = assets[0].created
    for asset in reversed(assets):
        Asset.objects.filter(id=asset.id).update(created=created)

    listed = []
    page = 1
    while True:
        resp = api_client.get(endpoint, {**params, 'page_size': 1, 'page': page}).json()
        listed += [r['asset_id'] for r in resp['results']]
        if resp['next'] is None:
            break
        page += 1

    expected = [str(a.asset_id) for a in sorted(assets, key=lambda a: a.id)]
    # Every asset exactly once: no repeats, no skips at page boundaries
    assert sorted(listed) == sorted(expected)
    # ... because ties are broken by `id`
    assert listed == expected
