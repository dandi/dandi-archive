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


PART_SIZE = 500 * 1024 * 1024  # 500 MB


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

    response = client.head_object(
        Bucket=source_bucket,
        Key=source_key,
    )
    content_length = response['ContentLength']

    copy_source = f'{source_bucket}/{source_key}'

    # Use multipart copy so files > 5GB are supported

    parts_count = content_length // PART_SIZE
    if content_length % PART_SIZE > 0:
        # The extra part is for the remaining bytes that might be less than PART_SIZE
        parts_count += 1

    response = client.create_multipart_upload(
        Bucket=dest_bucket,
        Key=dest_key,
    )
    upload_id = response['UploadId']

    progress = 0
    remaining = content_length
    parts = []
    for part_number in range(1, parts_count + 1):
        # Calculate the range to be copied
        if remaining > PART_SIZE:
            copy_range = f'bytes={progress}-{progress+PART_SIZE-1}'
            progress += PART_SIZE
            remaining -= PART_SIZE
        else:
            copy_range = f'bytes={progress}-{content_length-1}'

        # Copy the part
        response = client.upload_part_copy(
            Bucket=dest_bucket,
            Key=dest_key,
            UploadId=upload_id,
            CopySource=copy_source,
            CopySourceRange=copy_range,
            PartNumber=part_number,
        )

        # Save the ETag + Part number
        etag = response['CopyPartResult']['ETag']
        parts += [{'ETag': etag, 'PartNumber': part_number}]

    # Complete the multipart copy
    client.complete_multipart_upload(
        Bucket=dest_bucket,
        Key=dest_key,
        UploadId=upload_id,
        MultipartUpload={'Parts': parts},
    )

    # Delete the original object
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
    # The Minio client will automatically use multipart upload if the file size is too big
    client = storage.client
    copy_source = f'{source_bucket}/{source_key}'
    client.copy_object(dest_bucket, dest_key, copy_source)
    client.remove_object(source_bucket, source_key)
