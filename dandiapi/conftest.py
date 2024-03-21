from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.core.files.storage import Storage
from minio_storage.storage import MinioStorage
import pytest
from pytest_factoryboy import register
from rest_framework.test import APIClient

from dandiapi.api.storage import create_s3_storage
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
from dandiapi.zarr.tests.factories import ZarrArchiveFactory
from dandiapi.zarr.tests.utils import upload_zarr_file

if TYPE_CHECKING:
    from django.core.files.storage import Storage
    from minio_storage.storage import MinioStorage
    from storages.backends.s3 import S3Storage

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


# Register zarr file/directory factories
@pytest.fixture()
def zarr_file_factory():
    return upload_zarr_file


@pytest.fixture()
def user(user_factory):
    """Override the default `user` fixture to use our `UserFactory` so `UserMetadata` works."""
    return user_factory()


@pytest.fixture(params=[DraftAssetFactory, PublishedAssetFactory], ids=['draft', 'published'])
def asset_factory(request):
    return request.param


@pytest.fixture()
def asset(asset_factory):
    return asset_factory()


@pytest.fixture(params=[DraftVersionFactory, PublishedVersionFactory], ids=['draft', 'published'])
def version(request):
    return request.param()


@pytest.fixture()
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture()
def authenticated_api_client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


# storage fixtures are copied from django-s3-file-field test fixtures


def base_s3_storage_factory(bucket_name: str) -> S3Storage:
    return create_s3_storage(bucket_name)


def s3_storage_factory():
    return base_s3_storage_factory(settings.DANDI_DANDISETS_BUCKET_NAME)


def base_minio_storage_factory(bucket_name: str) -> MinioStorage:
    return create_s3_storage(bucket_name)


def minio_storage_factory() -> MinioStorage:
    return base_minio_storage_factory(settings.DANDI_DANDISETS_BUCKET_NAME)


@pytest.fixture()
def s3_storage() -> S3Storage:
    return s3_storage_factory()


@pytest.fixture()
def minio_storage() -> MinioStorage:
    return minio_storage_factory()


@pytest.fixture(params=[s3_storage_factory, minio_storage_factory], ids=['s3', 'minio'])
def storage(request, settings) -> Storage:
    storage_factory = request.param
    if storage_factory == s3_storage_factory:
        settings.DEFAULT_FILE_STORAGE = 'storages.backends.s3.S3Storage'
        settings.AWS_S3_ACCESS_KEY_ID = settings.MINIO_STORAGE_ACCESS_KEY
        settings.AWS_S3_SECRET_ACCESS_KEY = settings.MINIO_STORAGE_SECRET_KEY
        settings.AWS_S3_REGION_NAME = 'test-region'
        settings.AWS_S3_ENDPOINT_URL = (
            f'{"https" if settings.MINIO_STORAGE_USE_HTTPS else "http"}:'
            f'//{settings.MINIO_STORAGE_ENDPOINT}'
        )
    else:
        # fake-bucket-name is unused, this setting is just parsed for the base url
        # components in create_s3_storage. TODO: refactor storage construction in the future.
        settings.MINIO_STORAGE_MEDIA_URL = (
            f'{"https" if settings.MINIO_STORAGE_USE_HTTPS else "http"}:'
            f'//{settings.MINIO_STORAGE_ENDPOINT}'
            f'/fake-bucket-name'
        )

    return storage_factory()
