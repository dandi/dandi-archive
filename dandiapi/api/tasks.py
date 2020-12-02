import hashlib
from urllib.request import urlopen

from celery import shared_task
from celery.utils.log import get_task_logger
from django.db.transaction import atomic

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

    try:
        buffer_size = 4096
        h = hashlib.sha256()

        with urlopen(validation.blob.url) as stream:
            # html = f.read().decode('utf-8')
            buffer = stream.read(buffer_size)
            while buffer != b'':
                h.update(buffer)
                buffer = stream.read(buffer_size)

        sha256 = h.hexdigest()
        logger.info('Calculated sha256 %s', sha256)
        if sha256 != validation.sha256:
            raise ChecksumMismatch(validation.sha256, sha256)

        # TODO: Run dandi-cli validation

        validation.state = Validation.State.SUCCEEDED
        validation.error = None
        validation.save()

        # TODO separate storages for Validations and Assets require a copy at this point
        asset_blob, created = AssetBlob.from_validation(validation)
        if created:
            asset_blob.save()
    except ChecksumMismatch as e:
        logger.info('Checksum mismatch: %s', str(e))
        validation.state = Validation.State.FAILED
        validation.error = str(e)
        validation.save()
    except Exception as e:
        validation.state = Validation.State.FAILED
        validation.error = f'Internal error: {e}'
        validation.save()
        # TODO: Can celery recover from a task error?
        # raise e
