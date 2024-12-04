from __future__ import annotations

from datetime import timedelta
import json
from uuid import uuid4

from celery.utils.log import get_task_logger
from django.core import serializers
from django.db import transaction
from django.utils import timezone
from more_itertools import chunked

from dandiapi.api.models import AssetBlob, GarbageCollectionEvent, Upload
from dandiapi.api.storage import DandiMultipartMixin

logger = get_task_logger(__name__)

UPLOAD_EXPIRATION_TIME = DandiMultipartMixin._url_expiration  # noqa: SLF001
ASSET_BLOB_EXPIRATION_TIME = timedelta(days=7)

GARBAGE_COLLECTION_EVENT_CHUNK_SIZE = 1000

# How long to keep GarbageCollectionEvent records around for after the garbage collection
# is performed to allow for restoration of deleted records.
# This should be equal to the time set in the "trailing delete" lifecycle rule.
RESTORATION_WINDOW = timedelta(
    days=30
)  # TODO: pick this up from env var set by Terraform to ensure consistency?


def _garbage_collect_uploads() -> int:
    qs = Upload.objects.filter(
        created__lt=timezone.now() - UPLOAD_EXPIRATION_TIME,
    )

    # Chunk the queryset to avoid creating a single
    # GarbageCollectionEvent with a huge JSONField
    gc_event_uuid = uuid4()
    deleted_records = 0
    for uploads_chunk in chunked(qs.iterator(), GARBAGE_COLLECTION_EVENT_CHUNK_SIZE):
        with transaction.atomic():
            GarbageCollectionEvent.objects.create(
                garbage_collection_event_id=gc_event_uuid,
                records=json.loads(serializers.serialize('json', uploads_chunk)),
                type=Upload.__name__,
            )

            # Delete the blobs from S3
            for chunk in uploads_chunk:
                chunk.blob.delete()

            deleted_records += Upload.objects.filter(
                pk__in=[u.pk for u in uploads_chunk],
            ).delete()[0]

    return deleted_records


def _garbage_collect_asset_blobs() -> int:
    qs = AssetBlob.objects.filter(
        assets__isnull=True,
        created__lt=timezone.now() - ASSET_BLOB_EXPIRATION_TIME,
    )

    # Chunk the queryset to avoid creating a single
    # GarbageCollectionEvent with a huge JSONField
    gc_event_uuid = uuid4()
    deleted_records = 0
    for asset_blobs_chunk in chunked(qs.iterator(), GARBAGE_COLLECTION_EVENT_CHUNK_SIZE):
        with transaction.atomic():
            GarbageCollectionEvent.objects.create(
                garbage_collection_event_id=gc_event_uuid,
                records=json.loads(serializers.serialize('json', asset_blobs_chunk)),
                type=AssetBlob.__name__,
            )

            # Delete the blobs from S3
            for chunk in asset_blobs_chunk:
                chunk.blob.delete()

            deleted_records += AssetBlob.objects.filter(
                pk__in=[a.pk for a in asset_blobs_chunk],
            ).delete()[0]

    return deleted_records


def garbage_collect():
    with transaction.atomic():
        garbage_collected_uploads = _garbage_collect_uploads()
        garbage_collected_asset_blobs = _garbage_collect_asset_blobs()

        GarbageCollectionEvent.objects.filter(
            timestamp__lt=timezone.now() - RESTORATION_WINDOW
        ).delete()

    logger.info('Garbage collected %s Uploads.', garbage_collected_uploads)
    logger.info('Garbage collected %s AssetBlobs.', garbage_collected_asset_blobs)
