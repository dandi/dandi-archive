from __future__ import annotations

from datetime import timedelta

from celery.utils.log import get_task_logger
from django.db import transaction
from django.utils import timezone

from dandiapi.api.models import GarbageCollectionEvent
from dandiapi.api.multipart import DandiS3MultipartManager
from dandiapi.api.services.garbage_collection import asset_blob, upload

logger = get_task_logger(__name__)

UPLOAD_EXPIRATION_TIME = DandiS3MultipartManager._url_expiration  # noqa: SLF001
ASSET_BLOB_EXPIRATION_TIME = timedelta(days=7)

GARBAGE_COLLECTION_EVENT_CHUNK_SIZE = 1000

# How long to keep GarbageCollectionEvent records around for after the garbage collection
# is performed to allow for restoration of deleted records.
# This should be equal to the time set in the "trailing delete" lifecycle rule.
RESTORATION_WINDOW = timedelta(
    days=30
)  # TODO: pick this up from env var set by Terraform to ensure consistency?


def garbage_collect():
    with transaction.atomic():
        garbage_collected_uploads = upload.garbage_collect()
        garbage_collected_asset_blobs = asset_blob.garbage_collect()

        GarbageCollectionEvent.objects.filter(
            timestamp__lt=timezone.now() - RESTORATION_WINDOW
        ).delete()

    logger.info('Garbage collected %s Uploads.', garbage_collected_uploads)
    logger.info('Garbage collected %s AssetBlobs.', garbage_collected_asset_blobs)
