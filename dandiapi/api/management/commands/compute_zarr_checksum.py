import boto3
import djclick as click

from dandiapi.api.models.zarr import ZarrArchive
from dandiapi.api.zarr_checksums import (
    ZarrChecksum,
    ZarrChecksumFileUpdater,
    ZarrChecksums,
    ZarrChecksumUpdater,
)


class WriteOnlyZarrChecksumFileUpdater(ZarrChecksumFileUpdater):
    def __enter__(self):
        self._checksums = ZarrChecksums()
        return self


def yield_files(client, zarr: ZarrArchive):
    """Get all objects in the bucket, through repeated object listing."""
    continuation_token = None
    common_options = {'Bucket': zarr.storage.bucket_name, 'Prefix': zarr.s3_path('')}
    while True:
        options = {**common_options}
        if continuation_token is not None:
            options['ContinuationToken'] = continuation_token

        # Fetch
        res = client.list_objects_v2(**options)

        # If all files fetched, end
        if res['IsTruncated'] is False or not res['Contents']:
            break

        # Yield this batch of files
        yield [
            ZarrChecksum(
                md5=file['ETag'].strip('"'),
                path=file['Key'].replace(zarr.s3_path(''), ''),
            )
            for file in res['Contents']
        ]

        # Get next continuation token
        continuation_token = res['NextContinuationToken']


@click.command()
@click.argument('zarr_id', type=int)
def compute_zarr_checksum(zarr_id: int):
    client = boto3.client('s3')
    zarr: ZarrArchive = ZarrArchive.objects.get(id=zarr_id)

    # Instantiate updater and add files as they come in
    updater = ZarrChecksumUpdater(zarr_archive=zarr, file_updater=WriteOnlyZarrChecksumFileUpdater)
    for checksums in yield_files(client, zarr):
        updater.update_file_checksums(checksums)
