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
        self._session_start = session_start

    def read_checksum_file(self) -> Optional[ZarrChecksumListing]:
        """Load a checksum listing from the checksum file."""
        storage = self.zarr_archive.storage
        checksum_path = self.checksum_file_path
        exists = storage.exists(checksum_path)

        # Only read existing if it's one that we've created
        if exists and storage.modified_time(checksum_path) >= self._session_start:
            with storage.open(checksum_path) as f:
                x = f.read()
                return self._serializer.deserialize(x)
        else:
            return None


class SessionZarrChecksumUpdater(ZarrChecksumUpdater):
    """ZarrChecksumUpdater to distinguish existing and new checksum files."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._session_start = datetime.now()

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
        yield [
            ZarrChecksum(
                md5=file['ETag'].strip('"'),
                path=file['Key'].replace(zarr.s3_path(''), ''),
            )
            for file in res['Contents']
        ]

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
def compute_zarr_checksum(zarr_id: int):
    client = get_client()
    zarr: ZarrArchive = ZarrArchive.objects.get(id=zarr_id)

    # Instantiate updater and add files as they come in
    updater = SessionZarrChecksumUpdater(zarr_archive=zarr)
    for checksums in yield_files(client, zarr):
        updater.update_file_checksums(checksums)
