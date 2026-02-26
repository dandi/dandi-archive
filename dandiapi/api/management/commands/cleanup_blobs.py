from __future__ import annotations

from django.core.files.storage import default_storage
import djclick as click

from dandiapi.api.models.upload import AssetBlob


@click.command()
@click.option('--delete', is_flag=True, default=False)
def cleanup_blobs(*, delete: bool):
    client = default_storage.s3_client
    bucket_name = default_storage.bucket_name
    # Ignore pagination for now, hopefully there aren't enough objects to matter
    objs = client.list_object_versions(Bucket=bucket_name, Prefix='dev/')
    for version in objs['Versions']:
        if not AssetBlob.objects.filter(etag=version['ETag'][1:-1]).exists():
            click.echo(f'Deleting version {version["Key"]}')
            if delete:
                client.delete_object(
                    Bucket=bucket_name, Key=version['Key'], VersionId=version['VersionId']
                )
    for delete_marker in objs['DeleteMarkers']:
        click.echo(f'Deleting delete marker {delete_marker["Key"]}')
        if delete:
            client.delete_object(
                Bucket=bucket_name, Key=delete_marker['Key'], VersionId=delete_marker['VersionId']
            )
