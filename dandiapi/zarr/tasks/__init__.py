from __future__ import annotations

from typing import TYPE_CHECKING

from celery import shared_task
from celery.utils.log import get_task_logger
from django.db import OperationalError, transaction
from django.utils import timezone
import psycopg.errors
from zarr_checksum import compute_zarr_checksum
from zarr_checksum.generators import S3ClientOptions, yield_files_s3

from dandiapi.api.asset_paths import add_zarr_paths, delete_zarr_paths
from dandiapi.api.models.asset import Asset
from dandiapi.api.models.version import Version
from dandiapi.api.services.exceptions import DandiError
from dandiapi.zarr.models import ZarrArchive, ZarrArchiveStatus, ZarrUploadURL

if TYPE_CHECKING:
    from collections.abc import Iterator

    from zarr_checksum.generators import ZarrArchiveFile

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    queue='ingest_zarr_archive',
    time_limit=3600,
    max_retries=3,
    retry_backoff=True,
)
def ingest_zarr_archive(self, zarr_id: str, *, force: bool = False):
    try:
        _ingest_zarr_archive(zarr_id, force=force)
    except OperationalError as e:
        if isinstance(e.__cause__, psycopg.errors.DeadlockDetected):
            raise self.retry(exc=e) from e
        raise


def _ingest_zarr_archive(zarr_id: str, *, force: bool = False):
    # Ensure zarr is in pending state before proceeding
    with transaction.atomic():
        zarr: ZarrArchive = ZarrArchive.objects.select_for_update().get(zarr_id=zarr_id)

        # Published zarrs are immutable, and must never be re-ingested (even if forced)
        try:
            zarr.ensure_modifiable()
        except DandiError as e:
            logger.info('Cannot ingest zarr %s: %s Exiting...', zarr_id, e.message)
            return

        if not force and zarr.status != ZarrArchiveStatus.UPLOADED:
            logger.info('Zarrs must be in an UPLOADED state to begin ingestion. Exiting...')
            return

        # Set as ingesting
        previous_status = zarr.status
        zarr.status = ZarrArchiveStatus.INGESTING
        zarr.checksum = None
        zarr.save(update_fields=['status', 'checksum'])

    # Retrieve all upload URLs which could still be used to write to this zarr. No new URLs can be
    # issued while the zarr is INGESTING, so this set can only shrink from here on.
    outstanding_urls = list(
        ZarrUploadURL.objects.filter(zarr_archive=zarr, expires_at__gt=timezone.now()).values_list(
            'path', 'md5', 'expires_at'
        )
    )
    outstanding_paths = {path for path, _, _ in outstanding_urls}

    # The MD5 (ETag) of every listed file with an outstanding upload URL
    listed_md5s: dict[str, str] = {}

    def record_outstanding_md5s(files: Iterator[ZarrArchiveFile]) -> Iterator[ZarrArchiveFile]:
        for file in files:
            path = str(file.path)
            if path in outstanding_paths:
                listed_md5s[path] = file.digest
            yield file

    # Instantiate updater and add files as they come in.
    # Compute the checksum before starting the transaction to avoid long lived locks.
    logger.info('Computing checksum for zarr %s...', zarr.zarr_id)
    checksum = compute_zarr_checksum(
        record_outstanding_md5s(
            yield_files_s3(
                bucket=zarr.storage.bucket_name,
                prefix=zarr.s3_path(''),
                client_options=S3ClientOptions(
                    region_name=zarr.storage.region_name,
                    use_ssl=zarr.storage.use_ssl,
                    verify=zarr.storage.verify,
                    endpoint_url=zarr.storage.endpoint_url,
                    aws_access_key_id=zarr.storage.access_key,
                    aws_secret_access_key=zarr.storage.secret_key,
                    aws_session_token=zarr.storage.security_token,
                    config=zarr.storage.client_config,
                ),
            )
        )
    )

    # Each upload URL can only write the content it was signed with. So a URL is harmless if the
    # listed file at its path already has that content, as using it again won't change anything.
    # Otherwise, it could still change the zarr after ingestion, making the checksum incorrect.
    now = timezone.now()
    unsafe_url_expirations = [
        expires_at
        for path, md5, expires_at in outstanding_urls
        if listed_md5s.get(path) != md5 and expires_at > now
    ]
    if unsafe_url_expirations:
        # Defer ingestion until these URLs have expired, at which point the zarr will be picked
        # up by `ingest_deferred_zarr_archives`. A zarr which was force ingested while PENDING is
        # returned to that state, so that the upload may continue.
        deferred_until = max(unsafe_url_expirations)
        logger.info(
            'Zarr %s has %d unused or superseded upload URLs. Deferring ingestion until %s.',
            zarr_id,
            len(unsafe_url_expirations),
            deferred_until.isoformat(),
        )
        deferred_fields: dict = (
            {'status': ZarrArchiveStatus.PENDING}
            if previous_status == ZarrArchiveStatus.PENDING
            else {'status': ZarrArchiveStatus.UPLOADED, 'ingestion_deferred_until': deferred_until}
        )
        ZarrArchive.objects.filter(zarr_id=zarr_id, status=ZarrArchiveStatus.INGESTING).update(
            **deferred_fields
        )
        return

    # Zarr is in correct state, lock until ingestion finishes
    with transaction.atomic():
        zarr = (
            ZarrArchive.objects.select_related('dandiset')
            .select_for_update(of=['self'])
            .get(zarr_id=zarr_id, status=ZarrArchiveStatus.INGESTING)
        )

        # Remove all asset paths associated with this zarr before ingest
        delete_zarr_paths(zarr)

        # Set zarr fields
        zarr.checksum = checksum.digest
        zarr.file_count = checksum.count
        zarr.size = checksum.size
        zarr.status = ZarrArchiveStatus.COMPLETE
        zarr.ingestion_deferred_until = None
        zarr.save()

        # Add asset paths after ingest is finished
        add_zarr_paths(zarr)

        # Set version status back to PENDING, and update modified.
        Version.objects.filter(id=zarr.dandiset.draft_version.id).update(
            status=Version.Status.PENDING, modified=timezone.now()
        )

        # Set the asset status back to pending, and update modified
        zarr_assets = Asset.objects.filter(zarr=zarr, published=False)
        if zarr_assets.exists():
            zarr_assets.update(status=Asset.Status.PENDING, modified=timezone.now())


def ingest_dandiset_zarrs(dandiset_id: int, **kwargs):
    for zarr in ZarrArchive.objects.filter(dandiset__id=dandiset_id):
        ingest_zarr_archive.delay(str(zarr.zarr_id), **kwargs)


@shared_task(soft_time_limit=60)
def ingest_deferred_zarr_archives():
    """
    Dispatch ingestion for UPLOADED zarr archives which no longer have any unexpired upload URLs.

    This picks up zarrs whose ingestion was deferred due to unused or superseded upload URLs, as
    well as any zarr whose ingestion task was otherwise lost. Dispatching ingestion for a zarr
    that's already being ingested is harmless, as the task exits if the zarr isn't UPLOADED.
    """
    zarr_ids = (
        ZarrArchive.objects.filter(status=ZarrArchiveStatus.UPLOADED)
        .exclude(upload_urls__expires_at__gt=timezone.now())
        .values_list('zarr_id', flat=True)
    )
    for zarr_id in zarr_ids.iterator():
        logger.info('Dispatching deferred ingestion of zarr %s', zarr_id)
        ingest_zarr_archive.delay(str(zarr_id))


@shared_task(soft_time_limit=300)
def delete_expired_zarr_upload_urls():
    """Delete records of zarr upload URLs that have expired, as they can no longer be used."""
    deleted, _ = ZarrUploadURL.objects.filter(expires_at__lte=timezone.now()).delete()
    logger.info('Deleted %d expired zarr upload URLs', deleted)
