from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, wait
from datetime import timedelta
import json

from celery.utils.log import get_task_logger
from django.core import serializers
from django.db import transaction
from django.utils import timezone
from more_itertools import chunked

from dandiapi.api.models import (
    AssetBlob,
    GarbageCollectionEvent,
    GarbageCollectionEventRecord,
    Upload,
)
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
    if not qs.exists():
        return 0

    deleted_records = 0
    futures: list[Future] = []

    with transaction.atomic(), ThreadPoolExecutor() as executor:
        event = GarbageCollectionEvent.objects.create(type=Upload.__name__)
        for uploads_chunk in chunked(qs.iterator(), GARBAGE_COLLECTION_EVENT_CHUNK_SIZE):
            GarbageCollectionEventRecord.objects.bulk_create(
                GarbageCollectionEventRecord(
                    event=event, record=json.loads(serializers.serialize('json', [u]))[0]
                )
                for u in uploads_chunk
            )

            # Delete the blobs from S3
            futures.append(
                executor.submit(
                    lambda chunk: [u.blob.delete(save=False) for u in chunk],
                    uploads_chunk,
                )
            )

            deleted_records += Upload.objects.filter(
                pk__in=[u.pk for u in uploads_chunk],
            ).delete()[0]

        wait(futures)

    return deleted_records


def _garbage_collect_asset_blobs() -> int:
    qs = AssetBlob.objects.filter(
        assets__isnull=True,
        created__lt=timezone.now() - ASSET_BLOB_EXPIRATION_TIME,
    )
    if not qs.exists():
        return 0

    deleted_records = 0
    futures: list[Future] = []

    with transaction.atomic(), ThreadPoolExecutor() as executor:
        event = GarbageCollectionEvent.objects.create(type=AssetBlob.__name__)
        for asset_blobs_chunk in chunked(qs.iterator(), GARBAGE_COLLECTION_EVENT_CHUNK_SIZE):
            GarbageCollectionEventRecord.objects.bulk_create(
                GarbageCollectionEventRecord(
                    event=event, record=json.loads(serializers.serialize('json', [a]))[0]
                )
                for a in asset_blobs_chunk
            )

            # Delete the blobs from S3
            futures.append(
                executor.submit(
                    lambda chunk: [a.blob.delete(save=False) for a in chunk],
                    asset_blobs_chunk,
                )
            )

            deleted_records += AssetBlob.objects.filter(
                pk__in=[a.pk for a in asset_blobs_chunk],
            ).delete()[0]

        wait(futures)

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
