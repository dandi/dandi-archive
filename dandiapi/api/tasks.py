from celery import shared_task
from celery.utils.log import get_task_logger
from django.db.transaction import atomic

from dandiapi.api.checksum import calculate_sha256_checksum
from dandiapi.api.models import AssetBlob, Validation

logger = get_task_logger(__name__)


class ChecksumMismatch(Exception):
    def __init__(self, expected_sha256, actual_sha256):
        self.expected_sha256 = expected_sha256
        self.actual_sha256 = actual_sha256

    def __str__(self):
        return (
            f'Given checksum {self.expected_sha256} did not match '
            f'calculated checksum {self.actual_sha256}.'
        )


@shared_task
@atomic
def validate(validation_id: int) -> None:
    validation: Validation = Validation.objects.get(pk=validation_id)
    logger.info('Starting validation %s', validation.sha256)

    try:
        sha256 = calculate_sha256_checksum(validation.blob.storage, validation.blob.name)
        logger.info('Calculated sha256 %s', sha256)
        if sha256 != validation.sha256:
            raise ChecksumMismatch(validation.sha256, sha256)

        # TODO: Run dandi-cli validation

        logger.info('Saving successful validation %s', validation.sha256)
        validation.state = Validation.State.SUCCEEDED
        validation.error = None
        validation.save()

        logger.info('Copying validated blob to asset storage')
        asset_blob, created = AssetBlob.from_validation(validation)
        if created:
            asset_blob.save()
    except ChecksumMismatch as e:
        logger.info('Checksum mismatch: %s', str(e))
        validation.state = Validation.State.FAILED
        validation.error = str(e)
        validation.save()
    except Exception as e:
        logger.error('Internal error', exc_info=True)
        validation.state = Validation.State.FAILED
        validation.error = f'Internal error: {e}'
        validation.save()
        # TODO: Can celery recover from a task error?
        # raise e
