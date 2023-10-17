from django.conf import settings
import djclick as click
from storages.backends.s3 import S3Storage

from dandiapi.api.models.upload import AssetBlob

BUCKET = settings.DANDI_DANDISETS_BUCKET_NAME


def s3_client():
    storage = S3Storage(bucket_name=BUCKET)
    return storage.connection.meta.client


@click.command()
@click.option('--delete', is_flag=True, default=False)
def cleanup_blobs(delete: bool):
    client = s3_client()
    # Ignore pagination for now, hopefully there aren't enough objects to matter
    objs = client.list_object_versions(Bucket=BUCKET, Prefix='dev/')
    for version in objs['Versions']:
        if not AssetBlob.objects.filter(etag=version['ETag'][1:-1]).exists():
            click.echo(f'Deleting version {version["Key"]}')
            if delete:
                client.delete_object(
                    Bucket=BUCKET, Key=version['Key'], VersionId=version['VersionId']
                )
    for delete_marker in objs['DeleteMarkers']:
        click.echo(f'Deleting delete marker {delete_marker["Key"]}')
        if delete:
            client.delete_object(
                Bucket=BUCKET, Key=delete_marker['Key'], VersionId=delete_marker['VersionId']
            )
