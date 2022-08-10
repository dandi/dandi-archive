from django.db.models.query import QuerySet
import djclick as click

from dandiapi.api.models.zarr import ZarrArchive


@click.command()
def migrate_zarr_checksums(*args, **kwargs):
    """Fill in checksums for all zarrs, following addition of zarr checksum field."""
    qs: QuerySet[ZarrArchive] = ZarrArchive.objects.filter(checksum__isnull=True)

    # Process each zarr with a missing checksum
    for zarr in qs.iterator():
        # Attempt to fetch checksumm from S3
        checksum = zarr.get_checksum()

        # If checksum exists, save
        if checksum is not None:
            zarr.checksum = checksum
            zarr.status = ZarrArchive.Status.COMPLETE
            zarr.save(update_fields=['status', 'checksum'])
