from __future__ import annotations

import dandischema.digests.dandietag
import pytest
from pytest_factoryboy import register
from rest_framework.test import APIClient

import dandiapi.api.models
from dandiapi.api.tests.factories import (
    AssetBlobFactory,
    DandisetFactory,
    DraftAssetFactory,
    DraftVersionFactory,
    EmbargoedAssetBlobFactory,
    EmbargoedUploadFactory,
    PublishedAssetFactory,
    PublishedVersionFactory,
    SocialAccountFactory,
    UploadFactory,
    UserFactory,
)
from dandiapi.zarr.tests.factories import (
    EmbargoedZarrArchiveFactory,
    ZarrArchiveFactory,
    ZarrFileFactory,
)

register(PublishedAssetFactory, _name='published_asset')
register(DraftAssetFactory, _name='draft_asset')
register(AssetBlobFactory)
register(EmbargoedAssetBlobFactory, _name='embargoed_asset_blob')
register(DandisetFactory)
register(EmbargoedUploadFactory)
register(PublishedVersionFactory, _name='published_version')
register(DraftVersionFactory, _name='draft_version')
# registering DraftVersionFactory after PublishedVersionFactory means
# the fixture `version` will always be a draft
register(UserFactory)
register(SocialAccountFactory)
register(UploadFactory)

# zarr app
register(ZarrArchiveFactory)
register(EmbargoedZarrArchiveFactory, _name='embargoed_zarr_archive')
register(ZarrFileFactory, name='zarr_file')


@pytest.fixture(autouse=True)
def _mock_etag_regex(mocker):
    """Expect uploads in every test to set an MD5-style ETag, not a multi-part upload ETag."""
    md5_pattern = r'^[a-f0-9]{32}$'
    mocker.patch.object(dandiapi.api.models.Upload, 'ETAG_REGEX', md5_pattern)
    mocker.patch.object(dandiapi.api.models.AssetBlob, 'ETAG_REGEX', md5_pattern)
    mocker.patch.object(dandischema.digests.dandietag.DandiETag, 'REGEX', md5_pattern)


@pytest.fixture
def user(user_factory):
    """Override the default `user` fixture to use our `UserFactory` so `UserMetadata` works."""
    return user_factory()


@pytest.fixture(params=[DraftAssetFactory, PublishedAssetFactory], ids=['draft', 'published'])
def asset_factory(request):
    return request.param


@pytest.fixture
def asset(asset_factory):
    return asset_factory()


@pytest.fixture(params=[DraftVersionFactory, PublishedVersionFactory], ids=['draft', 'published'])
def version(request):
    return request.param()


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def authenticated_api_client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client
