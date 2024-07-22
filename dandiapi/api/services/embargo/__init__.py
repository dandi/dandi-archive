from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import logging
from typing import TYPE_CHECKING

from botocore.config import Config
from django.conf import settings
from django.db import transaction
from more_itertools import chunked

from dandiapi.api.mail import send_dandiset_unembargoed_message
from dandiapi.api.models import AssetBlob, Dandiset, Version
from dandiapi.api.services.asset.exceptions import DandisetOwnerRequiredError
from dandiapi.api.services.exceptions import DandiError
from dandiapi.api.storage import get_boto_client
from dandiapi.api.tasks import unembargo_dandiset_task

from .exceptions import (
    AssetBlobEmbargoedError,
    AssetTagRemovalError,
    DandisetActiveUploadsError,
    DandisetNotEmbargoedError,
)

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from mypy_boto3_s3 import S3Client


logger = logging.getLogger(__name__)
ASSET_BLOB_TAG_REMOVAL_CHUNK_SIZE = 5000


def _delete_asset_blob_tags(client: S3Client, blob: str):
    client.delete_object_tagging(
        Bucket=settings.DANDI_DANDISETS_BUCKET_NAME,
        Key=blob,
    )


# NOTE: In testing this took ~2 minutes for 100,000 files
def _remove_dandiset_asset_blob_embargo_tags(dandiset: Dandiset):
    client = get_boto_client(config=Config(max_pool_connections=100))
    embargoed_asset_blobs = (
        AssetBlob.objects.filter(embargoed=True, assets__versions__dandiset=dandiset)
        .values_list('blob', flat=True)
        .iterator(chunk_size=ASSET_BLOB_TAG_REMOVAL_CHUNK_SIZE)
    )

    # Chunk the blobs so we're never storing a list of all embargoed blobs
    chunks = chunked(embargoed_asset_blobs, ASSET_BLOB_TAG_REMOVAL_CHUNK_SIZE)
    for chunk in chunks:
        with ThreadPoolExecutor(max_workers=100) as e:
            futures = [
                e.submit(_delete_asset_blob_tags, client=client, blob=blob) for blob in chunk
            ]

        # Check if any failed and raise exception if so
        failed = [blob for i, blob in enumerate(chunk) if futures[i].exception() is not None]
        if failed:
            raise AssetTagRemovalError('Some blobs failed to remove tags', blobs=failed)


@transaction.atomic()
def unembargo_dandiset(ds: Dandiset):
    """Unembargo a dandiset by copying all embargoed asset blobs to the public bucket."""
    logger.info('Unembargoing Dandiset %s', ds.identifier)
    logger.info('\t%s assets', ds.draft_version.assets.count())

    if ds.embargo_status != Dandiset.EmbargoStatus.UNEMBARGOING:
        raise DandiError(
            message=f'Expected dandiset state {Dandiset.EmbargoStatus.UNEMBARGOING}, found {ds.embargo_status}',  # noqa: E501
            http_status_code=500,
        )
    if ds.uploads.all().exists():
        raise DandisetActiveUploadsError(http_status_code=500)

    # Remove tags in S3
    logger.info('Removing tags...')
    _remove_dandiset_asset_blob_embargo_tags(ds)

    # Update embargoed flag on asset blobs
    updated = AssetBlob.objects.filter(embargoed=True, assets__versions__dandiset=ds).update(
        embargoed=False
    )
    logger.info('Updated %s asset blobs', updated)

    # Set status to OPEN
    Dandiset.objects.filter(pk=ds.pk).update(embargo_status=Dandiset.EmbargoStatus.OPEN)
    logger.info('Dandiset embargo status updated')

    # Fetch version to ensure changed embargo_status is included
    # Save version to update metadata through populate_metadata
    v = Version.objects.select_for_update().get(dandiset=ds, version='draft')
    v.save()
    logger.info('Version metadata updated')

    # Notify owners of completed unembargo
    send_dandiset_unembargoed_message(ds)
    logger.info('Dandiset owners notified.')

    logger.info('...Done')


def remove_asset_blob_embargoed_tag(asset_blob: AssetBlob) -> None:
    """Remove the embargoed tag of an asset blob."""
    if asset_blob.embargoed:
        raise AssetBlobEmbargoedError

    _delete_asset_blob_tags(client=get_boto_client(), blob=asset_blob.blob.name)


def kickoff_dandiset_unembargo(*, user: User, dandiset: Dandiset):
    """Set dandiset status to kickoff unembargo."""
    if dandiset.embargo_status != Dandiset.EmbargoStatus.EMBARGOED:
        raise DandisetNotEmbargoedError

    if not user.has_perm('owner', dandiset):
        raise DandisetOwnerRequiredError

    if dandiset.uploads.count():
        raise DandisetActiveUploadsError

    with transaction.atomic():
        Dandiset.objects.filter(pk=dandiset.pk).update(
            embargo_status=Dandiset.EmbargoStatus.UNEMBARGOING
        )
        transaction.on_commit(lambda: unembargo_dandiset_task.delay(dandiset.pk))
