from __future__ import annotations

from datetime import timedelta

from celery.utils.log import get_task_logger
from django.core import serializers
from django.db import transaction
from django.utils import timezone

from dandiapi.api.models import AssetBlob, GarbageCollectionEvent, Upload
from dandiapi.api.storage import DandiMultipartMixin

logger = get_task_logger(__name__)

UPLOAD_EXPIRATION_TIME = DandiMultipartMixin._url_expiration
ASSET_BLOB_EXPIRATION_TIME = timedelta(days=7)

# How long to keep GarbageCollectionEvent records around for after the garbage collection is performed
# to allow for restoration of deleted records.
# This should be equal to the time set in the "trailing delete" lifecycle rule.
RESTORATION_WINDOW = timedelta(
    days=30
)  # TODO: pick this up from env var set by Terraform to ensure consistency?


def _garbage_collect_uploads() -> int:
    with transaction.atomic():
        qs = Upload.objects.filter(
            created__lt=timezone.now() - UPLOAD_EXPIRATION_TIME,
        )
        GarbageCollectionEvent.objects.create(record=serializers.serialize('json', qs))
        return qs.delete()[0]


def _garbage_collect_asset_blobs() -> int:
    with transaction.atomic():
        qs = AssetBlob.objects.filter(
            assets__isnull=True,
            created__lt=timezone.now() - ASSET_BLOB_EXPIRATION_TIME,
        )
        GarbageCollectionEvent.objects.create(record=serializers.serialize('json', qs))
        return qs.delete()[0]


def garbage_collect():
    with transaction.atomic():
        garbage_collected_uploads = _garbage_collect_uploads()
        garbage_collected_asset_blobs = _garbage_collect_asset_blobs()

        GarbageCollectionEvent.objects.filter(
            created__lt=timezone.now() - RESTORATION_WINDOW
        ).delete()

        logger.info(f'Garbage collected {garbage_collected_uploads} Uploads.')
        logger.info(f'Garbage collected {garbage_collected_asset_blobs} AssetBlobs.')
