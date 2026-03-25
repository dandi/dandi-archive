from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, wait
from datetime import timedelta
import json
from typing import TYPE_CHECKING

from celery.utils.log import get_task_logger
from django.core import serializers
from django.db import transaction
from django.utils import timezone
from more_itertools import chunked

from dandiapi.api.models import (
    AssetBlob,
    GarbageCollectionEvent,
    GarbageCollectionEventRecord,
)

if TYPE_CHECKING:
    from django.db.models import QuerySet

logger = get_task_logger(__name__)

ASSET_BLOB_EXPIRATION_TIME = timedelta(days=7)


def get_queryset() -> QuerySet[AssetBlob]:
    """Get the queryset of AssetBlobs that are eligible for garbage collection."""
    return AssetBlob.objects.filter(
        assets__isnull=True,
        created__lt=timezone.now() - ASSET_BLOB_EXPIRATION_TIME,
    )


def garbage_collect() -> int:
    from . import GARBAGE_COLLECTION_EVENT_CHUNK_SIZE

    qs = get_queryset()

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
