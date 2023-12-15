"""
Define and register any scheduled celery tasks.

This module is imported from celery.py in a post-app-load hook.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import timedelta
import time
from typing import TYPE_CHECKING

from celery import shared_task
from celery.schedules import crontab
from celery.utils.log import get_task_logger
from django.conf import settings
from django.contrib.auth.models import User
from django.db import connection
from django.db.models.query_utils import Q

from dandiapi.analytics.tasks import collect_s3_log_records_task
from dandiapi.api.mail import send_pending_users_message
from dandiapi.api.models import UserMetadata, Version
from dandiapi.api.models.asset import Asset
from dandiapi.api.services.metadata import version_aggregate_assets_summary
from dandiapi.api.services.metadata.exceptions import VersionMetadataConcurrentlyModifiedError
from dandiapi.api.tasks import (
    validate_asset_metadata_task,
    validate_version_metadata_task,
    write_manifest_files,
)
from dandiapi.zarr.models import ZarrArchiveStatus

if TYPE_CHECKING:
    from collections.abc import Iterable

    from celery.app.base import Celery

logger = get_task_logger(__name__)


def throttled_iterator(iterable: Iterable, max_per_second: int = 100) -> Iterable:
    """
    Yield items from iterable, throttling to max_per_second.

    This is useful for putting messages on a queue, where you don't want to
    overwhelm the queue with too many messages at once.
    """
    for item in iterable:
        yield item
        time.sleep(1 / max_per_second)


@shared_task(
    soft_time_limit=60,
    autoretry_for=(VersionMetadataConcurrentlyModifiedError,),
    retry_backoff=True,
)
def aggregate_assets_summary_task(version_id: int):
    version = Version.objects.get(id=version_id)
    version_aggregate_assets_summary(version)


@shared_task(soft_time_limit=30)
def validate_pending_asset_metadata():
    validatable_assets = (
        Asset.objects.filter(status=Asset.Status.PENDING)
        .filter(
            (Q(blob__isnull=False) & Q(blob__sha256__isnull=False))
            | (
                Q(zarr__isnull=False)
                & Q(zarr__checksum__isnull=False)
                & Q(zarr__status=ZarrArchiveStatus.COMPLETE)
            )
        )
        .values_list('id', flat=True)
    )
    validatable_assets_count = validatable_assets.count()
    if validatable_assets_count > 0:
        logger.info('Found %s assets to validate', validatable_assets_count)
        for asset_id in throttled_iterator(validatable_assets.iterator()):
            validate_asset_metadata_task.delay(asset_id)


@shared_task(soft_time_limit=20)
def validate_draft_version_metadata():
    # Select only the id of draft versions that have status PENDING
    pending_draft_versions = (
        Version.objects.filter(status=Version.Status.PENDING)
        .filter(version='draft')
        .values_list('id', flat=True)
    )
    pending_draft_versions_count = pending_draft_versions.count()
    if pending_draft_versions_count > 0:
        logger.info('Found %s versions to validate', pending_draft_versions_count)
        for draft_version_id in pending_draft_versions.iterator():
            validate_version_metadata_task.delay(draft_version_id)
            aggregate_assets_summary_task.delay(draft_version_id)

            # Revalidation should be triggered every time a version is modified,
            # so now is a good time to write out the manifests as well.
            write_manifest_files.delay(draft_version_id)


@shared_task(soft_time_limit=20)
def send_pending_users_email() -> None:
    """Send an email to admins listing users with status set to PENDING."""
    pending_users = User.objects.filter(metadata__status=UserMetadata.Status.PENDING)
    if pending_users.exists():
        send_pending_users_message(pending_users)


@shared_task(soft_time_limit=60)
def refresh_materialized_view_search() -> None:
    """
    Execute a REFRESH MATERIALIZED VIEW query to update the view used by asset search.

    Note that this is a "concurrent" refresh, which means that the view will be
    updated without locking the table.
    """
    with connection.cursor() as cursor:
        cursor.execute('REFRESH MATERIALIZED VIEW CONCURRENTLY asset_search;')


def register_scheduled_tasks(sender: Celery, **kwargs):
    """Register tasks with a celery beat schedule."""
    # Check for any draft versions that need validation every minute
    sender.add_periodic_task(
        timedelta(seconds=settings.DANDI_VALIDATION_JOB_INTERVAL),
        validate_draft_version_metadata.s(),
    )
    # Check for any assets that need validation every minute
    sender.add_periodic_task(
        timedelta(seconds=settings.DANDI_VALIDATION_JOB_INTERVAL),
        validate_pending_asset_metadata.s(),
    )

    # Send daily email to admins containing a list of users awaiting approval
    sender.add_periodic_task(crontab(hour=0, minute=0), send_pending_users_email.s())

    # Refresh the materialized view used by asset search every 10 mins.
    sender.add_periodic_task(timedelta(minutes=10), refresh_materialized_view_search.s())

    # Process new S3 logs every hour
    for log_bucket in [
        settings.DANDI_DANDISETS_LOG_BUCKET_NAME,
        settings.DANDI_DANDISETS_EMBARGO_LOG_BUCKET_NAME,
    ]:
        sender.add_periodic_task(
            timedelta(hours=1),
            collect_s3_log_records_task.s(log_bucket),
        )
