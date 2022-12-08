from __future__ import annotations

from datetime import datetime
from pathlib import Path

from celery import shared_task
from celery.utils.log import get_task_logger
from dandischema.digests.zarr import EMPTY_CHECKSUM
from django.conf import settings
from django.db import transaction
from django.db.transaction import atomic

from dandiapi.api.asset_paths import add_zarr_paths, delete_zarr_paths
from dandiapi.api.storage import get_boto_client, yield_files
from dandiapi.zarr.checksums import (
    ZarrChecksum,
    ZarrChecksumFileUpdater,
    ZarrChecksumListing,
    ZarrChecksumModification,
    ZarrChecksumModificationQueue,
    ZarrChecksumUpdater,
)
from dandiapi.zarr.models import ZarrArchive, ZarrArchiveStatus

logger = get_task_logger(__name__)


def clear_checksum_files(zarr: ZarrArchive):
    """Remove all checksum files."""
    client = get_boto_client()
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


@shared_task(queue='ingest_zarr_archive', time_limit=3600)
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
        if not force and zarr.status != ZarrArchiveStatus.PENDING:
            logger.info(f'{ZarrArchive.INGEST_ERROR_MSG}. Exiting...')
            return

        # Set as ingesting
        zarr.status = ZarrArchiveStatus.INGESTING
        zarr.checksum = None
        zarr.save(update_fields=['status', 'checksum'])

    # Zarr is in correct state, lock until ingestion finishes
    with transaction.atomic():
        zarr = ZarrArchive.objects.select_for_update().get(zarr_id=zarr_id)

        # Remove all asset paths associated with this zarr before ingest
        delete_zarr_paths(zarr)

        # Reset before compute
        if not no_size:
            zarr.size = 0
        if not no_count:
            zarr.file_count = 0

        # Instantiate updater and add files as they come in
        empty = True
        queue = ZarrChecksumModificationQueue()
        logger.info(f'Fetching files for zarr {zarr.zarr_id}...')
        for files in yield_files(bucket=zarr.storage.bucket_name, prefix=zarr.s3_path('')):
            if len(files):
                empty = False

            # Update size and file count
            if not no_size:
                zarr.size += sum(file['Size'] for file in files)
            if not no_count:
                zarr.file_count += len(files)

            # Update checksums
            if not no_checksum:
                for file in files:
                    path = Path(file['Key'].replace(zarr.s3_path(''), ''))
                    checksum = ZarrChecksum(
                        name=path.name,
                        size=file['Size'],
                        digest=file['ETag'].strip('"'),
                    )
                    queue.queue_file_update(key=path.parent, checksum=checksum)

        # If no files were actually yielded, remove all checksum files
        if empty:
            clear_checksum_files(zarr)
        else:
            # Perform updates
            SessionZarrChecksumUpdater(zarr_archive=zarr).modify(modifications=queue)

        # Set checksum field to top level checksum, after ingestion completion
        checksum = zarr.get_checksum()

        # Raise an exception if empty and checksum are ever out of sync.
        # The reported checksum should never be None if there are files,
        # and there shouldn't be any files if the checksum is None
        if (checksum is None) != empty:
            raise Exception(
                f'Inconsistency between reported files and computed checksum. Checksum is '
                f'{checksum}, while {"no" if empty else ""} files were found in the zarr.'
            )

        # If checksum is None, that means there were no files, and we should set
        # the checksum to EMPTY_CHECKSUM, as it's still been ingested, it's just empty.
        zarr.checksum = checksum or EMPTY_CHECKSUM
        zarr.status = ZarrArchiveStatus.COMPLETE
        zarr.save(update_fields=['status', 'checksum'])

        # Save all assets that reference this zarr, so their metadata is updated
        zarr.save(update_fields=['size', 'file_count'])
        for asset in zarr.assets.iterator():
            asset.save()

        # Add asset paths after ingest is finished
        add_zarr_paths(zarr)


def ingest_dandiset_zarrs(dandiset_id: int, **kwargs):
    for zarr in ZarrArchive.objects.filter(dandiset__id=dandiset_id):
        ingest_zarr_archive.delay(str(zarr.zarr_id), **kwargs)


@shared_task(soft_time_limit=60)
@atomic
def cancel_zarr_upload(zarr_id: str):
    zarr_archive: ZarrArchive = ZarrArchive.objects.select_for_update().get(zarr_id=zarr_id)
    zarr_archive.cancel_upload()
