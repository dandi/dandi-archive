"""
Define and register any scheduled celery tasks.

This module is imported from celery.py in a post-app-load hook.
"""
from datetime import timedelta

from celery import shared_task
from celery.app.base import Celery
from celery.schedules import crontab
from celery.utils.log import get_task_logger
from django.conf import settings
from django.db.transaction import atomic

from dandiapi.api.models import Version
from dandiapi.api.tasks import (
    send_pending_users_email,
    validate_version_metadata,
    write_manifest_files,
)

logger = get_task_logger(__name__)


@shared_task
@atomic
def validate_draft_version_metadata():
    # Select only the id of draft versions that have status PENDING
    pending_draft_versions = (
        Version.objects.filter(status=Version.Status.PENDING).filter(version='draft').values('id')
    )
    if pending_draft_versions.count() > 0:
        logger.info('Found %s versions to validate', pending_draft_versions.count())
        for draft_version in pending_draft_versions:
            validate_version_metadata.delay(draft_version['id'])

            # Revalidation should be triggered every time a version is modified,
            # so now is a good time to write out the manifests as well.
            write_manifest_files.delay(draft_version['id'])


def register_scheduled_tasks(sender: Celery, **kwargs):
    """Register tasks with a celery beat schedule."""
    # Check for any draft versions that need validation every minute
    sender.add_periodic_task(
        timedelta(seconds=settings.DANDI_VALIDATION_JOB_INTERVAL),
        validate_draft_version_metadata.s(),
    )

    # Send daily email to admins containing a list of users awaiting approval
    sender.add_periodic_task(crontab(hour=0, minute=0), send_pending_users_email.s())
