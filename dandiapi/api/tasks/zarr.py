from __future__ import annotations

from datetime import datetime
from pathlib import Path

import boto3
from celery import shared_task
from celery.utils.log import get_task_logger
from dandischema.digests.zarr import EMPTY_CHECKSUM
from django.conf import settings
from django.db import transaction

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


logger = get_task_logger(__name__)


def get_client():
    """Return an s3 client from the current storage."""
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


def yield_files(bucket: str, prefix: str | None = None):
    """Get all objects in the bucket, through repeated object listing."""
    client = get_client()
    common_options = {'Bucket': bucket}
    if prefix is not None:
        common_options['Prefix'] = prefix

    continuation_token = None
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


def clear_checksum_files(zarr: ZarrArchive):
    """Remove all checksum files."""
    client = get_client()
    bucket = zarr.storage.bucket_name
    prefix = (
        f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}'
        f'{settings.DANDI_ZARR_CHECKSUM_PREFIX_NAME}/{zarr.zarr_id}'
    )

    for files in yield_files(bucket=bucket, prefix=prefix):
        if not files:
            break

        # Handle both versioned and non-versioned buckets
        allowed = {'Key', 'VersionId'}
        objects = [{k: v for k, v in file.items() if k in allowed} for file in files]
        client.delete_objects(Bucket=bucket, Delete={'Objects': objects})


class SessionZarrChecksumFileUpdater(ZarrChecksumFileUpdater):
    """Override ZarrChecksumFileUpdater to ignore old files."""

    def __init__(self, *args, session_start: datetime, **kwargs):
        super().__init__(*args, **kwargs)

        # Set the start of when new files may have been written
        self._session_start = session_start

    def read_checksum_file(self) -> ZarrChecksumListing | None:
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


@shared_task(queue='ingest_zarr_archive')
def ingest_zarr_archive(
    zarr_id: str,
    no_checksum: bool = False,
    no_size: bool = False,
    no_count: bool = False,
    force: bool = False,
):
    # Ensure zarr is in pending state before proceeding
    with transaction.atomic():
        zarr: ZarrArchive = ZarrArchive.objects.select_for_update().get(zarr_id=zarr_id)
        if not force and zarr.status != ZarrArchive.Status.PENDING:
            logger.info(f'{ZarrArchive.INGEST_ERROR_MSG}. Exiting...')
            return

        # Set as ingesting
        zarr.status = ZarrArchive.Status.INGESTING
        zarr.checksum = None
        zarr.save(update_fields=['status', 'checksum'])

    # Zarr is in correct state, lock until ingestion finishes
    with transaction.atomic():
        zarr: ZarrArchive = ZarrArchive.objects.select_for_update().get(zarr_id=zarr_id)

        # Reset before compute
        if not no_size:
            zarr.size = 0
        if not no_count:
            zarr.file_count = 0

        # Instantiate updater and add files as they come in
        empty = True
        updater = SessionZarrChecksumUpdater(zarr_archive=zarr)
        for files in yield_files(bucket=zarr.storage.bucket_name, prefix=zarr.s3_path('')):
            if len(files):
                empty = False

            # Update size and file count
            if not no_size:
                zarr.size += sum((file['Size'] for file in files))
            if not no_count:
                zarr.file_count += len(files)

            # Update checksums
            if not no_checksum:
                updater.update_file_checksums(
                    {
                        file['Key'].replace(zarr.s3_path(''), ''): ZarrChecksum(
                            digest=file['ETag'].strip('"'),
                            name=Path(file['Key'].replace(zarr.s3_path(''), '')).name,
                            size=file['Size'],
                        )
                        for file in files
                    }
                )

        # If no files were actually yielded, remove all checksum files
        if empty:
            clear_checksum_files(zarr)

        # Set checksum field to top level checksum, after ingestion completion
        checksum = zarr.get_checksum()

        # Raise an exception if empty and checksum are ever out of sync.
        # The reported checksum should never be None if there are files,
        # and there shouldn't be any files if the checksum is None
        if (checksum is None) != empty:
            raise Exception(
                (
                    f'Inconsistency between reported files and computed checksum. Checksum is '
                    f'{checksum}, while {"no" if empty else ""} files were found in the zarr.'
                )
            )

        # If checksum is None, that means there were no files, and we should set
        # the checksum to EMPTY_CHECKSUM, as it's still been ingested, it's just empty.
        zarr.checksum = checksum or EMPTY_CHECKSUM
        zarr.status = ZarrArchive.Status.COMPLETE
        zarr.save(update_fields=['status', 'checksum'])

        # Save all assets that reference this zarr, so their metadata is updated
        zarr.save(update_fields=['size', 'file_count'])
        for asset in zarr.assets.all().iterator():
            asset.save()


def ingest_dandiset_zarrs(dandiset_id: int, **kwargs):
    for zarr in ZarrArchive.objects.filter(dandiset__id=dandiset_id):
        ingest_zarr_archive.delay(str(zarr.zarr_id), **kwargs)
