from celery import shared_task
from celery.utils.log import get_task_logger
from django.db.transaction import atomic

from dandiapi.api.checksum import calculate_sha256_checksum
from dandiapi.api.models import AssetBlob

logger = get_task_logger(__name__)


@shared_task
@atomic
def calculate_sha256(uuid: int) -> None:
    logger.info('Starting sha256 calculation for blob %s', uuid)
    asset_blob = AssetBlob.objects.get(uuid=uuid)

    sha256 = calculate_sha256_checksum(asset_blob.blob.storage, asset_blob.blob.name)
    logger.info('Calculated sha256 %s', sha256)

    # TODO: Run dandi-cli validation

    logger.info('Saving sha256 %s to blob %s', sha256, uuid)

    asset_blob.sha256 = sha256
    asset_blob.save()
