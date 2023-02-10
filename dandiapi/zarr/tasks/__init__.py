from __future__ import annotations

from celery import shared_task
from celery.utils.log import get_task_logger
from django.db import transaction
from zarr_checksum import compute_zarr_checksum
from zarr_checksum.generators import S3ClientOptions, yield_files_s3

from dandiapi.api.asset_paths import add_zarr_paths, delete_zarr_paths
from dandiapi.api.storage import get_storage_params
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
        logger.info(f'Computing checksum for zarr {zarr.zarr_id}...')
        storage_params = get_storage_params(zarr.storage)
        checksum = compute_zarr_checksum(
            yield_files_s3(
                bucket=zarr.storage.bucket_name,
                prefix=zarr.s3_path(''),
                client_options=S3ClientOptions(
                    endpoint_url=storage_params['endpoint_url'],
                    aws_access_key_id=storage_params['access_key'],
                    aws_secret_access_key=storage_params['secret_key'],
                    region_name='us-east-1',
                ),
            )
        )

        # Set zarr fields
        zarr.checksum = checksum.digest
        zarr.file_count = checksum.count
        zarr.size = checksum.size
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
