from __future__ import annotations

from pathlib import Path

from celery import shared_task
from celery.utils.log import get_task_logger
from dandischema.digests.zarr import EMPTY_CHECKSUM
from django.db import transaction
from django.db.transaction import atomic

from dandiapi.api.asset_paths import add_zarr_paths, delete_zarr_paths
from dandiapi.api.storage import yield_files
from dandiapi.zarr.checksums import (
    ZarrChecksum,
    ZarrChecksumModificationQueue,
    ZarrChecksumUpdater,
    parse_checksum_string,
)
from dandiapi.zarr.models import ZarrArchive, ZarrArchiveStatus

logger = get_task_logger(__name__)


@shared_task(queue='ingest_zarr_archive', time_limit=3600)
def ingest_zarr_archive(zarr_id: str, force: bool = False):
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

        # Instantiate updater and add files as they come in
        empty = True
        queue = ZarrChecksumModificationQueue()
        logger.info(f'Fetching files for zarr {zarr.zarr_id}...')
        for files in yield_files(bucket=zarr.storage.bucket_name, prefix=zarr.s3_path('')):
            if len(files):
                empty = False

            # Update checksums
            for file in files:
                path = Path(file['Key'].replace(zarr.s3_path(''), ''))
                checksum = ZarrChecksum(
                    name=path.name,
                    size=file['Size'],
                    digest=file['ETag'].strip('"'),
                )
                queue.queue_file_update(key=path.parent, checksum=checksum)

        # Compute checksum tree and retrieve top level checksum
        checksum = ZarrChecksumUpdater(zarr_archive=zarr).modify(modifications=queue)

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
        zarr.file_count, zarr.size = parse_checksum_string(zarr.checksum)
        zarr.status = ZarrArchiveStatus.COMPLETE
        zarr.save()

        # Save all assets that reference this zarr, so their metadata is updated
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
