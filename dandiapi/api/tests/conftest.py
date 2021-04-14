from typing import TYPE_CHECKING

from botocore.exceptions import ClientError
from django.conf import settings
from django.core.files.storage import Storage
from minio import Minio
from minio_storage.storage import MinioStorage
import pytest
from pytest_factoryboy import register
from rest_framework.test import APIClient
from storages.backends.s3boto3 import S3Boto3Storage

from .factories import (
    AssetBlobFactory,
    AssetFactory,
    AssetMetadataFactory,
    DandisetFactory,
    DraftVersionFactory,
    PublishedVersionFactory,
    SocialAccountFactory,
    UploadFactory,
    UserFactory,
    VersionMetadataFactory,
)

if TYPE_CHECKING:
    # mypy_boto3_s3 only provides types
    import mypy_boto3_s3 as s3


register(AssetFactory)
register(AssetBlobFactory)
register(AssetMetadataFactory)
register(DandisetFactory)
register(PublishedVersionFactory, _name='published_version')
register(DraftVersionFactory, _name='draft_version')
# registering DraftVersionFactory after PublishedVersionFactory means
# the fixture `version` will always be a draft
register(UserFactory)
register(SocialAccountFactory)
register(UploadFactory)
register(VersionMetadataFactory)


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


# storage fixtures are copied from django-s3-file-field test fixtures


def s3boto3_storage_factory() -> 'S3Boto3Storage':
    storage = S3Boto3Storage(
        access_key=settings.MINIO_STORAGE_ACCESS_KEY,
        secret_key=settings.MINIO_STORAGE_SECRET_KEY,
        region_name='test-region',
        bucket_name=settings.DANDI_DANDISETS_BUCKET_NAME,
        # For testing, connect to a local Minio instance
        endpoint_url=(
            f'{"https" if settings.MINIO_STORAGE_USE_HTTPS else "http"}:'
            f'//{settings.MINIO_STORAGE_ENDPOINT}'
        ),
    )

    resource: s3.ServiceResource = storage.connection
    client: s3.Client = resource.meta.client
    try:
        client.head_bucket(Bucket=settings.MINIO_STORAGE_MEDIA_BUCKET_NAME)
    except ClientError:
        client.create_bucket(Bucket=settings.MINIO_STORAGE_MEDIA_BUCKET_NAME)

    return storage


def minio_storage_factory() -> MinioStorage:
    return MinioStorage(
        minio_client=Minio(
            endpoint=settings.MINIO_STORAGE_ENDPOINT,
            secure=settings.MINIO_STORAGE_USE_HTTPS,
            access_key=settings.MINIO_STORAGE_ACCESS_KEY,
            secret_key=settings.MINIO_STORAGE_SECRET_KEY,
            # Don't use s3_connection_params.region, let Minio set its own value internally
        ),
        bucket_name=settings.DANDI_DANDISETS_BUCKET_NAME,
        auto_create_bucket=True,
        presign_urls=True,
        base_url=settings.MINIO_STORAGE_MEDIA_URL,
        # TODO: Test the case of an alternate base_url
        # base_url='http://minio:9000/bucket-name'
    )


@pytest.fixture
def s3boto3_storage() -> 'S3Boto3Storage':
    return s3boto3_storage_factory()


@pytest.fixture
def minio_storage() -> MinioStorage:
    return minio_storage_factory()


@pytest.fixture(params=[s3boto3_storage_factory, minio_storage_factory], ids=['s3boto3', 'minio'])
def storage(request) -> Storage:
    storage_factory = request.param
    return storage_factory()
