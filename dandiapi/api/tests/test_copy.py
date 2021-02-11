from typing import TYPE_CHECKING

from botocore.exceptions import ClientError
from django.conf import settings
import pytest
from storages.backends.s3boto3 import S3Boto3Storage

from dandiapi.api.copy import _copy_object_s3, copy_object

if TYPE_CHECKING:
    # mypy_boto3_s3 only provides types
    import mypy_boto3_s3 as s3


def s3boto3_storage_factory() -> 'S3Boto3Storage':
    storage = S3Boto3Storage(
        access_key=settings.MINIO_STORAGE_ACCESS_KEY,
        secret_key=settings.MINIO_STORAGE_SECRET_KEY,
        region_name='test-region',
        bucket_name=settings.MINIO_STORAGE_MEDIA_BUCKET_NAME,
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


@pytest.mark.django_db
def test_copy_minio(validation):
    destination = 'blobs/test'

    # Delete the blob if it is already present in the test storage
    validation.blob.field.storage.delete(destination)
    assert not validation.blob.field.storage.exists(destination)

    copy_object(validation, destination)

    # Verify object was copied
    assert validation.blob.field.storage.exists(destination)

    # Verify original object was deleted
    assert not validation.blob.field.storage.exists(validation.blob.name)


@pytest.mark.django_db
def test_copy_s3(validation):
    destination = 'blobs/test'

    # Delete the blob if it is already present in the test storage
    validation.blob.field.storage.delete(destination)
    assert not validation.blob.field.storage.exists(destination)

    # Rather than setting up an actual S3 storage, we just create an artificial S3Boto3Storage
    # which is backed by the minio storage.
    storage = s3boto3_storage_factory()
    source_bucket = validation.blob.field.storage.bucket_name
    # TODO: we may eventually want different buckets
    dest_bucket = source_bucket
    source_key = validation.blob.name

    # Call the S3 copy method directly, as copy_object() would check the storage on the field and
    # use _copy_object_minio instead.
    _copy_object_s3(storage, source_bucket, source_key, dest_bucket, destination)

    # Verify object was copied
    assert validation.blob.field.storage.exists(destination)

    # Verify original object was deleted
    assert not validation.blob.field.storage.exists(validation.blob.name)
