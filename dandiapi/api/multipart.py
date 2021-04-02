from datetime import timedelta
from typing import Iterator, Tuple

from dandi.core.digests.dandietag import PartGenerator
from django.core.files.storage import Storage
from s3_file_field._multipart import MultipartManager
from s3_file_field._multipart_boto3 import Boto3MultipartManager
from s3_file_field._multipart_minio import MinioMultipartManager


class UnsupportedStorageException(Exception):
    """Raised when MultipartManager does not support the given Storage."""

    pass


class DandiMultipartMixin:
    @staticmethod
    def _iter_part_sizes(file_size: int, part_size: int = None) -> Iterator[Tuple[int, int]]:
        generator = PartGenerator.for_file_size(file_size)
        for part in generator:
            yield part.number, part.size

    _url_expiration = timedelta(days=7)


class DandiBoto3MultipartManager(DandiMultipartMixin, Boto3MultipartManager):
    def _create_upload_id(self, object_key: str) -> str:
        resp = self._client.create_multipart_upload(
            Bucket=self._bucket_name,
            Key=object_key,
            ACL='bucket-owner-full-control',
        )
        return resp['UploadId']


class DandiMinioMultipartManager(DandiMultipartMixin, MinioMultipartManager):
    def _create_upload_id(self, object_key: str) -> str:
        return self._client._new_multipart_upload(
            bucket_name=self._bucket_name,
            object_name=object_key,
            metadata={'x-amz-acl': 'bucket-owner-full-control'},
        )


class DandiMultipartManager(MultipartManager):
    @classmethod
    def from_storage(cls, storage: Storage) -> MultipartManager:
        try:
            from storages.backends.s3boto3 import S3Boto3Storage
        except ImportError:
            pass
        else:
            if isinstance(storage, S3Boto3Storage):
                return DandiBoto3MultipartManager(storage)

        try:
            from minio_storage.storage import MinioStorage
        except ImportError:
            pass
        else:
            if isinstance(storage, MinioStorage):
                return DandiMinioMultipartManager(storage)

        raise UnsupportedStorageException('Unsupported storage provider.')
