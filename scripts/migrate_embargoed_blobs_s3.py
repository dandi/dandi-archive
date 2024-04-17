#!/usr/bin/env python

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import json

import boto3
from botocore.config import Config
import click
from dandischema.digests.dandietag import Part, PartGenerator
from tqdm import tqdm

client = boto3.client('s3', config=Config(max_pool_connections=1000))


@dataclass
class CopyPartResponse:
    etag: str
    part_number: int

    def as_dict(self):
        return {'ETag': self.etag, 'PartNumber': self.part_number}


@dataclass
class CopyObjectPart:
    # The part itself
    part: Part

    # Upload/Bucket info
    upload_id: str
    copy_source: str
    dest_bucket: str
    dest_key: str

    # Whether or not to include the byte range in the request
    # (excluded for single part copies)
    include_range: bool = True

    @property
    def copy_range(self) -> str | None:
        return (
            # Subtract one due to zero-indexing
            f'bytes={self.part.offset}-{self.part.offset + self.part.size - 1}'
            if self.include_range
            else None
        )


def _copy_object_part(client, object_part: CopyObjectPart) -> CopyPartResponse:
    # Add conditional params
    extra_params = {}
    if object_part.copy_range is not None:
        extra_params['CopySourceRange'] = object_part.copy_range

    # Make copy request
    response = client.upload_part_copy(
        Bucket=object_part.dest_bucket,
        Key=object_part.dest_key,
        UploadId=object_part.upload_id,
        CopySource=object_part.copy_source,
        PartNumber=object_part.part.number,
        **extra_params,
    )

    # Return the ETag & part number
    etag = response['CopyPartResult']['ETag'].strip('"')
    return CopyPartResponse(etag=etag, part_number=object_part.part.number)


def copy_object_single(*, source_bucket: str, blob: str, dest_bucket: str, new_blob: str):
    # Bucket is the DESTINATION bucket, Key is the DESTINATION object key
    client.copy_object(
        Bucket=dest_bucket,
        Key=new_blob,
        CopySource={
            'Bucket': source_bucket,
            'Key': blob,
        },
        TaggingDirective='REPLACE',
        Tagging='embargoed=true',
    )


def copy_object_multipart(
    *, source_bucket: str, source_key: str, dest_bucket: str, dest_key: str, blob_size: int
):
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


def copy_object(blob: str, blob_etag: str, blob_size: int, source_bucket: str, dest_bucket: str):
    new_blob = '/'.join(blob.split('/')[1:])

    try:
        if '-' not in blob_etag:
            copy_object_single(
                source_bucket=source_bucket,
                blob=blob,
                dest_bucket=dest_bucket,
                new_blob=new_blob,
            )
        else:
            copy_object_multipart(
                source_bucket=source_bucket,
                source_key=blob,
                dest_bucket=dest_bucket,
                dest_key=new_blob,
                blob_size=blob_size,
            )

        with open('blobnames.txt', 'a') as f:  # noqa: PTH123
            print(blob, '|', new_blob, file=f)

    except client.exceptions.NoSuchKey:
        with open('missing.txt', 'a') as f:  # noqa: PTH123
            print(blob, file=f)


def is_success(future):
    return future.done() and not future.cancelled() and future.exception() is None


def check_object(
    *, source_bucket: str, dest_bucket: str, old_blob: str, old_etag: str, old_size: int
):
    # First make sure the objects exists in the old bucket. If not, exit without error
    try:
        resp = client.head_object(Bucket=source_bucket, Key=old_blob)
    except client.exceptions.ClientError as e:
        if e.response['Error']['Code'] != '404':
            raise
        return

    # Now check the new object
    blob = '/'.join(old_blob.split('/')[1:])
    resp = client.head_object(Bucket=dest_bucket, Key=blob)

    old_etag = old_etag.strip('"')
    etag = resp['ETag'].strip('"')
    if etag != old_etag:
        raise Exception(f"Etags don't match for blob {blob}: {etag} != {old_etag}")  # noqa: TRY002

    size = resp['ContentLength']
    if size != old_size:
        raise Exception(f"Sizes don't match for blob {blob}: {size} != {old_size}")  # noqa: TRY002

    # Now check for tags
    expected_tags = [{'Key': 'embargoed', 'Value': 'true'}]
    resp = client.get_object_tagging(Bucket=dest_bucket, Key=blob)
    if resp['TagSet'] != expected_tags:
        raise Exception(  # noqa: TRY002
            f"Tag set doesn't match for blob {blob}: {resp['TagSet']} != {expected_tags}"
        )


@click.command()
@click.argument('blobs_file', type=click.STRING)
@click.option('--bucket', 'bucket', type=click.STRING, required=True)
@click.option('--embargoed-bucket', 'embargoed_bucket', type=click.STRING, required=True)
def copy_embargoed_blobs(blobs_file, embargoed_bucket: str, bucket: str):
    with open(blobs_file) as f:  # noqa: PTH123
        embargoed_blobs = json.load(f)

    # Use s3 client to copy objects. We would ideally use s3 batch to accomplish this, but we need
    # to remove the dandiset prefix that exists for every object in the embargoed bucket, and it
    # doesn't seem that s3 batch supports that operation.
    click.echo('Copying S3 Objects...')
    with tqdm(total=len(embargoed_blobs)) as pbar, ThreadPoolExecutor(max_workers=40) as e:
        futures = [
            e.submit(
                copy_object,
                blob=blob['blob'],
                blob_etag=blob['etag'],
                blob_size=blob['size'],
                source_bucket=embargoed_bucket,
                dest_bucket=bucket,
            )
            for blob in embargoed_blobs
        ]
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
                source_bucket=embargoed_bucket,
                dest_bucket=bucket,
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


if __name__ == '__main__':
    copy_embargoed_blobs()
