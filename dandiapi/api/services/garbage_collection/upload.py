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
from dandiapi.api.multipart import DandiS3MultipartManager
from dandiapi.zarr.models import ZarrUpload

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from dandiapi.api.models.upload import BaseUpload

logger = get_task_logger(__name__)

UPLOAD_EXPIRATION_TIME = DandiS3MultipartManager._url_expiration  # noqa: SLF001

# The upload models which are garbage collected, all of which represent an in-progress
# multipart upload that has expired.
UPLOAD_MODELS: list[type[BaseUpload]] = [Upload, ZarrUpload]


def get_queryset(model: type[BaseUpload] = Upload) -> QuerySet[BaseUpload]:
    """Get the queryset of uploads of the given model that are eligible for garbage collection."""
    return model.objects.filter(
        created__lt=timezone.now() - UPLOAD_EXPIRATION_TIME,
    )


def garbage_collect() -> int:
    return sum(_garbage_collect_model(model) for model in UPLOAD_MODELS)


def _garbage_collect_model(model: type[BaseUpload]) -> int:
    from . import GARBAGE_COLLECTION_EVENT_CHUNK_SIZE

    qs = get_queryset(model)

    if not qs.exists():
        return 0

    deleted_records = 0
    futures: list[Future] = []

    with transaction.atomic(), ThreadPoolExecutor() as executor:
        event = GarbageCollectionEvent.objects.create(type=model.__name__)
        for uploads_chunk in chunked(qs.iterator(), GARBAGE_COLLECTION_EVENT_CHUNK_SIZE):
            GarbageCollectionEventRecord.objects.bulk_create(
                GarbageCollectionEventRecord(
                    event=event, record=json.loads(serializers.serialize('json', [u]))[0]
                )
                for u in uploads_chunk
            )

            # Release the object store resources held by these uploads. Note that this does
            # not necessarily delete the uploaded object; see `BaseUpload.abort`.
            futures.append(
                executor.submit(
                    lambda chunk: [u.abort() for u in chunk],
                    uploads_chunk,
                )
            )

            deleted_records += model.objects.filter(
                pk__in=[u.pk for u in uploads_chunk],
            ).delete()[0]

        wait(futures)

    return deleted_records
