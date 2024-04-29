from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from botocore.config import Config
from django.conf import settings
from django.db import transaction

from dandiapi.api.mail import send_dandisets_to_unembargo_message
from dandiapi.api.models import Asset, AssetBlob, Dandiset, Version
from dandiapi.api.services.asset.exceptions import DandisetOwnerRequiredError
from dandiapi.api.storage import get_boto_client

from .exceptions import AssetBlobEmbargoedError, DandisetNotEmbargoedError

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from django.db.models import QuerySet
    from mypy_boto3_s3 import S3Client


def _delete_asset_blob_tags(client: S3Client, blob: str):
    client.delete_object_tagging(
        Bucket=settings.DANDI_DANDISETS_BUCKET_NAME,
        Key=blob,
    )


# NOTE: In testing this took ~2 minutes for 100,000 files
def _remove_dandiset_asset_blob_embargo_tags(dandiset: Dandiset):
    # First we need to generate a CSV manifest containing all asset blobs that need to be untaged
    embargoed_asset_blobs = AssetBlob.objects.filter(
        embargoed=True, assets__versions__dandiset=dandiset
    ).values_list('blob', flat=True)

    client = get_boto_client(config=Config(max_pool_connections=100))
    with ThreadPoolExecutor(max_workers=100) as e:
        for blob in embargoed_asset_blobs:
            e.submit(_delete_asset_blob_tags, client=client, blob=blob)


@transaction.atomic()
def _unembargo_dandiset(dandiset: Dandiset):
    # NOTE: Before proceeding, all asset blobs must have their embargoed tags removed in s3

    draft_version: Version = dandiset.draft_version
    embargoed_assets: QuerySet[Asset] = draft_version.assets.filter(blob__embargoed=True)
    AssetBlob.objects.filter(assets__in=embargoed_assets).update(embargoed=False)

    # Update draft version metadata
    draft_version.metadata['access'] = [
        {'schemaKey': 'AccessRequirements', 'status': 'dandi:OpenAccess'}
    ]
    draft_version.save()

    # Set access on dandiset
    dandiset.embargo_status = Dandiset.EmbargoStatus.OPEN
    dandiset.save()


def remove_asset_blob_embargoed_tag(asset_blob: AssetBlob) -> None:
    """Remove the embargoed tag of an asset blob."""
    if asset_blob.embargoed:
        raise AssetBlobEmbargoedError

    _delete_asset_blob_tags(client=get_boto_client(), blob=asset_blob.blob.name)


def unembargo_dandiset(*, user: User, dandiset: Dandiset):
    """Unembargo a dandiset by copying all embargoed asset blobs to the public bucket."""
    if dandiset.embargo_status != Dandiset.EmbargoStatus.EMBARGOED:
        raise DandisetNotEmbargoedError

    if not user.has_perm('owner', dandiset):
        raise DandisetOwnerRequiredError

    # A scheduled task will pick up any new dandisets with this status and email the admins to
    # initiate the un-embargo process
    dandiset.embargo_status = Dandiset.EmbargoStatus.UNEMBARGOING
    dandiset.save()

    # Send initial email to ensure it's seen in a timely manner
    send_dandisets_to_unembargo_message(dandisets=[dandiset])
