from __future__ import annotations
import pytest
from rest_framework.permissions import SAFE_METHODS


@pytest.mark.parametrize(
    ('method', 'url_format', 'owner_required'),
    [
        # Dandisets
        ('get', '/api/dandisets/', False),
        ('post', '/api/dandisets/', False),
        ('get', '/api/dandisets/{dandiset.identifier}/', False),
        ('delete', '/api/dandisets/{dandiset.identifier}/', True),
        ('post', '/api/dandisets/{dandiset.identifier}/unembargo/', True),
        ('get', '/api/dandisets/{dandiset.identifier}/users/', False),
        ('put', '/api/dandisets/{dandiset.identifier}/users/', False),
        # Versions
        ('get', '/api/dandisets/{dandiset.identifier}/versions/', False),
        ('get', '/api/dandisets/{dandiset.identifier}/versions/draft/', False),
        ('put', '/api/dandisets/{dandiset.identifier}/versions/draft/', True),
        ('delete', '/api/dandisets/{dandiset.identifier}/versions/draft/', True),
        ('get', '/api/dandisets/{dandiset.identifier}/versions/draft/info/', False),
        ('post', '/api/dandisets/{dandiset.identifier}/versions/draft/publish/', True),
        # Assets
        ('get', '/api/assets/{asset.asset_id}/', False),
        ('get', '/api/assets/{asset.asset_id}/download/', False),
        ('get', '/api/assets/{asset.asset_id}/info/', False),
        ('get', '/api/dandisets/{dandiset.identifier}/versions/draft/assets/', False),
        ('post', '/api/dandisets/{dandiset.identifier}/versions/draft/assets/', True),
        ('get', '/api/dandisets/{dandiset.identifier}/versions/draft/assets/paths/', False),
        (
            'get',
            '/api/dandisets/{dandiset.identifier}/versions/draft/assets/{asset.asset_id}/',
            False,
        ),
        (
            'put',
            '/api/dandisets/{dandiset.identifier}/versions/draft/assets/{asset.asset_id}/',
            True,
        ),
        (
            'delete',
            '/api/dandisets/{dandiset.identifier}/versions/draft/assets/{asset.asset_id}/',
            True,
        ),
        (
            'get',
            '/api/dandisets/{dandiset.identifier}/versions/draft/assets/{asset.asset_id}/download/',
            False,
        ),
        (
            'get',
            '/api/dandisets/{dandiset.identifier}/versions/draft/assets/{asset.asset_id}/info/',
            False,
        ),
        (
            'get',
            '/api/dandisets/{dandiset.identifier}/versions/draft/assets/{asset.asset_id}/validation/',  # noqa: E501
            False,
        ),
        # Zarrs
        ('get', '/api/zarr/', False),
        ('post', '/api/zarr/', True),
        ('get', '/api/zarr/{zarr.zarr_id}/', False),
        ('delete', '/api/zarr/{zarr.zarr_id}/files/', True),
        ('post', '/api/zarr/{zarr.zarr_id}/files/', True),
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
    owner_required,
):
    dandiset = dandiset_factory()
    version = draft_version_factory(dandiset=dandiset)
    zarr = zarr_archive_factory(dandiset=dandiset)
    asset = draft_asset_factory()
    version.assets.add(asset)

    url = url_format.format(dandiset=dandiset, asset=asset, zarr=zarr)
    response = getattr(api_client, method)(url)

    # Safe method, read only is okay
    if method.upper() in SAFE_METHODS:
        assert response.status_code < 400
        return

    # The client is not authenticated, so all response codes should be 401
    assert response.status_code == 401

    # Owner not required, so further requests will succeed
    if not owner_required:
        return

    api_client.force_authenticate(user=user)

    # Zarr create is a special case, as permission can only be
    # denied after reading the request body
    if url == '/api/zarr/' and method == 'post':
        response = getattr(api_client, method)(
            url,
            data={'name': 'test', 'dandiset': dandiset.identifier},
            format='json',
        )
    else:
        response = getattr(api_client, method)(url)

    # The client is now authenticated but not an owner, so all response codes should be 403
    assert response.status_code == 403
