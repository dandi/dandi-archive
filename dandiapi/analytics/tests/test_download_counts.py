from django.conf import settings
import pytest

from dandiapi.analytics.models import ProcessedS3Log
from dandiapi.analytics.tasks import collect_s3_log_records_task
from dandiapi.api.storage import (
    create_s3_storage,
    get_boto_client,
    get_embargo_storage,
    get_storage,
)


@pytest.fixture
def s3_log_bucket():
    return create_s3_storage(settings.DANDI_DANDISETS_LOG_BUCKET_NAME).bucket_name


@pytest.fixture
def s3_log_file(s3_log_bucket, asset_blob):
    embargoed = s3_log_bucket == settings.DANDI_DANDISETS_EMBARGO_LOG_BUCKET_NAME
    s3 = get_boto_client(get_storage() if not embargoed else get_embargo_storage())

    log_file_name = '2019-02-06-00-00-38-5C5B0E0CA8F2B1B5'
    s3.put_object(
        Bucket=s3_log_bucket,
        Key=log_file_name,
        # this is the minimum necessary structure for s3logparse to successfully parse the log
        Body=' '.join(
            [
                '-',
                '-',
                '[06/Feb/2019:00:00:38 +0000]',
                '-',
                '-',
                '-',
                'REST.GET.OBJECT',
                asset_blob.blob.name,
                '-',
                '200',
            ]
            + ['-'] * 10
        ),
    )

    yield

    s3.delete_object(Bucket=s3_log_bucket, Key=log_file_name)


@pytest.mark.django_db
def test_processing_s3_log_files(s3_log_bucket, s3_log_file, asset_blob):
    collect_s3_log_records_task(s3_log_bucket)
    asset_blob.refresh_from_db()

    assert ProcessedS3Log.objects.count() == 1
    assert asset_blob.download_count == 1


@pytest.mark.django_db
def test_processing_s3_log_files_idempotent(s3_log_bucket, s3_log_file, asset_blob):
    collect_s3_log_records_task(s3_log_bucket)
    # run the task again, it should skip the existing log record
    collect_s3_log_records_task(s3_log_bucket)
    asset_blob.refresh_from_db()

    assert ProcessedS3Log.objects.count() == 1
    assert asset_blob.download_count == 1
