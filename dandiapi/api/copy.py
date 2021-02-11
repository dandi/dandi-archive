from dandiapi.api.models.validation import Validation

try:
    from storages.backends.s3boto3 import S3Boto3Storage
except ImportError:
    # This should only be used for type interrogation, never instantiation
    S3Boto3Storage = type('FakeS3Boto3Storage', (), {})
try:
    from minio_storage.storage import MinioStorage
except ImportError:
    # This should only be used for type interrogation, never instantiation
    MinioStorage = type('FakeMinioStorage', (), {})


def copy_object(validation: Validation, dest_key: str):
    storage = Validation.blob.field.storage
    source_bucket = storage.bucket_name
    # TODO: we may eventually want different buckets
    dest_bucket = source_bucket
    source_key = validation.blob.name

    if isinstance(Validation.blob.field.storage, S3Boto3Storage):
        _copy_object_s3(storage, source_bucket, source_key, dest_bucket, dest_key)
    elif isinstance(Validation.blob.field.storage, MinioStorage):
        _copy_object_minio(storage, source_bucket, source_key, dest_bucket, dest_key)
    else:
        raise ValueError(f'Unknown Validation storage {Validation.blob.field.storage}')


def _copy_object_s3(
    storage,
    source_bucket: str,
    source_key: str,
    dest_bucket: str,
    dest_key: str,
):
    # TODO This copy maxes out at 5GB. Use multipart copy API instead:
    # https://docs.aws.amazon.com/AmazonS3/latest/userguide/CopyingObjctsMPUapi.html
    client = storage.connection.meta.client
    copy_source = f'{source_bucket}/{source_key}'
    client.copy_object(
        Bucket=dest_bucket,
        Key=dest_key,
        CopySource=copy_source,
    )
    client.delete_object(
        Bucket=source_bucket,
        Key=source_key,
    )


def _copy_object_minio(
    storage,
    source_bucket: str,
    source_key: str,
    dest_bucket: str,
    dest_key: str,
):
    # TODO This copy maxes out at 5GB. Use multipart copy API instead:
    # https://docs.aws.amazon.com/AmazonS3/latest/userguide/CopyingObjctsMPUapi.html
    client = storage.client
    copy_source = f'{source_bucket}/{source_key}'
    client.copy_object(dest_bucket, dest_key, copy_source)
    client.remove_object(source_bucket, source_key)
