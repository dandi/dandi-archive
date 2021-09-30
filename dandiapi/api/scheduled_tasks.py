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
def validate_draft_version_metadata():
    logger.info('Checking for draft versions that need validation')
    # Select only the id of draft versions that have status PENDING
    pending_draft_versions = (
        Version.objects.filter(status=Version.Status.PENDING).filter(version='draft').values('id')
    )
    logger.info('Found %s versions to validate', pending_draft_versions.count())
    for draft_version in pending_draft_versions:
        validate_version_metadata.delay(draft_version['id'])

        # Revalidation should be triggered every time a version is modified,
        # so now is a good time to write out the manifests as well.
        write_manifest_files.delay(draft_version.id)


def register_scheduled_tasks(sender, **kwargs):
    """Register tasks with a celery beat schedule."""
    # Check for any draft versions that need validation every minute
    sender.add_periodic_task(crontab(), validate_draft_version_metadata.s())
