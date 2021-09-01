import hashlib

from django.core.files.storage import Storage


class UnsupportedStorageError(Exception):
    """Raised when the given Storage is not supported."""

    pass


class ChecksumCalculatorFile:
    """File-like object that calculates the checksum of everything written to it."""

    def __init__(self):
        self.h = hashlib.sha256()

    def write(self, bytes):
        self.h.update(bytes)

    @property
    def checksum(self):
        return self.h.hexdigest()


def _calculate_checksum_boto3(storage: Storage, name: str):
    obj = storage.bucket.Object(name)
    calculator = ChecksumCalculatorFile()
    obj.download_fileobj(calculator)
    return calculator.checksum


def _calculate_checksum_minio(storage: Storage, name: str):
    obj = storage.client.get_object(storage.bucket_name, name)
    calculator = ChecksumCalculatorFile()
    for d in obj.stream(amt=1024 * 1024):
        calculator.write(d)
    return calculator.checksum


def calculate_sha256_checksum(storage: Storage, name: str):
    """
    Calculate the checksum of an S3 blob.

    Using blob.open() downloads the entire file to disk and returns a file handle pointing to that
    file, rather than streaming the bytes as you read. This method determines whether the blob is
    stored in S3 or Minio and uses the appropriate client to stream the data rather than
    downloading in one go.
    """
    try:
        from storages.backends.s3boto3 import S3Boto3Storage
    except ImportError:
        pass
    else:
        if isinstance(storage, S3Boto3Storage):
            return _calculate_checksum_boto3(storage, name)

    try:
        from minio_storage.storage import MinioStorage
    except ImportError:
        pass
    else:
        if isinstance(storage, MinioStorage):
            return _calculate_checksum_minio(storage, name)

    raise UnsupportedStorageError('Unsupported storage provider.')
