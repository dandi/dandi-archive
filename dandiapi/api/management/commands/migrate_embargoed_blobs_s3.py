from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, as_completed

from botocore.config import Config
from dandischema.digests.dandietag import PartGenerator, mb
from django.conf import settings
import djclick as click
from tqdm import tqdm

from dandiapi.api.copy import CopyObjectPart, CopyPartResponse, _copy_object_part
from dandiapi.api.models.asset import EmbargoedAssetBlob
from dandiapi.api.storage import get_boto_client

client = get_boto_client(config=Config(max_pool_connections=1000))


def copy_object_single(blob: str, new_blob: str):
    # Bucket is the DESTINATION bucket, Key is the DESTINATION object key
    client.copy_object(
        Bucket=settings.DANDI_DANDISETS_BUCKET_NAME,
        Key=new_blob,
        CopySource={
            'Bucket': settings.DANDI_DANDISETS_EMBARGO_BUCKET_NAME,
            'Key': blob,
        },
        TaggingDirective='REPLACE',
        Tagging='embargoed=true',
    )


def copy_object_multipart(source_key: str, dest_key: str, blob_size: int):
    # Raise error if file is less than 5MB in size
    if blob_size < mb(5):
        raise ValueError('File is too small for multipart copy')

    source_bucket = settings.DANDI_DANDISETS_EMBARGO_BUCKET_NAME
    dest_bucket = settings.DANDI_DANDISETS_BUCKET_NAME

    # Generate parts
    parts = list(PartGenerator.for_file_size(blob_size))

    # Create upload
    upload_id = client.create_multipart_upload(
        Bucket=dest_bucket,
        Key=dest_key,
        ACL='bucket-owner-full-control',
        Tagging='embargoed=true',
    )['UploadId']

    # alternatively use settings.DANDI_MULTIPART_COPY_MAX_WORKERS
    # Perform concurrent copying of object parts
    uploading_parts: list[Future[CopyPartResponse]] = []
    with ThreadPoolExecutor(max_workers=25) as executor:
        for part in parts:
            # Submit part copy for execution in thread pool
            future = executor.submit(
                _copy_object_part,
                client=client,
                object_part=CopyObjectPart(
                    part=part,
                    upload_id=upload_id,
                    copy_source=f'{source_bucket}/{source_key}',
                    dest_bucket=dest_bucket,
                    dest_key=dest_key,
                    include_range=len(parts) > 1,
                ),
            )

            # Store future to extract later
            uploading_parts.append(future)

    # Retrieve results of part uploads. This blocks until all parts are uploaded.
    uploaded_parts = [part.result().as_dict() for part in uploading_parts]

    # Complete the multipart copy
    client.complete_multipart_upload(
        Bucket=dest_bucket,
        Key=dest_key,
        UploadId=upload_id,
        MultipartUpload={'Parts': uploaded_parts},
    )


def copy_object(blob: str, blob_size: int):
    new_blob = '/'.join(blob.split('/')[1:])

    # Try multi-part copy. If this fails due to size constraint, use single part
    try:
        copy_object_multipart(source_key=blob, dest_key=new_blob, blob_size=blob_size)
    except ValueError:
        copy_object_single(blob=blob, new_blob=new_blob)


def is_success(future):
    return future.done() and not future.cancelled() and future.exception() is None


def check_object(*, old_blob: str, old_etag: str, old_size: int):
    blob = '/'.join(old_blob.split('/')[1:])
    resp = client.head_object(Bucket=settings.DANDI_DANDISETS_BUCKET_NAME, Key=blob)

    old_etag = old_etag.strip('"')
    etag = resp['ETag'].strip('"')
    if etag != old_etag:
        raise Exception(f"Etags don't match for blob {blob}: {etag} != {old_etag}")  # noqa: TRY002

    size = resp['ContentLength']
    if size != old_size:
        raise Exception(f"Sizes don't match for blob {blob}: {size} != {old_size}")  # noqa: TRY002

    # Now check for tags
    expected_tags = [{'Key': 'embargoed', 'Value': 'true'}]
    resp = client.get_object_tagging(Bucket=settings.DANDI_DANDISETS_BUCKET_NAME, Key=blob)
    if resp['TagSet'] != expected_tags:
        raise Exception(  # noqa: TRY002
            f"Tag set doesn't match for blob {blob}: {resp['TagSet']} != {expected_tags}"
        )


@click.command()
def copy_embargoed_blobs():
    # Get the current list of all embargoed asset blobs in storage. Order randomly so that size
    # isn't skewed to one side or another, hopefully giving consistent progression
    embargoed_blobs = list(
        EmbargoedAssetBlob.objects.all().order_by('?').values('blob', 'etag', 'size')
    )

    # Use s3 client to copy objects. We would ideally use s3 batch to accomplish this, but we need
    # to remove the dandiset prefix that exists for every object in the embargoed bucket, and it
    # doesn't seem that s3 batch supports that operation.
    click.echo('Copying S3 Objects...')
    with tqdm(total=len(embargoed_blobs)) as pbar, ThreadPoolExecutor(max_workers=40) as e:
        futures = [e.submit(copy_object, blob['blob'], blob['size']) for blob in embargoed_blobs]
        for future in as_completed(futures):
            pbar.update(1)
            future.result()

    # Reaching here means all the thread jobs have finished
    click.echo(click.style(text='All files successfully copied', fg='green'))
    click.echo('Verifying new object integrity...')

    # Check that all files exist in the new bucket with their tags
    with tqdm(total=len(embargoed_blobs)) as pbar, ThreadPoolExecutor(max_workers=100) as e:
        futures = [
            e.submit(
                check_object,
                old_blob=blob['blob'],
                old_etag=blob['etag'],
                old_size=blob['size'],
            )
            for blob in embargoed_blobs
        ]
        for future in as_completed(futures):
            pbar.update(1)
            future.result()

    # Reaching here means all the thread jobs have finished
    click.echo(click.style(text='All objects verified', fg='green'))
