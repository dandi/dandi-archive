"""
Define and register any scheduled celery tasks.

This module is imported from celery.py in a post-app-load hook.
"""

from celery import shared_task
from celery.schedules import crontab
from celery.utils.log import get_task_logger
from django.db.transaction import atomic

from dandiapi.api.models import Version
from dandiapi.api.tasks import write_manifest_files, validate_version_metadata

logger = get_task_logger(__name__)


@shared_task
@atomic
def write_draft_manifest_files():
    logger.info('Writing manifest files for all draft versions')
    # TODO Optimize this if it causes too much load in production.
    # Rewriting every draft manifest every time is guaranteed not to miss any changes,
    # so just do that for now to avoid the complexity involved with modification dates.
    for draft_version in Version.objects.filter(version='draft').all():
        write_manifest_files.delay(draft_version.id)


@shared_task
@atomic
def validate_draft_version_metadata():
    logger.info('Checking for draft versions that need validation')
    # Select only the id of draft versions that have status PENDING
    pending_draft_versions = (
        Version.objects.filter(status=Version.Status.PENDING).filter(version='draft').values('id')
    )
    logger.info('Found %s versions to validate', pending_draft_versions.count())
    for draft_version in pending_draft_versions:
        validate_version_metadata.delay(draft_version['id'])


def register_scheduled_tasks(sender, **kwargs):
    """Register tasks with a celery beat schedule."""
    # Write out all draft manifests every day at 1 AM
    sender.add_periodic_task(crontab(hour=1), write_draft_manifest_files.s())

    # Check for any draft versions that need validation every 2 minutes
    sender.add_periodic_task(crontab(minute='*/2'), validate_draft_version_metadata.s())
