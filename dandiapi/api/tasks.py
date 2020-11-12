from celery import shared_task
from celery.utils.log import get_task_logger
from django.db.transaction import atomic

from dandiapi.api.models import Validation

logger = get_task_logger(__name__)


@shared_task
@atomic
def validate(validation_id: int) -> None:
    validation: Validation = Validation.objects.get(pk=validation_id)
    # TODO: Verify sha256 checksum
    # TODO: Run dandi-cli validation

    # For now we just wait 10 seconds to simulate some latency
    import time

    time.sleep(10)

    validation.state = Validation.State.SUCCEEDED
    validation.save()
