from collections import Counter
from collections.abc import Generator
from pathlib import Path

from celery.app import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.db import transaction
from django.db.models.aggregates import Max
from django.db.models.expressions import F
from django.db.utils import IntegrityError
from s3logparse import s3logparse

from dandiapi.analytics.models import ProcessedS3Log
from dandiapi.api.models.asset import AssetBlob, EmbargoedAssetBlob
from dandiapi.api.storage import get_boto_client, get_embargo_storage, get_storage

logger = get_task_logger(__name__)

# should be one of the DANDI_DANDISETS_*_LOG_BUCKET_NAME settings
LogBucket = str


def _bucket_objects_after(bucket: str, after: str | None) -> Generator[dict, None, None]:
    if bucket not in {
        settings.DANDI_DANDISETS_LOG_BUCKET_NAME,
        settings.DANDI_DANDISETS_EMBARGO_LOG_BUCKET_NAME,
    }:
        raise ValueError(f'Non-log bucket: {bucket}')
    embargoed = bucket == settings.DANDI_DANDISETS_EMBARGO_LOG_BUCKET_NAME
    s3 = get_boto_client(get_storage() if not embargoed else get_embargo_storage())
    kwargs = {}
    if after:
        kwargs['StartAfter'] = after

    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket, **kwargs):
        yield from page.get('Contents', [])


@shared_task(queue='s3-log-processing', soft_time_limit=60, time_limit=80)
def collect_s3_log_records_task(bucket: LogBucket) -> None:
    """Dispatch a task per S3 log file to process for download counts."""
    if bucket not in {
        settings.DANDI_DANDISETS_LOG_BUCKET_NAME,
        settings.DANDI_DANDISETS_EMBARGO_LOG_BUCKET_NAME,
    }:
        raise RuntimeError
    embargoed = bucket == settings.DANDI_DANDISETS_EMBARGO_LOG_BUCKET_NAME
    after = ProcessedS3Log.objects.filter(embargoed=embargoed).aggregate(last_log=Max('name'))[
        'last_log'
    ]

    for s3_log_object in _bucket_objects_after(bucket, after):
        process_s3_log_file_task.delay(bucket, s3_log_object['Key'])


@shared_task(queue='s3-log-processing', soft_time_limit=120, time_limit=140)
def process_s3_log_file_task(bucket: LogBucket, s3_log_key: str) -> None:
    """
    Process a single S3 log file for download counts.

    Creates a ProcessedS3Log entry and updates the download counts for the relevant
    asset blobs. Prevents duplicate processing with a unique constraint on the ProcessedS3Log name
    and embargoed fields.
    """
    if bucket not in {
        settings.DANDI_DANDISETS_LOG_BUCKET_NAME,
        settings.DANDI_DANDISETS_EMBARGO_LOG_BUCKET_NAME,
    }:
        raise RuntimeError
    embargoed = bucket == settings.DANDI_DANDISETS_EMBARGO_LOG_BUCKET_NAME

    # short circuit if the log file has already been processed. note that this doesn't guarantee
    # exactly once processing, that's what the unique constraint on ProcessedS3Log is for.
    if ProcessedS3Log.objects.filter(name=Path(s3_log_key).name, embargoed=embargoed).exists():
        return

    s3 = get_boto_client(get_storage() if not embargoed else get_embargo_storage())
    BlobModel = AssetBlob if not embargoed else EmbargoedAssetBlob
    data = s3.get_object(Bucket=bucket, Key=s3_log_key)
    download_counts = Counter()

    for log_entry in s3logparse.parse_log_lines(
        line.decode('utf8') for line in data['Body'].iter_lines()
    ):
        if log_entry.operation == 'REST.GET.OBJECT' and log_entry.status_code == 200:
            download_counts.update({log_entry.s3_key: 1})

    with transaction.atomic():
        try:
            log = ProcessedS3Log(name=Path(s3_log_key).name, embargoed=embargoed)
            # disable constraint validation checking so duplicate errors can be detected and
            # ignored. the rest of the full_clean errors should still be raised.
            log.full_clean(validate_constraints=False)
            log.save()
        except IntegrityError as e:
            if 'unique_name_embargoed' in str(e):
                logger.info('Already processed log file %s, embargo: %s', s3_log_key, embargoed)
            return

        # note this task is run serially per log file. this is to avoid the contention between
        # multiple log files trying to update the same blobs. this serialization is enforced through
        # the task queue configuration.
        for blob, download_count in download_counts.items():
            BlobModel.objects.filter(blob=blob).update(
                download_count=F('download_count') + download_count
            )
