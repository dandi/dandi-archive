from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.db import transaction

from dandiapi.api.models import Asset, AssetBlob, Dandiset, Version
from dandiapi.api.services.asset.exceptions import DandisetOwnerRequiredError
from dandiapi.api.storage import get_boto_client

from .exceptions import AssetBlobEmbargoedError, DandisetNotEmbargoedError

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from django.db.models import QuerySet


def remove_asset_blob_embargoed_tag(asset_blob: AssetBlob) -> None:
    if asset_blob.embargoed:
        raise AssetBlobEmbargoedError

    client = get_boto_client()
    client.delete_object_tagging(
        Bucket=settings.DANDI_DANDISETS_BUCKET_NAME,
        Key=asset_blob.blob.name,
    )


@transaction.atomic()
def _unembargo_dandiset(dandiset: Dandiset):
    # TODO: Remove embargoed tags from objects in s3

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
