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

from dandiapi.api.mail import send_pending_users_message, send_publish_reminder_message
from dandiapi.api.models import UserMetadata, Version
from dandiapi.api.models.asset import Asset
from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.models.stats import ApplicationStats
from dandiapi.api.services.garbage_collection import garbage_collect
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
    else:
        logger.debug('Found no assets to validate')


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
    else:
        logger.debug('Found no versions to validate')


@shared_task(soft_time_limit=20)
def send_pending_users_email() -> None:
    """Send an email to admins listing users with status set to PENDING."""
    pending_users = User.objects.filter(metadata__status=UserMetadata.Status.PENDING)
    if pending_users.exists():
        send_pending_users_message(pending_users)


REFRESH_MATERIALIZED_VIEW_TIMEOUT = timedelta(minutes=3).total_seconds()


@shared_task(soft_time_limit=REFRESH_MATERIALIZED_VIEW_TIMEOUT)
def refresh_materialized_view_search() -> None:
    """
    Execute a REFRESH MATERIALIZED VIEW query to update the view used by asset search.

    Note that this is a "concurrent" refresh, which means that the view will be
    updated without locking the table.
    """
    with connection.cursor() as cursor:
        # This query may take a long time, so we explicitly set a timeout with
        # postgres that is slightly less (5 seconds) than the Celery soft_time_limit to
        # avoid it running too long.
        # Note that setting Celery time limits alone is not sufficient. If the task times out,
        # Celery will stop the Python execution, but not the DB query.
        cursor.execute('BEGIN;')
        statement_timeout = (REFRESH_MATERIALIZED_VIEW_TIMEOUT * 1000) - 5000
        cursor.execute('SET LOCAL statement_timeout = %s;', [statement_timeout])
        cursor.execute('REFRESH MATERIALIZED VIEW CONCURRENTLY asset_search;')
        cursor.execute('COMMIT;')


@shared_task(soft_time_limit=60)
def garbage_collection() -> None:
    garbage_collect()


@shared_task(soft_time_limit=60)
def compute_application_stats() -> None:
    ApplicationStats.objects.create(
        dandiset_count=Dandiset.objects.count(),
        published_dandiset_count=Dandiset.published_count(),
        user_count=User.objects.filter(metadata__status=UserMetadata.Status.APPROVED).count(),
        size=Asset.total_size(),
    )


# Number of days after which a draft-only dandiset is considered "stale" and
# eligible for a publish reminder email.
PUBLISH_REMINDER_DAYS = 30


@shared_task(soft_time_limit=120)
def send_publish_reminder_emails() -> None:
    """
    Send reminder emails to owners of draft-only dandisets that haven't been modified recently.

    This task finds all dandisets that:
    1. Have never been published (only have a draft version)
    2. Have a draft version that hasn't been modified in PUBLISH_REMINDER_DAYS days
    3. Are not embargoed (embargoed dandisets have different publication workflows)
    4. Have not already received a publish reminder email

    For each such dandiset, an email is sent to all owners reminding them to publish.
    The dandiset's publish_reminder_sent_at field is then updated to prevent duplicate emails.
    """
    from django.utils import timezone

    cutoff_date = timezone.now() - timedelta(days=PUBLISH_REMINDER_DAYS)

    # Find dandisets that:
    # - Are not embargoed
    # - Have never been published (no versions other than 'draft')
    # - Have a draft version that was last modified before the cutoff date
    # - Have not already received a publish reminder email
    stale_draft_dandisets = (
        Dandiset.objects.filter(
            embargo_status=Dandiset.EmbargoStatus.OPEN,
            publish_reminder_sent_at__isnull=True,  # Only dandisets that haven't been reminded
        )
        .exclude(
            # Exclude dandisets that have any published versions
            versions__version__regex=r'^\d'
        )
        .filter(
            # Only include dandisets with draft versions modified before cutoff
            versions__version='draft',
            versions__modified__lt=cutoff_date,
        )
        .distinct()
    )

    stale_count = stale_draft_dandisets.count()
    if stale_count > 0:
        logger.info('Found %s stale draft dandisets to send publish reminders', stale_count)
        for dandiset in stale_draft_dandisets.iterator():
            try:
                send_publish_reminder_message(dandiset)
                # Mark the dandiset as having received a reminder
                dandiset.publish_reminder_sent_at = timezone.now()
                dandiset.save(update_fields=['publish_reminder_sent_at'])
            except Exception:
                logger.exception(
                    'Failed to send publish reminder for dandiset %s', dandiset.identifier
                )
    else:
        logger.debug('Found no stale draft dandisets to send publish reminders')


def register_scheduled_tasks(sender: Celery, **kwargs):
    """Register tasks with a celery beat schedule."""
    logger.info(
        'Registering scheduled tasks for %s. DANDI_VALIDATION_JOB_INTERVAL is %s seconds.',
        sender,
        settings.DANDI_VALIDATION_JOB_INTERVAL,
    )
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

    # Refresh the application stats every 6 hours
    sender.add_periodic_task(timedelta(hours=6), compute_application_stats.s())

    # Run garbage collection once a day
    # TODO: enable this once we're ready to run garbage collection automatically
    # sender.add_periodic_task(timedelta(days=1), garbage_collection.s())

    # Send weekly publish reminder emails to owners of stale draft-only dandisets
    sender.add_periodic_task(crontab(hour=9, minute=0, day_of_week=1), send_publish_reminder_emails.s())
