from __future__ import annotations
import pytest

from dandiapi.api.models import Dandiset


@pytest.fixture(
    params=[
        Dandiset.EmbargoStatus.EMBARGOED,
        Dandiset.EmbargoStatus.UNEMBARGOING,
    ]
)
def embargo_status(request):
    return request.param


EMPTY_PAGINATION = {
    'count': 0,
    'next': None,
    'previous': None,
    'results': [],
}


@pytest.mark.parametrize(
    ('method', 'url_format'),
    [
        ('get', '/api/dandisets/{dandiset.identifier}/'),
        ('delete', '/api/dandisets/{dandiset.identifier}/'),
        ('post', '/api/dandisets/{dandiset.identifier}/unembargo/'),
        ('get', '/api/dandisets/{dandiset.identifier}/users/'),
        ('put', '/api/dandisets/{dandiset.identifier}/users/'),
        ('get', '/api/dandisets/{dandiset.identifier}/versions/'),
        ('get', '/api/dandisets/{dandiset.identifier}/versions/draft/'),
        ('put', '/api/dandisets/{dandiset.identifier}/versions/draft/'),
        ('delete', '/api/dandisets/{dandiset.identifier}/versions/draft/'),
        ('get', '/api/dandisets/{dandiset.identifier}/versions/draft/info/'),
        ('post', '/api/dandisets/{dandiset.identifier}/versions/draft/publish/'),
        ('get', '/api/dandisets/{dandiset.identifier}/versions/draft/assets/'),
        ('post', '/api/dandisets/{dandiset.identifier}/versions/draft/assets/'),
        ('get', '/api/dandisets/{dandiset.identifier}/versions/draft/assets/paths/'),
        ('get', '/api/dandisets/{dandiset.identifier}/versions/draft/assets/{asset.asset_id}/'),
        ('put', '/api/dandisets/{dandiset.identifier}/versions/draft/assets/{asset.asset_id}/'),
        ('delete', '/api/dandisets/{dandiset.identifier}/versions/draft/assets/{asset.asset_id}/'),
        ('get', '/api/assets/{asset.asset_id}/'),
        ('get', '/api/assets/{asset.asset_id}/download/'),
        ('get', '/api/assets/{asset.asset_id}/info/'),
        (
            'get',
            '/api/dandisets/{dandiset.identifier}/versions/draft/assets/{asset.asset_id}/download/',
        ),
        (
            'get',
            '/api/dandisets/{dandiset.identifier}/versions/draft/assets/{asset.asset_id}/info/',
        ),
        (
            'get',
            '/api/dandisets/{dandiset.identifier}/versions/draft/assets/{asset.asset_id}/validation/',  # noqa: E501
        ),
    ],
)
@pytest.mark.django_db()
def test_embargo_visibility(
    api_client,
    user,
    dandiset_factory,
    draft_version_factory,
    draft_asset_factory,
    embargoed_asset_blob,
    embargo_status,
    method,
    url_format,
):
    dandiset = dandiset_factory(embargo_status=embargo_status)
    version = draft_version_factory(dandiset=dandiset)
    asset = draft_asset_factory(blob=None, embargoed_blob=embargoed_asset_blob)
    version.assets.add(asset)

    url = url_format.format(dandiset=dandiset, asset=asset)
    response = getattr(api_client, method)(url)
    # The client is not authenticated, so all response codes should be 401
    assert response.status_code == 401

    api_client.force_authenticate(user=user)
    response = getattr(api_client, method)(url)
    # The client is now authenticated but not an owner, so all response codes should be 403
    assert response.status_code == 403
