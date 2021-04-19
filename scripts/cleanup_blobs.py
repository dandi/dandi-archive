from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage

from dandiapi.api.models.upload import AssetBlob

BUCKET = settings.DANDI_DANDISETS_BUCKET_NAME


def s3_client():
    storage = S3Boto3Storage(bucket_name=BUCKET)
    return storage.connection.meta.client


def run(*args):
    # Only delete the objects if the argument "delete" is passed to the script
    delete = len(args) == 1 and args[0] == 'delete'

    client = s3_client()
    # Ignore pagination for now, hopefully there aren't enough objects to matter
    objs = client.list_object_versions(Bucket=BUCKET, Prefix='blobs/')
    print(objs['DeleteMarkers'])
    for delete_marker in objs['Versions']:
        if not AssetBlob.objects.filter(etag=delete_marker['ETag'][1:-1]).exists():
            print(f'Deleting delete marker {delete_marker["Key"]}')
            if delete:
                client.delete_object(
                    Bucket=BUCKET, Key=delete_marker['Key'], VersionId=delete_marker['VersionId']
                )
    for version in objs['Versions']:
        if not AssetBlob.objects.filter(etag=version['ETag'][1:-1]).exists():
            print(f'Deleting version {version["Key"]}')
            if delete:
                client.delete_object(
                    Bucket=BUCKET, Key=version['Key'], VersionId=version['VersionId']
                )
