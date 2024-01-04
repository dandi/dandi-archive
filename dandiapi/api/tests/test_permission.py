import pytest
from rest_framework.permissions import SAFE_METHODS


@pytest.mark.parametrize(
    ('method', 'url_format'),
    [
        # Dandisets
        ('get', '/api/dandisets/'),  # FAILING
        ('post', '/api/dandisets/'),
        ('get', '/api/dandisets/{dandiset.identifier}/'),  # FAILING
        ('delete', '/api/dandisets/{dandiset.identifier}/'),
        ('post', '/api/dandisets/{dandiset.identifier}/unembargo/'),
        ('get', '/api/dandisets/{dandiset.identifier}/users/'),  # FAILING
        ('put', '/api/dandisets/{dandiset.identifier}/users/'),
        # Versions
        ('get', '/api/dandisets/{dandiset.identifier}/versions/'),
        ('get', '/api/dandisets/{dandiset.identifier}/versions/draft/'),
        ('put', '/api/dandisets/{dandiset.identifier}/versions/draft/'),
        ('delete', '/api/dandisets/{dandiset.identifier}/versions/draft/'),
        ('get', '/api/dandisets/{dandiset.identifier}/versions/draft/info/'),
        ('post', '/api/dandisets/{dandiset.identifier}/versions/draft/publish/'),
        # Assets
        ('get', '/api/assets/{asset.asset_id}/'),
        ('get', '/api/assets/{asset.asset_id}/download/'),
        ('get', '/api/assets/{asset.asset_id}/info/'),
        ('get', '/api/dandisets/{dandiset.identifier}/versions/draft/assets/'),
        ('post', '/api/dandisets/{dandiset.identifier}/versions/draft/assets/'),
        ('get', '/api/dandisets/{dandiset.identifier}/versions/draft/assets/paths/'),
        (
            'get',
            '/api/dandisets/{dandiset.identifier}/versions/draft/assets/{asset.asset_id}/',
        ),
        (
            'put',
            '/api/dandisets/{dandiset.identifier}/versions/draft/assets/{asset.asset_id}/',
        ),
        (
            'delete',
            '/api/dandisets/{dandiset.identifier}/versions/draft/assets/{asset.asset_id}/',
        ),
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
        # Zarrs
        ('get', '/api/zarr/'),
        ('post', '/api/zarr/'),
        ('get', '/api/zarr/{zarr.zarr_id}/'),
        ('delete', '/api/zarr/{zarr.zarr_id}/files/'),
        ('post', '/api/zarr/{zarr.zarr_id}/files/'),
    ],
)
@pytest.mark.django_db()
def test_approved_or_readonly(
    api_client,
    user,
    dandiset_factory,
    draft_version_factory,
    draft_asset_factory,
    zarr_archive_factory,
    method,
    url_format,
):
    dandiset = dandiset_factory()
    version = draft_version_factory(dandiset=dandiset)
    zarr = zarr_archive_factory(dandiset=dandiset)
    asset = draft_asset_factory()
    version.assets.add(asset)

    url = url_format.format(dandiset=dandiset, asset=asset, zarr=zarr)
    response = getattr(api_client, method)(url)

    # The client is not authenticated, so all response codes should be 401
    assert response.status_code == 401

    api_client.force_authenticate(user=user)

    # Zarr create is a special case, as permission can only be
    # denied after reading the request body
    if url == '/api/zarr/' and method == 'post':
        response = getattr(api_client, method)(
            url,
            data={'name': 'test', 'dandiset': dandiset.identifier},
            format='json',
        )
        assert response.status_code == 403
    else:
        response = getattr(api_client, method)(url)

        if method.upper() in SAFE_METHODS:
            assert response.status_code < 400
            return

        # Would occur due to ReadOnlyModelViewSet
        assert response.status_code >= 400
