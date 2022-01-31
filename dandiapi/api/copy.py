from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
import math
from typing import List

import boto3

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

from dandischema.digests.dandietag import Part, PartGenerator, gb, tb


@dataclass
class CopyObjectResponse:
    key: str
    etag: str


@dataclass
class CopyPartResponse:
    etag: str
    part_number: int

    def as_dict(self):
        return {'ETag': self.etag, 'PartNumber': self.part_number}


@dataclass
class CopyObjectPart:
    # The part itself
    part: Part

    # Upload/Bucket info
    upload_id: str
    copy_source: str
    dest_bucket: str
    dest_key: str

    # Whether or not to include the byte range in the request
    # (exlcuded for single part copies)
    include_range: bool = True

    @property
    def copy_range(self) -> str:
        return (
            # Subtract one due to zero-indexing
            f'bytes={self.part.offset}-{self.part.offset + self.part.size - 1}'
            if self.include_range
            else ''
        )


@dataclass
class CopyPartGenerator(PartGenerator):
    """Override the normal PartGenerator class to account for larger copy part sizes."""

    DEFAULT_PART_SIZE = gb(5)

    @classmethod
    def for_file_size(cls, file_size: int) -> CopyPartGenerator:
        """Calculate sequential part sizes given a file size."""
        if file_size == 0:
            return cls(0, 0, 0)

        part_size = cls.DEFAULT_PART_SIZE

        if file_size > tb(5):
            raise ValueError('File is larger than the S3 maximum object size.')

        if math.ceil(file_size / part_size) >= cls.MAX_PARTS:
            part_size = math.ceil(file_size / cls.MAX_PARTS)

        assert cls.MIN_PART_SIZE <= part_size <= cls.MAX_PART_SIZE

        part_qty, final_part_size = divmod(file_size, part_size)
        if final_part_size == 0:
            final_part_size = part_size
        else:
            part_qty += 1
        if part_qty == 1:
            part_size = final_part_size
        return cls(part_qty, part_size, final_part_size)


def copy_object(
    storage, source_bucket: str, source_key: str, dest_bucket: str, dest_key: str
) -> CopyObjectResponse:
    """Copy an object, returning the new object key and etag."""
    if isinstance(storage, S3Boto3Storage):
        client = storage.connection.meta.client
    elif isinstance(storage, MinioStorage):
        # Instantiate an s3 client against the minio storage
        client = boto3.client(
            's3',
            endpoint_url=storage.client._endpoint_url,
            aws_access_key_id=storage.client._access_key,
            aws_secret_access_key=storage.client._secret_key,
            region_name='us-east-1',
        )
    else:
        raise ValueError(f'Unknown storage {storage}')

    return copy_object_multipart(
        client,
        source_bucket=source_bucket,
        source_key=source_key,
        dest_bucket=dest_bucket,
        dest_key=dest_key,
    )


def copy_object_part(client, object_part: CopyObjectPart) -> CopyPartResponse:
    response = client.upload_part_copy(
        Bucket=object_part.dest_bucket,
        Key=object_part.dest_key,
        UploadId=object_part.upload_id,
        CopySource=object_part.copy_source,
        CopySourceRange=object_part.copy_range,
        PartNumber=object_part.part.number,
    )

    # Return the ETag & part number
    etag = response['CopyPartResult']['ETag'].strip('"')
    return CopyPartResponse(etag=etag, part_number=object_part.part.number)


def copy_object_multipart(
    client,
    source_bucket: str,
    source_key: str,
    dest_bucket: str,
    dest_key: str,
) -> CopyObjectResponse:
    """Copy an object using multipart copy."""
    content_length: int = client.head_object(Bucket=source_bucket, Key=source_key)['ContentLength']
    copy_source = f'{source_bucket}/{source_key}'
    upload_id = client.create_multipart_upload(Bucket=dest_bucket, Key=dest_key)['UploadId']
    parts = list(CopyPartGenerator.for_file_size(content_length))

    # Perform concurrent copying of object parts
    uploading_parts: List[Future[CopyPartResponse]] = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        for part in parts:
            # Submit part copy for execution in thread pool
            future = executor.submit(
                copy_object_part,
                client=client,
                object_part=CopyObjectPart(
                    part=part,
                    upload_id=upload_id,
                    copy_source=copy_source,
                    dest_bucket=dest_bucket,
                    dest_key=dest_key,
                    include_range=len(parts) > 1,
                ),
            )

            # Store future to extract later
            uploading_parts.append(future)

    # Retrieve results of part uploads. This blocks until all parts are uploaded.
    uploaded_parts = [part.result().as_dict() for part in uploading_parts]

    # Complete the multipart copy
    res = client.complete_multipart_upload(
        Bucket=dest_bucket,
        Key=dest_key,
        UploadId=upload_id,
        MultipartUpload={'Parts': uploaded_parts},
    )

    # Delete the original object
    client.delete_object(
        Bucket=source_bucket,
        Key=source_key,
    )

    etag = res['ETag'].strip('"')
    return CopyObjectResponse(key=res['Key'], etag=etag)
