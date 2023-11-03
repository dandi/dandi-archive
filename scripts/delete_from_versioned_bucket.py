"""
Delete files from a versioned S3 bucket.

Versioned S3 buckets do not actually delete objects when deleted through any of the normal methods.
Instead, they insert a "delete marker", which is a special version of the object.
An object with a delete marker will not appear in any normal API requests.
To delete objects and delete markers, you need to explicitly delete the version.

This script was the best way I could find to bulk delete objects in an S3 directory.

You will need an AWS CLI profile set up with permission to delete objects from the desired bucket.
See https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-profiles.html
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

import boto3
import click

WARN_THRESHOLD = 1000


def delete_version(bucket, thing):
    key = thing['Key']
    version_id = thing['VersionId']
    click.echo(f'Deleting {bucket.name}/{key} # {version_id}')
    version = bucket.Object(key).Version(version_id)
    version.delete()


@click.command()
@click.option(
    '--profile',
    prompt='AWS profile name',
    help='The AWS profile to use. See https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-profiles.html',  # noqa: E501
)
@click.option('--bucket', prompt='Bucket', help='The bucket to delete from')
@click.option('--prefix', prompt='Path to delete', help='The prefix to delete all files under')
@click.option('--force', is_flag=True, help='Skip confirmation prompts')
@click.option('--threads', prompt='Threads', default=30, help='How many threads to use')
def delete_objects(*, profile: str, bucket: str, prefix: str, force: bool, threads: int):
    session = boto3.Session(profile_name=profile)
    s3 = session.resource('s3')
    bucket = s3.Bucket(bucket)
    response = s3.meta.client.list_object_versions(Bucket=bucket.name, Prefix=prefix)
    delete_markers = response.get('DeleteMarkers', [])
    versions = response.get('Versions', [])
    delete_count = len(delete_markers) + len(versions)
    if delete_count >= WARN_THRESHOLD:
        click.echo('There are more than 1000 objects to delete.')
        click.echo('This operation will continue to fetch objects until they are all deleted.')
    if force or click.confirm(f'Delete {delete_count} objects from {bucket.name}/{prefix}?'):
        while True:
            with ThreadPoolExecutor(max_workers=int(threads)) as executor:
                futures = [
                    executor.submit(delete_version, bucket, delete_marker)
                    for delete_marker in delete_markers
                ]
                futures += [
                    executor.submit(delete_version, bucket, version) for version in versions
                ]
                list(as_completed(futures))
            if 'DeleteMarkers' not in response and 'Versions' not in response:
                click.echo('Done!')
                break
            response = s3.meta.client.list_object_versions(Bucket=bucket.name, Prefix=prefix)
            delete_markers = response.get('DeleteMarkers', [])
            versions = response.get('Versions', [])


if __name__ == '__main__':
    delete_objects()
