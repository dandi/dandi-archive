from __future__ import annotations

from datetime import timedelta
import json
from typing import TYPE_CHECKING

from celery.utils.log import get_task_logger
from django.core import serializers
from django.db import transaction
from django.utils import timezone
from more_itertools import chunked

from dandiapi.api.models import (
    Asset,
    GarbageCollectionEvent,
    GarbageCollectionEventRecord,
)

if TYPE_CHECKING:
    from django.db.models import QuerySet

logger = get_task_logger(__name__)

ASSET_EXPIRATION_TIME = timedelta(days=30)


def get_queryset() -> QuerySet[Asset]:
    """Get the queryset of Assets that are eligible for garbage collection."""
    return Asset.objects.filter(
        versions__isnull=True,
        published=False,
        blob__isnull=False,  # only delete assets with blobs; zarrs are not supported yet
        modified__lt=timezone.now() - ASSET_EXPIRATION_TIME,
    )


def garbage_collect() -> int:
    from . import GARBAGE_COLLECTION_EVENT_CHUNK_SIZE

    qs = get_queryset()

    if not qs.exists():
        return 0

    deleted_records = 0

    with transaction.atomic():
        event = GarbageCollectionEvent.objects.create(type=Asset.__name__)
        for assets_chunk in chunked(qs.iterator(), GARBAGE_COLLECTION_EVENT_CHUNK_SIZE):
            GarbageCollectionEventRecord.objects.bulk_create(
                GarbageCollectionEventRecord(
                    event=event, record=json.loads(serializers.serialize('json', [a]))[0]
                )
                for a in assets_chunk
            )

            deleted_records += Asset.objects.filter(
                pk__in=[a.pk for a in assets_chunk],
            ).delete()[0]

    return deleted_records
