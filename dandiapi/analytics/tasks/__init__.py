from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from celery.app import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.db import transaction
from django.db.models.aggregates import Max
from django.db.models.expressions import F
from django.db.utils import IntegrityError
from more_itertools import batched
from s3logparse import s3logparse

from dandiapi.analytics.models import ProcessedS3Log
from dandiapi.api.models.asset import AssetBlob
from dandiapi.api.storage import get_boto_client, get_storage

if TYPE_CHECKING:
    from collections.abc import Generator

logger = get_task_logger(__name__)

# should be one of the DANDI_DANDISETS_*_LOG_BUCKET_NAME settings
LogBucket = str


def _bucket_objects_after(after: str | None) -> Generator[dict, None, None]:
    s3 = get_boto_client(get_storage())
    kwargs = {}
    if after:
        kwargs['StartAfter'] = after

    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=settings.DANDI_DANDISETS_LOG_BUCKET_NAME, **kwargs):
        yield from page.get('Contents', [])


@shared_task(queue='s3-log-processing', soft_time_limit=60, time_limit=80)
def collect_s3_log_records_task() -> None:
    """Dispatch a task per S3 log file to process for download counts."""
    after = ProcessedS3Log.objects.aggregate(last_log=Max('name'))['last_log']

    for s3_log_object in _bucket_objects_after(after):
        process_s3_log_file_task.delay(s3_log_object['Key'])


@shared_task(queue='s3-log-processing', soft_time_limit=120, time_limit=140)
def process_s3_log_file_task(s3_log_key: str) -> None:
    """
    Process a single S3 log file for download counts.

    Creates a ProcessedS3Log entry and updates the download counts for the relevant
    asset blobs. Prevents duplicate processing with a unique constraint on the ProcessedS3Log name.
    """
    # short circuit if the log file has already been processed. note that this doesn't guarantee
    # exactly once processing, that's what the unique constraint on ProcessedS3Log is for.
    if ProcessedS3Log.objects.filter(name=s3_log_key.split('/')[-1]).exists():
        return

    s3 = get_boto_client(get_storage())
    data = s3.get_object(Bucket=settings.DANDI_DANDISETS_LOG_BUCKET_NAME, Key=s3_log_key)
    download_counts = Counter()

    for log_entry in s3logparse.parse_log_lines(
        line.decode('utf8') for line in data['Body'].iter_lines()
    ):
        if log_entry.operation == 'REST.GET.OBJECT' and log_entry.status_code == 200:  # noqa: PLR2004
            download_counts.update({log_entry.s3_key: 1})

    with transaction.atomic():
        try:
            log = ProcessedS3Log(name=s3_log_key.split('/')[-1])
            # disable constraint validation checking so duplicate errors can be detected and
            # ignored. the rest of the full_clean errors should still be raised.
            log.full_clean(validate_constraints=False)
            log.save()
        except IntegrityError as e:
            if '_unique_name' in str(e):
                logger.info('Already processed log file %s', s3_log_key)
            return

        # we need to store all of the fully hydrated blob objects in memory in order to use
        # bulk_update, but this turns out to not be very costly. 1,000 blobs use about ~8kb
        # of memory.
        asset_blobs = []

        # batch the blob queries to avoid a large WHERE IN clause
        for batch in batched(download_counts, 1_000):
            asset_blobs += AssetBlob.objects.filter(blob__in=batch)

        for asset_blob in asset_blobs:
            asset_blob.download_count = F('download_count') + download_counts[asset_blob.blob]

        # note this task is run serially per log file. this is to avoid the contention between
        # multiple log files trying to update the same blobs. this serialization is enforced through
        # the task queue configuration.
        AssetBlob.objects.bulk_update(asset_blobs, ['download_count'], batch_size=1_000)
