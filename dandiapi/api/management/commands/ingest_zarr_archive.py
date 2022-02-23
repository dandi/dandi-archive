from datetime import datetime
from typing import Optional

import boto3
import djclick as click

from dandiapi.api.models.zarr import ZarrArchive
from dandiapi.api.storage import get_storage
from dandiapi.api.zarr_checksums import (
    ZarrChecksum,
    ZarrChecksumFileUpdater,
    ZarrChecksumListing,
    ZarrChecksumModification,
    ZarrChecksumUpdater,
)

try:
    from minio_storage.storage import MinioStorage
except ImportError:
    # This should only be used for type interrogation, never instantiation
    MinioStorage = type('FakeMinioStorage', (), {})


class SessionZarrChecksumFileUpdater(ZarrChecksumFileUpdater):
    """Override ZarrChecksumFileUpdater to ignore old files."""

    def __init__(self, *args, session_start: datetime, **kwargs):
        super().__init__(*args, **kwargs)

        # Set the start of when new files may have been written
        self._session_start = session_start

    def read_checksum_file(self) -> Optional[ZarrChecksumListing]:
        """Load a checksum listing from the checksum file."""
        storage = self.zarr_archive.storage
        checksum_path = self.checksum_file_path

        # Check if this file was modified during this session
        read_existing = False
        if storage.exists(checksum_path):
            read_existing = storage.modified_time(self.checksum_file_path) >= self._session_start

        # Read existing file if necessary
        if read_existing:
            with storage.open(checksum_path) as f:
                x = f.read()
                return self._serializer.deserialize(x)
        else:
            return None


class SessionZarrChecksumUpdater(ZarrChecksumUpdater):
    """ZarrChecksumUpdater to distinguish existing and new checksum files."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # Set microseconds to zero, since the timestamp from S3/Minio won't include them
        # Failure to set this to zero will result in false negatives
        self._session_start = datetime.now().replace(tzinfo=None, microsecond=0)

    def apply_modification(
        self, modification: ZarrChecksumModification
    ) -> SessionZarrChecksumFileUpdater:
        with SessionZarrChecksumFileUpdater(
            zarr_archive=self.zarr_archive,
            zarr_directory_path=modification.path,
            session_start=self._session_start,
        ) as file_updater:
            file_updater.add_file_checksums(modification.files_to_update)
            file_updater.add_directory_checksums(modification.directories_to_update)
            file_updater.remove_checksums(modification.paths_to_remove)

        return file_updater


def yield_files(client, zarr: ZarrArchive):
    """Get all objects in the bucket, through repeated object listing."""
    continuation_token = None
    common_options = {'Bucket': zarr.storage.bucket_name, 'Prefix': zarr.s3_path('')}
    while True:
        options = {**common_options}
        if continuation_token is not None:
            options['ContinuationToken'] = continuation_token

        # Fetch
        res = client.list_objects_v2(**options)

        # Yield this batch of files
        yield res.get('Contents', [])

        # If all files fetched, end
        if res['IsTruncated'] is False:
            break

        # Get next continuation token
        continuation_token = res['NextContinuationToken']


def get_client():
    storage = get_storage()
    if isinstance(storage, MinioStorage):
        return boto3.client(
            's3',
            endpoint_url=storage.client._endpoint_url,
            aws_access_key_id=storage.client._access_key,
            aws_secret_access_key=storage.client._secret_key,
            region_name='us-east-1',
        )

    return storage.connection.meta.client


@click.command()
@click.argument('zarr_id', type=int)
@click.option('--no-checksum', help="Don't recompute checksums", is_flag=True)
@click.option('--no-size', help="Don't recompute total size", is_flag=True)
@click.option('--no-count', help="Don't recompute total file count", is_flag=True)
def ingest_zarr_archive(zarr_id: int, no_checksum: bool, no_size: bool, no_count: bool):
    client = get_client()
    zarr: ZarrArchive = ZarrArchive.objects.get(id=zarr_id)

    # Reset before compute
    if not no_size:
        zarr.size = 0
    if not no_count:
        zarr.file_count = 0

    # Instantiate updater and add files as they come in
    updater = SessionZarrChecksumUpdater(zarr_archive=zarr)
    for files in yield_files(client, zarr):
        # Update size and file count
        if not no_size:
            zarr.size += sum((file['Size'] for file in files))
        if not no_count:
            zarr.file_count += len(files)

        # Update checksums
        if not no_checksum:
            updater.update_file_checksums(
                [
                    ZarrChecksum(
                        md5=file['ETag'].strip('"'),
                        path=file['Key'].replace(zarr.s3_path(''), ''),
                    )
                    for file in files
                ]
            )

    # Save zarr after completion
    zarr.save()
