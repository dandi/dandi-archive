from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, wait
import json
from typing import TYPE_CHECKING

from celery.utils.log import get_task_logger
from django.core import serializers
from django.db import transaction
from django.utils import timezone
from more_itertools import chunked

from dandiapi.api.models import (
    GarbageCollectionEvent,
    GarbageCollectionEventRecord,
    Upload,
)
from dandiapi.api.storage import DandiMultipartMixin

if TYPE_CHECKING:
    from django.db.models import QuerySet

logger = get_task_logger(__name__)

UPLOAD_EXPIRATION_TIME = DandiMultipartMixin._url_expiration  # noqa: SLF001


def get_queryset() -> QuerySet[Upload]:
    """Get the queryset of Uploads that are eligible for garbage collection."""
    return Upload.objects.filter(
        created__lt=timezone.now() - UPLOAD_EXPIRATION_TIME,
    )


def garbage_collect() -> int:
    from . import GARBAGE_COLLECTION_EVENT_CHUNK_SIZE

    qs = get_queryset()

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
